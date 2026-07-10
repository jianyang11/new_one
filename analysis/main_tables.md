# BREEZE Main Analysis Tables

Date: 2026-07-04

All numbers below are derived from local CSV/JSON outputs. Do not cite any
number that is not traceable to the source path listed with the table.

## Table A. PU Main Downstream Results

Source: `breeze/results/downstream_file.csv`

Rows: 14 baselines x 3 few-shot settings x 8 seeds = 336.

| baseline | n_real/class | accuracy mean | accuracy std | macro-F1 mean | macro-F1 std |
|---|---:|---:|---:|---:|---:|
| real_only | 10 | 0.6447 | 0.1085 | 0.6038 | 0.1290 |
| real_only | 25 | 0.7370 | 0.0374 | 0.7184 | 0.0426 |
| real_only | 50 | 0.7886 | 0.0195 | 0.7748 | 0.0252 |
| open_loop_basic | 10 | 0.3971 | 0.0744 | 0.2827 | 0.1060 |
| open_loop_basic | 25 | 0.6522 | 0.0656 | 0.5934 | 0.0905 |
| open_loop_basic | 50 | 0.6415 | 0.0236 | 0.5862 | 0.0509 |
| open_loop_phys | 10 | 0.7834 | 0.0408 | 0.7870 | 0.0411 |
| open_loop_phys | 25 | 0.8186 | 0.0221 | 0.8185 | 0.0254 |
| open_loop_phys | 50 | 0.8498 | 0.0219 | 0.8537 | 0.0218 |
| stats_only | 10 | 0.7196 | 0.0382 | 0.7193 | 0.0401 |
| stats_only | 25 | 0.7754 | 0.0371 | 0.7724 | 0.0385 |
| stats_only | 50 | 0.8268 | 0.0234 | 0.8290 | 0.0234 |
| envelope_only | 10 | 0.7964 | 0.0337 | 0.7991 | 0.0312 |
| envelope_only | 25 | 0.8180 | 0.0267 | 0.8178 | 0.0292 |
| envelope_only | 50 | 0.8439 | 0.0238 | 0.8469 | 0.0234 |
| breeze_k0 | 10 | 0.7135 | 0.0427 | 0.7141 | 0.0430 |
| breeze_k0 | 25 | 0.7999 | 0.0231 | 0.7994 | 0.0278 |
| breeze_k0 | 50 | 0.8324 | 0.0233 | 0.8334 | 0.0231 |
| breeze_k1 | 10 | 0.7327 | 0.0610 | 0.7350 | 0.0596 |
| breeze_k1 | 25 | 0.8002 | 0.0249 | 0.7994 | 0.0247 |
| breeze_k1 | 50 | 0.8224 | 0.0666 | 0.8211 | 0.0801 |
| breeze_k2 | 10 | 0.7196 | 0.0636 | 0.7187 | 0.0730 |
| breeze_k2 | 25 | 0.7773 | 0.0220 | 0.7783 | 0.0187 |
| breeze_k2 | 50 | 0.8381 | 0.0224 | 0.8402 | 0.0236 |
| breeze_k3 | 10 | 0.7283 | 0.0667 | 0.7304 | 0.0682 |
| breeze_k3 | 25 | 0.7844 | 0.0247 | 0.7853 | 0.0215 |
| breeze_k3 | 50 | 0.8317 | 0.0138 | 0.8336 | 0.0143 |
| noise_aug | 10 | 0.6992 | 0.0544 | 0.7008 | 0.0586 |
| noise_aug | 25 | 0.8225 | 0.0508 | 0.8192 | 0.0544 |
| noise_aug | 50 | 0.8616 | 0.0235 | 0.8635 | 0.0233 |
| vae | 10 | 0.6821 | 0.0893 | 0.6641 | 0.1067 |
| vae | 25 | 0.7605 | 0.0317 | 0.7482 | 0.0422 |
| vae | 50 | 0.8314 | 0.0719 | 0.8278 | 0.0839 |
| gan | 10 | 0.7179 | 0.0829 | 0.7155 | 0.0842 |
| gan | 25 | 0.7851 | 0.0544 | 0.7716 | 0.0583 |
| gan | 50 | 0.8484 | 0.0281 | 0.8492 | 0.0265 |
| vae_fs | 10 | 0.6298 | 0.0798 | 0.6047 | 0.1058 |
| vae_fs | 25 | 0.7547 | 0.0703 | 0.7397 | 0.0861 |
| vae_fs | 50 | 0.8104 | 0.0442 | 0.8079 | 0.0478 |
| gan_fs | 10 | 0.7109 | 0.0652 | 0.7012 | 0.0759 |
| gan_fs | 25 | 0.7554 | 0.0646 | 0.7377 | 0.0765 |
| gan_fs | 50 | 0.8454 | 0.0362 | 0.8430 | 0.0388 |

Claim boundary: BREEZE variants improve over real-only but are not the
highest-accuracy methods in every setting. `noise_aug` is strongest at 50-shot
in this table.

