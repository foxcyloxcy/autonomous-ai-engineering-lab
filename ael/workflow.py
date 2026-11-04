"""Bounded repair workflow. Only the independent verifier can grant verified."""

from dataclasses import asdict
import difflib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import uuid

from .agents import Context, MutationProposer, Proposal, Proposer
from .memory import Memory, check_events
from .policy import PolicyError, authorize, canonical, digest, load_task, validate_source
from .sandbox import Sandbox
from .verifier import load_oracle


def write_json(path: Path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temp, path)


def snapshot(path: Path, files: dict[str, str]):
    path.mkdir()
    for name, data in files.items():
        (path / name).write_text(data)


def apply_proposal(files: dict, proposal: Proposal, function: str) -> dict:
    authorize("patch_run_copy")
    if proposal.path != "math_ops.py":
        raise PolicyError("only math_ops.py can be patched")
    if digest(files[proposal.path].encode()) != proposal.before_sha256:
        raise PolicyError("stale patch preimage")
    validate_source(proposal.replacement, function)
    if proposal.replacement == files[proposal.path]:
        raise PolicyError("empty proposal")
    return {**files, proposal.path: proposal.replacement}


def bindings(before: dict, after: dict, oracle: Path):
    return {"original": {k: digest(v.encode()) for k, v in before.items()},
            "candidate": {k: digest(v.encode()) for k, v in after.items()},
            "oracle": digest(oracle.read_bytes())}


def independent_verify(run: Path, oracle: Path) -> dict:
    # -I/-S discard environment Python paths, startup hooks, and site packages.
    # The only added path is the installed AEL package, never a target repository.
    package_root = str(Path(__file__).resolve().parent.parent)
    bootstrap = f"import sys; sys.path.insert(0, {package_root!r}); from ael.verifier import main; raise SystemExit(main())"
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", bootstrap,
         str(run / "original"), str(run / "candidate"), str(oracle), str(run / "binding.json")],
        cwd="/", env={"LANG": "C.UTF-8"}, capture_output=True, timeout=60, close_fds=True,
    )
    report = json.loads(completed.stdout)
    if completed.returncode not in (0, 1) or (completed.returncode == 0) != (report.get("status") == "verified"):
        raise PolicyError("independent verifier exit/report mismatch")
    return report


