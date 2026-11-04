# Current research and engineering comparison

Research date: **2026-11-04 (Asia/Manila)**. Primary repository documentation,
license files and commit metadata were inspected. This is a source/design
comparison, not a reproduced performance study. No upstream benchmark suite or
agent framework was executed in this milestone. Pinned repository heads are in
[research-sources.json](research-sources.json); links below identify inspected
sources. Findings inform AEL decisions rather than imply code reuse.

## Comparison

| Approach | What it provides | Fit for AEL | Decision and limitations |
|---|---|---|---|
| [Sakana AI Scientist v1](https://github.com/SakanaAI/AI-Scientist/tree/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb) | Idea generation, coded experiments, paper generation and review around scientific templates | Research/experiment lifecycle reference | Study patterns; do not vendor it. Templates and scientific writeups do not establish general issue repair. Its README calls for restricting generated-code execution and web access. |
| [AI Scientist v2](https://github.com/SakanaAI/AI-Scientist-v2) | Agentic tree-search approach to automated research | Candidate search and experiment history reference | Design reference, not installed or reproduced. Resource requirements and scientific review differ from AEL's first repair task. |
| [AI Scientist v3 / Agentic Scientist](https://github.com/SakanaAI/AI-Scientist-v3) | Coding-agent orchestration, baselines, ablations, final evaluation and run directories | Strong current reference for separating investigation from final scoring | Design reference. Its documented broad agent permissions and credential forwarding are unsuitable as AEL defaults. No v3 code was copied. |
| [OpenHands](https://github.com/OpenHands/OpenHands) and [Software Agent SDK](https://github.com/OpenHands/software-agent-sdk/tree/c76d30534b549616266ea737fdbffb2803561dc9) | Current application is Agent Canvas; SDK holds agents, tools, conversations, workspaces/events and agent server | Preferred future coding-agent adapter; reuse rather than rebuild a full terminal agent | Keep AEL's acceptance service separate. Local workspace mode does not satisfy arbitrary-code isolation; evaluate remote/container workspaces. Not installed yet. |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench/tree/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e) | Real issue-to-patch evaluation with Docker-based reproducibility | Engineering evaluation methodology and later external task set | Adopt baseline/candidate separation and regression checks. A tiny arithmetic fixture score is not a SWE-bench result. Pin task/data/harness versions before future runs. |
| [MLE-bench](https://github.com/openai/mle-bench/tree/507f92e1138bb6e40dac5c6ee7a6758e6424bf97) | ML engineering tasks with submission grading and agent-agnostic evaluation | Later experimentation track; compare artifacts with separately held answers | Defer costly data/GPU work. README records paused new leaderboard submissions and known task issues; version results and audit graders rather than infer comparability from leaderboard ranks. |

## License findings affecting reuse

| Inspected code | License finding | AEL consequence |
|---|---|---|
| [AI Scientist v1 LICENSE](https://github.com/SakanaAI/AI-Scientist/blob/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb/LICENSE) | Custom AI Scientist Source Code License, December 2025, based on a Responsible AI license; includes use/distribution restrictions | Do not describe this version as permissively licensed or copy it into AEL under Apache-2.0. Seek appropriate review before reuse. |
| [Software Agent SDK LICENSE](https://github.com/OpenHands/software-agent-sdk/blob/c76d30534b549616266ea737fdbffb2803561dc9/LICENSE) | MIT | Candidate reusable dependency with notices; audit each ecosystem component separately. |
| [SWE-bench LICENSE](https://github.com/SWE-bench/SWE-bench/blob/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e/LICENSE) | MIT harness code | Separately inspect task repository/data licensing before redistributing benchmark material. |
| [MLE-bench LICENSE](https://github.com/openai/mle-bench/blob/507f92e1138bb6e40dac5c6ee7a6758e6424bf97/LICENSE) | MIT code; explicitly excludes downloaded external datasets/files | Dataset access/licensing must be handled per competition; do not bundle downloaded data automatically. |

AEL contains original code and small original fixtures. Upstream license
observations are engineering dependency considerations, not a legal opinion.

## Recommended approach

Build the evidence/control plane first, then attach proven coding agents.
The first executable baseline should be narrow enough to audit: known failed
tests, a source-only patch, no host credentials, bounded execution, a separate
oracle, and reproducible output. This establishes whether the harness detects
wrong repairs before asking a stronger model to produce them.

After that foundation, integrate the OpenHands SDK behind the `Proposer`
contract and qualify a general sandbox backend. Keep research/planning agents
read-only; give coding/experiment agents scoped workspace operations; reserve
completion authority and withheld answers for the evaluator. Compare a single
agent to multiple roles under identical budgets before assuming additional
agents improve performance. Any memory-driven policy change should face a
held-out regression suite before promotion.

External evaluation should progress from original synthetic fixtures, to a
pinned small SWE-bench subset, to larger engineering tasks, then selected
MLE-bench tasks after data/compute review. Research capability should use
predeclared metrics, baselines, repeated seeds and ablations; writing a report
is not evidence of a successful experiment.

## Supporting implementation references

- [OpenHands SDK architecture](https://github.com/OpenHands/docs/blob/main/sdk/arch/overview.mdx)
- [AI Scientist v1 README](https://github.com/SakanaAI/AI-Scientist/blob/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb/README.md)
- [Agentic Scientist v3 README](https://github.com/SakanaAI/AI-Scientist-v3/blob/main/README.md)
- [MLE-bench grading and known issues](https://github.com/openai/mle-bench/blob/507f92e1138bb6e40dac5c6ee7a6758e6424bf97/README.md)
- [SWE-bench Docker evaluation](https://github.com/SWE-bench/SWE-bench/blob/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e/README.md)
- [Linux Landlock documentation](https://docs.kernel.org/userspace-api/landlock.html): probed here and unavailable, so not used
- [libseccomp rule API](https://man7.org/linux/man-pages/man3/seccomp_rule_add.3.html)
- [Ollama chat API](https://docs.ollama.com/api/chat)

Mutable links for v2/v3 and service documentation are discovery references,
not pinned runtime dependencies. Refresh and pin them before integration.
