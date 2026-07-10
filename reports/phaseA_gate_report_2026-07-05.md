# Phase-A LLM Contribution Gate

Date: 2026-07-05

Inputs:

- Downstream CSV: `breeze/results/phaseA_downstream_cnn.csv`
- Random pool: `breeze/runs/recipe_ablation_random_v2_full/pool_v2.npz`
- Rule pool: `breeze/runs/recipe_ablation_rule_v2_full/pool_v2.npz`
- LLM K=3 + v2 rescreen pool: `breeze/runs/rescreen_v2_full/pool_v2.npz`

All three recipe sources use 150 recipe slots per class and the same renderer/v2 verifier for admission in this Phase-A comparison. Random accepted no slots, so its downstream augmentation contains no synthetic samples and equals real-only for the same seeds.

## Pool Admission

| baseline | recipe_slots | accepted_slots | slot_acceptance | accepted_items_before_diversity | kept_after_diversity | kept_healthy | kept_OR | kept_IR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phaseA_random_v2 | 450 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| phaseA_rule_v2 | 450 | 167 | 0.371111 | 763 | 703 | 227 | 407 | 69 |
| phaseA_llm_k3_v2 | 450 | 286 | 0.635556 | 761 | 757 | 192 | 304 | 261 |

## Downstream Means

| baseline | n_real | metric | n | mean | std | median | n_syn_values |
| --- | --- | --- | --- | --- | --- | --- | --- |
| real_only | 10 | acc | 8 | 0.6449 | 0.108713 | 0.6923 | 0 |
| real_only | 10 | macro_f1 | 8 | 0.603962 | 0.129172 | 0.6733 | 0 |
| real_only | 25 | acc | 8 | 0.737125 | 0.0372077 | 0.7484 | 0 |
| real_only | 25 | macro_f1 | 8 | 0.71845 | 0.042482 | 0.72315 | 0 |
| real_only | 50 | acc | 8 | 0.788075 | 0.0197175 | 0.79625 | 0 |
| real_only | 50 | macro_f1 | 8 | 0.774288 | 0.0253079 | 0.7785 | 0 |
| phaseA_random_v2 | 10 | acc | 8 | 0.6449 | 0.108713 | 0.6923 | 0 |
| phaseA_random_v2 | 10 | macro_f1 | 8 | 0.603962 | 0.129172 | 0.6733 | 0 |
| phaseA_random_v2 | 25 | acc | 8 | 0.737125 | 0.0372077 | 0.7484 | 0 |
| phaseA_random_v2 | 25 | macro_f1 | 8 | 0.71845 | 0.042482 | 0.72315 | 0 |
| phaseA_random_v2 | 50 | acc | 8 | 0.788075 | 0.0197175 | 0.79625 | 0 |
| phaseA_random_v2 | 50 | macro_f1 | 8 | 0.774288 | 0.0253079 | 0.7785 | 0 |
| phaseA_rule_v2 | 10 | acc | 8 | 0.719725 | 0.0588177 | 0.71985 | 469 |
| phaseA_rule_v2 | 10 | macro_f1 | 8 | 0.719712 | 0.0590299 | 0.7145 | 469 |
| phaseA_rule_v2 | 25 | acc | 8 | 0.784563 | 0.0301219 | 0.7869 | 469 |
| phaseA_rule_v2 | 25 | macro_f1 | 8 | 0.779888 | 0.0377071 | 0.7809 | 469 |
| phaseA_rule_v2 | 50 | acc | 8 | 0.851862 | 0.0156298 | 0.85705 | 469 |
| phaseA_rule_v2 | 50 | macro_f1 | 8 | 0.853662 | 0.017639 | 0.86045 | 469 |
| phaseA_llm_k3_v2 | 10 | acc | 8 | 0.78795 | 0.0311851 | 0.7843 | 592 |
| phaseA_llm_k3_v2 | 10 | macro_f1 | 8 | 0.790637 | 0.0289341 | 0.78755 | 592 |
| phaseA_llm_k3_v2 | 25 | acc | 8 | 0.808213 | 0.0324192 | 0.8181 | 592 |
| phaseA_llm_k3_v2 | 25 | macro_f1 | 8 | 0.807887 | 0.0354339 | 0.8148 | 592 |
| phaseA_llm_k3_v2 | 50 | acc | 8 | 0.845612 | 0.0174439 | 0.8508 | 592 |
| phaseA_llm_k3_v2 | 50 | macro_f1 | 8 | 0.848375 | 0.0177844 | 0.85285 | 592 |

## One-Sided Paired Wilcoxon Tests

| metric | n_real | comparison | mean_delta | median_delta | wins | losses | wilcoxon_p_one_sided | holm_q | bh_q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| acc | 10 | phaseA_llm_k3_v2>phaseA_random_v2 | 0.14305 | 0.1097 | 8 | 0 | 0.00390625 | 0.046875 | 0.009375 |
| acc | 10 | phaseA_llm_k3_v2>phaseA_rule_v2 | 0.068225 | 0.08055 | 7 | 1 | 0.0117188 | 0.0703125 | 0.0175781 |
| acc | 25 | phaseA_llm_k3_v2>phaseA_random_v2 | 0.0710875 | 0.0598 | 7 | 1 | 0.0078125 | 0.0546875 | 0.015625 |
| acc | 25 | phaseA_llm_k3_v2>phaseA_rule_v2 | 0.02365 | 0.03115 | 6 | 2 | 0.0390625 | 0.117188 | 0.046875 |
| acc | 50 | phaseA_llm_k3_v2>phaseA_random_v2 | 0.0575375 | 0.0525 | 8 | 0 | 0.00390625 | 0.046875 | 0.009375 |
| acc | 50 | phaseA_llm_k3_v2>phaseA_rule_v2 | -0.00625 | -0.0016 | 4 | 4 | 0.808594 | 1 | 0.808594 |
| macro_f1 | 10 | phaseA_llm_k3_v2>phaseA_random_v2 | 0.186675 | 0.13205 | 8 | 0 | 0.00390625 | 0.046875 | 0.009375 |
| macro_f1 | 10 | phaseA_llm_k3_v2>phaseA_rule_v2 | 0.070925 | 0.0741 | 7 | 1 | 0.0117188 | 0.0703125 | 0.0175781 |
| macro_f1 | 25 | phaseA_llm_k3_v2>phaseA_random_v2 | 0.0894375 | 0.08095 | 8 | 0 | 0.00390625 | 0.046875 | 0.009375 |
| macro_f1 | 25 | phaseA_llm_k3_v2>phaseA_rule_v2 | 0.028 | 0.03685 | 6 | 2 | 0.0273438 | 0.109375 | 0.0364583 |
| macro_f1 | 50 | phaseA_llm_k3_v2>phaseA_random_v2 | 0.0740875 | 0.0629 | 8 | 0 | 0.00390625 | 0.046875 | 0.009375 |
| macro_f1 | 50 | phaseA_llm_k3_v2>phaseA_rule_v2 | -0.0052875 | -0.0022 | 4 | 4 | 0.769531 | 1 | 0.808594 |

## Gate Decision

Phase A does not pass.

Reason: LLM K=3 + v2 is significantly better than the random recipe source, but it is not significantly better than the rule recipe source after Holm correction, and at n_real=50 it is slightly worse than rule on both Accuracy and Macro-F1. This violates the required gate that LLM recipe downstream Accuracy/Macro-F1 must be significantly higher than both random and rule.

Per the latest user instruction, do not proceed to Stage B/C/D/E/F/G expansion until the LLM contribution mechanism is improved and this Phase-A gate is re-run.
