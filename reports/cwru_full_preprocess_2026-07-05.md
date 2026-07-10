# CWRU Full Preprocessing Report

Date: 2026-07-05

Protocol: official CWRU 12 kHz drive-end bearing-fault files parsed from the saved CWRU pages. Full preprocessing uses the DE vibration channel only because the official 0.028 inch files do not contain FE or BA fields. Missing channels are not padded.

Files: 64
Sampling rate: 12000 Hz
Window: 2048; hop: 2048
All-window array: (4367, 1, 2048)
Class counts: healthy:828, IR:944, B:943, OR:1652

Generated artifacts:

- `proc/cwru_de12k_all.npz`
- `proc/cwru_de12k_within_load*_train/test.npz`
- `proc/cwru_de12k_lolo_load*_train/test.npz`
- `proc/cwru_de12k_train_load0_test_load*_train/test.npz`
- `analysis/cwru_de12k_full_file_summary_2026-07-05.csv`
- `analysis/cwru_de12k_split_summary_2026-07-05.csv`

The within-load splits are chronological within each source file and are useful for comparability with common CWRU window-level protocols. The leave-one-load-out and train-load0-to-target-load splits are stricter condition-generalization protocols and should be preferred for strong claims.
