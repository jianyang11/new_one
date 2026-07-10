# MU-TCM v3 Inner-Val Gate Report

Status: inner-val only. No preregistration/formal test was run by this script.
- Selected n_syn from inner-val scan: `20`
- Core pass count: `2/6`
- Gate passed: `False`

## Synthetic Pool Support

- rule: `{'path': '/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_rule_pool.npz', 'n': 160, 'counts': {'healthy': 80, 'worn': 80}}`
- random_open_loop: `{'path': '/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_random_open_loop_pool.npz', 'n': 160, 'counts': {'healthy': 80, 'worn': 80}}`
- LLM_synthetic: `{'path': '/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_llm_synthetic_pool.npz', 'n': 121, 'counts': {'healthy': 60, 'worn': 61}, 'api_requests_total': 51}`

## Core Comparisons

- n_real=2 acc: LLM `0.7252`, noise `0.6608`, rule `0.7382`, random `0.7404` -> `False`
- n_real=2 macro_f1: LLM `0.7131`, noise `0.6397`, rule `0.7272`, random `0.7305` -> `False`
- n_real=5 acc: LLM `0.7419`, noise `0.7186`, rule `0.7458`, random `0.7387` -> `False`
- n_real=5 macro_f1: LLM `0.7322`, noise `0.7042`, rule `0.7361`, random `0.7285` -> `False`
- n_real=10 acc: LLM `0.7407`, noise `0.7328`, rule `0.7377`, random `0.7358` -> `True`
- n_real=10 macro_f1: LLM `0.7316`, noise `0.7221`, rule `0.7285`, random `0.7266` -> `True`

## Hard Constraints

- healthy_not_collapsed: `True`
- worn_not_collapsed: `True`
- condition_not_single_condition: `True`
- berkeley_like_weak_gain_risk: `True`

## Holm Diagnostics

- n_real=2 acc LLM_synthetic>noise_aug: delta `0.0645`, win_rate `0.750`, q `0.01133`
- n_real=2 acc LLM_synthetic>rule: delta `-0.0130`, win_rate `0.150`, q `1`
- n_real=2 acc LLM_synthetic>random_open_loop: delta `-0.0152`, win_rate `0.200`, q `1`
- n_real=2 macro_f1 LLM_synthetic>noise_aug: delta `0.0734`, win_rate `0.750`, q `0.01415`
- n_real=2 macro_f1 LLM_synthetic>rule: delta `-0.0141`, win_rate `0.200`, q `1`
- n_real=2 macro_f1 LLM_synthetic>random_open_loop: delta `-0.0174`, win_rate `0.250`, q `1`
- n_real=5 acc LLM_synthetic>noise_aug: delta `0.0233`, win_rate `0.600`, q `0.04117`
- n_real=5 acc LLM_synthetic>rule: delta `-0.0039`, win_rate `0.300`, q `0.8654`
- n_real=5 acc LLM_synthetic>random_open_loop: delta `0.0032`, win_rate `0.400`, q `0.4886`
- n_real=5 macro_f1 LLM_synthetic>noise_aug: delta `0.0280`, win_rate `0.650`, q `0.03948`
- n_real=5 macro_f1 LLM_synthetic>rule: delta `-0.0039`, win_rate `0.300`, q `0.8688`
- n_real=5 macro_f1 LLM_synthetic>random_open_loop: delta `0.0037`, win_rate `0.500`, q `0.3803`
- n_real=10 acc LLM_synthetic>noise_aug: delta `0.0078`, win_rate `0.500`, q `0.1277`
- n_real=10 acc LLM_synthetic>rule: delta `0.0029`, win_rate `0.700`, q `0.1828`
- n_real=10 acc LLM_synthetic>random_open_loop: delta `0.0049`, win_rate `0.500`, q `0.1828`
- n_real=10 macro_f1 LLM_synthetic>noise_aug: delta `0.0095`, win_rate `0.600`, q `0.08908`
- n_real=10 macro_f1 LLM_synthetic>rule: delta `0.0032`, win_rate `0.700`, q `0.1977`
- n_real=10 macro_f1 LLM_synthetic>random_open_loop: delta `0.0050`, win_rate `0.600`, q `0.1977`

Decision: inner-val gate failed. Do not preregister and do not run formal held-out test.
