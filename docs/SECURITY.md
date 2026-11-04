# Security and verification threat model

## Supported use

Milestone 1 is a controlled single-host evaluation harness, not a hardened
multi-tenant service. Use reviewed task fixtures in a disposable environment.
The admitted function language is deliberately tiny. Do not relax it for
unreviewed Python, native extensions, package installers or arbitrary builds.

Trusted: host operator, AEL supervisor/verifier code, Python and libseccomp,
kernel, task/oracle authors and local model server configuration. Untrusted:
repository descriptions/tests, model text, patches, worker output, past claims.
An in-process `Proposer` plugin is trusted controller code; third-party plugin
code is not admitted automatically. The Ollama model only returns data.

## Actual controls

| Risk | Control | Boundary/remaining limitation |
|---|---|---|
| Host reads/writes | Worker receives source as data; file opens denied by default-deny seccomp | Python/libseccomp initialization reads trusted runtime files before confinement |
| Secret inheritance | Explicit minimal environment; close all nonstandard descriptors; isolated Python startup | No defense against an already compromised trusted host |
| Network or process escape | No socket, exec, clone/fork, ptrace, kill, mount, io_uring syscalls admitted | Shared kernel; no claim against kernel exploits |
| Resource exhaustion | 192 MiB address space, 2s CPU, 4s wall limit, 32 KiB combined output, 64 KiB input | Restricted workers only; model/controller have separate bounded operations, not tenant quotas |
| Test deletion or source injection | Exact patch path + preimage digest; pure arithmetic AST policy; original tests held by controller | General-purpose source repair unsupported |
| Fabricated completion | Independent process replays tests and compares fresh function results with oracle | Oracle correctness/coverage is trusted; finite tests are not proof for all inputs |
| Public-test overfitting | Oracle withheld from proposer; comparisons performed in verifier, not candidate interpreter | Included fixture oracles are public; no benchmark confidentiality claim |
| Regression | Preserve public test bytes/count; rerun twice; check originally passing oracle cases | Does not detect every possible regression |
| Evidence rewriting | SHA-256 manifest, preimage/oracle binding, hash-linked event chain, fresh replay | Same-host owner can rewrite all artifacts; no signing or remote attestation |
| Consequential actions | Runtime has no push/merge/deploy/spend/access-grant adapter; policy denies unknown actions | Approval UI/service is future work, not implemented |

The test worker loads public test Python only after seccomp confinement. Those
tests can misreport unittest outcomes or monkeypatch their own interpreter;
their claims alone never suffice. The verifier calls only AST-admitted numeric
functions in fresh workers and compares return values outside those workers.
Function syntax excludes calls, imports, attributes, introspection and I/O, so
it cannot rewrite the comparison logic or forge the worker protocol. Admission
and OS restrictions are both required.

The allowlist includes memory management, signals, time, random bytes, standard
pipe I/O and process identity; no file opens. `doctor` must demonstrate blocked
file read/write, socket, fork and exec calls before any supplied test code runs.
Missing libseccomp, unsupported filter loading and failing probes stop execution.
There is no automatic unconfined fallback.

## Production approval contract: proposed

A human approval record should include action ID, actor, repository/destination,
base revision, patch digest, allowed capability, budget, expiry and one-time
nonce. Reject changed diffs, stale revisions, new destinations and replayed
approvals. Research text, model output and memory cannot create approvals.
Never forward cloud credentials or a Docker socket into an agent workspace.

General repositories require disposable rootless containers or microVMs,
read-only baseline mounts, separate evaluator identities, no default egress,
explicit package-proxy access, process/disk quotas, dependency provenance,
secret redaction and adversarial breakout testing. None is implied by the
restricted arithmetic worker.

To report issues, retain a minimal reproduction and contact the maintainer of
`foxcyloxcy/autonomous-ai-engineering-lab`. Do
not publish live secrets or exploitation details in a shared evidence bundle.
