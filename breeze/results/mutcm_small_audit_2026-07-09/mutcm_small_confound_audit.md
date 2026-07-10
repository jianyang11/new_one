# MU-TCM Small Subset Confound Audit

Status: 0-API data audit only; not a formal conclusion.

## Dataset Support

- Experiments: `8`
- Rounded VB levels: `[0.0, 0.1, 0.2, 0.3]`
- Conditions with multiple rounded VB levels: `2/2`

## Label Schemes

| scheme | label | n experiments | VB values |
|---|---|---:|---|
| A | healthy | 4 | 0;0.039;0.12;0.139 |
| A | worn | 4 | 0.201;0.213;0.276;0.291 |
| B | healthy | 1 | 0 |
| B | unlabeled | 3 | 0.039;0.12;0.139 |
| B | worn | 4 | 0.201;0.213;0.276;0.291 |

Scheme A maps rounded VB levels: healthy=`{0.0,0.1}`, worn=`{0.2,0.3}`.
Scheme B uses strict labels: healthy=`VB==0.0`, worn=`VB>=0.2`, discarding `0<VB<0.2`.

## Baselines

| scheme | baseline | status | n | Acc | Macro-F1 | majority Acc | per-class F1 |
|---|---|---|---:|---:|---:|---:|---|
| A | metadata_only | ok | 8 | 0.0000 | 0.0000 | 0.5000 | `{"healthy": 0.0, "worn": 0.0}` |
| A | signal_only | ok | 8 | 0.6250 | 0.6190 | 0.5000 | `{"healthy": 0.6666666666666666, "worn": 0.5714285714285714}` |
| B | metadata_only | insufficient_label_support_for_leave_one_experiment_out | 5 |  |  | 0.8000 | `` |
| B | signal_only | insufficient_label_support_for_leave_one_experiment_out | 5 |  |  | 0.8000 | `` |

## Pass/Fail Against Screening Conditions

| condition | pass |
|---|---:|
| same_condition_multiple_wear_levels | True |
| metadata_only_not_near_100_percent_scheme_A | True |
| signal_only_above_majority_scheme_A | True |
| scheme_A_support_enough | True |
| scheme_B_support_enough | False |
| experiment_level_split_constructible_scheme_A | True |
| experiment_level_split_constructible_scheme_B | False |

## Interpretation

- The small subset has repeated wear levels under the same machining condition when material is included in the condition key.
- Scheme A has enough healthy/worn support for leave-one-experiment-out diagnostics; Scheme B does not because it has only one strict `VB==0.0` healthy experiment.
- This audit is useful for deciding whether to expand to the full MU-TCM dataset, but the small subset is too small to serve as a formal milling result by itself.
