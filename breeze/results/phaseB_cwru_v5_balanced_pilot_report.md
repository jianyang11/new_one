# Phase-B CWRU v5 Balanced Pilot Report

## API Usage

- Cumulative Phase-B API requests: 70.
- v5 pilot added 15 requests to supplement fault classes after v3/v4; total CWRU API use is 70.

## Pool Counts

- LLM combined v5 pilot: healthy=42, IR=50, B=41, OR=50.
- Rule pilot v1: healthy=38, IR=92, B=80, OR=99.
- Downstream synthetic budget: n_syn=38/class for LLM/rule/noise, total n_syn=152.

## 10-Seed Balanced Pilot Summary

| method | n_real | seeds | mean acc | mean macro-F1 |
|---|---:|---:|---:|---:|
| llm_v5_pilot_nsyn38 | 5 | 10 | 0.6337 | 0.6778 |
| rule_pilot_nsyn38 | 5 | 10 | 0.5726 | 0.6137 |
| noise_nsyn38 | 5 | 10 | 0.5134 | 0.5411 |
| llm_v5_pilot_nsyn38 | 10 | 10 | 0.6310 | 0.6779 |
| rule_pilot_nsyn38 | 10 | 10 | 0.5935 | 0.6404 |
| noise_nsyn38 | 10 | 10 | 0.5722 | 0.6120 |
| llm_v5_pilot_nsyn38 | 25 | 10 | 0.6833 | 0.7290 |
| rule_pilot_nsyn38 | 25 | 10 | 0.6425 | 0.6904 |
| noise_nsyn38 | 25 | 10 | 0.6775 | 0.7161 |

## Paired Wilcoxon Smoke Tests

| n_real | metric | comparison | seeds | mean delta | wins | p raw | Holm q |
|---:|---|---|---:|---:|---:|---:|---:|
| 5 | acc | llm_v5_pilot_nsyn38>rule_pilot_nsyn38 | 10 | 0.0611 | 10/10 | 0.0009766 | 0.001953 |
| 5 | acc | llm_v5_pilot_nsyn38>noise_nsyn38 | 10 | 0.1203 | 10/10 | 0.0009766 | 0.001953 |
| 5 | macro_f1 | llm_v5_pilot_nsyn38>rule_pilot_nsyn38 | 10 | 0.0641 | 9/10 | 0.001953 | 0.001953 |
| 5 | macro_f1 | llm_v5_pilot_nsyn38>noise_nsyn38 | 10 | 0.1367 | 10/10 | 0.0009766 | 0.001953 |
| 10 | acc | llm_v5_pilot_nsyn38>rule_pilot_nsyn38 | 10 | 0.0376 | 8/10 | 0.01172 | 0.01367 |
| 10 | acc | llm_v5_pilot_nsyn38>noise_nsyn38 | 10 | 0.0588 | 9/10 | 0.006836 | 0.01367 |
| 10 | macro_f1 | llm_v5_pilot_nsyn38>rule_pilot_nsyn38 | 10 | 0.0375 | 8/10 | 0.01367 | 0.01367 |
| 10 | macro_f1 | llm_v5_pilot_nsyn38>noise_nsyn38 | 10 | 0.0659 | 9/10 | 0.001953 | 0.003906 |
| 25 | acc | llm_v5_pilot_nsyn38>rule_pilot_nsyn38 | 10 | 0.0408 | 8/10 | 0.004883 | 0.009766 |
| 25 | acc | llm_v5_pilot_nsyn38>noise_nsyn38 | 10 | 0.0059 | 5/10 | 0.6045 | 0.6045 |
| 25 | macro_f1 | llm_v5_pilot_nsyn38>rule_pilot_nsyn38 | 10 | 0.0386 | 9/10 | 0.00293 | 0.005859 |
| 25 | macro_f1 | llm_v5_pilot_nsyn38>noise_nsyn38 | 10 | 0.0129 | 6/10 | 0.3477 | 0.3477 |

## Decision

- Balanced pilot gate: NO_GO.
- Do not scale CWRU; further prompt/verifier/renderer iteration is required.