## Table B. PU v2 Gate-Admitted Pool Downstream Results

Source: `breeze/results/custom_pool_eval.csv`

`breeze_v2_full` pool: `breeze/runs/rescreen_v2_full/pool_v2.npz`, 757 samples
with class counts healthy 192 / OR 304 / IR 261.

| baseline | n_real/class | accuracy mean | accuracy std | macro-F1 mean | macro-F1 std | F1 healthy | F1 OR | F1 IR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| real_only | 10 | 0.6449 | 0.1087 | 0.6040 | 0.1292 | 0.8283 | 0.5178 | 0.4658 |
| breeze_v2_full | 10 | 0.7880 | 0.0312 | 0.7906 | 0.0289 | 0.9786 | 0.6673 | 0.7260 |
| real_only | 25 | 0.7371 | 0.0372 | 0.7184 | 0.0425 | 0.8577 | 0.5684 | 0.7293 |
| breeze_v2_full | 25 | 0.8082 | 0.0324 | 0.8079 | 0.0354 | 0.9795 | 0.6784 | 0.7657 |
| real_only | 50 | 0.7881 | 0.0197 | 0.7743 | 0.0253 | 0.9499 | 0.6087 | 0.7643 |
| breeze_v2_full | 50 | 0.8456 | 0.0174 | 0.8484 | 0.0178 | 0.9918 | 0.7619 | 0.7914 |

Paired Wilcoxon, `breeze_v2_full` vs `real_only`:

| n_real/class | delta accuracy | p |
|---:|---:|---:|
| 10 | +0.1433 | 0.0078125 |
| 25 | +0.0712 | 0.0156250 |
| 50 | +0.0570 | 0.0078125 |

## Table C. v2 vs Main Strong Baselines

Sources:
- `breeze/results/significance_v2_vs_main.csv` for the original focused
  paired tests.
- `breeze/results/revision_v2_significance_all_baselines_bh.csv` for the
  revised Benjamini-Hochberg q-values over the full 42-test family
  (14 baselines x 3 few-shot settings).

| n_real/class | comparator | v2 mean | comparator mean | delta | Wilcoxon p | BH q over 42 |
|---:|---|---:|---:|---:|---:|---:|
| 10 | real_only | 0.7880 | 0.6447 | +0.1433 | 0.0078 | 0.0328 |
| 10 | breeze_k3 | 0.7880 | 0.7283 | +0.0597 | 0.0156 | 0.0438 |
| 10 | stats_only | 0.7880 | 0.7196 | +0.0684 | 0.0078 | 0.0328 |
| 10 | envelope_only | 0.7880 | 0.7964 | -0.0084 | 0.2109 | 0.3281 |
| 10 | open_loop_phys | 0.7880 | 0.7834 | +0.0046 | 0.8438 | 0.8643 |
| 10 | noise_aug | 0.7880 | 0.6992 | +0.0888 | 0.0078 | 0.0328 |
| 25 | real_only | 0.8082 | 0.7370 | +0.0712 | 0.0156 | 0.0438 |
| 25 | breeze_k3 | 0.8082 | 0.7844 | +0.0238 | 0.0547 | 0.1209 |
| 25 | stats_only | 0.8082 | 0.7754 | +0.0329 | 0.1016 | 0.1939 |
| 25 | envelope_only | 0.8082 | 0.8180 | -0.0098 | 0.4609 | 0.6165 |
| 25 | open_loop_phys | 0.8082 | 0.8186 | -0.0104 | 0.7422 | 0.8203 |
| 25 | noise_aug | 0.8082 | 0.8225 | -0.0143 | 0.3828 | 0.5359 |
| 50 | real_only | 0.8456 | 0.7886 | +0.0570 | 0.0078 | 0.0328 |
| 50 | breeze_k3 | 0.8456 | 0.8317 | +0.0139 | 0.0391 | 0.0965 |
| 50 | stats_only | 0.8456 | 0.8268 | +0.0188 | 0.1953 | 0.3155 |
| 50 | envelope_only | 0.8456 | 0.8439 | +0.0017 | 0.8438 | 0.8643 |
| 50 | open_loop_phys | 0.8456 | 0.8498 | -0.0042 | 0.5469 | 0.6756 |
| 50 | noise_aug | 0.8456 | 0.8616 | -0.0160 | 0.1484 | 0.2494 |

Claim boundary: after correction across all 42 v2-vs-main-baseline tests, the
defensible significance claim is v2 vs real-only at 10/25/50 shots and selected
easy comparators. The manuscript must not claim uniform superiority over
`open_loop_phys`, `envelope_only`, or `noise_aug`.

## Table D. Physical Metrics

Sources:
- `breeze/results/pool_metrics.csv`
- `breeze/results/pool_metrics_v2.csv`