def seal(run: Path):
    files = {}
    for path in sorted(run.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files[path.relative_to(run).as_posix()] = digest(path.read_bytes())
    write_json(run / "manifest.json", {"schema_version": 1, "sha256": files})


def check_bundle(run: Path) -> dict:
    manifest = json.loads((run / "manifest.json").read_text())
    entries = manifest["sha256"]
    required = {"result.json", "events.jsonl", "original/math_ops.py", "original/test_math_ops.py", "original/task.json"}
    if not required.issubset(entries):
        raise PolicyError("incomplete evidence bundle")
    for name, expected in entries.items():
        relative = PurePosixPath(name)
        path = run / name
        if (relative.is_absolute() or ".." in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(run.resolve()) or not path.is_file()
                or digest(path.read_bytes()) != expected):
            raise PolicyError(f"artifact integrity failure: {name}")
    chain = check_events(run / "events.jsonl")
    result = json.loads((run / "result.json").read_text())
    if chain["run_id"] != result["run_id"]:
        raise PolicyError("event/result run mismatch")
    return {"files": len(entries), "event_chain": chain}


def replay(run: Path, oracle: Path) -> dict:
    integrity = check_bundle(run)
    report = independent_verify(run.resolve(), oracle.resolve())
    return {"integrity": integrity, "verification": report}


def run_workflow(repo: Path, oracle: Path, output_root: Path, proposer: Proposer | None = None,
                 max_attempts: int = 24, retry_of: str | None = None) -> dict:
    if not 1 <= max_attempts <= 24:
        raise PolicyError("attempt budget must be 1..24")
    authorize("read_controlled_repo")
    spec, files = load_task(repo)
    fn = validate_source(files["math_ops.py"], spec["function"]).body[0]
    oracle = oracle.resolve()
    # Supervisor validates oracle; it is intentionally absent from Context.
    load_oracle(oracle, spec["function"], len(fn.args.args))
    output_root = output_root.resolve()
    if output_root == repo.resolve() or output_root.is_relative_to(repo.resolve()):
        raise PolicyError("output must be outside controlled repository")
    output_root.mkdir(parents=True, exist_ok=True)
    memory = Memory(output_root / "memory.sqlite3")
    if retry_of:
        memory.validate_retry(retry_of, spec["task_id"])
    run_id = uuid.uuid4().hex
    run = output_root / run_id
    run.mkdir(mode=0o700)
    memory.create(run_id, spec["task_id"], run)
    proposer = proposer or MutationProposer()
    started = time.monotonic()
    result = {"schema_version": 1, "run_id": run_id, "task_id": spec["task_id"],
              "provider": proposer.name, "status": "failed", "attempts": 0, "artifact_path": str(run)}
    try:
        memory.event(run_id, "admitted", {"task": spec, "retry_of": retry_of,
                      "max_attempts": max_attempts, "source_sha256": digest(files["math_ops.py"].encode())})
        snapshot(run / "original", files)
        runtime = {p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}
        write_json(run / "runtime.json", {"python": sys.version, "ael_source_sha256": runtime})
        preflight = Sandbox().preflight()
        write_json(run / "sandbox.json", preflight)
        memory.event(run_id, "sandbox_ready", preflight)
        baseline = Sandbox().test(files["math_ops.py"], files["test_math_ops.py"])
        write_json(run / "baseline.json", baseline)
        if baseline["result"]["tests"] == 0 or baseline["result"]["failures"] == 0 or baseline["result"]["errors"]:
            raise PolicyError("baseline must reproduce at least one assertion failure without errors")
        memory.event(run_id, "baseline_failed", baseline)
        context = Context(spec, files["math_ops.py"], files["test_math_ops.py"], baseline)
        plan = {"analysis": "Known assertion failure reproduced. Search bounded source-only repairs; tests are immutable.",
                "steps": ["propose", "validate policy/preimage", "test isolated candidate", "independent replay and oracle"],
                "provider": proposer.name, "approval": "artifact-only; consequential capabilities absent"}
        write_json(run / "plan.json", plan)
        memory.event(run_id, "planned", plan)
        attempts_dir = run / "attempts"
        attempts_dir.mkdir()
        selected = None
        for proposal in proposer.propose(context):
            if result["attempts"] >= max_attempts:
                break
            result["attempts"] += 1
            attempt = {"index": result["attempts"], "proposal": asdict(proposal)}
            try:
                candidate = apply_proposal(files, proposal, spec["function"])
                tested = Sandbox().test(candidate["math_ops.py"], files["test_math_ops.py"])
                attempt["test"] = tested
                if tested["result"]["passed"] and tested["result"]["tests"] == baseline["result"]["tests"]:
                    selected = (proposal, candidate)
            except Exception as exc:
                attempt["error"] = f"{type(exc).__name__}: {exc}"
            write_json(attempts_dir / f"{result['attempts']:03d}.json", attempt)
            memory.event(run_id, "experiment", attempt)
            if selected:
                break
        if selected is None:
            result.update(status="rejected", reason="no admitted candidate passed public tests within budget")
        else:
            proposal, candidate = selected
            snapshot(run / "candidate", candidate)
            write_json(run / "proposal.json", asdict(proposal))
            write_json(run / "binding.json", bindings(files, candidate, oracle))
            (run / "patch.diff").write_text("".join(difflib.unified_diff(
                files["math_ops.py"].splitlines(keepends=True), candidate["math_ops.py"].splitlines(keepends=True),
                fromfile="a/math_ops.py", tofile="b/math_ops.py")))
            memory.event(run_id, "verification_started", {"proposal_sha256": digest(canonical(asdict(proposal)))})
            report = independent_verify(run, oracle)
            write_json(run / "verification.json", report)
            result.update(status=report["status"], verification_report="verification.json")
    except Exception as exc:
        result.update(status="failed", reason=f"{type(exc).__name__}: {exc}")
    finally:
        result["duration_seconds"] = time.monotonic() - started
        memory.event(run_id, result["status"], {"reason": result.get("reason"), "attempts": result["attempts"]})
        write_json(run / "result.json", result)
        memory.export(run_id, run / "events.jsonl")
        seal(run)
    return result
