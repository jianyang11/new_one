# Milling Dataset Preprocessing

## Berkeley_NASA_milling
- fs_hz: 250.0
- channels: smcAC;smcDC;vib_table;vib_spindle;AE_table;AE_spindle
- window: 512
- window_seconds: 2.048
- label_definition: healthy VB<0.2; degraded VB>=0.2; measured VB only
- split: case-level; test_cases=[2, 4, 8, 14, 15]
- train_counts: {'healthy': 629, 'degraded': 1207}
- test_counts: {'healthy': 221, 'degraded': 425}

