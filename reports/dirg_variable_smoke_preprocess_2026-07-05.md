# DIRG VariableSpeedAndLoad Preprocess

Date: 2026-07-05

Mode: smoke
Output NPZ: `proc/dirg_variable_smoke.npz`
Source archive: `data/dirg/raw/VariableSpeedAndLoad.zip`
Sampling rate: 51200 Hz
Window/hop: 4096/4096 samples
Files processed: 3
Windows: 375
Shape: (375, 6, 4096)
Class counts: {"IR450": 125, "healthy": 125, "roller450": 125}
Unique speed-load conditions: 2

Split policy: full-mode splits are frozen by held-out speed-load operating condition. This avoids putting windows from the same acquisition file in both train and test.
