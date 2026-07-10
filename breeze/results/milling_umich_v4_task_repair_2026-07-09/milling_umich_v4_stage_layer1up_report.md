# UMich v4 Stage-Contiguous Preprocessing: milling_umich_v4_stage_layer1up

- Selected stages: `['Layer 1 Up']`
- Window length: `64` samples (6.400 s)
- Windowing: contiguous within one Machining_Process stage; no cross-stage windows.
- Split unit: experiment-level; source_units remain experiment ids.
- Train counts: {'unworn': 24, 'worn': 21}
- Test counts: {'unworn': 5, 'worn': 6}
- Unit audit CSV: `milling_umich_v4_stage_layer1up_units.csv`
- Stage count CSV: `milling_umich_v4_stage_layer1up_stage_counts.csv`
