# Phase-B CWRU Full v1 Smoke Report

## API and Pool

- Cumulative Phase-B API requests: 637.
- full_v1_supplement actual requests: 567; total CWRU API requests including pilots: 637.
- Combined full pool counts: {'healthy': 603, 'IR': 750, 'B': 631, 'OR': 750}.
- Schedule used here: n_real=5/10 use n_syn=38/class; n_real=25 uses n_syn=20/class, as pre-full pilot-selected schedule.

## Downstream Summary

| n_real | method | seeds | mean acc | mean macro-F1 | n_syn values |
|---:|---|---:|---:|---:|---|
| 5 | llm_full | 10 | 0.6298 | 0.6729 | 152;152;152;152;152;152;152;152;152;152 |
| 5 | rule | 10 | 0.5726 | 0.6137 | 152;152;152;152;152;152;152;152;152;152 |
| 5 | noise | 10 | 0.5134 | 0.5411 | 152;152;152;152;152;152;152;152;152;152 |
| 10 | llm_full | 10 | 0.6251 | 0.6725 | 152;152;152;152;152;152;152;152;152;152 |
| 10 | rule | 10 | 0.5935 | 0.6404 | 152;152;152;152;152;152;152;152;152;152 |
| 10 | noise | 10 | 0.5722 | 0.6120 | 152;152;152;152;152;152;152;152;152;152 |
| 25 | llm_full | 20 | 0.6668 | 0.7033 | 80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80 |
| 25 | rule | 20 | 0.6430 | 0.6803 | 80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80 |
| 25 | noise | 20 | 0.6245 | 0.6497 | 80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80 |

## Paired Wilcoxon Smoke Tests

| n_real | metric | comparison | seeds | mean delta | wins | p raw | Holm q |
|---:|---|---|---:|---:|---:|---:|---:|
| 5 | acc | llm_full>rule | 10 | 0.0572 | 10/10 | 0.0009766 | 0.001953 |
| 5 | acc | llm_full>noise | 10 | 0.1164 | 9/10 | 0.00293 | 0.00293 |
| 5 | macro_f1 | llm_full>rule | 10 | 0.0592 | 9/10 | 0.001953 | 0.003906 |
| 5 | macro_f1 | llm_full>noise | 10 | 0.1318 | 9/10 | 0.00293 | 0.003906 |
| 10 | acc | llm_full>rule | 10 | 0.0317 | 8/10 | 0.01953 | 0.01953 |
| 10 | acc | llm_full>noise | 10 | 0.0529 | 9/10 | 0.006836 | 0.01367 |
| 10 | macro_f1 | llm_full>rule | 10 | 0.0321 | 7/10 | 0.02441 | 0.02441 |
| 10 | macro_f1 | llm_full>noise | 10 | 0.0606 | 9/10 | 0.00293 | 0.005859 |
| 25 | acc | llm_full>rule | 20 | 0.0238 | 17/20 | 0.001754 | 0.003508 |
| 25 | acc | llm_full>noise | 20 | 0.0423 | 13/20 | 0.003092 | 0.003508 |
| 25 | macro_f1 | llm_full>rule | 20 | 0.0230 | 18/20 | 0.0002928 | 0.0002928 |
| 25 | macro_f1 | llm_full>noise | 20 | 0.0536 | 17/20 | 1.812e-05 | 3.624e-05 |

## Decision

- Full v1 within-load0 smoke gate: PASS.
- This supports proceeding to the next CWRU Phase-B step: full within_load0 evaluation with the registered schedule and broader baselines/classifiers. It does not yet support XJTU/IMS or paper-level SOTA claims.
