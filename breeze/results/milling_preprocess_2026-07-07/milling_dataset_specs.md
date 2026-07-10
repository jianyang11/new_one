# Milling Dataset Preprocessing

## Berkeley_NASA_milling
- fs_hz: 250.0
- channels: smcAC;smcDC;vib_table;vib_spindle;AE_table;AE_spindle
- window: 512
- window_seconds: 2.048
- label_definition: sharp VB<0.2; worn 0.2<=VB<=0.45; severe VB>0.45; measured VB only
- split: case-level; test_cases=[2, 4, 8, 14, 15]
- train_counts: {'sharp': 629, 'worn': 731, 'severe': 476}
- test_counts: {'sharp': 221, 'worn': 255, 'severe': 170}

## UMich_CNC
- fs_hz: 10.0
- channels: X1_CurrentFeedback;Y1_CurrentFeedback;Z1_CurrentFeedback;S1_CurrentFeedback;X1_OutputCurrent;Y1_OutputCurrent;Z1_OutputCurrent;S1_OutputCurrent
- window: 64
- window_seconds: 6.4
- label_definition: tool_condition binary label; active machining rows only
- split: experiment-level; test_experiments=[1, 2, 6, 7, 8]
- train_counts: {'unworn': 91, 'worn': 117}
- test_counts: {'unworn': 31, 'worn': 27}

