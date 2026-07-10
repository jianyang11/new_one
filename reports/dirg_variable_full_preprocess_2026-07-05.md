# DIRG VariableSpeedAndLoad Preprocess

Date: 2026-07-05

Mode: full
Output NPZ: `proc/dirg_variable_all.npz`
Source archive: `data/dirg/raw/VariableSpeedAndLoad.zip`
Sampling rate: 51200 Hz
Window/hop: 4096/4096 samples
Files processed: 119
Windows: 14875
Shape: (14875, 6, 4096)
Class counts: {"IR150": 2125, "IR250": 2125, "IR450": 2125, "healthy": 2125, "roller150": 2125, "roller250": 2125, "roller450": 2125}
Unique speed-load conditions: 17

Split policy: full-mode splits are frozen by held-out speed-load operating condition. This avoids putting windows from the same acquisition file in both train and test.
