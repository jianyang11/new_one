# MU-TCM v2 Window Build Report

- Window secs: `[0.5, 1.0]`
- Overlap: `0.5`
- Target fs: `2000.0`
- Max windows per experiment: `12`
- Canonical NPZ: `proc/mutcm_v2_schemeA_window_signal.npz` mirrors `proc/mutcm_v2_schemeA_window_signal_1p0s.npz`.
- Per-experiment window table: `mutcm_v2_window_counts_by_experiment.csv`
- Channel statistic table: `mutcm_v2_window_channel_stats.csv`

## 0.5s Windows

- Output NPZ: `proc/mutcm_v2_schemeA_window_signal_0p5s.npz`
- Shape: `(804, 19, 1000)`
- Class window counts: `{'healthy': 396, 'worn': 408}`
- Conditions: `8`
- Insert-edge groups: `9`
- Experiments too short: `0`
- NaN/Inf total: `0`

## 1.0s Windows

- Output NPZ: `proc/mutcm_v2_schemeA_window_signal_1p0s.npz`
- Shape: `(783, 19, 2000)`
- Class window counts: `{'healthy': 387, 'worn': 396}`
- Conditions: `8`
- Insert-edge groups: `9`
- Experiments too short: `0`
- NaN/Inf total: `0`
