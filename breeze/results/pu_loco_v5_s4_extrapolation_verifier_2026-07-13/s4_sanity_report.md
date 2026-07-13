# PU LOCO v5 S4 extrapolation sanity audit

## Boundary

all audits are train-bearing-only; no pseudo-held-out or formal held-out waveform is read

## Decision

- Overall sanity status: **FAIL**.
- Predeclared healthy criterion: pooled raw rate >= 0.60 and every source raw rate >= 0.40.
- Predeclared negative-control criterion: 0 admitted wrong-label, white-noise, and constant windows.

## Healthy carrier admission

| target | pooled raw rate | source raw rates | target sanity |
|---|---:|---|---|
| N09_M07_F10 | 0.290 | N15_M01_F10=0.310, N15_M07_F04=0.240, N15_M07_F10=0.320 | FAIL |

## Negative controls

| target | control | admitted / n |
|---|---|---:|
| N09_M07_F10 | real_OR_labeled_IR | 76 / 100 |
| N09_M07_F10 | real_IR_labeled_OR | 62 / 100 |
| N09_M07_F10 | white_noise_labeled_healthy | 0 / 100 |
| N09_M07_F10 | white_noise_labeled_OR | 83 / 100 |
| N09_M07_F10 | white_noise_labeled_IR | 0 / 100 |
| N09_M07_F10 | constant_labeled_healthy | 0 / 100 |
| N09_M07_F10 | constant_labeled_OR | 0 / 100 |
| N09_M07_F10 | constant_labeled_IR | 0 / 100 |

## Fault transfer audit

The source-kinematics column measures morphology-boundary transfer. The literal-target column is a strict kinematic mismatch control, not a success metric.

| target | source | class | transfer pass / n | literal-target pass / n |
|---|---|---|---:|---:|
| N09_M07_F10 | N15_M01_F10 | OR | 98 / 100 | 100 / 100 |
| N09_M07_F10 | N15_M01_F10 | IR | 92 / 100 | 92 / 100 |
| N09_M07_F10 | N15_M07_F04 | OR | 97 / 100 | 99 / 100 |
| N09_M07_F10 | N15_M07_F04 | IR | 77 / 100 | 80 / 100 |
| N09_M07_F10 | N15_M07_F10 | OR | 95 / 100 | 96 / 100 |
| N09_M07_F10 | N15_M07_F10 | IR | 91 / 100 | 92 / 100 |
