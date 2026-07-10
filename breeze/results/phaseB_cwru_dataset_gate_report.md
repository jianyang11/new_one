# Phase-B CWRU Dataset Gate Report

Generated: 2026-07-06T16:25:43

## Protocol

Dataset: CWRU 12 kHz drive-end vibration; fs=12000 Hz; window=2048; hop=2048. Classes: healthy, IR, B, OR.
Bearing: 6205-2RS JEM SKF. Frequency multipliers: BPFI=5.4152, BPFO=3.5848, BSF=4.7135, FTF=0.39828.

Splits covered before moving to the next dataset: within-condition `within_load0`, cross-condition `train_load0_test_load1`, and leave-one-load-out `lolo_load1`.

## API And Pool Accounting

Phase-B cumulative API requests after CWRU: 637/2000. The API key was not written to project files; a repository scan for the provided key substring returned no matches.

| stage | planned | actual | cumulative | notes |
|---|---:|---:|---:|---|
| phaseB_api_counter_reset | 0 | 0 | 0 | User provided API endpoint/key; key is not stored in project files. Total budget cap remains <=2000 requests. |
| phaseB_cwru_llm_smoke | 20 | 20 | 20 | within_load0; tag=smoke_api_v1; decision=FAIL_NEEDS_ITERATION; model=mimo-v2.5; key_not_stored |
| phaseB_cwru_llm_smoke | 10 | 10 | 30 | within_load0; tag=smoke_api_v2_healthy_prompt; decision=FAIL_NEEDS_ITERATION; model=mimo-v2.5; key_not_stored |
| phaseB_cwru_llm_smoke | 10 | 10 | 40 | within_load0; tag=smoke_api_v3_healthy_compact; decision=PASS_FOR_DOWNSTREAM_SMOKE; model=mimo-v2.5; key_not_stored |
| phaseB_cwru_llm_smoke | 15 | 15 | 55 | within_load0; tag=smoke_api_v4_fault_quality; decision=PASS_FOR_DOWNSTREAM_SMOKE; model=mimo-v2.5; key_not_stored |
| phaseB_cwru_llm_smoke | 15 | 15 | 70 | within_load0; tag=smoke_api_v5_fault_quality_pilot; decision=PASS_FOR_DOWNSTREAM_SMOKE; model=mimo-v2.5; key_not_stored |
| phaseB_cwru_llm_smoke | 560 | 567 | 637 | within_load0; tag=full_v1_supplement; decision=PASS_FOR_DOWNSTREAM_SMOKE; model=mimo-v2.5; key_not_stored |

### Full Supplement Acceptance

| class | supplement slots | API requests | accepted slots | accepted items | slot acceptance |
|---|---:|---:|---:|---:|---:|
| healthy | 140 | 142 | 139 | 561 | 0.993 |
| IR | 140 | 141 | 140 | 700 | 1.000 |
| B | 140 | 144 | 140 | 590 | 1.000 |
| OR | 140 | 140 | 140 | 700 | 1.000 |

### Final Pools

| pool | total items | healthy | IR | B | OR |
|---|---:|---:|---:|---:|---:|
| LLM full combined | 2734 | 603 | 750 | 631 | 750 |
| rule pilot | 309 | 38 | 92 | 80 | 99 |

## Downstream Schedule Results

All downstream runs used the registered schedule: n=5/10 uses 38 synthetic samples per class; n=25 uses 20 synthetic samples per class. CNN uses 20 epochs. Within-load0 has 10 seeds; cross-load1 has 20 seeds; LOLO has 20 seeds for n=5/10 and 40 seeds for n=25 after the 20-seed n=25 vs noise_aug boundary.

### Within Load0

