"""Parent-side sandbox supervisor with bounded pipes and wall-clock budget."""

import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

from .policy import canonical


class SandboxError(RuntimeError):
    pass


class Sandbox:
    def __init__(self, timeout: float = 4, output_limit: int = 32768):
        self.timeout = timeout
        self.output_limit = output_limit

    def run(self, request: dict) -> dict:
        payload = canonical(request)
        if len(payload) > 65536:
            raise SandboxError("input budget exceeded")
        worker = Path(__file__).with_name("worker.py").resolve()
        started = time.monotonic()
        proc = subprocess.Popen(
            [sys.executable, "-I", "-S", "-B", str(worker)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd="/", env={"LANG": "C.UTF-8"}, close_fds=True, start_new_session=True,
        )
        out = bytearray()
        err = bytearray()
        try:
            # Input <=64 KiB; worker drains it before running any supplied code.
            proc.stdin.write(payload)
            proc.stdin.close()
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ, out)
                selector.register(proc.stderr, selectors.EVENT_READ, err)
                while selector.get_map():
                    remaining = self.timeout - (time.monotonic() - started)
                    if remaining <= 0:
                        raise SandboxError("wall-clock timeout")
                    for key, _ in selector.select(min(remaining, 0.05)):
                        chunk = os.read(key.fd, 4096)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        else:
                            key.data.extend(chunk)
                            if len(out) + len(err) > self.output_limit:
                                raise SandboxError("output budget exceeded")
            proc.wait(timeout=max(0.01, self.timeout - (time.monotonic() - started)))
            if proc.returncode:
                raise SandboxError(f"worker exit {proc.returncode}: {err.decode(errors='replace')[-1000:]}")
            try:
                result = json.loads(out)
            except (ValueError, UnicodeDecodeError) as exc:
                raise SandboxError("invalid worker protocol") from exc
            if result.get("sandbox") != "seccomp-default-deny-v1" or "result" not in result:
                raise SandboxError("missing sandbox protocol")
            return {"result": result["result"], "duration_seconds": time.monotonic() - started,
                    "exit_code": proc.returncode, "sandbox": result["sandbox"]}
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            for pipe in (proc.stdin, proc.stdout, proc.stderr):
                pipe.close()

    def preflight(self) -> dict:
        result = self.run({"mode": "probe"})
        blocked = result["result"].get("blocked", {})
        if set(blocked) != {"filesystem_read", "filesystem_write", "network", "process", "exec"} or not all(blocked.values()):
            raise SandboxError("confinement probe failed")
        return result

    def test(self, source: str, tests: str) -> dict:
        return self.run({"mode": "test", "source": source, "tests": tests})

    def call(self, source: str, function: str, args: list) -> dict:
        return self.run({"mode": "call", "source": source, "function": function, "args": args})
