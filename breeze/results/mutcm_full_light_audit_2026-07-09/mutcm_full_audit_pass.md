# MU-TCM Full Audit Pass

Status: light audit only; no MAT extraction beyond CSVs, no LLM/API, no preregistration, no formal test.

- Recommended label scheme: `A`
- Recommended split protocol: condition-aware outer split plus inner validation, with mandatory insert-edge grouped isolation/diagnostics.
- Recommended feature set for first formal protocol: `signals_stats.csv` signal statistics only; no filename/VB/metadata fields.
- Baselines: real_only, noise_aug on signal windows only after MAT extraction, rule/random/LLM only after inner-val verifier calibration.
- Next step: extract `signals_synced/*.mat` only, build experiment-level NPZ, and create a new preregistration before any formal held-out test.
- Critical caveat: metadata_leaky is near-perfect under non-insert-edge-isolated splits, so Insert/Edge/Repetition must never be treated as safe model features.

## Label Scheme Summary

| scheme | healthy | worn | unlabeled | supports_n_real_10 |
| --- | --- | --- | --- | --- |
| A | 33 | 34 | 0 | True |
| B | 17 | 34 | 16 | True |
| C | 33 | 34 | 0 | True |

## Metadata Baseline Snapshot

| scheme | baseline | split_protocol | status | acc | macro_f1 |
| --- | --- | --- | --- | --- | --- |
| A | metadata_safe | loeo | ok | 0.0 | 0.0 |
| A | metadata_safe | logo_condition | ok | 0.4925373134328358 | 0.49242424242424243 |
| A | metadata_safe | groupkfold_condition | ok | 0.4925373134328358 | 0.49242424242424243 |
| A | metadata_safe | groupkfold_insert_edge | ok | 0.26865671641791045 | 0.2680044593088071 |
| A | metadata_leaky | loeo | ok | 1.0 | 1.0 |
| A | metadata_leaky | logo_condition | ok | 1.0 | 1.0 |
| A | metadata_leaky | groupkfold_condition | ok | 1.0 | 1.0 |
| A | metadata_leaky | groupkfold_insert_edge | ok | 0.13432835820895522 | 0.11842105263157894 |
| B | metadata_safe | loeo | ok | 0.17647058823529413 | 0.15 |
| B | metadata_safe | logo_condition | ok | 0.5490196078431373 | 0.5122661122661123 |
| B | metadata_safe | groupkfold_condition | ok | 0.5490196078431373 | 0.5122661122661123 |
| B | metadata_safe | groupkfold_insert_edge | ok | 0.19607843137254902 | 0.16393442622950818 |
| B | metadata_leaky | loeo | ok | 1.0 | 1.0 |
| B | metadata_leaky | logo_condition | ok | 1.0 | 1.0 |
| B | metadata_leaky | groupkfold_condition | ok | 1.0 | 1.0 |
| B | metadata_leaky | groupkfold_insert_edge | ok | 0.6666666666666666 | 0.4 |
| C | metadata_safe | loeo | ok | 0.0 | 0.0 |
| C | metadata_safe | logo_condition | ok | 0.4925373134328358 | 0.49242424242424243 |
| C | metadata_safe | groupkfold_condition | ok | 0.4925373134328358 | 0.49242424242424243 |
| C | metadata_safe | groupkfold_insert_edge | ok | 0.26865671641791045 | 0.2680044593088071 |
| C | metadata_leaky | loeo | ok | 1.0 | 1.0 |
| C | metadata_leaky | logo_condition | ok | 1.0 | 1.0 |
| C | metadata_leaky | groupkfold_condition | ok | 1.0 | 1.0 |
| C | metadata_leaky | groupkfold_insert_edge | ok | 0.13432835820895522 | 0.11842105263157894 |

## Best Signal Baseline Snapshot

| scheme | split_protocol | model | acc | macro_f1 | majority_acc |
| --- | --- | --- | --- | --- | --- |
| A | groupkfold_condition | rf | 0.8805970149253731 | 0.8805704099821747 | 0.5074626865671642 |
| A | groupkfold_insert_edge | rf | 0.8656716417910447 | 0.8651911468812876 | 0.5074626865671642 |
| A | loeo | rf | 0.9701492537313433 | 0.9701426024955437 | 0.5074626865671642 |
| A | logo_condition | rf | 0.8955223880597015 | 0.8955223880597015 | 0.5074626865671642 |
| B | groupkfold_condition | rf | 0.9215686274509803 | 0.9141414141414141 | 0.6666666666666666 |
| B | groupkfold_insert_edge | rf | 0.7647058823529411 | 0.7267857142857144 | 0.6666666666666666 |
| B | loeo | logreg | 0.9411764705882353 | 0.9347547974413646 | 0.6666666666666666 |
| B | logo_condition | logreg | 0.9019607843137255 | 0.8912579957356077 | 0.6666666666666666 |
| C | groupkfold_condition | rf | 0.8805970149253731 | 0.8805704099821747 | 0.5074626865671642 |
| C | groupkfold_insert_edge | rf | 0.8656716417910447 | 0.8651911468812876 | 0.5074626865671642 |
| C | loeo | rf | 0.9701492537313433 | 0.9701426024955437 | 0.5074626865671642 |
| C | logo_condition | rf | 0.8955223880597015 | 0.8955223880597015 | 0.5074626865671642 |
