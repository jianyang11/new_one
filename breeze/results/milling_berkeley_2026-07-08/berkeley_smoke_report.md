# Berkeley/NASA Milling Smoke Report

## Scope

- Dataset: UC Berkeley/NASA milling, case-level split.
- Classes: `sharp`, `worn`, `severe`.
- Synthetic budget for downstream smoke: `n_syn=20/class`.
- Downstream smoke: CNN, epochs=20, seeds=0-4.
- API usage through this block: 866/2000 cumulative.

## Pool Status

| source | pool | counts | status |
|---|---|---:|---|
| LLM compact rescreen v4 | `breeze/runs/milling_generation_2026-07-08_llm_rescreen_v4/berkeley/llm_rescreen/pool.npz` | sharp=55, worn=34, severe=23 | class-balanced for B=20 |
| rule | `breeze/runs/milling_generation_2026-07-08_smoke_v7/berkeley/rule/pool.npz` | sharp=27, worn=38, severe=30 | class-balanced for B=20 |
| random open-loop | `breeze/runs/milling_generation_2026-07-08_smoke_v7/berkeley/random_open_loop/pool.npz` | sharp=20, worn=20, severe=20 | class-balanced for B=20 |

## Downstream Smoke Means

| n_real | method | Accuracy | Macro-F1 |
|---:|---|---:|---:|
| 2 | LLM | 0.4124 | 0.2964 |
| 2 | rule | 0.3889 | 0.2866 |
| 2 | random open-loop | 0.3514 | 0.1976 |
| 2 | noise_aug | 0.5046 | 0.4848 |
| 2 | real_only | 0.4579 | 0.4183 |
| 5 | LLM | 0.4913 | 0.4623 |
| 5 | rule | 0.4761 | 0.4327 |
| 5 | random open-loop | 0.3898 | 0.3243 |
| 5 | noise_aug | 0.5638 | 0.5343 |
| 5 | real_only | 0.4957 | 0.4529 |
| 10 | LLM | 0.5498 | 0.5348 |
| 10 | rule | 0.5610 | 0.5422 |
| 10 | random open-loop | 0.4344 | 0.3852 |
| 10 | noise_aug | 0.5891 | 0.5793 |
| 10 | real_only | 0.4978 | 0.4454 |

## Decision

Berkeley is not ready for formal 40-seed downstream claims. The LLM pool is consistently better than random open-loop and competitive with rule, but it is below `noise_aug` at n=2/5/10. The current evidence supports retaining Berkeley as an admission/physics audit candidate or continuing method development on training-fold validation; it does not support the milling downstream success gate.
