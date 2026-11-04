import dataclasses
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from ael.agents import Context, MutationProposer, OllamaProposer, Proposal
from ael.cli import main
from ael.memory import Memory, check_events
from ael.policy import PolicyError, authorize, digest, load_task, validate_source
from ael.sandbox import Sandbox, SandboxError
from ael.verifier import verify
from ael.workflow import apply_proposal, bindings, check_bundle, replay, run_workflow

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "addition"
SOURCE = (FIXTURE / "repo/math_ops.py").read_text()
PATCH = "def combine(a, b):\n    return a + b\n"


class Temporary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def copy_repo(self):
        return Path(shutil.copytree(FIXTURE / "repo", self.path / "repo"))


class PolicyTests(Temporary):
    def test_admits_pure_numeric_functions(self):
        validate_source("def f(a,b):\n return (a+b)*2/-3\n", "f")

    def test_denies_dangerous_python(self):
        cases = [
            "import os\ndef f(a): return a", "def f(a): return __import__('os')",
            "def f(a): return a.__class__", "def f(a): return f(a)",
            "def f(a): return [a]", "def f(a): return a**10000000",
            "def f(a): return 'hi'", "def f(a): return True",
            "def f(a):\n while True: pass", "def f(a=x()): return a",
            "@bad\ndef f(a): return a", "def f(a: x()): return a",
            "def f(a): return unknown", "def f(a): return 10000000000000",
        ]
        for source in cases:
            with self.subTest(source=source), self.assertRaises(PolicyError):
                validate_source(source, "f")

    def test_extra_files_denied(self):
        repo = self.copy_repo()
        (repo / "setup.py").write_text("raise SystemExit()")
        with self.assertRaises(PolicyError):
            load_task(repo)

    def test_symlink_denied(self):
        repo = self.copy_repo()
        target = self.path / "outside.py"
        target.write_text(SOURCE)
        (repo / "math_ops.py").unlink()
        (repo / "math_ops.py").symlink_to(target)
        with self.assertRaises(PolicyError):
            load_task(repo)

    def test_oversized_input_denied(self):
        repo = self.copy_repo()
        (repo / "math_ops.py").write_text(" " * 17000)
        with self.assertRaises(PolicyError):
            load_task(repo)

    def test_consequential_actions_denied(self):
        for action in ("merge", "push", "deploy", "delete", "network", "grant_access", "install_dependencies"):
            with self.subTest(action=action), self.assertRaises(PolicyError):
                authorize(action)

    def test_test_tampering_proposal_denied(self):
        _, files = load_task(FIXTURE / "repo")
        proposal = Proposal("test_math_ops.py", digest(files["test_math_ops.py"].encode()), "", "erase failures", "evil")
        with self.assertRaises(PolicyError):
            apply_proposal(files, proposal, "combine")

    def test_path_traversal_proposal_denied(self):
        _, files = load_task(FIXTURE / "repo")
        for name in ("../math_ops.py", "/tmp/math_ops.py", ".github/workflows/ci.yml"):
            with self.subTest(name=name), self.assertRaises(PolicyError):
                apply_proposal(files, Proposal(name, "", PATCH, "", "evil"), "combine")

    def test_stale_preimage_denied(self):
        _, files = load_task(FIXTURE / "repo")
        with self.assertRaises(PolicyError):
            apply_proposal(files, Proposal("math_ops.py", "stale", PATCH, "", "x"), "combine")


