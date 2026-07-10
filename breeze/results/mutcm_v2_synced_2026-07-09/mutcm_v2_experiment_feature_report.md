# MU-TCM v2 Experiment Feature Report

- Output NPZ: `proc/mutcm_v2_schemeA_experiment_features.npz`
- Shape: `(67, 180)`
- Signal feature columns: `180`
- Class counts: `{'healthy': 33, 'worn': 34}`
- Feature source: official `signals_stats.csv` time/frequency/time-frequency statistics.
- Removed fields: `_file_name`, `VB`, rounded VB, labels, Insert/Edge/Repetition, material/Vc/fz/ap/ae/Lubrication and start/end sync fields.
