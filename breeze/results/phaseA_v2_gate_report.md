# Phase-A v2 Gate Report

Date: 2026-07-05

## Protocol Lock

- Dataset/protocol: PU N09_M07_F10 file split, CNN downstream classifier.
- Synthetic budget: B=150 per class for LLM K=3, rule, and random open-loop; each downstream augmentation uses n_syn=450.
- Random+verifier accepted 0/450 slots and is reported as verifier robustness evidence only; downstream random comparison uses random open-loop without verifier.
- Seeds: 0-19; n_real in {5, 10, 25, 50}; each result row is checkpointed in `breeze/results/phaseA_v2_downstream_cnn.csv`.
- API usage in this Phase-A v2 rerun: 0 new LLM API calls. The LLM pool is the cached K=3 accepted/rescreened pool.

## Test Family Registration

For each n_real and each metric, the pre-registered family contains exactly two one-sided paired Wilcoxon tests: LLM K=3 > random open-loop and LLM K=3 > rule. Holm correction is applied within that family. Global BH q values across all pre-registered superiority tests are reported as a reference only. At n=50, LLM is accepted as not worse than rule if its paired mean delta is non-negative, or if a two-sided LLM-vs-rule Wilcoxon test has p>=0.05 when the mean delta is negative. LLM > real_only at n=50 is checked by positive paired mean delta and one-sided p<0.05.

## Completeness Check

| baseline | n_real | rows | seed_min | seed_max | n_syn_values |
| --- | --- | --- | --- | --- | --- |
| real_only | 5 | 20 | 0 | 19 | 0 |
| real_only | 10 | 20 | 0 | 19 | 0 |
| real_only | 25 | 20 | 0 | 19 | 0 |
| real_only | 50 | 20 | 0 | 19 | 0 |
| phaseA_v2_random_open_loop | 5 | 20 | 0 | 19 | 450 |
| phaseA_v2_random_open_loop | 10 | 20 | 0 | 19 | 450 |
| phaseA_v2_random_open_loop | 25 | 20 | 0 | 19 | 450 |
| phaseA_v2_random_open_loop | 50 | 20 | 0 | 19 | 450 |
| phaseA_v2_rule | 5 | 20 | 0 | 19 | 450 |
| phaseA_v2_rule | 10 | 20 | 0 | 19 | 450 |
| phaseA_v2_rule | 25 | 20 | 0 | 19 | 450 |
| phaseA_v2_rule | 50 | 20 | 0 | 19 | 450 |
| phaseA_v2_llm_k3 | 5 | 20 | 0 | 19 | 450 |
| phaseA_v2_llm_k3 | 10 | 20 | 0 | 19 | 450 |
| phaseA_v2_llm_k3 | 25 | 20 | 0 | 19 | 450 |
| phaseA_v2_llm_k3 | 50 | 20 | 0 | 19 | 450 |

## Budget Equality

| source | available_healthy | available_OR | available_IR | selected_B_per_class | selection_seed |
| --- | --- | --- | --- | --- | --- |
| rule | 227 | 407 | 151 | 150 | 20260705 |
| llm | 192 | 304 | 261 | 150 | 20260705 |
| random_open_loop | 150 | 150 | 150 | 150 | 20260705 |
| random_plus_verifier | 0 | 0 | 0 | 0 | 20260705 |

| pool | n | healthy | OR | IR |
| --- | --- | --- | --- | --- |
| phaseA_v2_rule_B150 | 450 | 150 | 150 | 150 |
| phaseA_v2_llm_k3_B150 | 450 | 150 | 150 | 150 |
| phaseA_v2_random_open_loop_B150 | 450 | 150 | 150 | 150 |

## Verifier Admission

| source | class | slots | accepted_slots | slot_acceptance | kept_after_diversity |
| --- | --- | --- | --- | --- | --- |
| random_plus_verifier | healthy | 150 | 0 | 0.0000 | 0 |
| random_plus_verifier | OR | 150 | 0 | 0.0000 | 0 |
| random_plus_verifier | IR | 150 | 0 | 0.0000 | 0 |
| rule_verified | healthy | 150 | 58 | 0.3867 | 227 |
| rule_verified | OR | 150 | 87 | 0.5800 | 407 |
| rule_verified | IR | 400 | 59 | 0.1475 | 151 |
| llm_k3_rescreen_v2 | healthy | 150 | 90 | 0.6000 | 192 |
| llm_k3_rescreen_v2 | OR | 150 | 90 | 0.6000 | 304 |
| llm_k3_rescreen_v2 | IR | 150 | 106 | 0.7067 | 261 |

