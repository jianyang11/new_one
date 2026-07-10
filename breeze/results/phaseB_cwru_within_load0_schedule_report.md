# Phase-B CWRU within_load0 Schedule Summary

This table includes real_only, noise augmentation, rule recipe, and LLM full v1 under the pilot-selected synthetic schedule.

| n_real | method | seeds | mean acc | mean macro-F1 | n_syn values |
|---:|---|---:|---:|---:|---|
| 5 | llm_full | 10 | 0.6298 | 0.6729 | 152;152;152;152;152;152;152;152;152;152 |
| 5 | rule | 10 | 0.5726 | 0.6137 | 152;152;152;152;152;152;152;152;152;152 |
| 5 | noise | 10 | 0.5134 | 0.5411 | 152;152;152;152;152;152;152;152;152;152 |
| 5 | real_only | 10 | 0.2627 | 0.1231 | 0;0;0;0;0;0;0;0;0;0 |
| 10 | llm_full | 10 | 0.6251 | 0.6725 | 152;152;152;152;152;152;152;152;152;152 |
| 10 | rule | 10 | 0.5935 | 0.6404 | 152;152;152;152;152;152;152;152;152;152 |
| 10 | noise | 10 | 0.5722 | 0.6120 | 152;152;152;152;152;152;152;152;152;152 |
| 10 | real_only | 10 | 0.3222 | 0.2540 | 0;0;0;0;0;0;0;0;0;0 |
| 25 | llm_full | 20 | 0.6668 | 0.7033 | 80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80 |
| 25 | rule | 20 | 0.6430 | 0.6803 | 80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80 |
| 25 | noise | 20 | 0.6245 | 0.6497 | 80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80;80 |
| 25 | real_only | 20 | 0.5013 | 0.5080 | 0;0;0;0;0;0;0;0;0;0;0;0;0;0;0;0;0;0;0;0 |

## LLM vs Baselines

| n_real | metric | comparison | seeds | mean delta | wins | p raw | Holm q |
|---:|---|---|---:|---:|---:|---:|---:|
| 5 | acc | llm_full>rule | 10 | 0.0572 | 10/10 | 0.0009766 | 0.00293 |
| 5 | acc | llm_full>noise | 10 | 0.1164 | 9/10 | 0.00293 | 0.00293 |
| 5 | acc | llm_full>real_only | 10 | 0.3670 | 10/10 | 0.0009766 | 0.00293 |
| 5 | macro_f1 | llm_full>rule | 10 | 0.0592 | 9/10 | 0.001953 | 0.003906 |
| 5 | macro_f1 | llm_full>noise | 10 | 0.1318 | 9/10 | 0.00293 | 0.003906 |
| 5 | macro_f1 | llm_full>real_only | 10 | 0.5498 | 10/10 | 0.0009766 | 0.00293 |
| 10 | acc | llm_full>rule | 10 | 0.0317 | 8/10 | 0.01953 | 0.01953 |
| 10 | acc | llm_full>noise | 10 | 0.0529 | 9/10 | 0.006836 | 0.01367 |
| 10 | acc | llm_full>real_only | 10 | 0.3029 | 10/10 | 0.0009766 | 0.00293 |
| 10 | macro_f1 | llm_full>rule | 10 | 0.0321 | 7/10 | 0.02441 | 0.02441 |
| 10 | macro_f1 | llm_full>noise | 10 | 0.0606 | 9/10 | 0.00293 | 0.005859 |
| 10 | macro_f1 | llm_full>real_only | 10 | 0.4185 | 10/10 | 0.0009766 | 0.00293 |
| 25 | acc | llm_full>rule | 20 | 0.0238 | 17/20 | 0.001754 | 0.003508 |
| 25 | acc | llm_full>noise | 20 | 0.0423 | 13/20 | 0.003092 | 0.003508 |
| 25 | acc | llm_full>real_only | 20 | 0.1655 | 20/20 | 4.422e-05 | 0.0001327 |
| 25 | macro_f1 | llm_full>rule | 20 | 0.0230 | 18/20 | 0.0002928 | 0.0002928 |
| 25 | macro_f1 | llm_full>noise | 20 | 0.0536 | 17/20 | 1.812e-05 | 3.624e-05 |
| 25 | macro_f1 | llm_full>real_only | 20 | 0.1953 | 20/20 | 9.537e-07 | 2.861e-06 |

## Decision

- CWRU within_load0 schedule gate: PASS.
- LLM full v1 beats real_only, noise_aug, and rule recipe under the registered schedule in this CNN within_load0 smoke. This supports expanding CWRU within-condition evaluation, but still does not justify XJTU/IMS or manuscript-level claims.
