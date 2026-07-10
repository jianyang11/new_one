# Phase-B CWRU Pool Quality Smoke

| method | class | n | pass rate | band L1 | PSD W1 mean | PSD W1 p90 | env prom mean | NN syn-real mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| rule_smoke_v5 | healthy | 13 | 1.000 | 0.0772 | 29.290 | 40.161 |  | 0.116 |
| rule_smoke_v5 | IR | 37 | 1.000 | 0.0377 | 229.591 | 242.735 | 9.322 | 0.531 |
| rule_smoke_v5 | B | 31 | 1.000 | 0.0520 | 77.332 | 99.058 | 9.623 | 0.247 |
| rule_smoke_v5 | OR | 40 | 1.000 | 0.0961 | 209.675 | 220.747 | 9.451 | 0.622 |
| llm_full_v1 | healthy | 603 | 1.000 | 0.0107 | 34.253 | 42.805 |  | 0.148 |
| llm_full_v1 | IR | 750 | 1.000 | 0.0406 | 231.536 | 244.067 | 11.538 | 0.549 |
| llm_full_v1 | B | 631 | 1.000 | 0.0529 | 99.429 | 123.445 | 9.697 | 0.251 |
| llm_full_v1 | OR | 750 | 1.000 | 0.0962 | 223.098 | 238.788 | 12.725 | 0.622 |

These are diagnostics only; they do not establish downstream superiority.
