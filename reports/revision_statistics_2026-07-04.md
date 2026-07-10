# BREEZE Revision Statistics

Date: 2026-07-04

All numbers are derived from existing frozen outputs; no new LLM generation was run.

## v2 Slot/Window Mapping

| block | slots | accepted_slots_before_diversity | accepted_items_before_diversity | kept_after_diversity | kept_selected_windows | kept_expansion_windows | few_shot_cap_windows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 450 | 286 | 761 | 757 | 284 | 473 | 592 |
| healthy | 150 | 90 | 196 | 192 | 88 | 104 | 192 |
| OR | 150 | 90 | 304 | 304 | 90 | 214 | 200 |
| IR | 150 | 106 | 261 | 261 | 106 | 155 | 200 |

Interpretation: a slot is one requested LLM generation unit. A feasible slot can
contribute the selected round window and zero or more feasible expansion windows.
The full v2 offline rescreening admits 286/450 slots, produces 761 accepted
items before diversity, and keeps 757 windows after diversity. Few-shot training
uses a 200-window/class cap, so the v2 training budget is 192+200+200=592.

## Candidate-Level Failed Gates

| scope | class | kind | gate | count | evaluations | rate_per_evaluation |
| --- | --- | --- | --- | --- | --- | --- |
| candidate_or_expansion | IR | expansion | soft_spectrum | 10 | 222 | 0.045045 |
| candidate_or_expansion | IR | expansion | stats_union | 59 | 222 | 0.265766 |
| candidate_or_expansion | IR | round | psd_w1 | 1 | 383 | 0.00261097 |
| candidate_or_expansion | IR | round | soft_spectrum | 23 | 383 | 0.0600522 |
| candidate_or_expansion | IR | round | stats_union | 237 | 383 | 0.618799 |
| candidate_or_expansion | OR | expansion | soft_spectrum | 41 | 319 | 0.128527 |
| candidate_or_expansion | OR | expansion | stats_union | 67 | 319 | 0.210031 |
| candidate_or_expansion | OR | round | envelope_multi | 7 | 238 | 0.0294118 |
| candidate_or_expansion | OR | round | soft_spectrum | 22 | 238 | 0.092437 |
| candidate_or_expansion | OR | round | stats_union | 122 | 238 | 0.512605 |
| candidate_or_expansion | healthy | expansion | envelope_multi | 103 | 218 | 0.472477 |
| candidate_or_expansion | healthy | expansion | psd_w1 | 13 | 218 | 0.059633 |
| candidate_or_expansion | healthy | expansion | stats_union | 6 | 218 | 0.0275229 |
| candidate_or_expansion | healthy | round | envelope_multi | 133 | 301 | 0.44186 |
| candidate_or_expansion | healthy | round | psd_w1 | 19 | 301 | 0.0631229 |
| candidate_or_expansion | healthy | round | stats_union | 49 | 301 | 0.162791 |

## Terminal Rejected-Slot Failed Gates

| scope | class | kind | gate | count | evaluations | rate_per_evaluation |
| --- | --- | --- | --- | --- | --- | --- |
| terminal_rejected_slot | IR | slot | soft_spectrum | 7 | 44 | 0.159091 |
| terminal_rejected_slot | IR | slot | stats_union | 43 | 44 | 0.977273 |
| terminal_rejected_slot | OR | slot | soft_spectrum | 21 | 60 | 0.35 |
| terminal_rejected_slot | OR | slot | stats_union | 45 | 60 | 0.75 |
| terminal_rejected_slot | healthy | slot | envelope_multi | 51 | 60 | 0.85 |
| terminal_rejected_slot | healthy | slot | psd_w1 | 10 | 60 | 0.166667 |
| terminal_rejected_slot | healthy | slot | stats_union | 4 | 60 | 0.0666667 |

## Paired Wilcoxon With BH Correction

