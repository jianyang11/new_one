# PU LOCO Gate Report

## Protocol
- Scope: leave-one-condition-out across N09_M07_F10, N15_M01_F10, N15_M07_F04, and N15_M07_F10.
- Split unit: operating condition; no window-level train/test random split.
- Seeds: 40 fixed seeds (0-39) for every fold, method, and shot.
- Shots: n_real = 5, 10, 25 per class.
- Synthetic budget: uniform n_syn = 20 per class (60 total windows) for LLM/rule/random_open_loop/noise_aug; real_only uses 0 synthetic windows.
- Statistical family: each (held-out condition, n_real, metric) is one family with Holm correction across llm>rule, llm>random_open_loop, llm>noise_aug, and llm>real_only; global BH is reported as reference.
- API usage for PU LOCO pool construction: 133 LLM calls; fold-specific LLM pools were generated from training conditions only, and rule/random_open_loop pools used no LLM calls.

## Completeness
- Expected rows: 2400; observed rows: 2400.
- Every fold/method/shot cell contains 40 seeds.

## Four-Fold Mean
| method | n_real | metric | fold_mean | fold_std | fold_min | fold_max |
| --- | --- | --- | --- | --- | --- | --- |
| llm | 5 | acc | 0.4322 | 0.0629 | 0.3592 | 0.5092 |
| llm | 5 | macro_f1 | 0.3373 | 0.0530 | 0.2636 | 0.3845 |
| llm | 10 | acc | 0.5190 | 0.0876 | 0.4355 | 0.6263 |
| llm | 10 | macro_f1 | 0.4593 | 0.0821 | 0.3871 | 0.5560 |
| llm | 25 | acc | 0.6075 | 0.0698 | 0.5373 | 0.6689 |
| llm | 25 | macro_f1 | 0.5671 | 0.0708 | 0.5006 | 0.6295 |
| rule | 5 | acc | 0.4169 | 0.0343 | 0.3687 | 0.4450 |
| rule | 5 | macro_f1 | 0.3188 | 0.0414 | 0.2879 | 0.3797 |
| rule | 10 | acc | 0.4740 | 0.0323 | 0.4389 | 0.5151 |
| rule | 10 | macro_f1 | 0.4120 | 0.0168 | 0.4005 | 0.4369 |
| rule | 25 | acc | 0.6081 | 0.0905 | 0.4991 | 0.6916 |
| rule | 25 | macro_f1 | 0.5759 | 0.1041 | 0.4493 | 0.6719 |
| random_open_loop | 5 | acc | 0.3751 | 0.0138 | 0.3581 | 0.3917 |
| random_open_loop | 5 | macro_f1 | 0.2688 | 0.0157 | 0.2466 | 0.2835 |
| random_open_loop | 10 | acc | 0.4670 | 0.0208 | 0.4472 | 0.4926 |
| random_open_loop | 10 | macro_f1 | 0.3885 | 0.0346 | 0.3480 | 0.4256 |
| random_open_loop | 25 | acc | 0.6138 | 0.0153 | 0.5908 | 0.6221 |
| random_open_loop | 25 | macro_f1 | 0.5664 | 0.0165 | 0.5437 | 0.5821 |
| noise_aug | 5 | acc | 0.5512 | 0.0252 | 0.5231 | 0.5793 |
| noise_aug | 5 | macro_f1 | 0.5041 | 0.0369 | 0.4606 | 0.5433 |
| noise_aug | 10 | acc | 0.5897 | 0.0358 | 0.5475 | 0.6241 |
| noise_aug | 10 | macro_f1 | 0.5421 | 0.0446 | 0.4856 | 0.5836 |
| noise_aug | 25 | acc | 0.6430 | 0.0229 | 0.6159 | 0.6638 |
| noise_aug | 25 | macro_f1 | 0.6009 | 0.0301 | 0.5717 | 0.6290 |
| real_only | 5 | acc | 0.3794 | 0.0156 | 0.3563 | 0.3906 |
| real_only | 5 | macro_f1 | 0.2539 | 0.0236 | 0.2189 | 0.2704 |
| real_only | 10 | acc | 0.3978 | 0.0177 | 0.3822 | 0.4198 |
| real_only | 10 | macro_f1 | 0.2901 | 0.0217 | 0.2723 | 0.3192 |
| real_only | 25 | acc | 0.5835 | 0.0298 | 0.5479 | 0.6094 |
| real_only | 25 | macro_f1 | 0.5306 | 0.0301 | 0.5022 | 0.5570 |

