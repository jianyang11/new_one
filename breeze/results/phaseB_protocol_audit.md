# Phase-B Protocol Audit

Date: 2026-07-05

This audit is a read-only preflight check before Phase-B generation or downstream training. It verifies local processed splits, class counts, operating-condition coverage, and simple train/test leakage keys.

## Dataset Decision

- Main Phase-B candidates: PU, CWRU, DIRG.
- XJTU-SY remains skipped per user instruction.
- IMS is retained as a run-to-failure audit dataset unless a transparent fault-onset labelling protocol is defined.
- HIT and JUST are not counted toward the main physical-generation claim at this point.

## Split Summary

| dataset | split | train_n | test_n | leakage_status | split_semantics | train_counts | test_counts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PU | N09_M07_F10_file_split | 3846 | 962 | PASS | file_chronological_within_each_bearing | `{"IR":1444,"OR":1202,"healthy":1200}` | `{"IR":361,"OR":301,"healthy":300}` |
| PU | N15_M01_F10_file_split | 3853 | 961 | PASS | file_chronological_within_each_bearing | `{"IR":1446,"OR":1204,"healthy":1203}` | `{"IR":361,"OR":300,"healthy":300}` |
| PU | N15_M07_F04_file_split | 3850 | 960 | PASS | file_chronological_within_each_bearing | `{"IR":1447,"OR":1201,"healthy":1202}` | `{"IR":360,"OR":300,"healthy":300}` |
| PU | N15_M07_F10_file_split | 3841 | 964 | PASS | file_chronological_within_each_bearing | `{"IR":1441,"OR":1200,"healthy":1200}` | `{"IR":362,"OR":301,"healthy":301}` |
| CWRU | lolo_load0 | 3365 | 1002 | PASS | file_or_condition_disjoint | `{"B":708,"IR":709,"OR":1239,"healthy":709}` | `{"B":235,"IR":235,"OR":413,"healthy":119}` |
| CWRU | lolo_load1 | 3246 | 1121 | PASS | file_or_condition_disjoint | `{"B":707,"IR":708,"OR":1239,"healthy":592}` | `{"B":236,"IR":236,"OR":413,"healthy":236}` |
| CWRU | lolo_load2 | 3246 | 1121 | PASS | file_or_condition_disjoint | `{"B":707,"IR":708,"OR":1239,"healthy":592}` | `{"B":236,"IR":236,"OR":413,"healthy":236}` |
| CWRU | lolo_load3 | 3244 | 1123 | PASS | file_or_condition_disjoint | `{"B":707,"IR":707,"OR":1239,"healthy":591}` | `{"B":236,"IR":237,"OR":413,"healthy":237}` |
| CWRU | train_load0_test_load1 | 1002 | 1121 | PASS | file_or_condition_disjoint | `{"B":235,"IR":235,"OR":413,"healthy":119}` | `{"B":236,"IR":236,"OR":413,"healthy":236}` |
| CWRU | train_load0_test_load2 | 1002 | 1121 | PASS | file_or_condition_disjoint | `{"B":235,"IR":235,"OR":413,"healthy":119}` | `{"B":236,"IR":236,"OR":413,"healthy":236}` |
| CWRU | train_load0_test_load3 | 1002 | 1123 | PASS | file_or_condition_disjoint | `{"B":235,"IR":235,"OR":413,"healthy":119}` | `{"B":236,"IR":237,"OR":413,"healthy":237}` |
| CWRU | within_load0 | 696 | 306 | PASS | chronological_within_file | `{"B":163,"IR":163,"OR":287,"healthy":83}` | `{"B":72,"IR":72,"OR":126,"healthy":36}` |
| CWRU | within_load1 | 780 | 341 | PASS | chronological_within_file | `{"B":164,"IR":164,"OR":287,"healthy":165}` | `{"B":72,"IR":72,"OR":126,"healthy":71}` |
| CWRU | within_load2 | 780 | 341 | PASS | chronological_within_file | `{"B":164,"IR":164,"OR":287,"healthy":165}` | `{"B":72,"IR":72,"OR":126,"healthy":71}` |
| CWRU | within_load3 | 781 | 342 | PASS | chronological_within_file | `{"B":164,"IR":165,"OR":287,"healthy":165}` | `{"B":72,"IR":72,"OR":126,"healthy":72}` |
| DIRG | loco_speed300_load1400 | 14000 | 875 | PASS | leave_one_speed_load_condition_out | `{"IR150":2000,"IR250":2000,"IR450":2000,"healthy":2000,"roller150":2000,"roller250":2000,"roller450":2000}` | `{"IR150":125,"IR250":125,"IR450":125,"healthy":125,"roller150":125,"roller250":125,"roller450":125}` |

## Phase-B Budget Note

No new LLM API calls are required for this audit. Any CWRU/DIRG LLM recipe generation must be separately budgeted before execution because it would require new dataset-specific prompts and verifier boundaries.
