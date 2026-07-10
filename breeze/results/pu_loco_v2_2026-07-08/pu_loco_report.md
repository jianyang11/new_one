# PU LOCO Gate Report

## Protocol
- Scope: leave-one-condition-out across N09_M07_F10, N15_M01_F10, N15_M07_F04, and N15_M07_F10.
- Split unit: operating condition; no window-level train/test random split.
- Seeds: 40 fixed seeds (0-39) for every fold, method, and shot.
- Shots: n_real = 5, 10, 25 per class.
- Synthetic budget: uniform n_syn = 20 per class (60 total windows) for LLM/rule/random_open_loop/noise_aug; real_only uses 0 synthetic windows.
- Statistical family: each (held-out condition, n_real, metric) is one family with Holm correction across llm>rule, llm>random_open_loop, llm>noise_aug, and llm>real_only; global BH is reported as reference.
- LLM source: v2 condition-aware rerendered pools using held-out condition metadata only; no held-out signals or labels were used during pool construction.
- API usage for this v2 rerender block: 0 new LLM calls. The reused morphology recipes came from the previously logged v1 PU LOCO LLM pools.
- Baseline provenance: rule/random_open_loop/noise_aug/real_only CSVs are copied unchanged from the v1 directory because their pools, splits, seeds, and training protocol are identical; v1 LLM CSVs are not reused.

## Completeness
- Expected rows: 2400; observed rows: 2400.
- Every fold/method/shot cell contains 40 seeds.