| n_real | baseline | v2_mean | other_mean | delta | p_wilcoxon | q_bh_all_18 | significant_at_fdr_0_05 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | breeze_k3 | 0.78795 | 0.7283 | 0.05965 | 0.015625 | 0.046875 | True |
| 10 | stats_only | 0.78795 | 0.719588 | 0.0683625 | 0.0078125 | 0.0351562 | True |
| 10 | envelope_only | 0.78795 | 0.7964 | -0.00845 | 0.210938 | 0.316406 | False |
| 10 | open_loop_phys | 0.78795 | 0.783387 | 0.0045625 | 0.84375 | 0.84375 | False |
| 10 | noise_aug | 0.78795 | 0.699187 | 0.0887625 | 0.0078125 | 0.0351562 | True |
| 10 | real_only | 0.78795 | 0.64465 | 0.1433 | 0.0078125 | 0.0351562 | True |
| 25 | breeze_k3 | 0.808213 | 0.784438 | 0.023775 | 0.0546875 | 0.123047 | False |
| 25 | stats_only | 0.808213 | 0.77535 | 0.0328625 | 0.101562 | 0.203125 | False |
| 25 | envelope_only | 0.808213 | 0.817963 | -0.00975 | 0.460938 | 0.592634 | False |
| 25 | open_loop_phys | 0.808213 | 0.818612 | -0.0104 | 0.742188 | 0.834961 | False |
| 25 | noise_aug | 0.808213 | 0.822512 | -0.0143 | 0.382812 | 0.530048 | False |
| 25 | real_only | 0.808213 | 0.737 | 0.0712125 | 0.015625 | 0.046875 | True |
| 50 | breeze_k3 | 0.845612 | 0.831725 | 0.0138875 | 0.0390625 | 0.100446 | False |
| 50 | stats_only | 0.845612 | 0.8268 | 0.0188125 | 0.195312 | 0.316406 | False |
| 50 | envelope_only | 0.845612 | 0.843938 | 0.001675 | 0.84375 | 0.84375 | False |
| 50 | open_loop_phys | 0.845612 | 0.8498 | -0.0041875 | 0.546875 | 0.65625 | False |
| 50 | noise_aug | 0.845612 | 0.861625 | -0.0160125 | 0.148438 | 0.267188 | False |
| 50 | real_only | 0.845612 | 0.788587 | 0.057025 | 0.0078125 | 0.0351562 | True |

Multiple-testing note: q-values use Benjamini-Hochberg correction across all
18 v2-vs-comparator tests in `significance_v2_vs_main.csv`.

## Full v2 vs All Main Baselines

