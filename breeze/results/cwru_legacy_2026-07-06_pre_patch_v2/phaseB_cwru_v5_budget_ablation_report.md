# Phase-B CWRU v5 Synthetic Budget Ablation

## Summary

| budget | method | n_real | seeds | mean acc | mean macro-F1 | n_syn values |
|---|---|---:|---:|---:|---:|---|
| nsyn20 | llm | 5 | 10 | 0.5866 | 0.5809 | 80;80;80;80;80;80;80;80;80;80 |
| nsyn20 | rule | 5 | 10 | 0.5588 | 0.5580 | 80;80;80;80;80;80;80;80;80;80 |
| nsyn20 | noise | 5 | 10 | 0.4689 | 0.4667 | 80;80;80;80;80;80;80;80;80;80 |
| nsyn20 | llm | 10 | 10 | 0.6278 | 0.6508 | 80;80;80;80;80;80;80;80;80;80 |
| nsyn20 | rule | 10 | 10 | 0.5869 | 0.6126 | 80;80;80;80;80;80;80;80;80;80 |
| nsyn20 | noise | 10 | 10 | 0.5255 | 0.5450 | 80;80;80;80;80;80;80;80;80;80 |
| nsyn20 | llm | 25 | 10 | 0.6699 | 0.7089 | 80;80;80;80;80;80;80;80;80;80 |
| nsyn20 | rule | 25 | 10 | 0.6418 | 0.6795 | 80;80;80;80;80;80;80;80;80;80 |
| nsyn20 | noise | 25 | 10 | 0.6461 | 0.6708 | 80;80;80;80;80;80;80;80;80;80 |
| nsyn38 | llm | 5 | 10 | 0.6337 | 0.6778 | 152;152;152;152;152;152;152;152;152;152 |
| nsyn38 | rule | 5 | 10 | 0.5726 | 0.6137 | 152;152;152;152;152;152;152;152;152;152 |
| nsyn38 | noise | 5 | 10 | 0.5134 | 0.5411 | 152;152;152;152;152;152;152;152;152;152 |
| nsyn38 | llm | 10 | 10 | 0.6310 | 0.6779 | 152;152;152;152;152;152;152;152;152;152 |
| nsyn38 | rule | 10 | 10 | 0.5935 | 0.6404 | 152;152;152;152;152;152;152;152;152;152 |
| nsyn38 | noise | 10 | 10 | 0.5722 | 0.6120 | 152;152;152;152;152;152;152;152;152;152 |
| nsyn38 | llm | 25 | 10 | 0.6833 | 0.7290 | 152;152;152;152;152;152;152;152;152;152 |
| nsyn38 | rule | 25 | 10 | 0.6425 | 0.6904 | 152;152;152;152;152;152;152;152;152;152 |
| nsyn38 | noise | 25 | 10 | 0.6775 | 0.7161 | 152;152;152;152;152;152;152;152;152;152 |

## Wilcoxon Smoke Tests

| budget | n_real | metric | comparison | mean delta | wins | Holm q |
|---|---:|---|---|---:|---:|---:|
| nsyn20 | 5 | acc | llm>rule | 0.0278 | 7/10 | 0.02441 |
| nsyn20 | 5 | acc | llm>noise | 0.1177 | 9/10 | 0.009766 |
| nsyn20 | 5 | macro_f1 | llm>rule | 0.0229 | 7/10 | 0.04883 |
| nsyn20 | 5 | macro_f1 | llm>noise | 0.1142 | 8/10 | 0.04883 |
| nsyn20 | 10 | acc | llm>rule | 0.0409 | 9/10 | 0.005859 |
| nsyn20 | 10 | acc | llm>noise | 0.1023 | 9/10 | 0.009766 |
| nsyn20 | 10 | macro_f1 | llm>rule | 0.0382 | 9/10 | 0.003906 |
| nsyn20 | 10 | macro_f1 | llm>noise | 0.1058 | 9/10 | 0.009766 |
| nsyn20 | 25 | acc | llm>rule | 0.0281 | 8/10 | 0.009766 |
| nsyn20 | 25 | acc | llm>noise | 0.0239 | 8/10 | 0.06152 |
| nsyn20 | 25 | macro_f1 | llm>rule | 0.0294 | 9/10 | 0.003906 |
| nsyn20 | 25 | macro_f1 | llm>noise | 0.0380 | 8/10 | 0.004883 |
| nsyn38 | 5 | acc | llm>rule | 0.0611 | 10/10 | 0.001953 |
| nsyn38 | 5 | acc | llm>noise | 0.1203 | 10/10 | 0.001953 |
| nsyn38 | 5 | macro_f1 | llm>rule | 0.0641 | 9/10 | 0.001953 |
| nsyn38 | 5 | macro_f1 | llm>noise | 0.1367 | 10/10 | 0.001953 |
| nsyn38 | 10 | acc | llm>rule | 0.0376 | 8/10 | 0.01367 |
| nsyn38 | 10 | acc | llm>noise | 0.0588 | 9/10 | 0.01367 |
| nsyn38 | 10 | macro_f1 | llm>rule | 0.0375 | 8/10 | 0.01367 |
| nsyn38 | 10 | macro_f1 | llm>noise | 0.0659 | 9/10 | 0.003906 |
| nsyn38 | 25 | acc | llm>rule | 0.0408 | 8/10 | 0.009766 |
| nsyn38 | 25 | acc | llm>noise | 0.0059 | 5/10 | 0.6045 |
| nsyn38 | 25 | macro_f1 | llm>rule | 0.0386 | 9/10 | 0.005859 |
| nsyn38 | 25 | macro_f1 | llm>noise | 0.0129 | 6/10 | 0.3477 |

## Interpretation

n_syn=38 is strongest at n=5/10, but at n=25 it does not significantly beat noise augmentation. n_syn=20 gives a better n=25 tradeoff against noise while still beating rule/noise at n=5/10 in mean. This suggests a shot-dependent synthetic budget schedule may be necessary, but it must be pre-registered before any full-scale CWRU run to avoid post hoc selection.
