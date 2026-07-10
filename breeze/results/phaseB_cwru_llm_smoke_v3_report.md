# Phase-B CWRU LLM Smoke v3 Report

## API and Admission

- Cumulative API requests since reset: 40.
- v1 faults: IR/B/OR each accepted 5/5 slots; healthy failed 0/5.
- v2 healthy full-anchor prompt: 10/10 parse failed due JSON truncation under max_tokens<=900.
- v3 healthy compact prompt: 10/10 slots accepted, 42 accepted items.
- Combined LLM smoke pool: breeze/runs/phaseB_cwru_within_load0_llm_smoke_combined_v3/pool.npz with by-class counts {'healthy': 42, 'IR': 23, 'B': 23, 'OR': 25}.

## Downstream Smoke

| method | n_real | seeds | mean acc | mean macro-F1 | acc values | macro-F1 values |
|---|---:|---:|---:|---:|---|---|
| llm_nsyn10 | 5 | 2 | 0.4151 | 0.3624 | 0.3072;0.5229 | 0.1848;0.5401 |
| llm_nsyn10 | 10 | 2 | 0.4951 | 0.4979 | 0.5098;0.4804 | 0.5147;0.4810 |
| llm_nsyn20 | 5 | 2 | 0.4755 | 0.4872 | 0.6209;0.3301 | 0.6453;0.3292 |
| llm_nsyn20 | 10 | 2 | 0.4575 | 0.4666 | 0.4444;0.4706 | 0.4488;0.4844 |
| llm_nsyn5 | 5 | 2 | 0.3121 | 0.2548 | 0.2092;0.4150 | 0.1227;0.3869 |
| llm_nsyn5 | 10 | 2 | 0.4771 | 0.4206 | 0.4673;0.4869 | 0.3169;0.5243 |
| noise_aug | 5 | 2 | 0.4968 | 0.5242 | 0.4706;0.5229 | 0.5020;0.5465 |
| noise_aug | 10 | 2 | 0.5964 | 0.6401 | 0.5392;0.6536 | 0.6017;0.6785 |
| real_only | 5 | 2 | 0.2353 | 0.0979 | 0.2353;0.2353 | 0.0952;0.1006 |
| real_only | 10 | 2 | 0.3954 | 0.3450 | 0.4085;0.3824 | 0.3259;0.3641 |
| rule_nsyn10 | 5 | 2 | 0.4772 | 0.4298 | 0.3791;0.5752 | 0.2263;0.6334 |
| rule_nsyn10 | 10 | 2 | 0.5736 | 0.5931 | 0.5817;0.5654 | 0.5975;0.5886 |

## Decision

Admission gate is repaired, but downstream smoke is not yet strong enough to justify CWRU full-pool scale-up. The LLM pool is unstable across seeds and does not consistently beat noise_aug or the existing rule smoke at the same n_syn=10 synthetic budget. Do not run 150/class CWRU LLM full generation yet. Next work should diagnose class-level mismatch and improve recipe quality before spending hundreds of API calls.
