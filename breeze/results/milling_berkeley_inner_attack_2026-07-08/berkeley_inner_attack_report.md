# Berkeley Inner-Val Attack Report

Date: 2026-07-08 Asia/Shanghai

Status: not passed. Formal preregistration was not written, and the formal 40-seed held-out Berkeley test was not run.

## Boundary

- Iteration data: `proc/milling_berkeley_inner_train.npz` and `proc/milling_berkeley_inner_val.npz`.
- Held-out test: not used for prompt/schema/renderer/n_syn/K selection and not evaluated in this window.
- New API calls in this attack window after the repair key handoff: 30.
- API accounting: cumulative usage is 929/3000 after this window; key was not stored in project files; request pacing followed `LLM_MIN_INTERVAL=2.0`.

## Completed Work

1. Step 0 gap diagnosis was completed and written to `berkeley_gap_diagnosis.md`.
2. Step 1 per-channel exemplar + per-band EQ was implemented in `milling_generation.py`.
3. Zero-API LLM recipe rerendering was implemented in `rerender_milling_llm_eq_pool.py`.
4. Step 2 class-order/prototype repair was attempted with `high_margin_coherent`, `full_train_margin`, repair prompting, combined pools, and train-only prototype admission.
5. Step 3 exemplar-grounded mixed background was attempted with full inner-train real backgrounds plus LLM wear overlays.
6. Step 4 `n_syn in {10,20,40}` scans were completed on the promoted candidates with 10 seeds.
7. The requested stop condition was reached because no inner-val candidate passed at least 5/6 Acc/Macro-F1 checks.

## Gate Summary

Inner-val threshold: for n={2,5,10} and metrics Acc/Macro-F1, at least 5/6 checks must satisfy LLM >= rule and LLM >= noise_aug.

| candidate | API calls | pool note | best passed checks |
|---|---:|---|---:|
| v6 coherent EQ | 0 | v4/v5 accepted recipes rerendered with per-band EQ | 0/6 |
| v7 ordered high-margin EQ | 0 | train-only high-margin class templates | 3/6 |
| v8 full-train-margin EQ | 0 | exemplar-grounded mixed background | 2/6 |
| v9 repair EQ coherent | 15 | first repair prompt smoke, 100/class rerender | 2/6 |
| v10 combined v6/v8/v9 | 0 | pool concatenation, counts 337/339/277 | 1/6 |
| v11 repair EQ coherent | 15 | repair supplement, 200/class rerender | 2/6 |
| v12 prototype-admitted | 0 | top 160/class by train-only prototype margin | 0/6 |

Best close result among final candidates was v11 at `n_syn=40`, n=2:

| method | n_real | Acc | Macro-F1 |
|---|---:|---:|---:|
| v11 repair EQ LLM | 2 | 0.59838 | 0.59772 |
| rule | 2 | 0.60108 | 0.60161 |
| noise_aug | 2 | 0.52942 | 0.51591 |

It still failed the rule comparison, so it cannot justify preregistration.

## Main Diagnosis

- The original weak class was `worn`; per-band EQ and repair prompting improved the low-shot worn region but did not create a reliable advantage over rule.
- Rule remains slightly cleaner at the decision boundary, especially for n=5 and n=10.
- Full real-background rendering improved structural distances, but the downstream classifier still favored the deterministic TPF structure in rule.
- Prototype admission based only on train-class margins did not transfer to inner-val; it reduced useful diversity rather than fixing the severe/worn boundary.

## Key Artifacts

- `berkeley_gap_diagnosis.md`
- `iteration_log.md`
- `berkeley_v7_inner_val_scan_summary.csv`
- `berkeley_v7_inner_val_gate_table.csv`
- `berkeley_v8_inner_val_scan_summary.csv`
- `berkeley_v8_inner_val_gate_table.csv`
- `berkeley_v9_inner_val_scan_summary.csv`
- `berkeley_v9_inner_val_gate_table.csv`
- `berkeley_v10_inner_val_scan_summary.csv`
- `berkeley_v10_inner_val_gate_table.csv`
- `berkeley_v11_inner_val_scan_summary.csv`
- `berkeley_v11_inner_val_gate_table.csv`
- `berkeley_v12_inner_val_scan_summary.csv`
- `berkeley_v12_inner_val_gate_table.csv`
- Pools:
  - `breeze/runs/milling_inner_attack_2026-07-08_v6_eq_coherent_x20/berkeley/llm/pool.npz`
  - `breeze/runs/milling_inner_attack_2026-07-08_v8_fulltrain_margin_eq/berkeley/llm/pool.npz`
  - `breeze/runs/milling_inner_attack_2026-07-08_v9_repair_eq_coherent/berkeley/llm/pool.npz`
  - `breeze/runs/milling_inner_attack_2026-07-08_v10_combined_v6_v8_v9/berkeley/llm/pool.npz`
  - `breeze/runs/milling_inner_attack_2026-07-08_v11_repair_eq_coherent_30slots/berkeley/llm/pool.npz`
  - `breeze/runs/milling_inner_attack_2026-07-08_v12_prototype_admitted/berkeley/llm/pool.npz`

## Final Decision

Do not run the formal held-out Berkeley test. The inner-val gate did not pass after the requested Step 1-4 route was exhausted. Berkeley remains an attack-log/failure-analysis result until the user approves a new strategy.
