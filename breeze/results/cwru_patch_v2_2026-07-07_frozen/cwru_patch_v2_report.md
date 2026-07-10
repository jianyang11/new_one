# CWRU Patch-v2 Gate Report

## Protocol
- Scope: CWRU within-load0 plus full leave-one-load-out folds load0/load1/load2/load3.
- Seeds: 40 fixed seeds (0-39) for every split, method, and shot.
- Shots: n_real = 5, 10, 25 per class.
- Synthetic budget: uniform n_syn = 20 per class (80 total windows) for LLM/rule/noise_aug; real_only uses 0 synthetic windows.
- Budget rationale: fixed a priori for this repair to avoid test-set-tuned per-shot budgets.
- Statistical family: each (split, n_real, metric) is one family with Holm correction across llm>rule, llm>noise_aug, and llm>real_only; global BH is reported as reference.
- API usage in this CWRU repair: 0 LLM calls; existing frozen CWRU pools were reused.

## Completeness
- Expected rows: 2400; observed rows: 2400.
- Every split/method/shot cell contains 40 seeds.

## LOLO Four-Fold Mean
| method | n_real | metric | fold_mean | fold_std | fold_min | fold_max |
| --- | --- | --- | --- | --- | --- | --- |
| llm | 5 | acc | 0.6171 | 0.0201 | 0.5885 | 0.6356 |
| llm | 5 | macro_f1 | 0.5943 | 0.0069 | 0.5864 | 0.6033 |
| llm | 10 | acc | 0.6374 | 0.0173 | 0.6159 | 0.6578 |
| llm | 10 | macro_f1 | 0.6306 | 0.0098 | 0.6204 | 0.6439 |
| llm | 25 | acc | 0.6740 | 0.0274 | 0.6398 | 0.7039 |
| llm | 25 | macro_f1 | 0.6813 | 0.0191 | 0.6652 | 0.7050 |
| rule | 5 | acc | 0.5895 | 0.0228 | 0.5572 | 0.6106 |
| rule | 5 | macro_f1 | 0.5643 | 0.0083 | 0.5588 | 0.5766 |
| rule | 10 | acc | 0.6025 | 0.0203 | 0.5747 | 0.6234 |
| rule | 10 | macro_f1 | 0.5956 | 0.0085 | 0.5896 | 0.6082 |
| rule | 25 | acc | 0.6533 | 0.0258 | 0.6197 | 0.6810 |
| rule | 25 | macro_f1 | 0.6604 | 0.0165 | 0.6466 | 0.6818 |
| noise_aug | 5 | acc | 0.5156 | 0.0281 | 0.4739 | 0.5349 |
| noise_aug | 5 | macro_f1 | 0.5012 | 0.0075 | 0.4922 | 0.5100 |
| noise_aug | 10 | acc | 0.5457 | 0.0281 | 0.5040 | 0.5655 |
| noise_aug | 10 | macro_f1 | 0.5313 | 0.0108 | 0.5175 | 0.5437 |
| noise_aug | 25 | acc | 0.6339 | 0.0227 | 0.6005 | 0.6490 |
| noise_aug | 25 | macro_f1 | 0.6377 | 0.0113 | 0.6236 | 0.6490 |
| real_only | 5 | acc | 0.2519 | 0.0112 | 0.2451 | 0.2686 |
| real_only | 5 | macro_f1 | 0.1397 | 0.0028 | 0.1372 | 0.1432 |
| real_only | 10 | acc | 0.3091 | 0.0054 | 0.3027 | 0.3139 |
| real_only | 10 | macro_f1 | 0.2374 | 0.0056 | 0.2329 | 0.2450 |
| real_only | 25 | acc | 0.5351 | 0.0311 | 0.4886 | 0.5544 |
| real_only | 25 | macro_f1 | 0.5046 | 0.0127 | 0.4860 | 0.5140 |

