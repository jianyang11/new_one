# Milling Dataset Preprocessing

## UMich_CNC
- fs_hz: 10.0
- channels: X1_CurrentFeedback;Y1_CurrentFeedback;S1_CurrentFeedback;X1_OutputCurrent;Y1_OutputCurrent;S1_OutputCurrent
- window: 64
- window_seconds: 6.4
- label_definition: tool_condition binary label; active machining rows only
- split: experiment-level; test_experiments=[1, 2, 6, 7, 8]
- train_counts: {'unworn': 91, 'worn': 117}
- test_counts: {'unworn': 31, 'worn': 27}

