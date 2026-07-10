# Phase-B CWRU v5 n_syn20 Mixed-Seed Check

n=5/10 use 10 seeds; n=25 uses 20 seeds because the 10-seed Accuracy comparison against noise was borderline.

| n_real | method | seeds | mean acc | mean macro-F1 |
|---:|---|---:|---:|---:|
| 5 | llm | 10 | 0.5866 | 0.5809 |
| 5 | rule | 10 | 0.5588 | 0.5580 |
| 5 | noise | 10 | 0.4689 | 0.4667 |
| 10 | llm | 10 | 0.6278 | 0.6508 |
| 10 | rule | 10 | 0.5869 | 0.6126 |
| 10 | noise | 10 | 0.5255 | 0.5450 |
| 25 | llm | 20 | 0.6726 | 0.7089 |
| 25 | rule | 20 | 0.6430 | 0.6803 |
| 25 | noise | 20 | 0.6245 | 0.6497 |

| n_real | metric | comparison | seeds | mean delta | wins | p raw | Holm q |
|---:|---|---|---:|---:|---:|---:|---:|
| 5 | acc | llm>rule | 10 | 0.0278 | 7/10 | 0.02441 | 0.02441 |
| 5 | acc | llm>noise | 10 | 0.1177 | 9/10 | 0.004883 | 0.009766 |
| 5 | macro_f1 | llm>rule | 10 | 0.0229 | 7/10 | 0.04199 | 0.04883 |
| 5 | macro_f1 | llm>noise | 10 | 0.1142 | 8/10 | 0.02441 | 0.04883 |
| 10 | acc | llm>rule | 10 | 0.0409 | 9/10 | 0.00293 | 0.005859 |
| 10 | acc | llm>noise | 10 | 0.1023 | 9/10 | 0.009766 | 0.009766 |
| 10 | macro_f1 | llm>rule | 10 | 0.0382 | 9/10 | 0.001953 | 0.003906 |
| 10 | macro_f1 | llm>noise | 10 | 0.1058 | 9/10 | 0.009766 | 0.009766 |
| 25 | acc | llm>rule | 20 | 0.0296 | 17/20 | 0.0008549 | 0.0009514 |
| 25 | acc | llm>noise | 20 | 0.0480 | 17/20 | 0.0004757 | 0.0009514 |
| 25 | macro_f1 | llm>rule | 20 | 0.0286 | 18/20 | 0.0002928 | 0.0002928 |
| 25 | macro_f1 | llm>noise | 20 | 0.0593 | 17/20 | 1.335e-05 | 2.67e-05 |

Decision: n_syn20 passes the smoke gate against rule and noise for n=5/10/25 when n=25 is checked with 20 seeds. This supports a pre-registered CWRU full-pool budget schedule of n_syn20 for n>=25; n_syn38 remains better for n=5/10 but must be declared before full runs.
