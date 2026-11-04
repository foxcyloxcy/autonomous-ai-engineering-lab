# Engineering decisions

Recorded 2026-11-04. Status is explicit; future choices are not installed features.

| ID | Decision | Why and tradeoff | Status |
|---|---|---|---|
| ADR-001 | Python 3.11+ controller with stdlib dataclasses/protocols | Small inspectable surface, no Python runtime dependencies, suitable for evaluation work; distributed schema generation deferred | Implemented |
| ADR-002 | Own the verifier; integrate agent tools behind proposal contracts | A framework's task-completed event must not grant success; an adapter can change without changing acceptance | Implemented contract; OpenHands adapter proposed |
| ADR-003 | Deterministic arithmetic mutation baseline before model claims | Measures harness behavior without API cost, randomness or credentials; does not establish LLM engineering ability | Implemented and exercised |
| ADR-004 | Self-hosted Ollama proposer on loopback | No provider lock-in; schema-validated source only, no tools; needs locally installed model and inference capacity | Adapter tested with fake transport; live inference unverified |
| ADR-005 | Default-deny seccomp, preloaded in-memory source | This environment has no Docker, working namespaces or Landlock. Deny all file opens/process/network operations after initialization; supports only admitted pure numeric functions and stdlib unittest | Implemented and locally exercised; not a general sandbox |
| ADR-006 | Separate verifier process and supervisor-side oracle | Keeps evaluation answers/authority away from proposer and test code; fresh subprocess per input has overhead | Implemented |
| ADR-007 | SQLite + hash-linked JSONL + filesystem artifacts | Self-hostable, transactional, easy replay; no multi-host writers or signed storage guarantees | Implemented |
| ADR-008 | Apache-2.0 for original AEL code; no upstream vendoring | Open contribution path. AI Scientist v1's current custom source license needs separate review before code reuse; benchmark data licenses differ from harness licenses | Implemented license; future dependency review required |
| ADR-009 | No consequential runtime capabilities in first release | A model cannot grant itself push/merge/deployment permissions. Future scoped approval adapter must bind exact action and evidence | Implemented deny policy; approval service proposed |
| ADR-010 | Prefer OpenHands Software Agent SDK for general coding integration | Current SDK exposes agents, events, tools and remote workspaces; reuse execution ecosystem while retaining independent AEL gates | Proposed, not installed |
| ADR-011 | Rootless containers with gVisor or dedicated microVM workers for general repos | Arbitrary builds need writable scratch, processes, dependency supply and stronger tenant separation; a different threat model from pure functions | Proposed; acceptance tests required before selection |
| ADR-012 | Postgres + S3-compatible objects when single-host limits are reached | Separate identities, retention, search and concurrency; avoid operating multiple services before first reproducible repair | Proposed |

No LangGraph, distributed scheduler, vector DB, agent SDK or cloud service is
required by the executable baseline. The explicit state/event contract comes
first; choose an orchestration framework after measuring crash, concurrency
and integration requirements. A future orchestrator must preserve verifier
authority, event provenance and approval boundaries.
