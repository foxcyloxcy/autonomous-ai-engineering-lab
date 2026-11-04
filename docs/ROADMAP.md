# Development roadmap

Stages are acceptance-driven. They are not promises that unbuilt features exist.

| Stage | Deliverables | Exit evidence | Status |
|---|---|---|---|
| M0: research/design | Source comparison, architecture, decisions, security model, test strategy | Reviewed primary sources, explicit scope/tradeoffs, reproducible first contract | Written |
| M1: controlled repair | Pure-function fixture workflow, restricted execution, independent oracle, memory/logs, recovery, CLI and CI configuration | All automated tests pass; repeated controlled repairs and fresh replay; source unchanged | Implemented and locally validated; publication in progress |
| M1.1: live local model | Run Ollama proposer with a chosen installed model and bounded config | Actual model/version and prompt recorded; repeated accepted repairs and failure cases; no hidden data in requests | Adapter exists; live inference pending |
| M2: general repository execution | Qualify OpenHands SDK adapter, rootless container/microVM backend, trusted base revisions, dependency preparation | Escape/egress/secret/quota tests; baseline and repaired real-repo tests in isolated workers; no host fallbacks | Proposed |
| M3: durable multi-agent orchestration | Separate research/planning/coding/experiment services; typed contracts; idempotent scheduling, leases, cancellation and crash replay | Fault injection including worker/controller loss; no duplicate consequential effects; role ablation study | Proposed |
| M4: stronger independent evaluation | Separate evaluator identity/storage, signed provenance, trusted external pins, protected tests, pinned SWE-bench subset | Third-party fresh replay; wrong-patch false acceptance measured; regression checks across versions | Proposed |
| M5: research and ML experiments | Curated research sources, registered hypotheses, reproducible data/compute, MLE-bench pilot | Source/data license review, budget approval, repeated experiments and ablations with raw metrics | Proposed |
| M6: evidence-based improvement | Retrieve verified memories; propose policy/prompt changes as reviewable experiments | Held-out improvement under equal budgets with no security/regression failures; human-controlled promotion | Proposed |
| M7: production readiness | AuthN/AuthZ, approvals, tenant isolation, monitoring, backups/restore, retention, supply-chain audit, deployment/rollback | Independent security review, load/failure tests, restore drill, audited approval/replay controls | Proposed |

## Immediate continuation

1. Finish publication to the newly created dedicated repository and verify its
   actual branch head. Do not reuse an unrelated repository as a workaround.
2. Run the configured CI and inspect actual Actions logs; do not label config
   existence as a passing CI run.
3. Install/select a local model and validate live Ollama repair behavior against
   the existing deterministic baseline. Do not silently fall back to baseline
   after model failure.
4. Increase task diversity before enlarging the agent system. Add negative and
   ambiguous tasks with independently written test oracles.
5. Select and qualify a general sandbox backend before admitting broader Python
   or shell syntax; retain this small harness as a regression baseline.

## Preservation rule

Keep the controlled baseline, tests, replay command and evidence contracts
working as new capabilities arrive. Any contract change needs a schema version,
migration notes, replay compatibility decision and regression evidence. New
features never justify deleting tests or accepting self-reported completion.