## Downstream Means

| baseline | n_real | metric | mean | std |
| --- | --- | --- | --- | --- |
| real_only | 5 | acc | 0.6575 | 0.0828 |
| real_only | 5 | macro_f1 | 0.6351 | 0.0856 |
| real_only | 10 | acc | 0.6635 | 0.0900 |
| real_only | 10 | macro_f1 | 0.6312 | 0.1032 |
| real_only | 25 | acc | 0.7339 | 0.0416 |
| real_only | 25 | macro_f1 | 0.7135 | 0.0473 |
| real_only | 50 | acc | 0.7874 | 0.0215 |
| real_only | 50 | macro_f1 | 0.7750 | 0.0279 |
| phaseA_v2_random_open_loop | 5 | acc | 0.4502 | 0.0291 |
| phaseA_v2_random_open_loop | 5 | macro_f1 | 0.4358 | 0.0529 |
| phaseA_v2_random_open_loop | 10 | acc | 0.4835 | 0.0126 |
| phaseA_v2_random_open_loop | 10 | macro_f1 | 0.4878 | 0.0147 |
| phaseA_v2_random_open_loop | 25 | acc | 0.5293 | 0.0221 |
| phaseA_v2_random_open_loop | 25 | macro_f1 | 0.5267 | 0.0172 |
| phaseA_v2_random_open_loop | 50 | acc | 0.6297 | 0.0417 |
| phaseA_v2_random_open_loop | 50 | macro_f1 | 0.6219 | 0.0375 |
| phaseA_v2_rule | 5 | acc | 0.6961 | 0.0526 |
| phaseA_v2_rule | 5 | macro_f1 | 0.6905 | 0.0494 |
| phaseA_v2_rule | 10 | acc | 0.7238 | 0.0423 |
| phaseA_v2_rule | 10 | macro_f1 | 0.7240 | 0.0404 |
| phaseA_v2_rule | 25 | acc | 0.7686 | 0.0248 |
| phaseA_v2_rule | 25 | macro_f1 | 0.7702 | 0.0243 |
| phaseA_v2_rule | 50 | acc | 0.8147 | 0.0281 |
| phaseA_v2_rule | 50 | macro_f1 | 0.8164 | 0.0262 |
| phaseA_v2_llm_k3 | 5 | acc | 0.7767 | 0.0273 |
| phaseA_v2_llm_k3 | 5 | macro_f1 | 0.7755 | 0.0264 |
| phaseA_v2_llm_k3 | 10 | acc | 0.7961 | 0.0305 |
| phaseA_v2_llm_k3 | 10 | macro_f1 | 0.7995 | 0.0286 |
| phaseA_v2_llm_k3 | 25 | acc | 0.8180 | 0.0208 |
| phaseA_v2_llm_k3 | 25 | macro_f1 | 0.8212 | 0.0219 |
| phaseA_v2_llm_k3 | 50 | acc | 0.8549 | 0.0261 |
| phaseA_v2_llm_k3 | 50 | macro_f1 | 0.8580 | 0.0263 |

## Pre-Registered Wilcoxon Tests

| family_id | comparison | mean_delta | wins | losses | p_value | holm_q_in_family | bh_q_global |
| --- | --- | --- | --- | --- | --- | --- | --- |
| n5_acc_superiority | phaseA_v2_llm_k3>phaseA_v2_random_open_loop | 0.3265 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n5_acc_superiority | phaseA_v2_llm_k3>phaseA_v2_rule | 0.0806 | 19 | 1 | 6.005e-05 | 6.005e-05 | 6.013e-05 |
| n5_macro_f1_superiority | phaseA_v2_llm_k3>phaseA_v2_random_open_loop | 0.3397 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n5_macro_f1_superiority | phaseA_v2_llm_k3>phaseA_v2_rule | 0.0850 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n10_acc_superiority | phaseA_v2_llm_k3>phaseA_v2_random_open_loop | 0.3126 | 20 | 0 | 4.422e-05 | 4.422e-05 | 5.443e-05 |
| n10_acc_superiority | phaseA_v2_llm_k3>phaseA_v2_rule | 0.0722 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n10_macro_f1_superiority | phaseA_v2_llm_k3>phaseA_v2_random_open_loop | 0.3117 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n10_macro_f1_superiority | phaseA_v2_llm_k3>phaseA_v2_rule | 0.0755 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n25_acc_superiority | phaseA_v2_llm_k3>phaseA_v2_random_open_loop | 0.2887 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n25_acc_superiority | phaseA_v2_llm_k3>phaseA_v2_rule | 0.0494 | 19 | 1 | 5.153e-05 | 5.153e-05 | 5.889e-05 |
| n25_macro_f1_superiority | phaseA_v2_llm_k3>phaseA_v2_random_open_loop | 0.2945 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n25_macro_f1_superiority | phaseA_v2_llm_k3>phaseA_v2_rule | 0.0510 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n50_acc_superiority | phaseA_v2_llm_k3>phaseA_v2_random_open_loop | 0.2252 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n50_acc_superiority | phaseA_v2_llm_k3>phaseA_v2_rule | 0.0401 | 19 | 1 | 6.013e-05 | 6.013e-05 | 6.013e-05 |
| n50_macro_f1_superiority | phaseA_v2_llm_k3>phaseA_v2_random_open_loop | 0.2361 | 20 | 0 | 9.537e-07 | 1.907e-06 | 1.387e-06 |
| n50_macro_f1_superiority | phaseA_v2_llm_k3>phaseA_v2_rule | 0.0416 | 19 | 1 | 1.907e-06 | 1.907e-06 | 2.543e-06 |

