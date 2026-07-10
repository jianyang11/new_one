# PU LOCO v3 Internal Candidate Pool Report

- Scope: internal simulated LOCO only; no formal held-out LOCO test is touched.
- API usage: 0 calls for morphology_idw/morphology_nearest; accepted v1 LLM recipes are reused as structural templates.
- Output root: `/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/runs/pu_loco_v3_internal_candidates_2026-07-08_full_v1`
- Generation/calibration data: only train-bearing windows from the three internal training conditions per fold.
- Pseudo held-out data use: metadata only for rpm/torque/load kinematics and morphology prediction target.

| candidate | pseudo heldout | nearest | accepted slots | kept healthy | kept OR | kept IR | status |
|---|---|---|---:|---:|---:|---:|---|
| morphology_idw | N09_M07_F10 | N15_M07_F10 | 12/18 | 13 | 6 | 20 | pool_short |
| morphology_idw | N15_M01_F10 | N15_M07_F10 | 20/22 | 35 | 58 | 42 | ready_for_smoke |
| morphology_idw | N15_M07_F04 | N15_M07_F10 | 15/17 | 33 | 30 | 45 | ready_for_smoke |
| morphology_idw | N15_M07_F10 | N09_M07_F10 | 21/21 | 38 | 54 | 58 | ready_for_smoke |
