# Phase-B CWRU v4 Smoke Decision Report

## API Usage

- Cumulative Phase-B API requests: 55.
- v4 fault-quality retry used 15 requests after v3 healthy repair; total CWRU API smoke requests: 55.

## 5-Seed Downstream Smoke

| method | n_real | seeds | n_syn values | mean acc | mean macro-F1 | acc values | macro-F1 values |
|---|---:|---:|---|---:|---:|---|---|
| llm_v4_nsyn20 | 5 | 5 | 80;80;80;80;80 | 0.5726 | 0.5685 | 0.5719;0.6046;0.5425;0.4967;0.6471 | 0.6119;0.6313;0.5300;0.4368;0.6324 |
| rule_nsyn20 | 5 | 5 | 73;73;73;73;73 | 0.4824 | 0.4484 | 0.3922;0.5392;0.5033;0.3627;0.6144 | 0.2556;0.5595;0.5278;0.2470;0.6519 |
| noise_nsyn20 | 5 | 5 | 80;80;80;80;80 | 0.4726 | 0.4498 | 0.2941;0.4641;0.5229;0.5556;0.5261 | 0.2453;0.4196;0.4841;0.6118;0.4881 |
| llm_v4_nsyn20 | 10 | 5 | 80;80;80;80;80 | 0.6216 | 0.6511 | 0.6405;0.6275;0.6503;0.5359;0.6536 | 0.6899;0.6504;0.6789;0.5636;0.6726 |
| rule_nsyn20 | 10 | 5 | 73;73;73;73;73 | 0.6020 | 0.6344 | 0.6078;0.6144;0.6111;0.5458;0.6307 | 0.6479;0.6518;0.6661;0.5853;0.6211 |
| noise_nsyn20 | 10 | 5 | 80;80;80;80;80 | 0.5536 | 0.5774 | 0.6176;0.4739;0.5588;0.6340;0.4837 | 0.6618;0.4411;0.6253;0.6552;0.5035 |

## Paired Deltas

| comparison | n_real | metric | seeds | mean delta | wins | delta values |
|---|---:|---|---:|---:|---:|---|
| llm_v4_nsyn20-rule_nsyn20 | 5 | acc | 5 | 0.0902 | 5/5 | 0.1797;0.0654;0.0392;0.1340;0.0327 |
| llm_v4_nsyn20-noise_nsyn20 | 5 | acc | 5 | 0.1000 | 4/5 | 0.2778;0.1405;0.0196;-0.0589;0.1210 |
| llm_v4_nsyn20-rule_nsyn20 | 5 | macro_f1 | 5 | 0.1201 | 4/5 | 0.3563;0.0718;0.0022;0.1898;-0.0195 |
| llm_v4_nsyn20-noise_nsyn20 | 5 | macro_f1 | 5 | 0.1187 | 4/5 | 0.3666;0.2117;0.0459;-0.1750;0.1443 |
| llm_v4_nsyn20-rule_nsyn20 | 10 | acc | 5 | 0.0196 | 4/5 | 0.0327;0.0131;0.0392;-0.0099;0.0229 |
| llm_v4_nsyn20-noise_nsyn20 | 10 | acc | 5 | 0.0680 | 4/5 | 0.0229;0.1536;0.0915;-0.0981;0.1699 |
| llm_v4_nsyn20-rule_nsyn20 | 10 | macro_f1 | 5 | 0.0166 | 3/5 | 0.0420;-0.0014;0.0128;-0.0217;0.0515 |
| llm_v4_nsyn20-noise_nsyn20 | 10 | macro_f1 | 5 | 0.0737 | 4/5 | 0.0281;0.2093;0.0536;-0.0916;0.1691 |

## Decision

CWRU v4 smoke is promising but still not a formal pass for full-scale CAS claims. With n_syn≈20, LLM v4 beats rule and noise on mean accuracy and macro-F1 in both n=5 and n=10 across 5 seeds, but the sample count is small and the rule pool has only 13 healthy accepted items at this synthetic budget. Before spending ~600 calls on a full CWRU pool, run a slightly broader local verification grid or generate a modest balanced pilot pool only if explicitly approved.

Quality diagnostics are in `breeze/results/phaseB_cwru_pool_quality_smoke_v4.md`.
