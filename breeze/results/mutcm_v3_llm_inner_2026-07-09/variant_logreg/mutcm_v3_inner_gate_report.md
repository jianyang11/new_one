# MU-TCM v3 Inner-Val Gate Report

Status: inner-val only. No preregistration/formal test was run by this script.
- Selected n_syn from inner-val scan: `40`
- Core pass count: `2/6`
- Gate passed: `False`

## Synthetic Pool Support

- rule: `{'path': 'breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_rule_pool.npz', 'n': 160, 'counts': {'healthy': 80, 'worn': 80}, 'classifier': 'LogisticRegression'}`
- random_open_loop: `{'path': 'breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_random_open_loop_pool.npz', 'n': 160, 'counts': {'healthy': 80, 'worn': 80}, 'classifier': 'LogisticRegression'}`
- LLM_synthetic: `{'path': 'breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_llm_synthetic_pool.npz', 'n': 121, 'counts': {'healthy': 60, 'worn': 61}, 'classifier': 'LogisticRegression'}`

## Core Comparisons

- n_real=2 acc: LLM `0.7145`, noise `0.6520`, rule `0.7471`, random `0.7468` -> `False`
- n_real=2 macro_f1: LLM `0.7030`, noise `0.6366`, rule `0.7388`, random `0.7389` -> `False`
- n_real=5 acc: LLM `0.7100`, noise `0.6966`, rule `0.7218`, random `0.7292` -> `False`
- n_real=5 macro_f1: LLM `0.7010`, noise `0.6874`, rule `0.7135`, random `0.7210` -> `False`
- n_real=10 acc: LLM `0.7301`, noise `0.7245`, rule `0.7132`, random `0.7265` -> `True`
- n_real=10 macro_f1: LLM `0.7234`, noise `0.7118`, rule `0.6927`, random `0.7126` -> `True`

## Hard Constraints

- healthy_not_collapsed: `True`
- worn_not_collapsed: `True`
- condition_not_single_condition: `True`
- berkeley_like_weak_gain_risk: `True`

## Holm Diagnostics

- n_real=2 acc LLM_synthetic>noise_aug: delta `0.0625`, win_rate `0.900`, q `0.000542`
- n_real=2 acc LLM_synthetic>rule: delta `-0.0326`, win_rate `0.100`, q `1`
- n_real=2 acc LLM_synthetic>random_open_loop: delta `-0.0324`, win_rate `0.100`, q `1`
- n_real=2 macro_f1 LLM_synthetic>noise_aug: delta `0.0664`, win_rate `0.900`, q `0.000123`
- n_real=2 macro_f1 LLM_synthetic>rule: delta `-0.0358`, win_rate `0.100`, q `1`
- n_real=2 macro_f1 LLM_synthetic>random_open_loop: delta `-0.0359`, win_rate `0.100`, q `1`
- n_real=5 acc LLM_synthetic>noise_aug: delta `0.0135`, win_rate `0.600`, q `0.1228`
- n_real=5 acc LLM_synthetic>rule: delta `-0.0118`, win_rate `0.200`, q `1`
- n_real=5 acc LLM_synthetic>random_open_loop: delta `-0.0191`, win_rate `0.150`, q `1`
- n_real=5 macro_f1 LLM_synthetic>noise_aug: delta `0.0136`, win_rate `0.650`, q `0.2474`
- n_real=5 macro_f1 LLM_synthetic>rule: delta `-0.0125`, win_rate `0.300`, q `1`
- n_real=5 macro_f1 LLM_synthetic>random_open_loop: delta `-0.0200`, win_rate `0.150`, q `1`
- n_real=10 acc LLM_synthetic>noise_aug: delta `0.0056`, win_rate `0.350`, q `1`
- n_real=10 acc LLM_synthetic>rule: delta `0.0169`, win_rate `0.300`, q `1`
- n_real=10 acc LLM_synthetic>random_open_loop: delta `0.0037`, win_rate `0.050`, q `1`
- n_real=10 macro_f1 LLM_synthetic>noise_aug: delta `0.0116`, win_rate `0.350`, q `1`
- n_real=10 macro_f1 LLM_synthetic>rule: delta `0.0308`, win_rate `0.300`, q `1`
- n_real=10 macro_f1 LLM_synthetic>random_open_loop: delta `0.0108`, win_rate `0.150`, q `1`

Decision: inner-val gate failed. Do not preregister and do not run formal held-out test.
