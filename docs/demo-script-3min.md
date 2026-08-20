# Three-minute demo script

**0:00–0:25 — Problem**  
“Coding agents are fast, but each session starts with amnesia. They can delete a strange-looking condition without knowing it was added after a production incident. Chat memory can describe the past; it cannot mechanically stop the old code from returning.”

**0:25–0:55 — Product**  
“RepoImmune mines resolved history into Behavior Cards: report, buggy commit, failing behavior, fix, regression test, AST change, symbol and invariant. Every claim carries primary URLs, SHAs, license, confidence class and limitations.” Show the evidence graph.

**0:55–1:35 — Real vertical slice**  
“Astropy issue #12906 showed nested model outputs becoming falsely coupled. PR #12907 changed one assignment from scalar `1` to the computed right-hand matrix and added four pytest configurations. Here is the card and the exact historical structures.” Show buggy/fix diff and tests.

**1:35–2:10 — Block a regression**  
Run `repoimmune check --diff examples/reintroduce-astropy-12907.diff --memory examples/memory`. “The checker sees the fixed AST being removed and the old buggy AST restored at line 245. It labels this critical and links the Issue, PR, merge and tests. It can emit SARIF and GitHub file annotations.”

**2:10–2:35 — Replay and agents**  
Run `repoimmune replay astropy-12907 --memory examples/memory`. “The isolated capsule reproduces the buggy failure and fixed pass without Docker. MCP lets Codex, OpenCode or Gemini query the same structured evidence before editing and before completion.”

**2:35–3:00 — Honesty and invitation**  
“This alpha proves the vertical slice, not universal semantic regression detection. Dataset cards remain externally reported; structural capsules are labeled heuristic; mining precision and Agent A/B are inconclusive until independently run. The project is Apache-2.0, offline-first and designed for contributors to add evidence sources and stronger language adapters.”