## n=50 Auxiliary Checks

| comparison | metric | mean_delta | wins | losses | p_value |
| --- | --- | --- | --- | --- | --- |
| phaseA_v2_llm_k3_vs_phaseA_v2_rule | acc | 0.0401 | 19 | 1 | 1.203e-04 |
| phaseA_v2_llm_k3>real_only | acc | 0.0675 | 19 | 1 | 5.160e-05 |
| phaseA_v2_llm_k3_vs_phaseA_v2_rule | macro_f1 | 0.0416 | 19 | 1 | 3.815e-06 |
| phaseA_v2_llm_k3>real_only | macro_f1 | 0.0830 | 19 | 1 | 1.907e-06 |

## Per-Class F1 Gap

| n_real | class_metric | llm_mean | rule_mean | random_open_loop_mean | real_only_mean | llm_minus_rule |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | f1_healthy | 0.9690 | 0.8420 | 0.3773 | 0.7849 | 0.1270 |
| 5 | f1_OR | 0.6309 | 0.5964 | 0.4471 | 0.5096 | 0.0345 |
| 5 | f1_IR | 0.7265 | 0.6332 | 0.4830 | 0.6106 | 0.0933 |
| 10 | f1_healthy | 0.9809 | 0.9092 | 0.5316 | 0.8223 | 0.0716 |
| 10 | f1_OR | 0.6802 | 0.6391 | 0.3854 | 0.5166 | 0.0410 |
| 10 | f1_IR | 0.7375 | 0.6238 | 0.5463 | 0.5546 | 0.1138 |
| 25 | f1_healthy | 0.9866 | 0.9639 | 0.6145 | 0.8485 | 0.0227 |
| 25 | f1_OR | 0.7125 | 0.6583 | 0.3625 | 0.5681 | 0.0543 |
| 25 | f1_IR | 0.7644 | 0.6883 | 0.6031 | 0.7240 | 0.0761 |
| 50 | f1_healthy | 0.9916 | 0.9852 | 0.7630 | 0.9533 | 0.0064 |
| 50 | f1_OR | 0.7846 | 0.7178 | 0.4591 | 0.6125 | 0.0668 |
| 50 | f1_IR | 0.7978 | 0.7461 | 0.6437 | 0.7592 | 0.0518 |

## Gate Failure Distribution

