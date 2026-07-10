# Berkeley Inner-Train Diagnostics

This is a zero-API diagnostic pass. All reference distributions come from `milling_berkeley_inner_train.npz`; no held-out Berkeley test signal is used.

## Inputs

- inner_train windows: 1462; counts: {"sharp": 510, "worn": 578, "severe": 374}
- inner_val windows: 374; counts: {"sharp": 119, "worn": 153, "severe": 102}
- diagnostic synthetic budget: 20/class for LLM, rule, random_open_loop, and noise_aug.
- spindle harmonics/TPF used for diagnostics: [13.766667, 27.533333, 41.3, 55.066667, 68.833333, 82.6]

Important caveat: the inspected current LLM/rule/random pools were built before the inner split existed. They are valid for failure diagnosis, but not valid as final inner-validation artifacts for choosing a formal protocol.

## PSD And Band-Energy Distance

| method | mean PSD-W1 | mean band L1 |
|---|---:|---:|
| llm | 6.2857 | 0.4136 |
| noise_aug | 4.8154 | 0.1977 |
| random_open_loop | 6.2599 | 0.3328 |
| rule | 5.2248 | 0.3315 |

Largest single PSD/band mismatches:
- noise_aug / sharp / smcDC: PSD-W1=18.783532, bandL1=0.536917
- llm / severe / vib_table: PSD-W1=14.866429, bandL1=0.625407
- random_open_loop / worn / vib_table: PSD-W1=14.577591, bandL1=0.573918
- llm / severe / vib_spindle: PSD-W1=12.500005, bandL1=0.738925
- noise_aug / worn / smcDC: PSD-W1=11.230906, bandL1=0.339772
- rule / worn / vib_spindle: PSD-W1=10.985939, bandL1=0.621413
- random_open_loop / worn / vib_spindle: PSD-W1=10.835191, bandL1=0.683736
- llm / worn / smcDC: PSD-W1=10.676042, bandL1=1.318530
- noise_aug / severe / smcDC: PSD-W1=10.523206, bandL1=0.258316
- random_open_loop / severe / vib_spindle: PSD-W1=10.318506, bandL1=0.583036

## Statistics And Channel Structure

| method | mean corr Frobenius delta | mean channel-energy L1 |
|---|---:|---:|
| llm | 0.5797 | 0.0176 |
| noise_aug | 0.2325 | 0.0180 |
| random_open_loop | 1.1454 | 0.2289 |
| rule | 0.3604 | 0.0109 |

Largest median feature deltas by absolute relative shift:
- noise_aug / severe / ch1_band5_frac: real=4.7754056e-05, method=0.12374614, robust_z=1696.541541, overlap=0.050000
- noise_aug / severe / ch1_band4_frac: real=7.6755411e-05, method=0.19238346, robust_z=1477.208648, overlap=0.050000
- noise_aug / worn / ch1_band5_frac: real=4.343938e-05, method=0.083851136, robust_z=927.050279, overlap=0.003460
- noise_aug / worn / ch1_band4_frac: real=6.3335488e-05, method=0.096081079, robust_z=685.787582, overlap=0.056920
- noise_aug / sharp / ch1_band3_frac: real=0.00022422419, method=0.12060712, robust_z=682.094498, overlap=0.023529
- noise_aug / sharp / ch1_band4_frac: real=0.00012508713, method=0.10529037, robust_z=672.781394, overlap=0.013725
- noise_aug / sharp / ch1_band5_frac: real=9.4011587e-05, method=0.080225618, robust_z=649.381163, overlap=0.000000
- noise_aug / severe / ch1_band3_frac: real=0.00017953859, method=0.17598459, robust_z=578.303227, overlap=0.050000
- noise_aug / worn / ch1_band3_frac: real=0.00017600102, method=0.10411467, robust_z=387.316887, overlap=0.113841
- random_open_loop / severe / ch1_band5_frac: real=4.7754056e-05, method=0.020532966, robust_z=280.957693, overlap=0.000000
- random_open_loop / worn / ch1_band5_frac: real=4.343938e-05, method=0.020441721, robust_z=225.638372, overlap=0.000000
- random_open_loop / severe / ch1_band4_frac: real=7.6755411e-05, method=0.024329649, robust_z=186.299195, overlap=0.000000

## Class-Ordering Check

No LLM key ordering feature has Spearman rho < 0.5 against the real class medians.

## Files

- `berkeley_inner_psd_w1.csv`
- `berkeley_inner_band_energy.csv`
- `berkeley_inner_stats_overlap.csv`
- `berkeley_inner_channel_structure.csv`
- `berkeley_inner_class_ordering.csv`
- `berkeley_noise_aug_diagnostic_pool.npz`
