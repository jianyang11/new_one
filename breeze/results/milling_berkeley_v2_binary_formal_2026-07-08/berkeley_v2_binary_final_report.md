# Berkeley v2 Binary Final Report

Date: 2026-07-08 Asia/Shanghai

Status: partial/no-go. Formal held-out test was run once after preregistration and is frozen.

## Protocol

- Task: `healthy` (`VB<0.2`) vs `degraded` (`VB>=0.2`).
- Rationale: literature-compatible Berkeley v2 three-class split (`0.2/0.7`) restored healthy/degradation separability but left failure F1 below `0.4`; binary protocol was preregistered before formal held-out evaluation.
- Formal train/test: `proc/milling_berkeley_v2_binary_train.npz` / `proc/milling_berkeley_v2_binary_test.npz`.
- Synthetic budget: `n_syn=20/class`.
- Real budgets: `n_real={2,5,10}`.
- Seeds: 40.
- API calls: 0 for v2 relabel, rerender, pools, and formal test.

## Formal Result

Registered comparisons passed: 15/18.

| n_real | metric | comparison | mean delta | Holm q | pass |
|---:|---|---|---:|---:|---|
| 2 | Acc | LLM > noise_aug | 0.090637 | 0.00000000 | True |
| 2 | Acc | LLM > rule | 0.002668 | 0.04625562 | True |
| 2 | Acc | LLM > random_open_loop | 0.261802 | 0.00000004 | True |
| 2 | Macro-F1 | LLM > noise_aug | 0.102760 | 0.00000000 | True |
| 2 | Macro-F1 | LLM > rule | 0.002065 | 0.10295770 | False |
| 2 | Macro-F1 | LLM > random_open_loop | 0.327402 | 0.00000000 | True |
| 5 | Acc | LLM > noise_aug | 0.060367 | 0.00000170 | True |
| 5 | Acc | LLM > rule | 0.004678 | 0.00016310 | True |
| 5 | Acc | LLM > random_open_loop | 0.169460 | 0.00000005 | True |
| 5 | Macro-F1 | LLM > noise_aug | 0.063922 | 0.00000114 | True |
| 5 | Macro-F1 | LLM > rule | 0.004067 | 0.00035919 | True |
| 5 | Macro-F1 | LLM > random_open_loop | 0.259447 | 0.00000000 | True |
| 10 | Acc | LLM > noise_aug | 0.037160 | 0.00000135 | True |
| 10 | Acc | LLM > rule | 0.000548 | 0.28766460 | False |
| 10 | Acc | LLM > random_open_loop | 0.132470 | 0.00000005 | True |
| 10 | Macro-F1 | LLM > noise_aug | 0.042463 | 0.00000004 | True |
| 10 | Macro-F1 | LLM > rule | 0.000202 | 0.38588630 | False |
| 10 | Macro-F1 | LLM > random_open_loop | 0.204615 | 0.00000004 | True |

## Interpretation

- The protocol revision fixed the v1 impossibility symptom: binary Berkeley is learnable and LLM strongly beats noise_aug and random_open_loop.
- The remaining failure is not random; it is the deterministic rule baseline. LLM is positive vs rule in all failed cells, but the n=2 Macro-F1 and n=10 Acc/Macro-F1 deltas are too small for Holm `q<0.05`.
- Berkeley cannot be claimed as a passed milling dataset under the registered success criterion.
- No post-test tuning is allowed. The next milling path is UMich CNC.

## Artifacts

- Preregistration: `breeze/results/milling_berkeley_v2_binary_2026-07-08/berkeley_v2_binary_preregistration.md`
- Formal summary: `berkeley_v2_binary_formal_summary.csv`
- Formal per-class F1: `berkeley_v2_binary_formal_per_class_f1.csv`
- Wilcoxon/Holm: `berkeley_v2_binary_formal_wilcoxon_holm.csv`
- Gate report: `berkeley_v2_binary_formal_gate_report.md`
