# Phase-B CWRU Pool Quality Smoke

| method | class | n | pass rate | band L1 | PSD W1 mean | PSD W1 p90 | env prom mean | NN syn-real mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| rule_smoke_v5 | healthy | 13 | 1.000 | 0.0772 | 29.290 | 40.161 |  | 0.116 |
| rule_smoke_v5 | IR | 37 | 1.000 | 0.0377 | 229.591 | 242.735 | 9.322 | 0.531 |
| rule_smoke_v5 | B | 31 | 1.000 | 0.0520 | 77.332 | 99.058 | 9.623 | 0.247 |
| rule_smoke_v5 | OR | 40 | 1.000 | 0.0961 | 209.675 | 220.747 | 9.451 | 0.622 |
| llm_combined_v4 | healthy | 42 | 1.000 | 0.0151 | 34.586 | 43.040 |  | 0.149 |
| llm_combined_v4 | IR | 25 | 1.000 | 0.0416 | 231.711 | 241.052 | 11.679 | 0.545 |
| llm_combined_v4 | B | 21 | 1.000 | 0.0531 | 88.126 | 108.414 | 9.212 | 0.253 |
| llm_combined_v4 | OR | 25 | 1.000 | 0.0964 | 222.471 | 236.148 | 12.064 | 0.618 |

These are diagnostics only; they do not establish downstream superiority.
