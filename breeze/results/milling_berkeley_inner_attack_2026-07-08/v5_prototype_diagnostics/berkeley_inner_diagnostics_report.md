# Berkeley Inner-Train Diagnostics

This is a zero-API diagnostic pass. All reference distributions come from `milling_berkeley_inner_train.npz`; no held-out Berkeley test signal is used.

## Inputs

- inner_train windows: 1462; counts: {"sharp": 510, "worn": 578, "severe": 374}
- inner_val windows: 374; counts: {"sharp": 119, "worn": 153, "severe": 102}
- diagnostic synthetic budget: 13/class for LLM, rule, random_open_loop, and noise_aug.
- spindle harmonics/TPF used for diagnostics: [13.766667, 27.533333, 41.3, 55.066667, 68.833333, 82.6]

Important caveat: the inspected current LLM/rule/random pools were built before the inner split existed. They are valid for failure diagnosis, but not valid as final inner-validation artifacts for choosing a formal protocol.

## PSD And Band-Energy Distance

| method | mean PSD-W1 | mean band L1 |
|---|---:|---:|
| llm | 7.3243 | 0.4150 |
| noise_aug | 4.9211 | 0.2287 |
| random_open_loop | 6.4474 | 0.3468 |
| rule | 5.2524 | 0.3592 |

Largest single PSD/band mismatches:
- noise_aug / sharp / smcDC: PSD-W1=22.557272, bandL1=0.624739
- noise_aug / severe / smcDC: PSD-W1=16.111280, bandL1=0.466559
- random_open_loop / worn / vib_table: PSD-W1=14.656809, bandL1=0.592028
- llm / worn / vib_spindle: PSD-W1=14.222821, bandL1=0.502740
- llm / worn / vib_table: PSD-W1=14.102439, bandL1=0.544078
- llm / severe / AE_spindle: PSD-W1=13.637469, bandL1=0.531205
- llm / severe / vib_table: PSD-W1=12.270623, bandL1=0.587295
- llm / severe / AE_table: PSD-W1=11.914545, bandL1=0.528144
- llm / worn / AE_spindle: PSD-W1=11.242924, bandL1=0.325811
- rule / worn / vib_spindle: PSD-W1=11.187620, bandL1=0.643274

## Statistics And Channel Structure

| method | mean corr Frobenius delta | mean channel-energy L1 |
|---|---:|---:|
| llm | 1.1875 | 0.0192 |
| noise_aug | 0.2497 | 0.0142 |
| random_open_loop | 1.2520 | 0.3394 |
| rule | 0.2921 | 0.0109 |

Largest median feature deltas by absolute relative shift:
- noise_aug / worn / ch1_band5_frac: real=4.343938e-05, method=0.11776075, robust_z=1302.146136, overlap=0.001730
- noise_aug / severe / ch1_band5_frac: real=4.7754056e-05, method=0.092410787, robust_z=1266.772589, overlap=0.000000
- noise_aug / worn / ch1_band4_frac: real=6.3335488e-05, method=0.14722423, robust_z=1051.067301, overlap=0.006920
- noise_aug / severe / ch1_band4_frac: real=7.6755411e-05, method=0.10831693, robust_z=831.449588, overlap=0.000000
- noise_aug / sharp / ch1_band3_frac: real=0.00022422419, method=0.13441134, robust_z=760.309785, overlap=0.017647
- noise_aug / sharp / ch1_band4_frac: real=0.00012508713, method=0.11055324, robust_z=706.449958, overlap=0.021569
- noise_aug / sharp / ch1_band5_frac: real=9.4011587e-05, method=0.083222156, robust_z=673.664901, overlap=0.000000
- noise_aug / severe / ch1_band3_frac: real=0.00017953859, method=0.12683132, robust_z=416.615663, overlap=0.008021
- noise_aug / worn / ch1_band3_frac: real=0.00017600102, method=0.10776161, robust_z=400.906856, overlap=0.249800
- random_open_loop / severe / ch1_band5_frac: real=4.7754056e-05, method=0.02014683, robust_z=275.661787, overlap=0.000000
- random_open_loop / worn / ch1_band5_frac: real=4.343938e-05, method=0.024055056, robust_z=265.607773, overlap=0.000000
- random_open_loop / worn / ch1_band4_frac: real=6.3335488e-05, method=0.026049498, robust_z=185.600979, overlap=0.006920

## Class-Ordering Check

No LLM key ordering feature has Spearman rho < 0.5 against the real class medians.

## Inner-Val Downstream Confusion Summary

Parsed downstream rows are summarized in `berkeley_inner_downstream_summary.csv`.
- llm n=2: acc=0.5765, macro_f1=0.5519, F1 sharp/worn/severe=0.6941/0.2866/0.6749
- llm n=5: acc=0.5700, macro_f1=0.5587, F1 sharp/worn/severe=0.7055/0.3751/0.5955
- llm n=10: acc=0.5861, macro_f1=0.5742, F1 sharp/worn/severe=0.7352/0.3632/0.6244
- noise_aug n=2: acc=0.5471, macro_f1=0.5275, F1 sharp/worn/severe=0.6138/0.3282/0.6405
- noise_aug n=5: acc=0.5054, macro_f1=0.4834, F1 sharp/worn/severe=0.6966/0.3253/0.4284
- noise_aug n=10: acc=0.5497, macro_f1=0.5373, F1 sharp/worn/severe=0.7382/0.3663/0.5075
- random_open_loop n=2: acc=0.4272, macro_f1=0.3769, F1 sharp/worn/severe=0.5632/0.0693/0.4982
- random_open_loop n=5: acc=0.3610, macro_f1=0.3216, F1 sharp/worn/severe=0.5976/0.1445/0.2226
- random_open_loop n=10: acc=0.4631, macro_f1=0.4241, F1 sharp/worn/severe=0.6584/0.1441/0.4698
- real_only n=2: acc=0.4519, macro_f1=0.3734, F1 sharp/worn/severe=0.3745/0.1649/0.5808
- real_only n=5: acc=0.4155, macro_f1=0.3651, F1 sharp/worn/severe=0.4810/0.2356/0.3788
- real_only n=10: acc=0.4706, macro_f1=0.4434, F1 sharp/worn/severe=0.5482/0.3997/0.3822
- rule n=2: acc=0.5775, macro_f1=0.5530, F1 sharp/worn/severe=0.6897/0.2841/0.6853
- rule n=5: acc=0.5770, macro_f1=0.5669, F1 sharp/worn/severe=0.7077/0.3873/0.6057
- rule n=10: acc=0.5866, macro_f1=0.5743, F1 sharp/worn/severe=0.7354/0.3625/0.6251

## Files

- `berkeley_inner_psd_w1.csv`
- `berkeley_inner_band_energy.csv`
- `berkeley_inner_stats_overlap.csv`
- `berkeley_inner_channel_structure.csv`
- `berkeley_inner_class_ordering.csv`
- `berkeley_noise_aug_diagnostic_pool.npz`
