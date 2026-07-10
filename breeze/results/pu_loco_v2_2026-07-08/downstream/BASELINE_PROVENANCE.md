# PU LOCO v2 Downstream Baseline Provenance

- `llm` rows in this directory are produced from the v2 condition-aware LLM pools under `breeze/runs/pu_loco_v2_condition_aware_2026-07-08/`.
- `noise_aug`, `random_open_loop`, `rule`, and `real_only` CSVs are copied unchanged from `breeze/results/pu_loco_2026-07-07/downstream/`.
- These copied baselines use the same PU LOCO split, `n_real={5,10,25}`, `n_syn=20/class` where applicable, 40 seeds, CNN architecture, and epochs=20 as the preregistered v2 downstream protocol.
- The v1 LLM CSVs are not reused.
