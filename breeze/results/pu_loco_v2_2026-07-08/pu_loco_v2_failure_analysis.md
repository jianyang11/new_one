# PU LOCO v2 Failure Analysis

## Status

PU LOCO v2 was executed according to `pu_loco_v2_preregistration.md`.

- Pool construction: passed the preregistered `>=20/class` target in all four folds.
- Additional API calls: 0.
- Downstream completeness: 2400/2400 rows.
- Gate result: failed. `60/96` registered Holm comparisons failed.

## Pool Counts

| heldout | accepted slots | kept healthy | kept OR | kept IR |
|---|---:|---:|---:|---:|
| N09_M07_F10 | 17/18 | 25 | 29 | 22 |
| N15_M01_F10 | 20/22 | 28 | 28 | 25 |
| N15_M07_F04 | 17/17 | 24 | 21 | 23 |
| N15_M07_F10 | 18/21 | 21 | 29 | 36 |

## Four-Fold Mean

| method | n_real | Accuracy | Macro-F1 |
|---|---:|---:|---:|
| LLM v2 | 5 | 0.4203 | 0.3237 |
| noise_aug | 5 | 0.5512 | 0.5041 |
| rule | 5 | 0.4169 | 0.3188 |
| random_open_loop | 5 | 0.3751 | 0.2688 |
| LLM v2 | 10 | 0.4999 | 0.4498 |
| noise_aug | 10 | 0.5897 | 0.5421 |
| rule | 10 | 0.4740 | 0.4120 |
| random_open_loop | 10 | 0.4670 | 0.3885 |
| LLM v2 | 25 | 0.6050 | 0.5699 |
| noise_aug | 25 | 0.6430 | 0.6009 |
| rule | 25 | 0.6081 | 0.5759 |
| random_open_loop | 25 | 0.6138 | 0.5664 |

## v2 vs v1 LLM Delta

| fold | n_real | Accuracy delta | Macro-F1 delta |
|---|---:|---:|---:|
| N09_M07_F10 | 5 | +0.0339 | +0.0355 |
| N09_M07_F10 | 10 | +0.0303 | +0.0451 |
| N09_M07_F10 | 25 | -0.0123 | -0.0026 |
| N15_M01_F10 | 5 | -0.0173 | -0.0048 |
| N15_M01_F10 | 10 | -0.0358 | -0.0272 |
| N15_M01_F10 | 25 | -0.0033 | +0.0057 |
| N15_M07_F04 | 5 | -0.0660 | -0.0510 |
| N15_M07_F04 | 10 | -0.0730 | -0.0544 |
| N15_M07_F04 | 25 | -0.0075 | -0.0043 |
| N15_M07_F10 | 5 | +0.0021 | -0.0340 |
| N15_M07_F10 | 10 | +0.0020 | -0.0016 |
| N15_M07_F10 | 25 | +0.0128 | +0.0127 |

## Per-Class Weakness

- N09_M07_F10: IR remains weak, especially n=5/10.
- N15_M01_F10: IR remains very weak across all shots; n=25 IR F1 is only about 0.186 despite healthy F1 being high.
- N15_M07_F04: OR is the weak class across all shots.
- N15_M07_F10: OR is the weak class across all shots.

## Interpretation

The frequency-mismatch diagnosis was real, and v2 corrected the kinematic fields. However, kinematic correction alone did not make the LOCO pool competitive with `noise_aug`. The likely remaining issue is non-frequency morphology mismatch across load/torque conditions: amplitude, resonance-band energy, and class-specific OR/IR morphology do not extrapolate by rpm alone.

This result must not be reported as a successful cross-condition claim. It can be reported as a failed preregistered v2 attempt unless a new preregistered LOCO v3 is designed using training-fold validation only.
