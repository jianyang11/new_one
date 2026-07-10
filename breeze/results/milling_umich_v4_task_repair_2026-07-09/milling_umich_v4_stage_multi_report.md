# UMich v4 Stage-Contiguous Preprocessing: milling_umich_v4_stage_multi

- Selected stages: `['Layer 1 Up', 'Layer 1 Down', 'Layer 2 Up', 'Layer 2 Down', 'Layer 3 Up', 'Layer 3 Down']`
- Window length: `64` samples (6.400 s)
- Windowing: contiguous within one Machining_Process stage; no cross-stage windows.
- Split unit: experiment-level; source_units remain experiment ids.
- Train counts: {'unworn': 80, 'worn': 104}
- Test counts: {'unworn': 29, 'worn': 19}
- Unit audit CSV: `milling_umich_v4_stage_multi_units.csv`
- Stage count CSV: `milling_umich_v4_stage_multi_stage_counts.csv`
