# PU LOCO v2 Condition-Aware Pool Report

- Protocol: `pu_loco_v2_preregistration.md`; no held-out signals or labels used.
- API usage: 0 calls for this condition-aware rerender block.
- Output root: `/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/runs/pu_loco_v2_condition_aware_2026-07-08`
- Kinematic metadata used: held-out condition rpm/torque/load from `config.CONDITIONS`.
- Verifier: stats/PSD boundaries calibrated on each source training condition; kinematic frequencies extrapolated to held-out rpm.

| heldout | accepted slots | kept healthy | kept OR | kept IR | status |
|---|---:|---:|---:|---:|---|
| N09_M07_F10 | 17/18 | 25 | 29 | 22 | target_reached |
| N15_M01_F10 | 20/22 | 28 | 28 | 25 | target_reached |
| N15_M07_F04 | 17/17 | 24 | 21 | 23 | target_reached |
| N15_M07_F10 | 18/21 | 21 | 29 | 36 | target_reached |

