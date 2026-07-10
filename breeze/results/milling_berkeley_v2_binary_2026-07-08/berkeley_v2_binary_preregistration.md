# Berkeley Milling v2 Binary Preregistration

Date: 2026-07-08 Asia/Shanghai

Status: frozen before formal held-out evaluation.

## Protocol Rationale

The Berkeley v1 three-class attack used an internal `0.2/0.45` label split and failed on inner-val. The revised v2 protocol first tested the public `0.2/0.7` three-state definition:

- `healthy`: `VB < 0.2 mm`
- `degradation`: `0.2 <= VB < 0.7 mm`
- `failure`: `VB >= 0.7 mm`

The v2 three-class inner-val smoke restored healthy/degradation separability but did not restore failure separability. Mean failure F1 stayed below `0.4` for all methods and shots, with only 119 failure windows in inner-train and 34 in inner-val. Per the v2 decision rule, the formal Berkeley protocol is therefore frozen as the literature-compatible binary task:

- `healthy`: `VB < 0.2 mm`
- `degraded`: `VB >= 0.2 mm`

This revision is based on external protocol plus inner-train/inner-val diagnostics only. No formal held-out Berkeley result was used.

## Frozen Data

- Formal train NPZ: `proc/milling_berkeley_v2_binary_train.npz`
- Formal held-out test NPZ: `proc/milling_berkeley_v2_binary_test.npz`
- Inner train NPZ used for selection: `proc/milling_berkeley_v2_binary_inner_train.npz`
- Inner val NPZ used for selection: `proc/milling_berkeley_v2_binary_inner_val.npz`
- Split unit: case/run, never random windows.
- Split seed for inner split: `20260708`

Counts:

| split | healthy | degraded |
|---|---:|---:|
| train | 629 | 1207 |
| test | 221 | 425 |
| inner_train | 510 | 969 |
| inner_val | 119 | 238 |

## Selected Synthetic Protocol

- Label task: binary `healthy` vs `degraded`.
- Renderer/verifier: `milling_generation.py` with train-only verifier, per-channel exemplar backgrounds, per-band EQ support, and mean/std preservation.
- LLM source: zero-API reuse of accepted repair compact recipes from `milling_inner_attack_2026-07-08_v9_repair_llm_smoke`, remapped as `sharp->healthy`, `worn->degraded`, `severe->degraded`, then rerendered and reverified on the current training fold.
- EQ strength: `0.75`.
- Template policy: `coherent`.
- LLM mode: `repair`.
- Synthetic budget: `n_syn=20/class`.
- Few-shot real budgets: `n_real={2,5,10}`.
- CNN epochs: `20`.
- Formal seeds: `0..39`.

Full-train pool paths to build before formal evaluation:

- LLM: `breeze/runs/milling_berkeley_v2_binary_formal_2026-07-08_v11_repair_eq_coherent/berkeley/llm/pool.npz`
- Rule: `breeze/runs/milling_berkeley_v2_binary_formal_2026-07-08_rule_random/berkeley/rule/pool.npz`
- Random open-loop: `breeze/runs/milling_berkeley_v2_binary_formal_2026-07-08_rule_random/berkeley/random_open_loop/pool.npz`

## Inner-Val Selection Record

Budgets scanned: `n_syn in {10,20,40}`, 10 seeds, `n_real={2,5,10}`. All choices used only `milling_berkeley_v2_binary_inner_train/val`.

`n_syn=20` is selected because it passed LLM >= rule and LLM >= noise_aug in all 6 Acc/Macro-F1 checks and had the strongest coverage against the full registered controls among scanned budgets.

Inner-val at `n_syn=20`:

| n_real | metric | LLM | rule | noise_aug | random_open_loop |
|---:|---|---:|---:|---:|---:|
| 2 | Acc | 0.66641 | 0.66053 | 0.64565 | 0.62522 |
| 2 | Macro-F1 | 0.66546 | 0.65966 | 0.64341 | 0.56977 |
| 5 | Acc | 0.68854 | 0.68322 | 0.68546 | 0.70701 |
| 5 | Macro-F1 | 0.68570 | 0.68067 | 0.67694 | 0.64370 |
| 10 | Acc | 0.68378 | 0.68126 | 0.67510 | 0.74482 |
| 10 | Macro-F1 | 0.68244 | 0.67998 | 0.67205 | 0.67630 |

The random open-loop Accuracy risk is explicitly recorded before formal evaluation. The formal test will still include random open-loop as a registered comparator.

## Formal Statistical Test

For each `(n_real, metric)` pair, define one family with three one-sided paired Wilcoxon signed-rank comparisons:

- `LLM > noise_aug`
- `LLM > rule`
- `LLM > random_open_loop`

Metrics:

- Accuracy
- Macro-F1

Correction:

- Holm correction within each `(n_real, metric)` family.
- A comparison passes if Holm-adjusted `q < 0.05` and mean paired delta is positive.

Dataset-level success criterion:

- All registered comparisons against `noise_aug`, `rule`, and `random_open_loop` should pass for the Berkeley binary claim.
- If any comparison fails, the formal result is frozen and reported as partial/no-go; no post-test tuning is allowed.

## Formal Execution Lock

After this file is written, the next Berkeley binary formal run is executed once in a new result directory. No prompt, renderer, verifier, label, `n_syn`, `K`, seed count, metric, or statistical family may be changed based on formal held-out results.
