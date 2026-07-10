# KinematicsPlugin PU Smoke Regression

Generated: 2026-07-07T09:14:18

Purpose: verify that introducing `breeze/src/kinematics.py` and routing PU `config.fault_freqs()` through `BearingKinematicsPlugin` does not change the frozen Phase-A v2 downstream behavior.

Protocol: `eval_custom_pool.py`, pool `breeze/runs/phaseA_v2_balanced/phaseA_v2_llm_k3_B150.npz`, `n_real=5`, seeds 0-1, `n_syn=150/class` (450 total), plus real_only. Output: `breeze/results/kinematics_plugin_pu_smoke_2026-07-07.csv`.

## Row Comparison

| baseline | n_real | seed | n_syn | acc | macro_f1 | matches frozen row |
|---|---:|---:|---:|---:|---:|---|
| real_only | 5 | 0 | 0 | 0.7412 | 0.7163 | yes |
| real_only | 5 | 1 | 0 | 0.7412 | 0.7177 | yes |
| phaseA_v2_llm_k3 | 5 | 0 | 450 | 0.7017 | 0.7056 | yes |
| phaseA_v2_llm_k3 | 5 | 1 | 450 | 0.7942 | 0.7985 | yes |

## Field Checks

| field | exact match |
|---|---|
| n_syn | yes |
| acc | yes |
| macro_f1 | yes |
| f1_healthy | yes |
| f1_OR | yes |
| f1_IR | yes |
| confusion | yes |

## Decision

PASS. The PU smoke rows are exact matches to `breeze/results/phaseA_v2_downstream_cnn.csv`; no Phase-A v2 frozen artifact was modified.
