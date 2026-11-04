"""Trusted one-shot worker. Installs seccomp BEFORE executing supplied code.

Invoked by the supervisor with Python -I -S -B. This file must be standalone.
No repository paths, credentials, oracle answers, or writable files are passed.
"""

import ctypes
import errno
import io
import json
import math
import os
import resource
import sys
import types
import unittest


def confine():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (192 * 1024**2, 192 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    # libseccomp uses a default-deny filter. No open/openat, sockets, exec,
    # fork/clone, ptrace, kill, io_uring, mount or filesystem mutation syscalls.
    lib = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0):  # PR_SET_NO_NEW_PRIVS
        raise OSError("no_new_privs unavailable")
    ctx = lib.seccomp_init(0x00050000 | errno.EPERM)  # SCMP_ACT_ERRNO
    if not ctx:
        raise OSError("seccomp_init failed")
    try:
        for name in ("read", "write", "close", "fstat", "lseek",
                     "mmap", "mprotect", "munmap", "mremap", "brk", "madvise",
                     "rt_sigaction", "rt_sigprocmask", "rt_sigreturn", "sigaltstack",
                     "futex", "clock_gettime", "gettimeofday", "getrusage",
                     "getpid", "gettid", "getrandom", "exit", "exit_group"):
            nr = lib.seccomp_syscall_resolve_name(name.encode())
            if nr < 0 or lib.seccomp_rule_add(ctx, 0x7FFF0000, nr, 0):
                raise OSError(f"seccomp rule failed: {name}")
        if lib.seccomp_load(ctx):
            raise OSError("seccomp_load failed")
    finally:
        lib.seccomp_release(ctx)


def probe():
    checks = {}
    for name, action in {
        "filesystem_read": lambda: os.open("/etc/passwd", os.O_RDONLY),
        "filesystem_write": lambda: os.open("/tmp/ael-forbidden", os.O_WRONLY | os.O_CREAT, 0o600),
        "network": lambda: socket.socket(),
        "process": lambda: os.fork(),
        "exec": lambda: os.execve("/usr/bin/true", ["true"], {}),
    }.items():
        try:
            action()
            checks[name] = False
        except PermissionError:
            checks[name] = True
    return checks


def main():
    # Read bounded protocol before confinement; stdin is at EOF afterwards.
    request = json.loads(sys.stdin.buffer.read(65537))
    if request["mode"] == "probe":
        global socket
        import socket
    confine()  # Any exception aborts the worker; no unsafe fallback exists.
    if request["mode"] == "probe":
        result = {"blocked": probe()}
    else:
        module = types.ModuleType("math_ops")
        exec(compile(request["source"], "math_ops.py", "exec"), module.__dict__)
        sys.modules["math_ops"] = module
        if request["mode"] == "call":
            value = getattr(module, request["function"])(*request["args"])
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("non-finite/non-numeric result")
            result = {"value": value}
        elif request["mode"] == "test":
            namespace = {"__name__": "ael_public_tests"}
            exec(compile(request["tests"], "test_math_ops.py", "exec"), namespace)
            suite = unittest.TestSuite()
            for obj in namespace.values():
                if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(obj))
            capture = io.StringIO()
            tested = unittest.TextTestRunner(stream=capture, verbosity=2).run(suite)
            result = {"tests": tested.testsRun, "failures": len(tested.failures),
                      "errors": len(tested.errors), "skipped": len(tested.skipped),
                      "passed": tested.wasSuccessful() and tested.testsRun > 0 and not tested.skipped,
                      "output": capture.getvalue()[:16000]}
        else:
            raise ValueError("unsupported mode")
    sys.stdout.write(json.dumps({"sandbox": "seccomp-default-deny-v1", "result": result}, allow_nan=False))


if __name__ == "__main__":
    main()