| n_real | method | Acc | Macro-F1 | seeds/count |
|---:|---|---:|---:|---:|
| 5 | llm_full | 0.6298 | 0.6729 | 10 |
| 5 | rule | 0.5726 | 0.6137 | 10 |
| 5 | noise | 0.5134 | 0.5411 | 10 |
| 5 | real_only | 0.2627 | 0.1231 | 10 |
| 10 | llm_full | 0.6251 | 0.6725 | 10 |
| 10 | rule | 0.5935 | 0.6404 | 10 |
| 10 | noise | 0.5722 | 0.6120 | 10 |
| 10 | real_only | 0.3222 | 0.2540 | 10 |
| 25 | llm_full | 0.6668 | 0.7033 | 20 |
| 25 | rule | 0.6430 | 0.6803 | 20 |
| 25 | noise | 0.6245 | 0.6497 | 20 |
| 25 | real_only | 0.5013 | 0.5080 | 20 |

Paired Holm tests: 18/18 comparisons reject at q<0.05; max Holm q=0.0244141.

### Cross Load1

| n_real | method | Acc | Macro-F1 | seeds/count |
|---:|---|---:|---:|---:|
| 5 | llm | 0.6373±0.0227 | 0.6464±0.0247 | 20 |
| 5 | noise_aug | 0.5613±0.0547 | 0.5518±0.0717 | 20 |
| 5 | real_only | 0.2355±0.0706 | 0.1304±0.0595 | 20 |
| 5 | rule | 0.5938±0.0282 | 0.5973±0.0360 | 20 |
| 10 | llm | 0.6505±0.0312 | 0.6599±0.0385 | 20 |
| 10 | noise_aug | 0.6119±0.0562 | 0.6048±0.0665 | 20 |
| 10 | real_only | 0.3070±0.1164 | 0.2276±0.1443 | 20 |
| 10 | rule | 0.6111±0.0270 | 0.6142±0.0393 | 20 |
| 25 | llm | 0.6943±0.0469 | 0.6955±0.0438 | 20 |
| 25 | noise_aug | 0.6635±0.0505 | 0.6607±0.0564 | 20 |
| 25 | real_only | 0.5486±0.0746 | 0.5070±0.0742 | 20 |
| 25 | rule | 0.6670±0.0321 | 0.6641±0.0318 | 20 |

Paired Holm tests: 18/18 comparisons reject at q<0.05; max Holm q=0.0147877.

### LOLO Load1

| n_real | method | Acc | Macro-F1 | seeds/count |
|---:|---|---:|---:|---:|
| 5 | llm | 0.6444±0.0257 | 0.6537±0.0298 | 20 |
| 5 | noise_aug | 0.5897±0.0585 | 0.5901±0.0739 | 20 |
| 5 | real_only | 0.2417±0.0545 | 0.1302±0.0544 | 20 |
| 5 | rule | 0.5962±0.0257 | 0.5984±0.0402 | 20 |
| 10 | llm | 0.6528±0.0251 | 0.6625±0.0265 | 20 |
| 10 | noise_aug | 0.6145±0.0554 | 0.6088±0.0670 | 20 |
| 10 | real_only | 0.3058±0.1391 | 0.2442±0.1656 | 20 |
| 10 | rule | 0.6123±0.0306 | 0.6159±0.0379 | 20 |
| 25 | llm | 0.6857±0.0378 | 0.6886±0.0432 | 40 |
| 25 | noise_aug | 0.6490±0.0570 | 0.6490±0.0618 | 40 |
| 25 | real_only | 0.5470±0.0791 | 0.5097±0.0834 | 40 |
| 25 | rule | 0.6628±0.0360 | 0.6650±0.0400 | 40 |

Paired Holm tests: 18/18 comparisons reject at q<0.05; max Holm q=0.00471783.

## Decision

CWRU Phase-B smoke gate PASSED for progression to the next dataset. The supported claim at this point is limited to CNN few-shot CWRU protocols against real_only, noise_aug, and the local rule pool under the registered synthetic budget. This is not yet a full Phase-C/SOTA claim against GAN/diffusion or multiple classifiers.

Next dataset per user order: XJTU-SY. Before any XJTU generation, run dataset availability/license/protocol audit, M4 kinematic reconfiguration if labels/geometries support it, train-only verifier calibration, then ≤30 API acceptance-rate smoke.