## Per-Fold LLM Comparisons
| split | n_real | metric | comparison | mean_delta | p_value | holm_q_in_family | passed_holm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| loco_N09_M07_F10 | 5 | acc | llm>rule | -0.0321 | 0.9842 | 1.0000 | False |
| loco_N09_M07_F10 | 5 | acc | llm>random_open_loop | 0.0212 | 0.0972 | 0.2915 | False |
| loco_N09_M07_F10 | 5 | acc | llm>noise_aug | -0.1102 | 1.0000 | 1.0000 | False |
| loco_N09_M07_F10 | 5 | macro_f1 | llm>rule | -0.0433 | 0.9729 | 1.0000 | False |
| loco_N09_M07_F10 | 5 | macro_f1 | llm>random_open_loop | 0.0627 | 0.0103 | 0.0308 | True |
| loco_N09_M07_F10 | 5 | macro_f1 | llm>noise_aug | -0.1243 | 1.0000 | 1.0000 | False |
| loco_N09_M07_F10 | 10 | acc | llm>rule | -0.0004 | 0.4252 | 1.0000 | False |
| loco_N09_M07_F10 | 10 | acc | llm>random_open_loop | 0.0136 | 0.3523 | 1.0000 | False |
| loco_N09_M07_F10 | 10 | acc | llm>noise_aug | -0.0867 | 0.9996 | 1.0000 | False |
| loco_N09_M07_F10 | 10 | macro_f1 | llm>rule | -0.0116 | 0.6470 | 1.0000 | False |
| loco_N09_M07_F10 | 10 | macro_f1 | llm>random_open_loop | 0.0473 | 0.0575 | 0.1724 | False |
| loco_N09_M07_F10 | 10 | macro_f1 | llm>noise_aug | -0.0903 | 0.9996 | 1.0000 | False |
| loco_N09_M07_F10 | 25 | acc | llm>rule | 0.0585 | 0.0002 | 0.0009 | True |
| loco_N09_M07_F10 | 25 | acc | llm>random_open_loop | -0.0628 | 0.9992 | 1.0000 | False |
| loco_N09_M07_F10 | 25 | acc | llm>noise_aug | -0.0745 | 1.0000 | 1.0000 | False |
| loco_N09_M07_F10 | 25 | macro_f1 | llm>rule | 0.0618 | 0.0005 | 0.0019 | True |
| loco_N09_M07_F10 | 25 | macro_f1 | llm>random_open_loop | -0.0551 | 0.9908 | 1.0000 | False |
| loco_N09_M07_F10 | 25 | macro_f1 | llm>noise_aug | -0.0605 | 0.9977 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | acc | llm>rule | -0.0095 | 0.6996 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | acc | llm>random_open_loop | -0.0181 | 0.9139 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | acc | llm>noise_aug | -0.1794 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | macro_f1 | llm>rule | -0.0358 | 0.9972 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | macro_f1 | llm>random_open_loop | -0.0199 | 0.9128 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | macro_f1 | llm>noise_aug | -0.2246 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | acc | llm>rule | -0.0033 | 0.6312 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | acc | llm>random_open_loop | -0.0392 | 0.9907 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | acc | llm>noise_aug | -0.1374 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | macro_f1 | llm>rule | -0.0164 | 0.8931 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | macro_f1 | llm>random_open_loop | -0.0200 | 0.8557 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | macro_f1 | llm>noise_aug | -0.1407 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | acc | llm>rule | -0.0315 | 0.9996 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | acc | llm>random_open_loop | -0.0535 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | acc | llm>noise_aug | -0.0786 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | macro_f1 | llm>rule | -0.0323 | 0.9996 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | macro_f1 | llm>random_open_loop | -0.0431 | 0.9953 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | macro_f1 | llm>noise_aug | -0.0777 | 1.0000 | 1.0000 | False |
| loco_N15_M07_F04 | 5 | acc | llm>rule | 0.0718 | 0.0031 | 0.0063 | True |
| loco_N15_M07_F04 | 5 | acc | llm>random_open_loop | 0.1511 | 5.27e-08 | 2.11e-07 | True |
| loco_N15_M07_F04 | 5 | acc | llm>noise_aug | -0.0701 | 0.9975 | 0.9975 | False |
| loco_N15_M07_F04 | 5 | macro_f1 | llm>rule | 0.0762 | 0.0116 | 0.0232 | True |
| loco_N15_M07_F04 | 5 | macro_f1 | llm>random_open_loop | 0.1380 | 3.50e-06 | 1.40e-05 | True |
| loco_N15_M07_F04 | 5 | macro_f1 | llm>noise_aug | -0.1587 | 1.0000 | 1.0000 | False |
| loco_N15_M07_F04 | 10 | acc | llm>rule | 0.1112 | 1.46e-06 | 2.92e-06 | True |
| loco_N15_M07_F04 | 10 | acc | llm>random_open_loop | 0.1730 | 5.82e-10 | 1.75e-09 | True |
| loco_N15_M07_F04 | 10 | acc | llm>noise_aug | 0.0120 | 0.0884 | 0.0884 | False |
| loco_N15_M07_F04 | 10 | macro_f1 | llm>rule | 0.1191 | 1.77e-05 | 3.55e-05 | True |
| loco_N15_M07_F04 | 10 | macro_f1 | llm>random_open_loop | 0.1828 | 1.74e-07 | 5.23e-07 | True |
| loco_N15_M07_F04 | 10 | macro_f1 | llm>noise_aug | -0.0154 | 0.6265 | 0.6265 | False |
| loco_N15_M07_F04 | 25 | acc | llm>rule | -0.0227 | 0.9982 | 0.9982 | False |
| loco_N15_M07_F04 | 25 | acc | llm>random_open_loop | 0.0468 | 0.0031 | 0.0092 | True |
| loco_N15_M07_F04 | 25 | acc | llm>noise_aug | 0.0089 | 0.2409 | 0.4818 | False |
| loco_N15_M07_F04 | 25 | macro_f1 | llm>rule | -0.0423 | 0.9998 | 0.9998 | False |
| loco_N15_M07_F04 | 25 | macro_f1 | llm>random_open_loop | 0.0475 | 0.0016 | 0.0048 | True |
| loco_N15_M07_F04 | 25 | macro_f1 | llm>noise_aug | 0.0048 | 0.4175 | 0.8350 | False |
| loco_N15_M07_F10 | 5 | acc | llm>rule | 0.0309 | 0.0459 | 0.0918 | False |
| loco_N15_M07_F10 | 5 | acc | llm>random_open_loop | 0.0740 | 9.73e-05 | 0.0004 | True |
| loco_N15_M07_F10 | 5 | acc | llm>noise_aug | -0.1163 | 1.0000 | 1.0000 | False |
| loco_N15_M07_F10 | 5 | macro_f1 | llm>rule | 0.0769 | 0.0005 | 0.0012 | True |
| loco_N15_M07_F10 | 5 | macro_f1 | llm>random_open_loop | 0.0935 | 8.00e-05 | 0.0003 | True |
| loco_N15_M07_F10 | 5 | macro_f1 | llm>noise_aug | -0.1597 | 1.0000 | 1.0000 | False |
| loco_N15_M07_F10 | 10 | acc | llm>rule | 0.0724 | 0.0004 | 0.0013 | True |
| loco_N15_M07_F10 | 10 | acc | llm>random_open_loop | 0.0607 | 0.0041 | 0.0083 | True |
| loco_N15_M07_F10 | 10 | acc | llm>noise_aug | -0.0708 | 0.9995 | 0.9995 | False |
| loco_N15_M07_F10 | 10 | macro_f1 | llm>rule | 0.0982 | 0.0004 | 0.0013 | True |
| loco_N15_M07_F10 | 10 | macro_f1 | llm>random_open_loop | 0.0731 | 0.0015 | 0.0031 | True |
| loco_N15_M07_F10 | 10 | macro_f1 | llm>noise_aug | -0.0848 | 0.9999 | 0.9999 | False |
| loco_N15_M07_F10 | 25 | acc | llm>rule | -0.0065 | 0.6911 | 0.7932 | False |
| loco_N15_M07_F10 | 25 | acc | llm>random_open_loop | 0.0444 | 0.0001 | 0.0006 | True |
| loco_N15_M07_F10 | 25 | acc | llm>noise_aug | 0.0024 | 0.3966 | 0.7932 | False |
| loco_N15_M07_F10 | 25 | macro_f1 | llm>rule | -0.0225 | 0.8332 | 1.0000 | False |
| loco_N15_M07_F10 | 25 | macro_f1 | llm>random_open_loop | 0.0535 | 6.21e-05 | 0.0002 | True |
| loco_N15_M07_F10 | 25 | macro_f1 | llm>noise_aug | -0.0020 | 0.5868 | 1.0000 | False |

## Gate Decision
- PU LOCO is not uniformly significant: 57 of 96 registered comparisons fail Holm q<0.05 with positive delta.
- Failed rows are retained in `pu_loco_wilcoxon.csv`; do not claim uniform PU LOCO superiority without qualifying these folds/settings.