class SandboxTests(Temporary):
    def test_real_syscall_confinement(self):
        self.assertTrue(all(Sandbox().preflight()["result"]["blocked"].values()))

    def test_arithmetic_runs(self):
        self.assertEqual(Sandbox().call(PATCH, "combine", [1.5, -2])["result"]["value"], -0.5)

    def test_actual_unittest_failure(self):
        tests = (FIXTURE / "repo/test_math_ops.py").read_text()
        result = Sandbox().test(SOURCE, tests)["result"]
        self.assertEqual(result["tests"], 3)
        self.assertEqual(result["failures"], 2)
        self.assertIn("AssertionError", result["output"])

    def test_environment_has_no_host_secret(self):
        os.environ["AEL_TEST_SENTINEL_SECRET"] = "never-forward-me"
        self.addCleanup(os.environ.pop, "AEL_TEST_SENTINEL_SECRET", None)
        tests = "import unittest, os\nclass T(unittest.TestCase):\n def test_env(self): self.assertNotIn('AEL_TEST_SENTINEL_SECRET',os.environ)"
        self.assertTrue(Sandbox().test(PATCH, tests)["result"]["passed"])

    def test_read_of_host_secret_denied(self):
        sentinel = self.path / "secret"
        sentinel.write_text("private")
        tests = f"import unittest\nclass T(unittest.TestCase):\n def test_read(self):\n  with self.assertRaises(PermissionError): open({str(sentinel)!r}).read()"
        self.assertTrue(Sandbox().test(PATCH, tests)["result"]["passed"])

    def test_write_denied(self):
        target = self.path / "forbidden"
        tests = f"import unittest\nclass T(unittest.TestCase):\n def test_write(self):\n  with self.assertRaises(PermissionError): open({str(target)!r}, 'w')"
        self.assertTrue(Sandbox().test(PATCH, tests)["result"]["passed"])
        self.assertFalse(target.exists())

    def test_wall_clock_timeout(self):
        with self.assertRaisesRegex(SandboxError, "timeout"):
            Sandbox(timeout=0.3).test(PATCH, "while True: pass")

    def test_memory_exhaustion_fails(self):
        with self.assertRaisesRegex(SandboxError, "worker exit"):
            Sandbox().test(PATCH, "a = bytearray(512*1024*1024)")

    def test_output_is_bounded(self):
        with self.assertRaisesRegex(SandboxError, "output budget"):
            Sandbox().test(PATCH, "print('x'*100000)")

    def test_no_tests_does_not_pass(self):
        self.assertFalse(Sandbox().test(PATCH, "")["result"]["passed"])

    def test_process_exit_cannot_claim_success(self):
        with self.assertRaises(SandboxError):
            Sandbox().test(PATCH, "import os\nos._exit(0)")

    def test_input_is_bounded(self):
        with self.assertRaisesRegex(SandboxError, "input budget"):
            Sandbox().run({"mode": "test", "tests": " " * 70000})

    def test_zero_deadline_stops_execution(self):
        with self.assertRaises(SandboxError):
            Sandbox(timeout=0).call(PATCH, "combine", [1, 2])

    def test_missing_seccomp_library_aborts_worker(self):
        code = (f"import sys; sys.path.insert(0,{str(ROOT)!r}); "
                "from ael import worker; "
                "worker.ctypes.CDLL=lambda *a,**k: (_ for _ in ()).throw(OSError('unavailable')); "
                "worker.confine(); print('UNSAFE_EXECUTION')")
        child = subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, timeout=5)
        self.assertNotEqual(child.returncode, 0)
        self.assertNotIn(b"UNSAFE_EXECUTION", child.stdout)


