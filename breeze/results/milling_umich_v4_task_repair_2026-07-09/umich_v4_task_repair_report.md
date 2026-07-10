# UMich v4 Task-Repair Report

Date: 2026-07-09 Asia/Shanghai

Status: stop before LLM generation. No formal held-out test was run.

## Protocol Boundary

- Berkeley v2 binary formal remains frozen as partial/no-go and is not tuned here.
- UMich v4 uses only outer-train derived inner-train/inner-val artifacts for task repair.
- LLM/API calls in this v4 repair stage: 0; cumulative API remains 1020/3000.
- Clean supervised labels are restricted to `unworn+passed_visual_inspection=yes` and `worn+passed_visual_inspection=no`.

## Clean Split

# UMich v4 Clean Inner Split

- Source NPZ: `proc/milling_umich_v4_stage_multi_train.npz`
- Clean definition: `unworn+passed_visual_inspection=yes` or `worn+passed_visual_inspection=no`.
- Split unit: experiment/source unit; no random window split.
- Validation units: `['experiment_03', 'experiment_09']`
- All clean counts: `{'unworn': 73, 'worn': 19}`
- Inner-train clean counts: `{'unworn': 59, 'worn': 13}`
- Inner-val clean counts: `{'unworn': 14, 'worn': 6}`
- Inner-train feedrate/clamp distribution: `{(12.0, 4.0): 13, (3.0, 4.0): 22, (3.0, 3.0): 20, (3.0, 2.5): 17}`
- Inner-val feedrate/clamp distribution: `{(6.0, 3.0): 14, (15.0, 4.0): 6}`

This split is for UMich v4 learnability repair only. It uses no held-out test labels or windows.

## Real-Only Learnability

| variant | method | n_real | Acc | Macro-F1 | F1 unworn | F1 worn |
|---|---|---:|---:|---:|---:|---:|
| all_label_layer1up | real_only | 2 | 0.5111 | 0.4740 | 0.5401 | 0.4079 |
| all_label_layer1up | real_only | 5 | 0.4555 | 0.4008 | 0.4221 | 0.3796 |
| all_label_layer1up | real_only | 10 | 0.4333 | 0.4017 | 0.4137 | 0.3897 |
| all_label_layer1up | real_only | 9999 | 0.4444 | 0.3925 | 0.5355 | 0.2496 |
| all_label_multi_raw | real_only | 2 | 0.5282 | 0.4900 | 0.4731 | 0.5070 |
| all_label_multi_raw | real_only | 5 | 0.5154 | 0.4882 | 0.4868 | 0.4897 |
| all_label_multi_raw | real_only | 10 | 0.5257 | 0.5011 | 0.4391 | 0.5631 |
| all_label_multi_raw | real_only | 9999 | 0.4923 | 0.4760 | 0.3906 | 0.5615 |
| all_label_multi_stagez | real_only | 2 | 0.5257 | 0.4895 | 0.4760 | 0.5030 |
| all_label_multi_stagez | real_only | 5 | 0.5154 | 0.4926 | 0.4667 | 0.5186 |
| all_label_multi_stagez | real_only | 10 | 0.5410 | 0.5115 | 0.4401 | 0.5830 |
| all_label_multi_stagez | real_only | 9999 | 0.4923 | 0.4754 | 0.3917 | 0.5590 |
| clean_multi_meta | real_only | 2 | 0.6650 | 0.6296 | 0.6778 | 0.5815 |
| clean_multi_meta | real_only | 5 | 0.7600 | 0.7352 | 0.7824 | 0.6880 |
| clean_multi_meta | real_only | 10 | 0.9000 | 0.8913 | 0.9159 | 0.8668 |
| clean_multi_meta | real_only | 9999 | 0.9400 | 0.8824 | 0.9647 | 0.8000 |
| clean_multi_raw | real_only | 2 | 0.6000 | 0.5803 | 0.5408 | 0.6199 |
| clean_multi_raw | real_only | 5 | 0.6600 | 0.6448 | 0.6096 | 0.6800 |
| clean_multi_raw | real_only | 10 | 0.6300 | 0.6106 | 0.5650 | 0.6561 |
| clean_multi_raw | real_only | 9999 | 0.9400 | 0.9001 | 0.9626 | 0.8376 |
| clean_multi_stagez | real_only | 2 | 0.6100 | 0.5884 | 0.5555 | 0.6213 |
| clean_multi_stagez | real_only | 5 | 0.6450 | 0.6286 | 0.5999 | 0.6572 |
| clean_multi_stagez | real_only | 10 | 0.6550 | 0.6361 | 0.5969 | 0.6754 |
| clean_multi_stagez | real_only | 9999 | 0.9550 | 0.9224 | 0.9720 | 0.8727 |
| clean_multi_stagez_meta | noise_aug | 2 | 0.6750 | 0.6415 | 0.7035 | 0.5796 |
| clean_multi_stagez_meta | noise_aug | 5 | 0.8100 | 0.7999 | 0.8350 | 0.7648 |
| clean_multi_stagez_meta | noise_aug | 10 | 0.9500 | 0.9465 | 0.9599 | 0.9330 |
| clean_multi_stagez_meta | real_only | 2 | 0.6600 | 0.6297 | 0.6795 | 0.5800 |
| clean_multi_stagez_meta | real_only | 5 | 0.7600 | 0.7349 | 0.7837 | 0.6862 |
| clean_multi_stagez_meta | real_only | 10 | 0.8950 | 0.8856 | 0.9112 | 0.8600 |
| clean_multi_stagez_meta | real_only | 9999 | 0.9400 | 0.8824 | 0.9647 | 0.8000 |

## Confound Audit

| baseline | Acc | Macro-F1 | F1 unworn | F1 worn |
|---|---:|---:|---:|---:|
| metadata_only | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| stage_only | 0.4500 | 0.4486 | 0.4762 | 0.4211 |
| signal_feature_only | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Clean feedrate/clamp support:
- clean_unworn: `[(3.0, 2.5, 17), (3.0, 3.0, 20), (3.0, 4.0, 22), (6.0, 3.0, 14)]`
- clean_worn: `[(12.0, 4.0, 13), (15.0, 4.0, 6)]`

There is no feedrate x clamp_pressure condition containing both clean classes. Metadata-only classification is perfect, so the clean task cannot distinguish tool wear from process-condition confounding under a condition-balanced protocol.

## Gate Decision

- Numeric learnability gate on the best clean CNN representation: `True`.
- Confound gate failed: `True`.
- Single-stage clean diagnosis is also under-supported: each active single stage has only 3-4 clean worn windows total, so n_real=10 cannot be evaluated without violating class support.
- Therefore UMich v4 must stop before LLM synthetic generation. Running LLM now would optimize a condition-confounded label boundary, not a defensible worn/unworn wear signal.

## Artifacts

- Downstream summary: `breeze/results/milling_umich_v4_task_repair_2026-07-09/umich_v4_task_repair_downstream_summary.csv`
- Audit report: `learnability_audit/umich_v4_learnability_audit.md`
- Clean split report: `clean_inner/umich_v4_clean_inner_split_report.md`
- Diagnostic baseline CSVs: `learnability_audit/umich_v4_diagnostic_baselines.csv`, `learnability_audit/umich_v4_diagnostic_baseline_confusions.csv`, `learnability_audit/umich_v4_diagnostic_baseline_per_condition.csv`
