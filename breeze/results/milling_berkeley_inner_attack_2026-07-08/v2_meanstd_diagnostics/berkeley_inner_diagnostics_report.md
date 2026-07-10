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
| llm | 5.5063 | 0.3121 |
| noise_aug | 4.8154 | 0.1977 |
| random_open_loop | 6.2709 | 0.3354 |
| rule | 5.2248 | 0.3315 |

Largest single PSD/band mismatches:
- noise_aug / sharp / smcDC: PSD-W1=18.783532, bandL1=0.536917
- random_open_loop / worn / vib_table: PSD-W1=14.834896, bandL1=0.589580
- llm / worn / vib_spindle: PSD-W1=14.135135, bandL1=0.639289
- llm / worn / vib_table: PSD-W1=13.009550, bandL1=0.534462
- noise_aug / worn / smcDC: PSD-W1=11.230906, bandL1=0.339772
- rule / worn / vib_spindle: PSD-W1=10.985939, bandL1=0.621413
- noise_aug / severe / smcDC: PSD-W1=10.523206, bandL1=0.258316
- random_open_loop / worn / vib_spindle: PSD-W1=10.320110, bandL1=0.677416
- rule / severe / vib_spindle: PSD-W1=9.616650, bandL1=0.582593
- random_open_loop / worn / AE_table: PSD-W1=9.528974, bandL1=0.382801

## Statistics And Channel Structure

| method | mean corr Frobenius delta | mean channel-energy L1 |
|---|---:|---:|
| llm | 0.3745 | 0.0112 |
| noise_aug | 0.2325 | 0.0180 |
| random_open_loop | 1.1872 | 0.2381 |
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
- random_open_loop / severe / ch1_band5_frac: real=4.7754056e-05, method=0.018708102, robust_z=255.929416, overlap=0.000000
- random_open_loop / worn / ch1_band5_frac: real=4.343938e-05, method=0.021293066, robust_z=235.055643, overlap=0.000000
- random_open_loop / severe / ch1_band4_frac: real=7.6755411e-05, method=0.025254825, robust_z=193.405958, overlap=0.000000

## Class-Ordering Check

LLM features whose class ordering does not follow inner-train real data:
- ch1_tpf_amp_ratio: real=(0.00088323457,0.00058047516,0.00070261043), LLM=(0.0016714586,0.0018348179,0.0021572036), rho=-0.500000
- ch3_tpf_amp_ratio: real=(0.032344303,0.033182067,0.028322119), LLM=(0.060092646,0.025659973,0.027513365), rho=-0.500000

## Inner-Val Downstream Confusion Summary

Parsed downstream rows are summarized in `berkeley_inner_downstream_summary.csv`.
- llm n=2: acc=0.5856, macro_f1=0.5619, F1 sharp/worn/severe=0.6952/0.3002/0.6903
- llm n=5: acc=0.5690, macro_f1=0.5560, F1 sharp/worn/severe=0.7078/0.3750/0.5854
- llm n=10: acc=0.5877, macro_f1=0.5754, F1 sharp/worn/severe=0.7369/0.3623/0.6270
- noise_aug n=2: acc=0.5471, macro_f1=0.5275, F1 sharp/worn/severe=0.6138/0.3282/0.6405
- noise_aug n=5: acc=0.5054, macro_f1=0.4834, F1 sharp/worn/severe=0.6966/0.3253/0.4284
- noise_aug n=10: acc=0.5497, macro_f1=0.5373, F1 sharp/worn/severe=0.7382/0.3663/0.5075
- random_open_loop n=2: acc=0.5626, macro_f1=0.5416, F1 sharp/worn/severe=0.5436/0.3997/0.6816
- random_open_loop n=5: acc=0.5925, macro_f1=0.5805, F1 sharp/worn/severe=0.6450/0.5024/0.5940
- random_open_loop n=10: acc=0.6118, macro_f1=0.5925, F1 sharp/worn/severe=0.7228/0.5152/0.5397
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
