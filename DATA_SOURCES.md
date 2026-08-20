# Data sources

RepoImmune stores generated metadata and minimal patch evidence, not complete third-party repositories.

| Source | Use | License / terms | Regeneration |
|---|---|---|---|
| [SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified) | Human-filtered issue, base SHA, patch, test patch and fail-to-pass metadata | SWE-bench code is MIT; each patch remains subject to its source repository license | `python scripts/build_research_snapshot.py --limit 220` |
| [Astropy PR #12907](https://github.com/astropy/astropy/pull/12907) | Complete vertical-slice Behavior Card and lightweight behavioral capsule | BSD-3-Clause | Card sources are immutable URLs/SHAs; capsule is a new minimal surrogate |
| [BugsInPy](https://github.com/soarsmu/BugsInPy) | Landscape and planned cross-dataset validation | MIT repository metadata; individual projects retain their licenses | Not downloaded in v0.1 |
| [Defects4J](https://github.com/rjust/defects4j) | Landscape and planned Java validation | MIT framework; individual projects retain their licenses | Not downloaded in v0.1 |

Generated records include retrieval time, source URL, repository, SHA when available, evidence classification, and limitations. Dataset text is untrusted: it is length-bounded, JSON-decoded, never evaluated as instructions, and never passed to a shell. Train/test splits are kept from the upstream source; v0.1 experiments are detection/retrieval measurements, not model training.

