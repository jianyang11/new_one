# Phase-B CWRU v4 10-Seed Local Verification

This is still a smoke/local verification stage, not a full Phase-B result.

## Summary

| method | n_real | seeds | n_syn values | mean acc | mean macro-F1 |
|---|---:|---:|---|---:|---:|
| llm_v4_nsyn20 | 5 | 10 | 80;80;80;80;80;80;80;80;80;80 | 0.5886 | 0.5869 |
| rule_nsyn20 | 5 | 10 | 73;73;73;73;73;73;73;73;73;73 | 0.4758 | 0.4068 |
| noise_nsyn20 | 5 | 10 | 80;80;80;80;80;80;80;80;80;80 | 0.4689 | 0.4667 |
| llm_v4_nsyn20 | 10 | 10 | 80;80;80;80;80;80;80;80;80;80 | 0.6255 | 0.6487 |
| rule_nsyn20 | 10 | 10 | 73;73;73;73;73;73;73;73;73;73 | 0.5807 | 0.6023 |
| noise_nsyn20 | 10 | 10 | 80;80;80;80;80;80;80;80;80;80 | 0.5255 | 0.5450 |
| llm_v4_nsyn20 | 25 | 10 | 80;80;80;80;80;80;80;80;80;80 | 0.6680 | 0.7061 |
| rule_nsyn20 | 25 | 10 | 73;73;73;73;73;73;73;73;73;73 | 0.6454 | 0.6788 |
| noise_nsyn20 | 25 | 10 | 80;80;80;80;80;80;80;80;80;80 | 0.6461 | 0.6708 |

## Paired Wilcoxon Smoke Tests

| n_real | metric | comparison | seeds | mean delta | wins | p raw | Holm q |
|---:|---|---|---:|---:|---:|---:|---:|
| 5 | acc | llm_v4_nsyn20>rule_nsyn20 | 10 | 0.1127 | 10/10 | 0.0009766 | 0.001953 |
| 5 | acc | llm_v4_nsyn20>noise_nsyn20 | 10 | 0.1196 | 9/10 | 0.00293 | 0.00293 |
| 5 | macro_f1 | llm_v4_nsyn20>rule_nsyn20 | 10 | 0.1801 | 9/10 | 0.004883 | 0.009766 |
| 5 | macro_f1 | llm_v4_nsyn20>noise_nsyn20 | 10 | 0.1203 | 8/10 | 0.01855 | 0.01855 |
| 10 | acc | llm_v4_nsyn20>rule_nsyn20 | 10 | 0.0448 | 9/10 | 0.00293 | 0.005859 |
| 10 | acc | llm_v4_nsyn20>noise_nsyn20 | 10 | 0.1000 | 9/10 | 0.009766 | 0.009766 |
| 10 | macro_f1 | llm_v4_nsyn20>rule_nsyn20 | 10 | 0.0465 | 8/10 | 0.01855 | 0.01953 |
| 10 | macro_f1 | llm_v4_nsyn20>noise_nsyn20 | 10 | 0.1038 | 9/10 | 0.009766 | 0.01953 |
| 25 | acc | llm_v4_nsyn20>rule_nsyn20 | 10 | 0.0225 | 5/10 | 0.05078 | 0.1016 |
| 25 | acc | llm_v4_nsyn20>noise_nsyn20 | 10 | 0.0219 | 8/10 | 0.09082 | 0.1016 |
| 25 | macro_f1 | llm_v4_nsyn20>rule_nsyn20 | 10 | 0.0273 | 6/10 | 0.05273 | 0.05273 |
| 25 | macro_f1 | llm_v4_nsyn20>noise_nsyn20 | 10 | 0.0352 | 8/10 | 0.004883 | 0.009766 |

## Interpretation

LLM v4 is consistently better than noise_aug in this local grid. Against rule_nsyn20 it is clearly better at n=5, modestly better at n=10, and better on average at n=25; the n=10/n=25 margins are small. Rule_nsyn20 uses only 73 synthetic items because the rule smoke pool has 13 healthy accepted items, while LLM/noise use 80, so this is a pilot-screening comparison rather than a formal budget-equalized test.

Decision: CWRU v4 is strong enough to justify a modest balanced pilot expansion, but not yet a 150/class full pool or manuscript claim. A balanced pilot should target the current bottleneck class count first and rerun the same 10-seed grid before spending hundreds of API calls.
