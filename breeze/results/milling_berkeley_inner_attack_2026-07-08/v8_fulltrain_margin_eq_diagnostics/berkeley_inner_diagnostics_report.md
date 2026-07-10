# Berkeley Inner-Train Diagnostics

This is a zero-API diagnostic pass. All reference distributions come from `milling_berkeley_inner_train.npz`; no held-out Berkeley test signal is used.

## Inputs

- inner_train windows: 1462; counts: {"sharp": 510, "worn": 578, "severe": 374}
- inner_val windows: 374; counts: {"sharp": 119, "worn": 153, "severe": 102}
- diagnostic synthetic budget: 40/class for LLM, rule, random_open_loop, and noise_aug.
- spindle harmonics/TPF used for diagnostics: [13.766667, 27.533333, 41.3, 55.066667, 68.833333, 82.6]

Important caveat: the inspected current LLM/rule/random pools were built before the inner split existed. They are valid for failure diagnosis, but not valid as final inner-validation artifacts for choosing a formal protocol.

## PSD And Band-Energy Distance

| method | mean PSD-W1 | mean band L1 |
|---|---:|---:|
| llm | 3.6593 | 0.2231 |
| noise_aug | 4.3518 | 0.1697 |
| random_open_loop | 6.2476 | 0.3334 |
| rule | 4.9236 | 0.3254 |

Largest single PSD/band mismatches:
- noise_aug / severe / smcDC: PSD-W1=23.728770, bandL1=0.817796
- random_open_loop / worn / vib_table: PSD-W1=14.151077, bandL1=0.567027
- noise_aug / sharp / smcDC: PSD-W1=12.392840, bandL1=0.339099
- rule / worn / vib_spindle: PSD-W1=11.658919, bandL1=0.653047
- random_open_loop / worn / vib_spindle: PSD-W1=10.465898, bandL1=0.671194
- random_open_loop / severe / vib_spindle: PSD-W1=9.871973, bandL1=0.583049
- rule / severe / vib_spindle: PSD-W1=9.732828, bandL1=0.594273
- random_open_loop / worn / AE_table: PSD-W1=9.595482, bandL1=0.389248
- rule / sharp / vib_spindle: PSD-W1=8.585323, bandL1=0.725638
- noise_aug / severe / vib_table: PSD-W1=8.426261, bandL1=0.284764

## Statistics And Channel Structure

| method | mean corr Frobenius delta | mean channel-energy L1 |
|---|---:|---:|
| llm | 0.3179 | 0.0192 |
| noise_aug | 0.1837 | 0.0092 |
| random_open_loop | 1.1855 | 0.2331 |
| rule | 0.3103 | 0.0109 |

Largest median feature deltas by absolute relative shift:
- noise_aug / severe / ch1_band5_frac: real=4.7754056e-05, method=0.088142387, robust_z=1208.230848, overlap=0.000000
- noise_aug / worn / ch1_band5_frac: real=4.343938e-05, method=0.096680629, robust_z=1068.965462, overlap=0.050000
- noise_aug / worn / ch1_band4_frac: real=6.3335488e-05, method=0.11445991, robust_z=817.054699, overlap=0.060381
- noise_aug / severe / ch1_band4_frac: real=7.6755411e-05, method=0.095157325, robust_z=730.363732, overlap=0.000000
- noise_aug / sharp / ch1_band4_frac: real=0.00012508713, method=0.093148251, robust_z=595.103744, overlap=0.050980
- noise_aug / sharp / ch1_band5_frac: real=9.4011587e-05, method=0.072737712, robust_z=588.699674, overlap=0.000000
- noise_aug / sharp / ch1_band3_frac: real=0.00022422419, method=0.099080688, robust_z=560.124843, overlap=0.156373
- noise_aug / worn / ch1_band3_frac: real=0.00017600102, method=0.10388954, robust_z=386.477960, overlap=0.149221
- noise_aug / severe / ch1_band3_frac: real=0.00017953859, method=0.099614611, robust_z=327.087442, overlap=0.002674
- random_open_loop / severe / ch1_band5_frac: real=4.7754056e-05, method=0.019909638, robust_z=272.408654, overlap=0.000000
- random_open_loop / worn / ch1_band5_frac: real=4.343938e-05, method=0.020416142, robust_z=225.355428, overlap=0.000000
- random_open_loop / severe / ch1_band4_frac: real=7.6755411e-05, method=0.025887221, robust_z=198.263723, overlap=0.000000

## Class-Ordering Check

LLM features whose class ordering does not follow inner-train real data:
- ch1_tpf_amp_ratio: real=(0.00088323457,0.00058047516,0.00070261043), LLM=(0.0022241288,0.0026271183,0.0019906452), rho=-0.500000

## Files

- `berkeley_inner_psd_w1.csv`
- `berkeley_inner_band_energy.csv`
- `berkeley_inner_stats_overlap.csv`
- `berkeley_inner_channel_structure.csv`
- `berkeley_inner_class_ordering.csv`
- `berkeley_noise_aug_diagnostic_pool.npz`
