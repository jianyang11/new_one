# Phase-B CWRU Pool Quality Smoke

| method | class | n | pass rate | band L1 | PSD W1 mean | PSD W1 p90 | env prom mean | NN syn-real mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| rule_smoke_v5 | healthy | 13 | 1.000 | 0.0772 | 29.290 | 40.161 |  | 0.116 |
| rule_smoke_v5 | IR | 37 | 1.000 | 0.0377 | 229.591 | 242.735 | 9.322 | 0.531 |
| rule_smoke_v5 | B | 31 | 1.000 | 0.0520 | 77.332 | 99.058 | 9.623 | 0.247 |
| rule_smoke_v5 | OR | 40 | 1.000 | 0.0961 | 209.675 | 220.747 | 9.451 | 0.622 |
| llm_combined_v3 | healthy | 42 | 1.000 | 0.0151 | 34.586 | 43.040 |  | 0.149 |
| llm_combined_v3 | IR | 23 | 1.000 | 0.0379 | 217.665 | 231.275 | 6.093 | 0.718 |
| llm_combined_v3 | B | 23 | 1.000 | 0.0530 | 67.114 | 85.681 | 6.673 | 0.635 |
| llm_combined_v3 | OR | 25 | 1.000 | 0.0964 | 208.742 | 232.939 | 6.309 | 0.770 |

These are diagnostics only; they do not establish downstream superiority.