| source | class | gate | failed_slots_with_gate | failed_slots_total | slots_total | share_of_all_slots |
| --- | --- | --- | --- | --- | --- | --- |
| llm_k3_rescreen_v2 | IR | stats_union | 44 | 44 | 150 | 0.2933 |
| llm_k3_rescreen_v2 | IR | soft_spectrum | 8 | 44 | 150 | 0.0533 |
| llm_k3_rescreen_v2 | IR | psd_w1 | 1 | 44 | 150 | 0.0067 |
| llm_k3_rescreen_v2 | OR | stats_union | 46 | 60 | 150 | 0.3067 |
| llm_k3_rescreen_v2 | OR | soft_spectrum | 22 | 60 | 150 | 0.1467 |
| llm_k3_rescreen_v2 | OR | envelope_multi | 2 | 60 | 150 | 0.0133 |
| llm_k3_rescreen_v2 | healthy | envelope_multi | 53 | 60 | 150 | 0.3533 |
| llm_k3_rescreen_v2 | healthy | psd_w1 | 10 | 60 | 150 | 0.0667 |
| llm_k3_rescreen_v2 | healthy | stats_union | 10 | 60 | 150 | 0.0667 |
| random_plus_verifier | IR | soft_spectrum | 147 | 150 | 150 | 0.9800 |
| random_plus_verifier | IR | stats_union | 145 | 150 | 150 | 0.9667 |
| random_plus_verifier | IR | psd_w1 | 82 | 150 | 150 | 0.5467 |
| random_plus_verifier | IR | envelope_multi | 9 | 150 | 150 | 0.0600 |
| random_plus_verifier | OR | soft_spectrum | 147 | 150 | 150 | 0.9800 |
| random_plus_verifier | OR | stats_union | 131 | 150 | 150 | 0.8733 |
| random_plus_verifier | OR | envelope_multi | 20 | 150 | 150 | 0.1333 |
| random_plus_verifier | OR | psd_w1 | 4 | 150 | 150 | 0.0267 |
| random_plus_verifier | healthy | soft_spectrum | 150 | 150 | 150 | 1.0000 |
| random_plus_verifier | healthy | stats_union | 133 | 150 | 150 | 0.8867 |
| random_plus_verifier | healthy | psd_w1 | 96 | 150 | 150 | 0.6400 |
| random_plus_verifier | healthy | envelope_multi | 60 | 150 | 150 | 0.4000 |
| rule_verified | IR | soft_spectrum | 252 | 341 | 400 | 0.6300 |
| rule_verified | IR | stats_union | 247 | 341 | 400 | 0.6175 |
| rule_verified | OR | stats_union | 56 | 63 | 150 | 0.3733 |
| rule_verified | OR | soft_spectrum | 9 | 63 | 150 | 0.0600 |
| rule_verified | healthy | envelope_multi | 66 | 92 | 150 | 0.4400 |
| rule_verified | healthy | stats_union | 51 | 92 | 150 | 0.3400 |

## Gate Criteria

| criterion | mean_delta | p_value | holm_q_in_family | passed |
| --- | --- | --- | --- | --- |
| n5_acc_llm_gt_phaseA_v2_random_open_loop | 0.3265 | 9.537e-07 | 1.907e-06 | True |
| n5_acc_llm_gt_phaseA_v2_rule | 0.0806 | 6.005e-05 | 6.005e-05 | True |
| n5_macro_f1_llm_gt_phaseA_v2_random_open_loop | 0.3397 | 9.537e-07 | 1.907e-06 | True |
| n5_macro_f1_llm_gt_phaseA_v2_rule | 0.0850 | 9.537e-07 | 1.907e-06 | True |
| n10_acc_llm_gt_phaseA_v2_random_open_loop | 0.3126 | 4.422e-05 | 4.422e-05 | True |
| n10_acc_llm_gt_phaseA_v2_rule | 0.0722 | 9.537e-07 | 1.907e-06 | True |
| n10_macro_f1_llm_gt_phaseA_v2_random_open_loop | 0.3117 | 9.537e-07 | 1.907e-06 | True |
| n10_macro_f1_llm_gt_phaseA_v2_rule | 0.0755 | 9.537e-07 | 1.907e-06 | True |
| n25_acc_llm_gt_phaseA_v2_random_open_loop | 0.2887 | 9.537e-07 | 1.907e-06 | True |
| n25_acc_llm_gt_phaseA_v2_rule | 0.0494 | 5.153e-05 | 5.153e-05 | True |
| n25_macro_f1_llm_gt_phaseA_v2_random_open_loop | 0.2945 | 9.537e-07 | 1.907e-06 | True |
| n25_macro_f1_llm_gt_phaseA_v2_rule | 0.0510 | 9.537e-07 | 1.907e-06 | True |
| n50_acc_llm_not_worse_than_rule | 0.0401 | 1.203e-04 |  | True |
| n50_acc_llm_gt_real_only | 0.0675 | 5.160e-05 |  | True |
| n50_macro_f1_llm_not_worse_than_rule | 0.0416 | 3.815e-06 |  | True |
| n50_macro_f1_llm_gt_real_only | 0.0830 | 1.907e-06 |  | True |

## Decision

Phase-A v2 passes the revised gate.

Supported claim scope: in PU few-shot settings n<=25, LLM recipes significantly outperform random open-loop and rule recipes for both Accuracy and Macro-F1 under the pre-registered Holm-corrected families. At n=50, LLM is not worse than rule under the registered auxiliary check and is superior to real-only.
