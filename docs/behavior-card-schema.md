# Behavior Card Schema v1

The canonical machine form is `schema/behavior-card.schema.json`; `schema/behavior-card.ts` is the TypeScript authoring contract. JSON is canonicalized with sorted keys, compact separators and UTF-8 before SHA-256. `content_hash` itself is excluded from the digest.

## Human-readable form

Renderers should present, in order: title and classification; trigger/failure/invariant; buggy/fixed code; affected symbols; regression tests; evidence links/SHAs; reproducer; applicability; confidence rationale; limitations and license. Human formatting must never change the canonical machine payload.

## Versioning and migrations

- Patch releases clarify validation without changing accepted documents.
- Minor releases add optional fields or evidence kinds and must remain backward-readable.
- Major releases may rename/remove fields. A `migrations/vN_to_vN+1.py` pure function must be shipped, preserve the original card under version control, recompute `content_hash`, and append a migration evidence record.
- Validators reject unknown major versions. They never silently coerce a v0/v1 card.
- Deprecated fields remain readable for at least one minor release and are documented in `CHANGELOG.md`.
- Capsule and Behavior Card versions are independent; a card records the capsule identifier and evidence status rather than embedding executable code.

## Promotion gate

A candidate becomes a Behavior Card only when it has primary HTTPS evidence, source and fixed SHAs, production before/after structure, an affected path/symbol, regression-test evidence, license, classification and explicit limitations. A PR title or LLM explanation alone never passes validation or promotion review.

