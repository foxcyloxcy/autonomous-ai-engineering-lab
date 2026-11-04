# Autonomous AI Engineering Lab (AEL)

An open-source project building toward autonomous engineering whose work can
be independently checked. **Current release: a tested, controlled repair
harness, not a production autonomous engineer.**

The first workflow accepts a small Python repository with a known failing
unittest, generates bounded patch proposals, applies a proposal to a run-local
copy, runs tests under OS restrictions, and asks an independent verifier process
to replay the original failure and evaluate the repaired function against
withheld cases. Only that verifier can produce a `verified` result.

## Current scope

- Deterministic AST operator repair baseline; three included test repositories.
- Optional Ollama proposer with strict response validation. Its adapter has
  transport tests; **no live model run has been validated**.
- Linux libseccomp default-deny workers, with no file opens, networking, child
  processes or executable launches after trusted initialization.
- Immutable-by-contract public tests, source preimage checks, fresh verification,
  two public-test replays, and supervisor-side numeric oracle comparisons.
- Transactional SQLite project/run history, hash-linked JSONL logs, bounded
  attempts, interruption recovery, patch diffs and replayable evidence bundles.
- Automated adversarial and integration tests, benchmark scripts and CI config.

The agents are typed role boundaries in a sequential controller today. Concurrent
LLM agents, general repository support, external research tools, training,
self-improvement and production deployment are future work. See
[status](docs/STATUS.md) for the exact evidence and limitations.

## Run locally

Requires Python 3.11+ on Linux with `libseccomp.so.2` and permission to install a
seccomp filter. On Debian/Ubuntu the OS package is `libseccomp2`. The Python
runtime has no third-party package dependencies. No API key is required for the
baseline; no model is downloaded automatically.

From this repository's root:

```bash
python3 -m ael doctor
python3 scripts/validate.py
python3 -m ael run --repo fixtures/addition/repo --oracle fixtures/addition/oracle.json --output runs/demo
```

The command prints the run's `artifact_path`. Use that exact directory to
verify again; substitute it for `RUN_DIRECTORY` below:

```bash
python3 -m ael verify RUN_DIRECTORY --oracle fixtures/addition/oracle.json
python3 scripts/benchmark.py --repetitions 3
```

`run` and `verify` return nonzero on rejection or execution failure. Read
`verification.json`, `baseline.json`, `patch.diff`, `events.jsonl`, `runtime.json`
and `manifest.json` in the run directory. A digest manifest establishes content
consistency; it is not a signature or remote attestation. Re-execution against
an independently trusted oracle is the meaningful behavioral check.

For a local Ollama instance with a model already installed:

```bash
python3 -m ael run --repo fixtures/addition/repo --oracle fixtures/addition/oracle.json --output runs/model --provider ollama --model YOUR_LOCAL_MODEL
```

Only `127.0.0.1:11434` is contacted by that proposer. No oracle answers are sent.
The model cannot execute tools or claim completion. Live inference needs its own
validation; transport mocks are not evidence of model capability.

## Controlled input contract

The admitted directory contains exactly `task.json`, `math_ops.py`, and
`test_math_ops.py`; fixtures demonstrate the format. The source must define one
pure numeric function of 1–4 positional arguments and a single return expression
using numeric constants and `+`, `-`, `*`, `/`. Imports, calls, attributes,
loops, decorators, annotations, defaults, filesystem links and extra files are
rejected. The oracle is a separate supervisor-owned JSON file; examples keep it
outside the test repository. Included fixture oracles are publicly inspectable,
so this is withholding from the proposer, not a confidential benchmark service.

This narrow contract makes the verification boundary inspectable. Do not point
this version at arbitrary repositories, package managers or production systems.

## Recovery

Ordinary bad proposals and sandbox failures are recorded and the next candidate
can be attempted within the budget. A killed controller leaves its last stage
in SQLite. After confirming it is no longer running:

```bash
python3 -m ael recover --memory runs/demo/memory.sqlite3 --run-id INTERRUPTED_RUN_ID
python3 -m ael run --repo fixtures/addition/repo --oracle fixtures/addition/oracle.json --output runs/demo --retry-of INTERRUPTED_RUN_ID
```

Recovery aborts the old run; retry replays from pristine input with a new run ID.
There is no automatic mid-command resume or retry of consequential actions.

## Design and development

- [Research and comparison](docs/RESEARCH.md)
- [Architecture and component contracts](docs/ARCHITECTURE.md)
- [Technology decisions](docs/DECISIONS.md)
- [MVP scope, tests and benchmark methodology](docs/TEST_STRATEGY.md)
- [Threat model and approval boundary](docs/SECURITY.md)
- [Current progress and evidence](docs/STATUS.md)
- [Development roadmap](docs/ROADMAP.md)
- [GitHub publication](docs/PUBLISHING.md)

License: Apache-2.0. Upstream implementations were researched, not vendored.
