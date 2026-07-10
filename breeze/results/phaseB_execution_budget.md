# Phase-B Execution Budget Before Full Runs

Date: 2026-07-05

This is the required pre-full-run budget checkpoint after Phase-A v2 passed and after Phase-B local smoke tests.

## Completed Without New API Calls

- Phase-A v2: 0 new LLM API calls; used cached PU K=3 LLM pool.
- Phase-B protocol audit: 0 API calls.
- CWRU physics config and verifier/renderer design: 0 API calls.
- CWRU downstream smoke: 0 API calls.
- CWRU random/rule synthetic smoke: 0 API calls.
- DIRG protocol/downstream smoke: 0 API calls.

Total new LLM API calls since Phase-A v2 patch: 0.

## Local Smoke Artifacts

- `breeze/results/phaseB_dataset_protocol_summary.csv`
- `breeze/results/phaseB_protocol_audit.md`
- `breeze/results/phaseB_cwru_physics_config.csv`
- `breeze/results/phaseB_cwru_verifier_renderer_design.md`
- `breeze/runs/phaseB_cwru_within_load0_rule_smoke_v5/pool.npz`
- `breeze/results/phaseB_cwru_downstream_smoke.csv`
- `breeze/results/phaseB_dirg_verifier_renderer_design.md`
- `breeze/results/phaseB_dirg_downstream_smoke.csv`

## Proposed Minimal Phase-B Full Grid

The minimal grid below is designed to satisfy Phase-B evidence before entering Phase-C full baseline expansion.

| dataset | protocols | classes | methods | shots | seeds | training runs |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| PU | 4 file-split conditions | 3 | real_only, random_open_loop, rule, LLM | 5,10,25,50 | 10 | 640 |
| CWRU | within_load0, train_load0_test_load1, lolo_load0 | 4 | real_only, random_open_loop, rule, LLM | 5,10,25,50 | 10 | 480 |
| DIRG | loco_speed300_load1400 | 7 | real_only, noise_aug, rule/spectral, optional LLM | 5,10,25,50 | 10 | 120-160 |

CPU training estimate from smoke timings: CWRU is light; DIRG is slower because each test window is 6x4096. The full minimal grid is likely multiple hours on CPU and should be launched only after all synthetic pools exist and result CSVs are checkpointed.

## LLM API Requirement

No dataset-specific LLM recipe pools exist for CWRU or DIRG. Generating them requires API configuration and a call budget decision.

Current task constraints state one recipe equals one API call and each recipe is rendered into multiple seeds locally. A class-balanced target of 150 recipes/class implies:

| dataset/protocol | classes | calls per protocol | notes |
| --- | ---: | ---: | --- |
| CWRU within_load0 only | 4 | 600 | minimum CWRU LLM pool smoke/full candidate |
| CWRU 3 protocols | 4 | 1800 | near the 2000-call total cap by itself |
| DIRG one protocol | 7 | 1050 | not recommended until geometry/claim boundary is settled |
| PU additional conditions | 3 | 450 per condition | cached PU K=3 exists only for main Phase-A condition |

Given the 2000-call cap, the next defensible API step is not to generate every Phase-B pool at once. Recommended sequence:

1. CWRU within_load0 LLM smoke: 20 recipes/class = 80 API calls, with renderer multi-seed and verifier admission.
2. If CWRU smoke admission/downstream is promising, expand CWRU within_load0 to 150 recipes/class = 600 total calls.
3. Only after CWRU passes, decide whether to spend the remaining budget on CWRU cross-condition/LOLO or PU additional conditions.

## Blocker

The required API configuration is not present in the task prompt. Before any new LLM recipe generation, the following must be supplied or confirmed:

- base_url
- model
- API key environment variable or key value
- whether the total remaining call cap is 2000 from this point, or 2000 including previous cached runs

Until then, Phase B can continue only with local non-LLM baselines and infrastructure.

## 2026-07-06 Addendum: CWRU API Smoke Result

The API endpoint/key were provided by the user on 2026-07-06. The key is not stored in project files. API usage is tracked in `breeze/results/phaseB_api_usage_log.csv`.