| pool | class | n | MMD2 | NN diversity | real-real NN diversity |
|---|---|---:|---:|---:|---:|
| open_loop_basic | healthy | 135 | 0.7769 | 1.3263 | 0.8910 |
| open_loop_basic | OR | 142 | 1.2786 | 0.7972 | 0.4122 |
| open_loop_basic | IR | 139 | 1.5248 | 1.6169 | 0.8598 |
| open_loop_phys | healthy | 150 | 0.1481 | 0.3495 | 0.8910 |
| open_loop_phys | OR | 150 | 0.0451 | 0.4224 | 0.4122 |
| open_loop_phys | IR | 150 | 0.0829 | 0.7162 | 0.8598 |
| envelope_only | healthy | 150 | 0.1481 | 0.3495 | 0.8910 |
| envelope_only | OR | 143 | 0.0474 | 0.4412 | 0.4122 |
| envelope_only | IR | 149 | 0.0821 | 0.7163 | 0.8598 |
| breeze_k3 | healthy | 519 | 0.1378 | 0.3305 | 0.8910 |
| breeze_k3 | OR | 638 | 0.0776 | 0.4239 | 0.4122 |
| breeze_k3 | IR | 390 | 0.1990 | 0.6919 | 0.8598 |
| breeze_v2_full | healthy | 192 | 0.1507 | 0.3468 | 0.8910 |
| breeze_v2_full | OR | 304 | 0.0713 | 0.4212 | 0.4122 |
| breeze_v2_full | IR | 261 | 0.1254 | 0.7123 | 0.8598 |

Claim boundary: v2 improves MMD2 over v1 for OR and IR, but not for healthy;
`open_loop_phys` and `envelope_only` remain strong on this feature-MMD metric.

## Table E. Verifier Coverage Sensitivity

Source: `breeze/results/calibration_sensitivity.csv`

| coverage | split | all pass rate | healthy | OR | IR | fail boundary | fail energy | fail envelope | fail MCSA | fail spectrum |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| c85 | train | 0.9285 | 0.9300 | 0.9285 | 0.9273 | 78 | 25 | 51 | 42 | 104 |
| c85 | test | 0.8992 | 0.9100 | 0.8970 | 0.8920 | 23 | 14 | 15 | 12 | 44 |
| c90 | train | 0.9368 | 0.9425 | 0.9326 | 0.9356 | 75 | 16 | 34 | 36 | 104 |
| c90 | test | 0.9148 | 0.9400 | 0.9103 | 0.8975 | 22 | 7 | 7 | 9 | 44 |
| c95 | train | 0.9441 | 0.9467 | 0.9443 | 0.9418 | 75 | 10 | 22 | 20 | 104 |
| c95 | test | 0.9210 | 0.9400 | 0.9169 | 0.9086 | 22 | 6 | 7 | 4 | 44 |

Interpretation: broader coverage increases train/test pass rates only modestly
because the spectrum gate is invariant across these calibrations in the current
v1 verifier. v2 was introduced partly to reduce this hard-band sensitivity.

## Table F. Private Machine-Tool Dataset

Sources:
- `breeze/results/mt_verifier_real_pass.csv`
- `breeze/results/mt_real_only_eval.csv`
- `reports/machine_tool_experiment_2026-07-04.md`

Local dataset documentation states that the private machine-tool data were
collected with four synchronous NI acquisition channels at 4000 Hz and contain
normal machining, lead-screw anomaly, and base imbalance. The local files still
do not map prefixes `1/2/3` to those state names, so all numerical tables keep
anonymous labels `MT-1/MT-2/MT-3`.

Verifier pass rates:

| split | class | n | pass rate | fail stats | fail soft spectrum | fail PSD-W1 |
|---|---|---:|---:|---:|---:|---:|
| train | MT-1 | 675 | 0.9585 | 4 | 2 | 25 |
| train | MT-2 | 383 | 0.9530 | 2 | 2 | 16 |
| train | MT-3 | 679 | 0.9381 | 4 | 4 | 39 |
| test | MT-1 | 166 | 0.7590 | 38 | 5 | 34 |
| test | MT-2 | 166 | 0.9337 | 0 | 5 | 11 |
| test | MT-3 | 154 | 0.7727 | 0 | 0 | 35 |

Real-only downstream:

| n_real/class | rows | accuracy mean | accuracy std | macro-F1 mean | macro-F1 std | F1 MT-1 | F1 MT-2 | F1 MT-3 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 8 | 0.3431 | 0.0321 | 0.3368 | 0.0318 | 0.3914 | 0.3402 | 0.2788 |
| 25 | 8 | 0.4964 | 0.0566 | 0.4897 | 0.0530 | 0.4792 | 0.4781 | 0.5119 |
| 50 | 8 | 0.7006 | 0.0626 | 0.7021 | 0.0632 | 0.6362 | 0.6750 | 0.7951 |

Claim boundary: no machine-tool BREEZE augmentation is available yet. These
numbers support portability of the verifier schema and provide a real-only
private-data baseline only.
