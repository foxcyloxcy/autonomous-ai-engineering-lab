# MVP scope and test strategy

## First executable slice

Accept an original controlled repository with a documented numeric function and
failing unittest. Reproduce the failure, search bounded pure-function changes,
apply a source-only patch to a disposable copy, and produce independently
replayable evaluation evidence. The initial baseline performs deterministic
operator search. This establishes the harness, not general AI competence.

In scope: explicit input schema, source policy, nonempty baseline failure,
restricted subprocess execution, immutable test bytes, bounded proposals,
separate verifier process, withheld numeric cases, preserved passing cases,
event persistence, error recording, abort/retry recovery and evidence replay.

Out of scope: arbitrary repositories/build commands, setup scripts, general
Python syntax, GPU experiments, web research execution, automated PRs,
merges/deployments, confidential hosted grading, distributed agents, self-
modification and production tenancy. Ollama's transport integration exists;
live inference still needs separate evidence.

## Acceptance gates

| Gate | Measured check |
|---|---|
| Isolation available | Worker installs kernel filter and demonstrates all five prohibited operations fail |
| Original bug real | Public test count >0, assertion failures >0, test errors =0 |
| Scoped change | Exact allowed path, valid preimage hash, admitted pure source, nonempty patch |
| Original tests preserved | Task/test bytes identical; same test count in repaired runs |
| Public repair stable | Candidate passes two fresh public-test replays without skips |
| Oracle meaningful | At least one original function result fails the separately supplied oracle |
| Behavioral repair | Every withheld case passes external numeric comparison |
| Regression preservation | Every previously passing withheld case still passes |
| Evidence reproducible | Hash checks/event chain pass; a fresh verifier run passes again |

Numeric comparisons use `rel_tol=1e-12` and `abs_tol=1e-12`; input and expected
output are finite, bounded numbers. Test count and tolerance are explicit
contracts, not approximate natural-language judgments.

## Automated tests

`python3 scripts/validate.py` saves raw unittest output and a JSON summary.
Tests exercise the real restricted subprocesses, full repair flow, independent
verifier and persistent SQLite store. Transport-only model tests are labeled.

- Admission: dangerous syntax, extra files, links, size limits, forbidden
  actions, path traversal and stale preimages.
- Sandbox: real syscall denial, host-secret isolation, file-write denial,
  CPU/wall limits, memory exhaustion, bounded input/output, missing libseccomp,
  zero tests and early process exit.
- Workflow: three complete repairs + fresh replay, budget exhaustion, already
  passing input, provider failure, invalid candidate then recovery, linked retry,
  public-only overfitting, changed tests/oracle/artifacts, manifest traversal.
- Memory: persistence across instances, chain tampering, interrupted-run abort,
  unknown/terminal recovery rejection.
- Model adapter: deterministic request schema, malformed output, unsafe code,
  and evidence that only the public Context fields are exposed.

CI runs the same suite and a one-repeat controlled benchmark on Ubuntu with
Python 3.11 and 3.12. The workflow has read-only repository permissions and no
credentials passed into test workers. CI is configured, **not remotely run**
until GitHub publication succeeds.

## Benchmark methodology

`python3 scripts/benchmark.py --repetitions 3` runs addition, multiplication and
an affine expression three times each. Each run starts from the original broken
fixture, uses identical attempt limits and requires verifier acceptance. This
is `ael-controlled-arithmetic-v1`; it is not SWE-bench or MLE-bench.

| Metric | Definition and first acceptance target |
|---|---|
| Controlled repair rate | Verified runs / all scheduled fixture runs; target 9/9 |
| Incorrect acceptance | Adversarial wrong-patch tests accepted; target 0 |
| Source/test preservation | Any unintended change to admitted input or protected tests; target 0 |
| Escape probes | Prohibited operations that succeed; target 0/5 |
| Reproducibility | Three repeated runs per fixture all verify; target 3/3 each |
| Attempt cost | Record proposal count, including rejected proposals; cap 24 |
| Latency | Record per-run wall time and median with host/Python metadata; no production SLA inferred |
| Model usage | Report provider/model and live inference separately; baseline has zero model calls |

The fixtures are intentionally simple and correlated; 9/9 says the harness
handles its current examples, not that an agent repairs real-world software.
Negative/adversarial test counts should be reported alongside positive rates.

## Future evaluation protocol

Pin framework commit, model/weights/digest, prompt, seed, temperature, source
revision, test revision, task split, dependency image digest and budgets. Keep
development cases separate from held-out acceptance cases. Compare mutation,
single-agent and multi-agent systems under equal wall/token/compute budgets.
Report task success, regression rate, false acceptance, timeout/recovery rate,
latency/cost and confidence intervals across independent tasks. Repeated runs
of the same task are not independent new tasks.

For research experiments, register the hypothesis/metric/baseline first;
preserve raw data and environment; require repetitions and ablations. A
memory-based improvement must beat the previous version on held-out tasks
without violating any regression/security gate. Failed experiments remain
visible. Nothing promotes itself merely because an agent calls it better.