class WorkflowTests(Temporary):
    def test_three_real_repairs_and_independent_replay(self):
        for name in ("addition", "product", "affine"):
            fixture = ROOT / "fixtures" / name
            original = {p.name: p.read_bytes() for p in (fixture / "repo").iterdir()}
            result = run_workflow(fixture / "repo", fixture / "oracle.json", self.path / name)
            self.assertEqual(result["status"], "verified", result)
            bundle = Path(result["artifact_path"])
            report = replay(bundle, fixture / "oracle.json")["verification"]
            self.assertEqual(report["status"], "verified", report)
            self.assertTrue(all(report["gates"].values()))
            self.assertEqual(original, {p.name: p.read_bytes() for p in (fixture / "repo").iterdir()})

    def test_budget_exhaustion_rejects_and_logs(self):
        fixture = ROOT / "fixtures/product"
        result = run_workflow(fixture / "repo", fixture / "oracle.json", self.path, max_attempts=1)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["attempts"], 1)
        self.assertGreater(check_bundle(Path(result["artifact_path"]))["event_chain"]["events"], 0)

    def test_passing_baseline_is_not_a_repair(self):
        repo = self.copy_repo()
        (repo / "math_ops.py").write_text(PATCH)
        result = run_workflow(repo, FIXTURE / "oracle.json", self.path / "runs")
        self.assertEqual(result["status"], "failed")
        self.assertIn("baseline", result["reason"])

    def test_wrong_candidate_rejected_by_withheld_cases(self):
        repo = self.copy_repo()
        (repo / "test_math_ops.py").write_text("import unittest\nfrom math_ops import combine\nclass T(unittest.TestCase):\n def test_add(self): self.assertEqual(combine(2,3),5)\n")
        class Constant:
            name = "claims-success"
            def propose(self, context):
                yield Proposal("math_ops.py", digest(context.source.encode()),
                               "def combine(a,b):\n return 5\n", "Everything is completed!", self.name)
        result = run_workflow(repo, FIXTURE / "oracle.json", self.path / "runs", Constant())
        self.assertEqual(result["status"], "rejected", result)
        report = json.loads((Path(result["artifact_path"]) / "verification.json").read_text())
        self.assertTrue(report["gates"]["public_replays_pass"])
        self.assertFalse(report["gates"]["oracle_passes"])

    def test_invalid_proposal_recovers_to_next_attempt(self):
        class Recovery:
            name = "adversarial-then-good"
            def propose(self, context):
                yield Proposal("test_math_ops.py", "", "", "delete tests", self.name)
                yield Proposal("math_ops.py", digest(context.source.encode()), PATCH, "fix", self.name)
        result = run_workflow(FIXTURE / "repo", FIXTURE / "oracle.json", self.path, Recovery())
        self.assertEqual(result["status"], "verified", result)
        self.assertEqual(result["attempts"], 2)
        first = json.loads((Path(result["artifact_path"]) / "attempts/001.json").read_text())
        self.assertIn("error", first)

    def test_provider_exception_persists_failure(self):
        class Broken:
            name = "broken"
            def propose(self, context):
                raise ConnectionError("local model offline")
        result = run_workflow(FIXTURE / "repo", FIXTURE / "oracle.json", self.path, Broken())
        self.assertEqual(result["status"], "failed")
        check_bundle(Path(result["artifact_path"]))

    def test_artifact_tampering_detected(self):
        result = run_workflow(FIXTURE / "repo", FIXTURE / "oracle.json", self.path)
        bundle = Path(result["artifact_path"])
        (bundle / "candidate/math_ops.py").write_text(SOURCE)
        with self.assertRaisesRegex(PolicyError, "integrity"):
            replay(bundle, FIXTURE / "oracle.json")

    def test_oracle_change_detected(self):
        result = run_workflow(FIXTURE / "repo", FIXTURE / "oracle.json", self.path / "runs")
        oracle = self.path / "different.json"
        oracle.write_text((FIXTURE / "oracle.json").read_text() + "\n")
        report = replay(Path(result["artifact_path"]), oracle)["verification"]
        self.assertEqual(report["status"], "rejected")
        self.assertIn("digest mismatch", report["error"])

    def test_protected_test_change_rejected_even_with_new_binding(self):
        result = run_workflow(FIXTURE / "repo", FIXTURE / "oracle.json", self.path)
        bundle = Path(result["artifact_path"])
        (bundle / "candidate/test_math_ops.py").write_text("pass")
        _, before = load_task(bundle / "original")
        _, after = load_task(bundle / "candidate")
        with self.assertRaisesRegex(PolicyError, "protected"):
            verify(bundle / "original", bundle / "candidate", FIXTURE / "oracle.json", bindings(before, after, FIXTURE / "oracle.json"))

    def test_output_cannot_be_inside_input(self):
        repo = self.copy_repo()
        with self.assertRaises(PolicyError):
            run_workflow(repo, FIXTURE / "oracle.json", repo / "runs")

    def test_retry_links_unsuccessful_run(self):
        fixture = ROOT / "fixtures/product"
        failed = run_workflow(fixture / "repo", fixture / "oracle.json", self.path, max_attempts=1)
        retried = run_workflow(fixture / "repo", fixture / "oracle.json", self.path, retry_of=failed["run_id"])
        self.assertEqual(retried["status"], "verified", retried)
        with self.assertRaises(ValueError):
            run_workflow(fixture / "repo", fixture / "oracle.json", self.path, retry_of=retried["run_id"])

    def test_manifest_path_traversal_rejected(self):
        result = run_workflow(FIXTURE / "repo", FIXTURE / "oracle.json", self.path / "runs")
        bundle = Path(result["artifact_path"])
        manifest = json.loads((bundle / "manifest.json").read_text())
        manifest["sha256"]["../escape"] = "anything"
        (bundle / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(PolicyError):
            check_bundle(bundle)


class MemoryTests(Temporary):
    def test_persistent_events_and_hash_tampering(self):
        memory = Memory(self.path / "memory.sqlite3")
        memory.create("r1", "test", self.path)
        memory.event("r1", "admitted", {"x": 1})
        memory.event("r1", "planned", {})
        log = self.path / "events.jsonl"
        Memory(memory.path).export("r1", log)
        self.assertEqual(check_events(log)["events"], 2)
        rows = log.read_text().splitlines()
        first = json.loads(rows[0])
        first["event"]["data"]["x"] = 2
        log.write_text(json.dumps(first) + "\n" + rows[1] + "\n")
        with self.assertRaisesRegex(ValueError, "integrity"):
            check_events(log)

    def test_recover_interrupted_run(self):
        memory = Memory(self.path / "memory.sqlite3")
        memory.create("r1", "test", self.path)
        memory.event("r1", "verification_started", {})
        Memory(memory.path).recover("r1")
        with memory.connect() as db:
            self.assertEqual(db.execute("SELECT status FROM runs").fetchone()[0], "aborted")
        with self.assertRaises(ValueError):
            memory.recover("r1")

    def test_unknown_recovery_rejected(self):
        with self.assertRaises(ValueError):
            Memory(self.path / "db.sqlite3").recover("missing")


class ProposerTests(unittest.TestCase):
    def context(self):
        spec, files = load_task(FIXTURE / "repo")
        return Context(spec, files["math_ops.py"], files["test_math_ops.py"], {"failure": "known"})

    def test_mutation_is_deterministic(self):
        context = self.context()
        self.assertEqual(list(MutationProposer().propose(context)), list(MutationProposer().propose(context)))

    def test_local_model_transport_contract(self):
        sent = []
        def fake(payload):
            sent.append(payload)
            return {"message": {"content": json.dumps({"replacement": PATCH, "rationale": "fix subtraction"})}}
        context = self.context()
        proposal = list(OllamaProposer("test-model", transport=fake).propose(context))[0]
        self.assertEqual(proposal.replacement, PATCH)
        self.assertNotIn("oracle", json.dumps(sent))
        self.assertEqual({f.name for f in dataclasses.fields(context)}, {"task", "source", "public_tests", "baseline"})

    def test_model_cannot_inject_shell(self):
        fake = lambda payload: {"message": {"content": json.dumps({"replacement": "import os\nos.system('echo bad')", "rationale": "override"})}}
        with self.assertRaises(PolicyError):
            list(OllamaProposer("test", transport=fake).propose(self.context()))

    def test_malformed_model_response(self):
        for content in ("not-json", json.dumps({"replacement": PATCH, "rationale": "ok", "completed": True})):
            with self.subTest(content=content), self.assertRaises(ValueError):
                list(OllamaProposer("test", transport=lambda payload: {"message": {"content": content}}).propose(self.context()))


if __name__ == "__main__":
    unittest.main()
