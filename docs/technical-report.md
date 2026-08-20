# RepoImmune: Evidence-Backed Executable Memory for Repository Regressions

## Abstract

Coding agents can modify software quickly but do not reliably preserve the reasons behind historical defensive code. RepoImmune represents resolved defects as versioned Behavior Cards connecting reports, buggy/fixed revisions, structural code patterns, tests, symbols, invariants, provenance and replay capsules. A hybrid patch checker locates restoration of historical buggy structure and weakening of protected assertions, returning primary evidence rather than an opaque risk score.

## System

The alpha uses a dependency-free Python core. Unified diffs become path/symbol/line facts. Python fragments become normalized AST fingerprints; TypeScript/TSX can use the pinned optional tree-sitter adapter for normalized structure and call extraction, while JavaScript uses deterministic structural tokens. Applicability first scopes matches by historical path, then compares added code with the buggy pattern and deleted code with the fixed pattern. A dual match is critical. Regression-assertion deletion is separately reported. Results serialize to JSON, Markdown, SARIF and static HTML, and the same operations are exposed through a read-only MCP server.

## Evidence discipline

Candidate mining and card promotion are separate. A title/message may nominate a PR, but promotion requires production and test patches, fail-to-pass evidence, source and fixed SHAs, URLs, license and explicit classification. Missing evidence causes abstention. Content hashes cover canonical card payloads. External benchmark execution remains `externally_reported`; a local structural replay is not mislabeled as full upstream behavior.

## Evaluation protocol

The reproducible snapshot uses bounded SWE-bench Verified metadata. Experiments include evidence coverage, title-query Recall@5/MRR, deliberate historical reversions, same-symbol fixed-form refactors, protected assertion deletions and a simple ablation. Mining precision and Agent A/B are reported inconclusive until independent labels and equal-budget trials exist. Exact values are generated in `research/results.json`.

## Threats to validity

Exact reversions favor AST matching and do not represent all future regressions. Same-path negative controls are narrow. Queries reuse title terms. Generated invariants lack human semantic review. Benchmark membership is not an independent mining-precision label. Full upstream environments are expensive and deferred to isolated Actions.

## Conclusion

RepoImmune demonstrates a complete path from one real historical bug to a mechanically explainable future patch block. The central open question is how far repository-specific evidence generalizes beyond exact or near-exact reversions without unacceptable false positives; v0.1 exposes the artifacts needed to study that question rather than claiming it is solved.
