# Contributing

Start with AGENTS.md and docs/STATUS.md. Use a dedicated branch and a controlled
test environment. Do not execute arbitrary task repositories on your host.

Run `python3 scripts/validate.py` for every code change. Changes to repair,
policy, sandbox or verification behavior also need the controlled benchmark
and adversarial regression evidence. Keep original fixtures working and report
tests actually run, including skipped/unverified environments.

Pull requests should describe the concrete behavior change, evidence, scope
limits and any new capability. New runtime capabilities require explicit
threat-model and approval-contract review. A failing gate must be fixed or
reported; deleting or weakening it to pass is not an acceptable repair.

Keep model-generated proposals and execution observations separate. A model's
confidence, summary or `completed` message never establishes correctness.
