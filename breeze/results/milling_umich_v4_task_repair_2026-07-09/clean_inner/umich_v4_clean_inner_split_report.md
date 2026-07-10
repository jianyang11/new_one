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