## Within-Load0 Means
| method | n_real | metric | mean | std | median |
| --- | --- | --- | --- | --- | --- |
| llm | 5 | acc | 0.5639 | 0.0684 | 0.5817 |
| llm | 5 | macro_f1 | 0.5673 | 0.0752 | 0.5887 |
| llm | 10 | acc | 0.6205 | 0.0369 | 0.6307 |
| llm | 10 | macro_f1 | 0.6459 | 0.0498 | 0.6498 |
| llm | 25 | acc | 0.6738 | 0.0372 | 0.6781 |
| llm | 25 | macro_f1 | 0.7106 | 0.0303 | 0.7166 |
| rule | 5 | acc | 0.5486 | 0.0535 | 0.5605 |
| rule | 5 | macro_f1 | 0.5540 | 0.0616 | 0.5745 |
| rule | 10 | acc | 0.5840 | 0.0331 | 0.5849 |
| rule | 10 | macro_f1 | 0.6113 | 0.0457 | 0.6237 |
| rule | 25 | acc | 0.6519 | 0.0372 | 0.6503 |
| rule | 25 | macro_f1 | 0.6891 | 0.0353 | 0.6896 |
| noise_aug | 5 | acc | 0.4545 | 0.0657 | 0.4444 |
| noise_aug | 5 | macro_f1 | 0.4598 | 0.0839 | 0.4630 |
| noise_aug | 10 | acc | 0.5341 | 0.0648 | 0.5196 |
| noise_aug | 10 | macro_f1 | 0.5536 | 0.0815 | 0.5408 |
| noise_aug | 25 | acc | 0.6277 | 0.0554 | 0.6307 |
| noise_aug | 25 | macro_f1 | 0.6550 | 0.0535 | 0.6714 |
| real_only | 5 | acc | 0.2641 | 0.0700 | 0.2353 |
| real_only | 5 | macro_f1 | 0.1323 | 0.0630 | 0.1041 |
| real_only | 10 | acc | 0.3379 | 0.1076 | 0.3546 |
| real_only | 10 | macro_f1 | 0.2447 | 0.1397 | 0.2132 |
| real_only | 25 | acc | 0.4932 | 0.0957 | 0.4968 |
| real_only | 25 | macro_f1 | 0.4990 | 0.0866 | 0.5019 |

