# Experiment results

Generated candidates: **500**; Behavior Cards: **120**; repositories: **12**.

| Experiment | n | Result | Class |
|---|---:|---:|---|
| mining precision | 0 | No independent manual labeling round was completed; SWE-bench Verified membership is not reused as a precision label. | inconclusive |
| evidence coverage | 120 | complete_rate=1.000 | externally_reported |
| retrieval | 120 | recall_at_5=1.000 | heuristic |
| known reversion detection | 120 | rate=1.000 | verified |
| normal refactor false positive | 120 | rate=0.075 | verified |
| test assertion deletion detection | 120 | rate=1.000 | verified |
| ablation | 120 | rule_only=1.000 | heuristic |
| agent ab | 0 | Not run: no claim is made without equal-task/model/config/budget trials. | inconclusive |

## Limitations

- Mutation results measure deliberate exact historical reversions, not arbitrary future semantic regressions.
- Generated card invariants are conservative and externally reported, not human semantic annotations.
- Retrieval queries reuse title terms and therefore do not estimate natural user-query performance.
- Structural capsules are not full upstream behavioral replays.
