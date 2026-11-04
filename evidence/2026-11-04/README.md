# Captured execution evidence

These files contain actual local results, not illustrative output.

- `validation/`: unittest summary and raw output (42 tests).
- `benchmark.json`: 9 controlled runs with real durations and provider identity.
- `index.json`: portable paths to all nine original evidence bundles.
- `benchmark-runs/`: baseline output, candidate tests, patches, snapshots,
  verifier comparisons, runtime digests, event logs and artifact manifests.
- `fresh-replays.json`: a second independent verification of each saved bundle.
- `installed-package-check.json`: installed wheel hash plus real doctor/CLI output.

All repairs are deterministic baseline runs. No live LLM inference, external
benchmark score, GitHub CI run, remote publication or production deployment is
represented. Public fixture oracles were withheld from the proposer interface,
not kept secret from repository readers.

Use paths from `index.json` after moving this directory. Raw execution reports
retain their original paths and timestamps as provenance. Hash manifests and
event chains are consistency checks, not signatures. For behavioral confidence,
rerun the verifier using the corresponding separately trusted fixture oracle.