## Wilcoxon/Holm Results
| split | n_real | metric | comparison | mean_delta | p_value | holm_q_in_family | passed_holm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| within_load0 | 5 | acc | llm>rule | 0.0153 | 0.0060 | 0.0060 | True |
| within_load0 | 5 | acc | llm>noise_aug | 0.1094 | 4.33e-07 | 8.67e-07 | True |
| within_load0 | 5 | macro_f1 | llm>rule | 0.0133 | 0.0385 | 0.0385 | True |
| within_load0 | 5 | macro_f1 | llm>noise_aug | 0.1075 | 2.47e-06 | 4.93e-06 | True |
| within_load0 | 10 | acc | llm>rule | 0.0365 | 1.92e-08 | 5.35e-08 | True |
| within_load0 | 10 | acc | llm>noise_aug | 0.0864 | 2.24e-07 | 2.24e-07 | True |
| within_load0 | 10 | macro_f1 | llm>rule | 0.0346 | 9.09e-13 | 2.73e-12 | True |
| within_load0 | 10 | macro_f1 | llm>noise_aug | 0.0923 | 2.51e-09 | 2.51e-09 | True |
| within_load0 | 25 | acc | llm>rule | 0.0220 | 2.38e-05 | 4.77e-05 | True |
| within_load0 | 25 | acc | llm>noise_aug | 0.0461 | 3.28e-05 | 4.77e-05 | True |
| within_load0 | 25 | macro_f1 | llm>rule | 0.0216 | 4.59e-06 | 4.59e-06 | True |
| within_load0 | 25 | macro_f1 | llm>noise_aug | 0.0556 | 3.64e-08 | 7.28e-08 | True |
| lolo_load0 | 5 | acc | llm>rule | 0.0313 | 8.75e-06 | 8.75e-06 | True |
| lolo_load0 | 5 | acc | llm>noise_aug | 0.1147 | 3.27e-08 | 6.54e-08 | True |
| lolo_load0 | 5 | macro_f1 | llm>rule | 0.0318 | 3.18e-06 | 3.18e-06 | True |
| lolo_load0 | 5 | macro_f1 | llm>noise_aug | 0.1015 | 3.23e-07 | 6.46e-07 | True |
| lolo_load0 | 10 | acc | llm>rule | 0.0412 | 3.02e-08 | 5.35e-08 | True |
| lolo_load0 | 10 | acc | llm>noise_aug | 0.1119 | 1.78e-08 | 5.35e-08 | True |
| lolo_load0 | 10 | macro_f1 | llm>rule | 0.0389 | 1.75e-07 | 1.75e-07 | True |
| lolo_load0 | 10 | macro_f1 | llm>noise_aug | 0.1110 | 9.09e-12 | 1.82e-11 | True |
| lolo_load0 | 25 | acc | llm>rule | 0.0201 | 2.76e-05 | 5.51e-05 | True |
| lolo_load0 | 25 | acc | llm>noise_aug | 0.0393 | 0.0002 | 0.0002 | True |
| lolo_load0 | 25 | macro_f1 | llm>rule | 0.0182 | 5.72e-05 | 5.72e-05 | True |
| lolo_load0 | 25 | macro_f1 | llm>noise_aug | 0.0429 | 1.65e-05 | 3.30e-05 | True |
| lolo_load1 | 5 | acc | llm>rule | 0.0291 | 1.70e-06 | 1.70e-06 | True |
| lolo_load1 | 5 | acc | llm>noise_aug | 0.0940 | 1.73e-11 | 5.18e-11 | True |
| lolo_load1 | 5 | macro_f1 | llm>rule | 0.0348 | 1.82e-06 | 1.82e-06 | True |
| lolo_load1 | 5 | macro_f1 | llm>noise_aug | 0.0901 | 1.27e-07 | 2.54e-07 | True |
| lolo_load1 | 10 | acc | llm>rule | 0.0351 | 2.41e-08 | 3.57e-08 | True |
| lolo_load1 | 10 | acc | llm>noise_aug | 0.0849 | 1.78e-08 | 3.57e-08 | True |
| lolo_load1 | 10 | macro_f1 | llm>rule | 0.0362 | 1.88e-10 | 3.77e-10 | True |
| lolo_load1 | 10 | macro_f1 | llm>noise_aug | 0.0992 | 3.27e-08 | 3.27e-08 | True |
| lolo_load1 | 25 | acc | llm>rule | 0.0229 | 3.17e-07 | 6.34e-07 | True |
| lolo_load1 | 25 | acc | llm>noise_aug | 0.0367 | 0.0020 | 0.0020 | True |
| lolo_load1 | 25 | macro_f1 | llm>rule | 0.0237 | 1.36e-06 | 2.71e-06 | True |
| lolo_load1 | 25 | macro_f1 | llm>noise_aug | 0.0396 | 0.0020 | 0.0020 | True |
| lolo_load2 | 5 | acc | llm>rule | 0.0251 | 2.07e-06 | 2.07e-06 | True |
| lolo_load2 | 5 | acc | llm>noise_aug | 0.1105 | 1.78e-08 | 5.35e-08 | True |
| lolo_load2 | 5 | macro_f1 | llm>rule | 0.0267 | 1.60e-06 | 1.60e-06 | True |
| lolo_load2 | 5 | macro_f1 | llm>noise_aug | 0.1044 | 9.05e-09 | 2.72e-08 | True |
| lolo_load2 | 10 | acc | llm>rule | 0.0344 | 2.24e-08 | 3.57e-08 | True |
| lolo_load2 | 10 | acc | llm>noise_aug | 0.1005 | 1.78e-08 | 3.57e-08 | True |
| lolo_load2 | 10 | macro_f1 | llm>rule | 0.0357 | 1.75e-07 | 1.75e-07 | True |
| lolo_load2 | 10 | macro_f1 | llm>noise_aug | 0.1102 | 2.73e-12 | 5.46e-12 | True |
| lolo_load2 | 25 | acc | llm>rule | 0.0229 | 7.99e-07 | 1.60e-06 | True |
| lolo_load2 | 25 | acc | llm>noise_aug | 0.0563 | 6.86e-06 | 6.86e-06 | True |
| lolo_load2 | 25 | macro_f1 | llm>rule | 0.0232 | 6.10e-07 | 1.22e-06 | True |
| lolo_load2 | 25 | macro_f1 | llm>noise_aug | 0.0607 | 1.60e-06 | 1.60e-06 | True |
| lolo_load3 | 5 | acc | llm>rule | 0.0248 | 3.92e-06 | 3.92e-06 | True |
| lolo_load3 | 5 | acc | llm>noise_aug | 0.0869 | 6.37e-12 | 1.91e-11 | True |
| lolo_load3 | 5 | macro_f1 | llm>rule | 0.0267 | 1.12e-06 | 2.23e-06 | True |
| lolo_load3 | 5 | macro_f1 | llm>noise_aug | 0.0764 | 1.08e-05 | 1.08e-05 | True |
| lolo_load3 | 10 | acc | llm>rule | 0.0290 | 3.32e-08 | 3.32e-08 | True |
| lolo_load3 | 10 | acc | llm>noise_aug | 0.0692 | 6.37e-11 | 1.27e-10 | True |
| lolo_load3 | 10 | macro_f1 | llm>rule | 0.0290 | 2.79e-10 | 5.58e-10 | True |
| lolo_load3 | 10 | macro_f1 | llm>noise_aug | 0.0767 | 2.51e-09 | 2.51e-09 | True |
| lolo_load3 | 25 | acc | llm>rule | 0.0170 | 1.28e-06 | 2.56e-06 | True |
| lolo_load3 | 25 | acc | llm>noise_aug | 0.0280 | 0.0009 | 0.0009 | True |
| lolo_load3 | 25 | macro_f1 | llm>rule | 0.0186 | 5.14e-07 | 1.03e-06 | True |
| lolo_load3 | 25 | macro_f1 | llm>noise_aug | 0.0312 | 0.0004 | 0.0004 | True |

## Gate Decision
- All registered CWRU patch-v2 comparisons pass Holm q<0.05 with positive mean delta.
