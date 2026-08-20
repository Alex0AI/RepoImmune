# Research landscape and differentiation

Survey refreshed 2026-08-20. Primary sources are linked inline; retrieved text is treated as untrusted research data.

## Adjacent systems

| System | What it preserves | Mechanical regression check | Historical causal chain | RepoImmune distinction |
|---|---|---:|---:|---|
| [GitHub Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) | Repository facts and user preferences learned during Copilot activity | Limited to fact revalidation | No issue→buggy code→fix→test capsule contract | RepoImmune mines resolved history independently of an agent session and emits executable assets. |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) | Issue-solving evaluation instances | Evaluation harness | Issue/patch/test are benchmark inputs | RepoImmune turns already-fixed tasks into long-lived PR defenses rather than grading a new fix. |
| [SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) | Human-filtered feasible SWE-bench tasks | Reference patch evaluation | Strong external evidence | It is an evidence source, not the product: RepoImmune adds schema, retrieval, repository applicability, patch matching, capsules, CI and MCP. |
| [BugsInPy](https://github.com/soarsmu/BugsInPy) | Reproducible Python buggy/fixed revisions | Test harness | Commit and test metadata | RepoImmune consumes selected metadata without vendoring projects and focuses on future patch immunity. |
| [Defects4J](https://github.com/rjust/defects4j) | Reproducible Java faults | Test infrastructure | Bug/fix revisions and tests | Excellent dataset; RepoImmune's v0.1 execution focus is Python/TypeScript and repository-native prevention. |
| [ast-grep](https://ast-grep.github.io/) | Generic structural search/rules | Yes | No repository bug evidence | RepoImmune can use structural engines but derives each rule from a repository's evidenced failure. |
| [Tree-sitter](https://tree-sitter.github.io/) | Concrete syntax trees | Primitive, not policy | No | Parser substrate; RepoImmune supplies evidence, behavior schema and patch decisions. |
| Git blame | Per-line authorship and commits | No | Partial | RepoImmune connects why, failure behavior, fix, test and invariant. |
| Static analyzers / CodeQL | General query libraries and dataflow | Yes | Usually no repository-specific historical failure | Complementary engine; RepoImmune's rules originate from target history. |
| Test generation tools | Generated inputs/assertions | Yes, when retained | Usually not issue/fix provenance | RepoImmune preserves source provenance and existing regression intent. |

## Novel mechanism

RepoImmune's unit of memory is a signed-by-content Behavior Card plus optional executable capsule. A check is admissible only when it can show: applicable path/symbol, historical buggy and fixed structures, test evidence, commits and URLs, evidence class, and limitations. Candidate mining is intentionally asymmetric: false abstention is preferable to inventing an invariant.

The research hypothesis is not “AST similarity predicts all regressions.” It is narrower and testable: **repository-specific hybrid retrieval (text + symbols + historical buggy AST + protected tests) detects more deliberate historical reintroductions than text-only memory at an acceptable false-positive rate on normal refactors.** The experiment scripts report each component and an ablation rather than a single opaque score.

## Non-claims

- RepoImmune does not prove semantic equivalence.
- A merged PR is not automatically a verified Behavior Card.
- SWE-bench or external test status remains `externally_reported` until replayed under the recorded environment.
- v0.1 does not provide whole-program call-graph soundness.
- No experiment result is statistically significant merely because it appears in the demo; confidence intervals and sample sizes are reported.

