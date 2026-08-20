# RepoImmune Research Snapshot — Data Card

## Purpose

This small, cleaned snapshot tests whether evidence-backed historical structures can be retrieved and detected in deliberate patch reversions. It is not a training corpus and must not be used to claim general semantic regression detection.

## Composition

`scripts/build_research_snapshot.py` requests at most 220 SWE-bench Verified rows, retains bounded candidate metadata, and promotes at most 120 records only when a production patch, test patch, fail-to-pass tests, base SHA and merged PR SHA exist. It spans the repositories returned in `snapshot.json`. Thirty optional capsules replay the patch-line distinction only; they are `heuristic`, not upstream execution.

## Provenance and licenses

Each record stores its SWE-bench source, original GitHub PR and base commit, retrieval time, and repository license detected through GitHub's license API. Original patch fragments retain their upstream licenses. No complete third-party repository is distributed.

## Processing

No LLM is used. Titles are length-bounded untrusted text. Buggy/fixed lines come directly from deleted/added production patch lines. Test names come from `FAIL_TO_PASS`. Generic invariants are intentionally conservative. Records missing any required evidence are skipped.

## Splits and leakage

The source test split is preserved. RepoImmune trains no model. Retrieval experiments query the same snapshot and clearly disclose that title terms are reused; this makes them plumbing tests, not a claim of unseen-query generalization.

## Sensitive data

Only public repository metadata is included. The generator does not retain author email, comments, secrets or full Issue bodies.

## Known limitations

See `results.json`. Most cards are `externally_reported`; only the hand-curated Astropy vertical slice has a locally verified behavioral surrogate. Generated capsules compare structural patch lines, not complete program behavior. No independent manual mining-precision labeling or controlled Agent A/B experiment was completed in v0.1.

