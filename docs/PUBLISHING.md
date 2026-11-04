# Dedicated GitHub repository publication

Repository: https://github.com/foxcyloxcy/autonomous-ai-engineering-lab

The user created this public repository on 2026-11-04. The connected GitHub
capabilities confirmed its owner, write access, empty contents and absence of
branches before initialization. The first README commit is
`e2700a131f2a33fb47d374192e60eec1092492b9`.

The initial implementation was prepared and locally validated at source commit
`c8c2d04916fd559f82973b9361e6eefbcbea7ddc`; the original downloadable handoff
retains that local history. Publication uses GitHub tree/commit operations
against the new repository, followed by a non-force update of its `main` branch.
No unrelated repository is used or modified.

## Publication checks

1. Transfer the prepared source, fixtures, documentation, workflow and curated
   real execution evidence. Preserve the existing branch history.
2. Confirm the resulting remote branch SHA and full file tree.
3. Inspect GitHub Actions runs for that exact commit, then the individual jobs
   and logs. Workflow configuration alone is not a passing CI result.
4. Record actual results in STATUS.md and retain CI evidence if available.

Runtime databases, credentials, environment files, build caches and unrelated
files are excluded. New CI failures must be fixed with evidence; never remove
or weaken verification gates just to publish a green badge.

## Local checkout after publication

```bash
git clone https://github.com/foxcyloxcy/autonomous-ai-engineering-lab.git
cd autonomous-ai-engineering-lab
python3 -m ael doctor
python3 scripts/validate.py
```

Live local-model runs, branch protections, releases and production deployment
remain separate follow-up work. Consult STATUS.md for observed remote CI state.