| n_real | baseline | v2_mean | other_mean | delta | p_wilcoxon | q_bh_all_baselines | significant_at_fdr_0_05 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | breeze_k0 | 0.78795 | 0.713487 | 0.0744625 | 0.0078125 | 0.0328125 | True |
| 10 | breeze_k1 | 0.78795 | 0.732725 | 0.055225 | 0.0546875 | 0.120888 | False |
| 10 | breeze_k2 | 0.78795 | 0.7196 | 0.06835 | 0.0078125 | 0.0328125 | True |
| 10 | breeze_k3 | 0.78795 | 0.7283 | 0.05965 | 0.015625 | 0.04375 | True |
| 10 | envelope_only | 0.78795 | 0.7964 | -0.00845 | 0.210938 | 0.328125 | False |
| 10 | gan | 0.78795 | 0.717912 | 0.0700375 | 0.109375 | 0.199728 | False |
| 10 | gan_fs | 0.78795 | 0.7109 | 0.07705 | 0.015625 | 0.04375 | True |
| 10 | noise_aug | 0.78795 | 0.699187 | 0.0887625 | 0.0078125 | 0.0328125 | True |
| 10 | open_loop_basic | 0.78795 | 0.3971 | 0.39085 | 0.0078125 | 0.0328125 | True |
| 10 | open_loop_phys | 0.78795 | 0.783387 | 0.0045625 | 0.84375 | 0.864329 | False |
| 10 | real_only | 0.78795 | 0.64465 | 0.1433 | 0.0078125 | 0.0328125 | True |
| 10 | stats_only | 0.78795 | 0.719588 | 0.0683625 | 0.0078125 | 0.0328125 | True |
| 10 | vae | 0.78795 | 0.682063 | 0.105888 | 0.0390625 | 0.0965074 | False |
| 10 | vae_fs | 0.78795 | 0.629812 | 0.158138 | 0.0078125 | 0.0328125 | True |
| 25 | breeze_k0 | 0.808213 | 0.7999 | 0.0083125 | 0.640625 | 0.727196 | False |
| 25 | breeze_k1 | 0.808213 | 0.80015 | 0.0080625 | 0.484375 | 0.616477 | False |
| 25 | breeze_k2 | 0.808213 | 0.777287 | 0.030925 | 0.015625 | 0.04375 | True |
| 25 | breeze_k3 | 0.808213 | 0.784438 | 0.023775 | 0.0546875 | 0.120888 | False |
| 25 | envelope_only | 0.808213 | 0.817963 | -0.00975 | 0.460938 | 0.616477 | False |
| 25 | gan | 0.808213 | 0.7851 | 0.0231125 | 0.3125 | 0.452586 | False |
| 25 | gan_fs | 0.808213 | 0.75545 | 0.0527625 | 0.078125 | 0.15625 | False |
| 25 | noise_aug | 0.808213 | 0.822512 | -0.0143 | 0.382812 | 0.535937 | False |
| 25 | open_loop_basic | 0.808213 | 0.65215 | 0.156062 | 0.0078125 | 0.0328125 | True |
| 25 | open_loop_phys | 0.808213 | 0.818612 | -0.0104 | 0.742188 | 0.820312 | False |
| 25 | real_only | 0.808213 | 0.737 | 0.0712125 | 0.015625 | 0.04375 | True |
| 25 | stats_only | 0.808213 | 0.77535 | 0.0328625 | 0.101562 | 0.193892 | False |
| 25 | vae | 0.808213 | 0.760525 | 0.0476875 | 0.015625 | 0.04375 | True |
| 25 | vae_fs | 0.808213 | 0.754675 | 0.0535375 | 0.148438 | 0.249375 | False |
| 50 | breeze_k0 | 0.845612 | 0.832388 | 0.013225 | 0.476562 | 0.616477 | False |
| 50 | breeze_k1 | 0.845612 | 0.822388 | 0.023225 | 0.640625 | 0.727196 | False |
| 50 | breeze_k2 | 0.845612 | 0.838088 | 0.007525 | 0.3125 | 0.452586 | False |
| 50 | breeze_k3 | 0.845612 | 0.831725 | 0.0138875 | 0.0390625 | 0.0965074 | False |
| 50 | envelope_only | 0.845612 | 0.843938 | 0.001675 | 0.84375 | 0.864329 | False |
| 50 | gan | 0.845612 | 0.848362 | -0.00275 | 0.640625 | 0.727196 | False |
| 50 | gan_fs | 0.845612 | 0.845375 | 0.0002375 | 0.96875 | 0.96875 | False |
| 50 | noise_aug | 0.845612 | 0.861625 | -0.0160125 | 0.148438 | 0.249375 | False |
| 50 | open_loop_basic | 0.845612 | 0.6415 | 0.204113 | 0.0078125 | 0.0328125 | True |
| 50 | open_loop_phys | 0.845612 | 0.8498 | -0.0041875 | 0.546875 | 0.675551 | False |
| 50 | real_only | 0.845612 | 0.788587 | 0.057025 | 0.0078125 | 0.0328125 | True |
| 50 | stats_only | 0.845612 | 0.8268 | 0.0188125 | 0.195312 | 0.315505 | False |
| 50 | vae | 0.845612 | 0.83135 | 0.0142625 | 0.84375 | 0.864329 | False |
| 50 | vae_fs | 0.845612 | 0.810412 | 0.0352 | 0.078125 | 0.15625 | False |

Multiple-testing note: q-values in this full table use Benjamini-Hochberg
correction across all v2-vs-main-baseline tests in
`revision_v2_significance_all_baselines_bh.csv`.

## MMD2 Protocol

The MMD2 tables use `breeze/src/metrics.py::pool_metrics`. For each class,
the script extracts up to 150 synthetic windows and up to 150 train-real
windows, computes an eight-dimensional vibration-channel feature vector
(RMS, kurtosis, crest factor, skewness, and four Welch-PSD band-energy
fractions over 0-500, 500-1500, 1500-2500, and 2500-4000 Hz), standardizes
features by the sampled real mean and standard deviation, and computes
RBF-kernel MMD2 using the median pairwise-distance bandwidth heuristic.
Nearest-neighbour diversity is the mean within-pool NN distance in the same
standardized feature space, reported next to the real-real reference.

