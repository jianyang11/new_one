# Supplementary Material Outline

## S1. Data Splits

- PU condition: `N09_M07_F10`
- Retained channels: `vibration_1`, `phase_current_1`, `phase_current_2`
- Train/test protocol: per-bearing file split, first 80% files for train and
  last 20% for test.
- Machine-tool private data: four synchronous NI acquisition channels at
  4000 Hz, channels `X/Y/Z/Current`, BREEZE windows of 2048 samples with stride
  1024, train files `1/2/4/5/10`, test files `7/8`.
- Documented operating states are normal machining, lead-screw anomaly, and
  base imbalance, but local file prefixes `1/2/3` are reported as anonymous
  labels `MT-1/MT-2/MT-3` until the mapping is confirmed.

## S2. Verifier Reports

Include representative JSON certificates from:

- `breeze/runs/rescreen_v2_full/records/`
- `breeze/runs/mt_verifier_real_details.csv`

Each certificate should include gate pass/fail states, measured feature values,
train-supported thresholds, and feedback messages.

## S3. Full Downstream Tables

Use:

- `breeze/results/downstream_file.csv`
- `breeze/results/custom_pool_eval.csv`
- `breeze/results/mt_real_only_eval.csv`

Report all seeds, not only means.

## S4. Physical Metrics and Sensitivity

Use:

- `breeze/results/pool_metrics.csv`
- `breeze/results/pool_metrics_v2.csv`
- `breeze/results/calibration_sensitivity.csv`

Include coverage c85/c90/c95 and per-gate fail counts.

## S5. Reproducibility Manifest

Key scripts:

- `breeze/scripts/freeze_snapshot.py`
- `breeze/src/verifier/v2.py`
- `breeze/src/rescreen_v2.py`
- `breeze/src/eval_custom_pool.py`
- `breeze/src/mt_verifier.py`
- `breeze/src/eval_mt_real.py`
- `breeze/src/figures.py`

Key reports:

- `reports/experiment_snapshot_2026-07-04.md`
- `reports/breeze_v2_rescreen_report_2026-07-04.md`
- `reports/machine_tool_experiment_2026-07-04.md`
- `analysis/main_tables.md`

## S6. Known Boundaries

- PU results use the retained 3-channel project schema, not the full raw PU
  channel set.
- Machine-tool labels are anonymous until the class mapping is supplied.
- No machine-tool BREEZE augmentation result is claimed because no audited
  synthetic pool exists for that dataset.
- BREEZE v2 is not uniformly higher than all strong baselines; claims should
  emphasize physical-gate admission, real-only gains, v1 improvement, and
  interpretability.
