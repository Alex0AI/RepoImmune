# 🛡️ RepoImmune patch check

Checked 1 files against 1 behavior cards.

## CRITICAL: Nested compound models must preserve the right-hand separability matrix

`astropy/modeling/separable.py:245` — This patch removes the historical fix and restores the old buggy AST structure.

```
        cright[-right.shape[0]:, -right.shape[1]:] = 1
```

Source evidence: [source](https://github.com/astropy/astropy/issues/12906), [source](https://github.com/astropy/astropy/pull/12907), [source](https://github.com/astropy/astropy/commit/738068e5d397490e4b1565b026a95301dc1cddec), [source](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified)