The first CWRU small-batch validation used the initial 30-request cap. After user approval, a compact healthy-only v3 repair used 10 additional requests:

| run tag | classes | planned slots | API requests | cumulative API | decision |
|---|---|---:|---:|---:|---|
| `smoke_api_v1` | healthy/IR/B/OR | 20 | 20 | 20 | FAIL_NEEDS_ITERATION |
| `smoke_api_v2_healthy_prompt` | healthy | 10 | 10 | 30 | FAIL_NEEDS_ITERATION |
| `smoke_api_v3_healthy_compact` | healthy | 10 | 10 | 40 | PASS_FOR_DOWNSTREAM_SMOKE |
| `smoke_api_v4_fault_quality` | IR/B/OR | 15 | 15 | 55 | PASS_FOR_DOWNSTREAM_SMOKE |

Admission result: repaired. IR/B/OR accepted in `smoke_api_v1`; healthy accepted in `smoke_api_v3_healthy_compact`. The failed v2 run is retained because it documents that 20-30 component prompts exceed the effective 900-token JSON budget. Combined report: `breeze/results/phaseB_cwru_llm_smoke_combined_gate_report.md`.

Downstream result after v3: not sufficient for scale-up. The combined LLM smoke pool passed admission, but CNN downstream smoke was unstable and did not consistently beat noise augmentation or the existing rule smoke at the same n_syn=10 budget. See `breeze/results/phaseB_cwru_llm_smoke_v3_report.md` and `breeze/results/phaseB_cwru_llm_smoke_v3_downstream_summary.csv`.

The v4 fault-quality prompt used the v3 diagnostics to lower fault RMS toward the real class median and increase diagnostic impact prominence without changing the verifier or post-processing samples. It produced accepted IR/B/OR slots and, when combined with v3 healthy, improved 5-seed downstream smoke at n_syn≈20. Summary: `breeze/results/phaseB_cwru_v4_smoke_decision_report.md`.

Decision: do not start CWRU full LLM pool generation, XJTU, or IMS yet. v4 is promising, but before spending ~600 API calls on 150/class CWRU generation, run a broader local verification grid using existing smoke pools and document the rule-pool healthy bottleneck at n_syn20.

## 2026-07-06 Addendum: CWRU v5 Balanced Pilot

The v5 pilot supplemented CWRU fault classes with 15 additional API requests and built a balanced pilot pool:

| pool | healthy | IR | B | OR |
|---|---:|---:|---:|---:|
| LLM v5 pilot | 42 | 50 | 41 | 50 |
| rule pilot v1 | 38 | 92 | 80 | 99 |

Total Phase-B API usage after v5: 70 requests.

Balanced pilot downstream used n_syn=38/class. It passed n=5/10 but did not significantly beat noise_aug on n=25. A budget ablation then showed that n_syn=20/class is more stable for n=25; the 20-seed n=25 check passed against rule and noise on Accuracy and Macro-F1. Reports:

- `breeze/results/phaseB_cwru_v5_balanced_pilot_report.md`
- `breeze/results/phaseB_cwru_v5_budget_ablation_report.md`
- `breeze/results/phaseB_cwru_v5_nsyn20_mixedseed_check.md`

Pre-full CWRU budget schedule, if full CWRU generation is approved:

- Use the v3 healthy compact prompt and v4/v5 fault-quality prompt family.
- Reuse pilot slots as provenance-preserved part of the CWRU full pool.
- Add 140 new slots/class to reach 150 LLM recipe slots/class, because each class already has 10 pilot slots.
- Additional API requests: 4 classes x 140 = 560.
- Projected cumulative Phase-B API requests: 70 + 560 = 630, below the 2000 cap.
- Downstream synthetic budget schedule to pre-register before full CWRU evaluation: n_syn=38/class for n_real=5/10 and n_syn=20/class for n_real>=25. This schedule is based on the pilot budget ablation and must be disclosed as a pilot-selected schedule, not as a final-test-tuned choice.
