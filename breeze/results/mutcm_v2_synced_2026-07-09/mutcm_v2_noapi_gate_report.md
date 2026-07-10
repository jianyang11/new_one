# MU-TCM v2 No-API Gate Report

Status: no LLM/API, no preregistration, no formal test.
- Gate passed: `True`

## Key Metrics

- real_only full Acc/Macro-F1: `0.8235/0.8211`
- real_only n_real=10 Acc/Macro-F1: `0.7941/0.7864`
- metadata_safe full Acc/Macro-F1: `0.4706/0.3200`
- rule full Acc/Macro-F1: `0.7059/0.6886`
- signal GroupKFold by condition Acc/Macro-F1: `0.8209/0.8189` majority `0.5075`
- signal GroupKFold by insert_edge Acc/Macro-F1: `0.7910/0.7906` majority `0.5075`

## Conditions

- real_only_full_acc_macro: `True`
- real_only_n10_acc_macro: `True`
- metadata_safe_not_close_to_signal: `True`
- insert_edge_group_signal_above_majority: `True`
- condition_group_signal_above_majority: `True`
- rule_not_saturated: `True`

## Decision

- No-API gate passed. MU-TCM may proceed to a separate v3 LLM inner-val attack only after freezing label scheme, split protocol, feature/window strategy, baselines, n_real/n_syn search, success criterion, Holm protocol, and API budget.
- Formal held-out test is still forbidden until preregistration is written.
