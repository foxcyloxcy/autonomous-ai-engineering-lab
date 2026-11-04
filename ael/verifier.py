"""Independent verifier: does not import the proposer or accept its verdict.

Run by a separate supervisor process. Only validated pure source is called;
oracle answers stay here and are never sent to the candidate worker.
"""

import json
import math
from pathlib import Path
import sys

from .policy import PolicyError, canonical, digest, load_task, validate_cases, validate_source
from .sandbox import Sandbox, SandboxError


def load_oracle(path: Path, function: str, arity: int) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
        raise PolicyError("invalid oracle file")
    oracle = json.loads(path.read_text())
    if (set(oracle) != {"schema_version", "function", "cases"}
            or oracle["schema_version"] != 1 or oracle["function"] != function):
        raise PolicyError("oracle contract mismatch")
    validate_cases(oracle["cases"], arity)
    return oracle


def verify(original: Path, candidate: Path, oracle_path: Path, expected: dict) -> dict:
    spec, before = load_task(original)
    after_spec, after = load_task(candidate)
    # Expected digests bind the independent verifier to the admitted input,
    # the supervisor-approved proposal, and the externally held oracle.
    actual = {"original": {k: digest(v.encode()) for k, v in before.items()},
              "candidate": {k: digest(v.encode()) for k, v in after.items()},
              "oracle": digest(oracle_path.read_bytes())}
    if actual != expected:
        raise PolicyError("snapshot/oracle digest mismatch")
    if after_spec != spec or any(before[k] != after[k] for k in before if k != "math_ops.py"):
        raise PolicyError("protected tests/task changed")
    if before["math_ops.py"] == after["math_ops.py"]:
        raise PolicyError("empty patch")
    tree = validate_source(after["math_ops.py"], spec["function"])
    oracle = load_oracle(oracle_path, spec["function"], len(tree.body[0].args.args))
    sandbox = Sandbox()
    preflight = sandbox.preflight()
    baseline = sandbox.test(before["math_ops.py"], before["test_math_ops.py"])
    repaired = [sandbox.test(after["math_ops.py"], before["test_math_ops.py"]) for _ in range(2)]
    baseline_result = baseline["result"]
    valid_baseline = baseline_result["tests"] > 0 and baseline_result["failures"] > 0 and baseline_result["errors"] == 0
    public_ok = all(x["result"]["passed"] and x["result"]["tests"] == baseline_result["tests"] for x in repaired)
    comparisons = []
    for case in oracle["cases"]:
        values = []
        for files in (before, after):
            try:
                evidence = sandbox.call(files["math_ops.py"], spec["function"], case["args"])
                value = evidence["result"]["value"]
                ok = type(value) in (int, float) and math.isclose(value, case["expected"], rel_tol=1e-12, abs_tol=1e-12)
                values.append({"value": value, "passed": ok, "execution": evidence})
            except SandboxError as exc:
                values.append({"passed": False, "error": str(exc)})
        comparisons.append({"args": case["args"], "expected": case["expected"], "before": values[0], "after": values[1]})
    hidden_ok = all(c["after"]["passed"] for c in comparisons)
    oracle_detects_bug = any(not c["before"]["passed"] for c in comparisons)
    preserved = all(c["after"]["passed"] for c in comparisons if c["before"]["passed"])
    passed = valid_baseline and public_ok and hidden_ok and oracle_detects_bug and preserved
    return {"schema_version": 1, "status": "verified" if passed else "rejected",
            "verifier": "ael-independent-process-v1", "inputs": actual,
            "sandbox_preflight": preflight, "baseline": baseline, "public_replays": repaired,
            "oracle_checks": comparisons,
            "gates": {"baseline_fails": valid_baseline, "public_replays_pass": public_ok,
                      "oracle_detects_original_bug": oracle_detects_bug, "oracle_passes": hidden_ok,
                      "passing_cases_preserved": preserved}}


def main():
    # File paths originate in the trusted supervisor, not a repository manifest.
    original, candidate, oracle, binding = map(Path, sys.argv[1:])
    try:
        report = verify(original, candidate, oracle, json.loads(binding.read_text()))
    except Exception as exc:
        report = {"schema_version": 1, "status": "rejected", "error": f"{type(exc).__name__}: {exc}"}
    print(canonical(report).decode())
    return 0 if report["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
