# MU-TCM v3 Inner-Val Gate Report

Status: inner-val only. No preregistration/formal test was run by this script.
- Selected n_syn from inner-val scan: `10`
- Core pass count: `0/6`
- Gate passed: `False`

## Synthetic Pool Support

- rule: `{'path': 'breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_rule_pool.npz', 'n': 160, 'counts': {'healthy': 80, 'worn': 80}}`
- random_open_loop: `{'path': 'breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_random_open_loop_pool.npz', 'n': 160, 'counts': {'healthy': 80, 'worn': 80}}`
- LLM_synthetic: `{'path': 'breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_llm_synthetic_pool_no_boundary.npz', 'n': 90, 'counts': {'healthy': 45, 'worn': 45}, 'filter': 'exclude boundary recipes'}`

## Core Comparisons

- n_real=2 acc: LLM `0.7289`, noise `0.6723`, rule `0.7407`, random `0.7333` -> `False`
- n_real=2 macro_f1: LLM `0.7169`, noise `0.6510`, rule `0.7287`, random `0.7225` -> `False`
- n_real=5 acc: LLM `0.7324`, noise `0.7230`, rule `0.7426`, random `0.7407` -> `False`
- n_real=5 macro_f1: LLM `0.7215`, noise `0.7108`, rule `0.7330`, random `0.7307` -> `False`
- n_real=10 acc: LLM `0.7355`, noise `0.7377`, rule `0.7375`, random `0.7373` -> `False`
- n_real=10 macro_f1: LLM `0.7258`, noise `0.7273`, rule `0.7281`, random `0.7280` -> `False`

## Hard Constraints

- healthy_not_collapsed: `True`
- worn_not_collapsed: `True`
- condition_not_single_condition: `True`
- berkeley_like_weak_gain_risk: `True`

## Holm Diagnostics

- n_real=2 acc LLM_synthetic>noise_aug: delta `0.0566`, win_rate `0.800`, q `0.002541`
- n_real=2 acc LLM_synthetic>rule: delta `-0.0118`, win_rate `0.300`, q `1`
- n_real=2 acc LLM_synthetic>random_open_loop: delta `-0.0044`, win_rate `0.200`, q `1`
- n_real=2 macro_f1 LLM_synthetic>noise_aug: delta `0.0658`, win_rate `0.800`, q `0.001525`
- n_real=2 macro_f1 LLM_synthetic>rule: delta `-0.0118`, win_rate `0.300`, q `1`
- n_real=2 macro_f1 LLM_synthetic>random_open_loop: delta `-0.0056`, win_rate `0.250`, q `1`
- n_real=5 acc LLM_synthetic>noise_aug: delta `0.0093`, win_rate `0.600`, q `0.1498`
- n_real=5 acc LLM_synthetic>rule: delta `-0.0103`, win_rate `0.150`, q `1`
- n_real=5 acc LLM_synthetic>random_open_loop: delta `-0.0083`, win_rate `0.200`, q `1`
- n_real=5 macro_f1 LLM_synthetic>noise_aug: delta `0.0107`, win_rate `0.650`, q `0.1819`
- n_real=5 macro_f1 LLM_synthetic>rule: delta `-0.0115`, win_rate `0.300`, q `1`
- n_real=5 macro_f1 LLM_synthetic>random_open_loop: delta `-0.0092`, win_rate `0.200`, q `1`
- n_real=10 acc LLM_synthetic>noise_aug: delta `-0.0022`, win_rate `0.400`, q `1`
- n_real=10 acc LLM_synthetic>rule: delta `-0.0020`, win_rate `0.300`, q `1`
- n_real=10 acc LLM_synthetic>random_open_loop: delta `-0.0017`, win_rate `0.500`, q `1`
- n_real=10 macro_f1 LLM_synthetic>noise_aug: delta `-0.0015`, win_rate `0.450`, q `1`
- n_real=10 macro_f1 LLM_synthetic>rule: delta `-0.0023`, win_rate `0.300`, q `1`
- n_real=10 macro_f1 LLM_synthetic>random_open_loop: delta `-0.0022`, win_rate `0.550`, q `1`

Decision: inner-val gate failed. Do not preregister and do not run formal held-out test.