## Four-Fold Mean
| method | n_real | metric | fold_mean | fold_std | fold_min | fold_max |
| --- | --- | --- | --- | --- | --- | --- |
| llm | 5 | acc | 0.4203 | 0.0523 | 0.3419 | 0.4495 |
| llm | 5 | macro_f1 | 0.3237 | 0.0472 | 0.2588 | 0.3719 |
| llm | 10 | acc | 0.4999 | 0.0731 | 0.3997 | 0.5553 |
| llm | 10 | macro_f1 | 0.4498 | 0.0661 | 0.3599 | 0.5016 |
| llm | 25 | acc | 0.6050 | 0.0759 | 0.5340 | 0.6791 |
| llm | 25 | macro_f1 | 0.5699 | 0.0724 | 0.5063 | 0.6397 |
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
| loco_N09_M07_F10 | 5 | acc | llm>rule | 0.0017 | 0.3377 | 0.6755 | False |
| loco_N09_M07_F10 | 5 | acc | llm>random_open_loop | 0.0550 | 0.0012 | 0.0036 | True |
| loco_N09_M07_F10 | 5 | acc | llm>noise_aug | -0.0764 | 0.9996 | 0.9996 | False |
| loco_N09_M07_F10 | 5 | macro_f1 | llm>rule | -0.0078 | 0.5774 | 1.0000 | False |
| loco_N09_M07_F10 | 5 | macro_f1 | llm>random_open_loop | 0.0982 | 0.0004 | 0.0011 | True |
| loco_N09_M07_F10 | 5 | macro_f1 | llm>noise_aug | -0.0888 | 0.9965 | 1.0000 | False |
| loco_N09_M07_F10 | 10 | acc | llm>rule | 0.0299 | 0.0484 | 0.0968 | False |
| loco_N09_M07_F10 | 10 | acc | llm>random_open_loop | 0.0439 | 0.0317 | 0.0952 | False |
| loco_N09_M07_F10 | 10 | acc | llm>noise_aug | -0.0564 | 0.9921 | 0.9921 | False |
| loco_N09_M07_F10 | 10 | macro_f1 | llm>rule | 0.0335 | 0.0808 | 0.1617 | False |
| loco_N09_M07_F10 | 10 | macro_f1 | llm>random_open_loop | 0.0924 | 0.0019 | 0.0058 | True |
| loco_N09_M07_F10 | 10 | macro_f1 | llm>noise_aug | -0.0452 | 0.9514 | 0.9514 | False |
| loco_N09_M07_F10 | 25 | acc | llm>rule | 0.0462 | 2.52e-05 | 0.0001 | True |
| loco_N09_M07_F10 | 25 | acc | llm>random_open_loop | -0.0751 | 1.0000 | 1.0000 | False |
| loco_N09_M07_F10 | 25 | acc | llm>noise_aug | -0.0868 | 1.0000 | 1.0000 | False |
| loco_N09_M07_F10 | 25 | macro_f1 | llm>rule | 0.0592 | 4.94e-05 | 0.0002 | True |
| loco_N09_M07_F10 | 25 | macro_f1 | llm>random_open_loop | -0.0577 | 0.9970 | 1.0000 | False |
| loco_N09_M07_F10 | 25 | macro_f1 | llm>noise_aug | -0.0632 | 0.9997 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | acc | llm>rule | -0.0268 | 0.9963 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | acc | llm>random_open_loop | -0.0354 | 0.9926 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | acc | llm>noise_aug | -0.1967 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | macro_f1 | llm>rule | -0.0406 | 0.9959 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | macro_f1 | llm>random_open_loop | -0.0247 | 0.8398 | 1.0000 | False |
| loco_N15_M01_F10 | 5 | macro_f1 | llm>noise_aug | -0.2294 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | acc | llm>rule | -0.0392 | 0.9987 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | acc | llm>random_open_loop | -0.0750 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | acc | llm>noise_aug | -0.1732 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | macro_f1 | llm>rule | -0.0436 | 0.9945 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | macro_f1 | llm>random_open_loop | -0.0471 | 0.9615 | 1.0000 | False |
| loco_N15_M01_F10 | 10 | macro_f1 | llm>noise_aug | -0.1679 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | acc | llm>rule | -0.0348 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | acc | llm>random_open_loop | -0.0568 | 0.9999 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | acc | llm>noise_aug | -0.0819 | 1.0000 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | macro_f1 | llm>rule | -0.0267 | 0.9921 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | macro_f1 | llm>random_open_loop | -0.0374 | 0.9911 | 1.0000 | False |
| loco_N15_M01_F10 | 25 | macro_f1 | llm>noise_aug | -0.0720 | 1.0000 | 1.0000 | False |
| loco_N15_M07_F04 | 5 | acc | llm>rule | 0.0058 | 0.3066 | 0.6133 | False |
| loco_N15_M07_F04 | 5 | acc | llm>random_open_loop | 0.0851 | 1.33e-05 | 5.32e-05 | True |
| loco_N15_M07_F04 | 5 | acc | llm>noise_aug | -0.1361 | 1.0000 | 1.0000 | False |
| loco_N15_M07_F04 | 5 | macro_f1 | llm>rule | 0.0251 | 0.1273 | 0.2547 | False |
| loco_N15_M07_F04 | 5 | macro_f1 | llm>random_open_loop | 0.0869 | 0.0004 | 0.0017 | True |
| loco_N15_M07_F04 | 5 | macro_f1 | llm>noise_aug | -0.2097 | 1.0000 | 1.0000 | False |
| loco_N15_M07_F04 | 10 | acc | llm>rule | 0.0382 | 0.0135 | 0.0270 | True |
| loco_N15_M07_F04 | 10 | acc | llm>random_open_loop | 0.1000 | 8.51e-05 | 0.0003 | True |
| loco_N15_M07_F04 | 10 | acc | llm>noise_aug | -0.0610 | 0.9989 | 0.9989 | False |
| loco_N15_M07_F04 | 10 | macro_f1 | llm>rule | 0.0647 | 0.0033 | 0.0067 | True |
| loco_N15_M07_F04 | 10 | macro_f1 | llm>random_open_loop | 0.1284 | 0.0002 | 0.0005 | True |
| loco_N15_M07_F04 | 10 | macro_f1 | llm>noise_aug | -0.0698 | 0.9967 | 0.9967 | False |
| loco_N15_M07_F04 | 25 | acc | llm>rule | -0.0303 | 0.9992 | 0.9992 | False |
| loco_N15_M07_F04 | 25 | acc | llm>random_open_loop | 0.0393 | 0.0008 | 0.0024 | True |
| loco_N15_M07_F04 | 25 | acc | llm>noise_aug | 0.0014 | 0.3377 | 0.6755 | False |
| loco_N15_M07_F04 | 25 | macro_f1 | llm>rule | -0.0467 | 0.9999 | 0.9999 | False |
| loco_N15_M07_F04 | 25 | macro_f1 | llm>random_open_loop | 0.0431 | 0.0003 | 0.0010 | True |
| loco_N15_M07_F04 | 25 | macro_f1 | llm>noise_aug | 0.0005 | 0.4439 | 0.8878 | False |
| loco_N15_M07_F10 | 5 | acc | llm>rule | 0.0330 | 0.1370 | 0.2741 | False |
| loco_N15_M07_F10 | 5 | acc | llm>random_open_loop | 0.0760 | 0.0005 | 0.0020 | True |
| loco_N15_M07_F10 | 5 | acc | llm>noise_aug | -0.1142 | 1.0000 | 1.0000 | False |
| loco_N15_M07_F10 | 5 | macro_f1 | llm>rule | 0.0429 | 0.0853 | 0.1705 | False |
| loco_N15_M07_F10 | 5 | macro_f1 | llm>random_open_loop | 0.0595 | 0.0133 | 0.0531 | False |
| loco_N15_M07_F10 | 5 | macro_f1 | llm>noise_aug | -0.1937 | 1.0000 | 1.0000 | False |
| loco_N15_M07_F10 | 10 | acc | llm>rule | 0.0744 | 0.0004 | 0.0009 | True |
| loco_N15_M07_F10 | 10 | acc | llm>random_open_loop | 0.0627 | 0.0003 | 0.0009 | True |
| loco_N15_M07_F10 | 10 | acc | llm>noise_aug | -0.0688 | 0.9984 | 0.9984 | False |
| loco_N15_M07_F10 | 10 | macro_f1 | llm>rule | 0.0967 | 0.0010 | 0.0020 | True |
| loco_N15_M07_F10 | 10 | macro_f1 | llm>random_open_loop | 0.0716 | 0.0004 | 0.0013 | True |
| loco_N15_M07_F10 | 10 | macro_f1 | llm>noise_aug | -0.0864 | 0.9986 | 0.9986 | False |
| loco_N15_M07_F10 | 25 | acc | llm>rule | 0.0063 | 0.2381 | 0.2381 | False |
| loco_N15_M07_F10 | 25 | acc | llm>random_open_loop | 0.0573 | 2.54e-05 | 7.62e-05 | True |
| loco_N15_M07_F10 | 25 | acc | llm>noise_aug | 0.0152 | 0.1069 | 0.2137 | False |
| loco_N15_M07_F10 | 25 | macro_f1 | llm>rule | -0.0098 | 0.5450 | 0.5900 | False |
| loco_N15_M07_F10 | 25 | macro_f1 | llm>random_open_loop | 0.0662 | 9.07e-05 | 0.0003 | True |
| loco_N15_M07_F10 | 25 | macro_f1 | llm>noise_aug | 0.0107 | 0.2950 | 0.5900 | False |

## Gate Decision
- PU LOCO is not uniformly significant: 60 of 96 registered comparisons fail Holm q<0.05 with positive delta.
- Failed rows are retained in `pu_loco_wilcoxon.csv`; do not claim uniform PU LOCO superiority without qualifying these folds/settings.
