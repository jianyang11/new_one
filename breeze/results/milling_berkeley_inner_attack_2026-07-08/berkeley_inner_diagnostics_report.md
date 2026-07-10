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
| llm | 5.9847 | 0.3290 |
| noise_aug | 4.8154 | 0.1977 |
| random_open_loop | 6.4076 | 0.3401 |
| rule | 4.7644 | 0.2533 |

Largest single PSD/band mismatches:
- noise_aug / sharp / smcDC: PSD-W1=18.783532, bandL1=0.536917
- llm / severe / vib_table: PSD-W1=16.226439, bandL1=1.021323
- llm / worn / vib_table: PSD-W1=12.890613, bandL1=0.420982
- random_open_loop / worn / vib_table: PSD-W1=12.231633, bandL1=0.528695
- random_open_loop / worn / vib_spindle: PSD-W1=12.000763, bandL1=0.705714
- llm / worn / vib_spindle: PSD-W1=11.306694, bandL1=0.531174
- noise_aug / worn / smcDC: PSD-W1=11.230906, bandL1=0.339772
- rule / sharp / vib_spindle: PSD-W1=11.228948, bandL1=0.618216
- random_open_loop / worn / AE_table: PSD-W1=10.589246, bandL1=0.413214
- noise_aug / severe / smcDC: PSD-W1=10.523206, bandL1=0.258316

## Statistics And Channel Structure

| method | mean corr Frobenius delta | mean channel-energy L1 |
|---|---:|---:|
| llm | 1.3425 | 1.7925 |
| noise_aug | 0.2325 | 0.0180 |
| random_open_loop | 1.2036 | 0.1202 |
| rule | 1.3478 | 1.8024 |

Largest median feature deltas by absolute relative shift:
- noise_aug / severe / ch1_band5_frac: real=4.7754056e-05, method=0.12374614, robust_z=1696.541541, overlap=0.050000
- noise_aug / severe / ch1_band4_frac: real=7.6755411e-05, method=0.19238346, robust_z=1477.208648, overlap=0.050000
- noise_aug / worn / ch1_band5_frac: real=4.343938e-05, method=0.083851136, robust_z=927.050279, overlap=0.003460
- noise_aug / worn / ch1_band4_frac: real=6.3335488e-05, method=0.096081079, robust_z=685.787582, overlap=0.056920
- noise_aug / sharp / ch1_band3_frac: real=0.00022422419, method=0.12060712, robust_z=682.094498, overlap=0.023529
- noise_aug / sharp / ch1_band4_frac: real=0.00012508713, method=0.10529037, robust_z=672.781394, overlap=0.013725
- noise_aug / sharp / ch1_band5_frac: real=9.4011587e-05, method=0.080225618, robust_z=649.381163, overlap=0.000000
- noise_aug / severe / ch1_band3_frac: real=0.00017953859, method=0.17598459, robust_z=578.303227, overlap=0.050000
- rule / sharp / energy_frac_ch0: real=0.058475151, method=0.92690415, robust_z=488.067773, overlap=0.000000
- llm / sharp / energy_frac_ch0: real=0.058475151, method=0.87311423, robust_z=457.837179, overlap=0.000000
- noise_aug / worn / ch1_band3_frac: real=0.00017600102, method=0.10411467, robust_z=387.316887, overlap=0.113841
- random_open_loop / severe / ch1_band5_frac: real=4.7754056e-05, method=0.021617541, robust_z=295.832807, overlap=0.000000

## Class-Ordering Check

No LLM key ordering feature has Spearman rho < 0.5 against the real class medians.

## Inner-Val Downstream Confusion Summary

Parsed downstream rows are summarized in `berkeley_inner_downstream_summary.csv`.
- llm n=2: acc=0.4668, macro_f1=0.3787, F1 sharp/worn/severe=0.1389/0.3878/0.6095
- llm n=5: acc=0.5022, macro_f1=0.4944, F1 sharp/worn/severe=0.5631/0.3676/0.5524
- llm n=10: acc=0.6615, macro_f1=0.6550, F1 sharp/worn/severe=0.7397/0.5774/0.6480
- noise_aug n=2: acc=0.5471, macro_f1=0.5275, F1 sharp/worn/severe=0.6138/0.3282/0.6405
- noise_aug n=5: acc=0.5054, macro_f1=0.4834, F1 sharp/worn/severe=0.6966/0.3253/0.4284
- noise_aug n=10: acc=0.5497, macro_f1=0.5373, F1 sharp/worn/severe=0.7382/0.3663/0.5075
- random_open_loop n=2: acc=0.3610, macro_f1=0.1937, F1 sharp/worn/severe=0.0221/0.3506/0.2083
- random_open_loop n=5: acc=0.3658, macro_f1=0.2798, F1 sharp/worn/severe=0.1995/0.2970/0.3430
- random_open_loop n=10: acc=0.5054, macro_f1=0.4383, F1 sharp/worn/severe=0.4645/0.5341/0.3165
- real_only n=2: acc=0.4519, macro_f1=0.3734, F1 sharp/worn/severe=0.3745/0.1649/0.5808
- real_only n=5: acc=0.4155, macro_f1=0.3651, F1 sharp/worn/severe=0.4810/0.2356/0.3788
- real_only n=10: acc=0.4706, macro_f1=0.4434, F1 sharp/worn/severe=0.5482/0.3997/0.3822
- rule n=2: acc=0.4588, macro_f1=0.3588, F1 sharp/worn/severe=0.1584/0.3536/0.5642
- rule n=5: acc=0.5032, macro_f1=0.4908, F1 sharp/worn/severe=0.6123/0.3544/0.5058
- rule n=10: acc=0.6604, macro_f1=0.6516, F1 sharp/worn/severe=0.7562/0.5703/0.6285

## Files

- `berkeley_inner_psd_w1.csv`
- `berkeley_inner_band_energy.csv`
- `berkeley_inner_stats_overlap.csv`
- `berkeley_inner_channel_structure.csv`
- `berkeley_inner_class_ordering.csv`
- `berkeley_noise_aug_diagnostic_pool.npz`
