# PU LOCO v1 Frequency-Mismatch Diagnostic

## Scope
- Purpose: test whether v1 synthetic recipes were rendered at training-condition kinematics instead of held-out deployment-condition kinematics.
- Inputs: synthetic recipe JSON files and known operating-condition metadata only.
- Held-out vibration/current windows and labels are not read.
- Fault frequencies are computed from PU 6203 geometry and condition rpm.

## Result
- Audited accepted OR/IR recipe records: 266.
- Records by source: llm=50, random_open_loop=120, rule=96.
- Records with absolute fault-rate error >10% relative to held-out target: 125/266.
- Error relative to the render condition is near zero for rule/conditionized LLM recipes; error relative to the held-out condition is large whenever the render condition rpm differs from the held-out rpm.

## Summary By Source / Fold / Render Condition / Class
| source | heldout | render_condition | class | n_records | mean_error_vs_heldout_pct | mean_abs_error_vs_heldout_pct | mean_abs_error_vs_render_condition_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| llm | N09_M07_F10 | N15_M01_F10 | IR | 2 | 66.67 | 66.67 | 0.00 |
| llm | N09_M07_F10 | N15_M01_F10 | OR | 2 | 66.67 | 66.67 | 0.00 |
| llm | N09_M07_F10 | N15_M07_F04 | IR | 1 | 66.67 | 66.67 | 0.00 |
| llm | N09_M07_F10 | N15_M07_F04 | OR | 2 | 66.67 | 66.67 | 0.00 |
| llm | N09_M07_F10 | N15_M07_F10 | IR | 2 | 66.67 | 66.67 | 0.00 |
| llm | N09_M07_F10 | N15_M07_F10 | OR | 2 | 66.67 | 66.67 | 0.00 |
| llm | N15_M01_F10 | N09_M07_F10 | IR | 2 | -40.00 | 40.00 | 0.00 |
| llm | N15_M01_F10 | N09_M07_F10 | OR | 3 | -40.00 | 40.00 | 0.00 |
| llm | N15_M01_F10 | N15_M07_F04 | IR | 2 | 0.00 | 0.00 | 0.00 |
| llm | N15_M01_F10 | N15_M07_F04 | OR | 2 | 0.00 | 0.00 | 0.00 |
| llm | N15_M01_F10 | N15_M07_F10 | IR | 2 | 0.00 | 0.00 | 0.00 |
| llm | N15_M01_F10 | N15_M07_F10 | OR | 4 | 0.00 | 0.00 | 0.00 |
| llm | N15_M07_F04 | N09_M07_F10 | IR | 2 | -40.00 | 40.00 | 0.00 |
| llm | N15_M07_F04 | N09_M07_F10 | OR | 2 | -40.00 | 40.00 | 0.00 |
| llm | N15_M07_F04 | N15_M01_F10 | IR | 1 | 0.00 | 0.00 | 0.00 |
| llm | N15_M07_F04 | N15_M01_F10 | OR | 1 | 0.00 | 0.00 | 0.00 |
| llm | N15_M07_F04 | N15_M07_F10 | IR | 2 | 0.00 | 0.00 | 0.00 |
| llm | N15_M07_F04 | N15_M07_F10 | OR | 2 | 0.00 | 0.00 | 0.00 |
| llm | N15_M07_F10 | N09_M07_F10 | IR | 4 | -40.00 | 40.00 | 0.00 |
| llm | N15_M07_F10 | N09_M07_F10 | OR | 3 | -40.00 | 40.00 | 0.00 |
| llm | N15_M07_F10 | N15_M01_F10 | IR | 2 | 0.00 | 0.00 | 0.00 |
| llm | N15_M07_F10 | N15_M01_F10 | OR | 1 | 0.00 | 0.00 | 0.00 |
| llm | N15_M07_F10 | N15_M07_F04 | IR | 1 | 0.00 | 0.00 | 0.00 |
| llm | N15_M07_F10 | N15_M07_F04 | OR | 3 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N09_M07_F10 | N15_M01_F10 | IR | 5 | 66.67 | 66.67 | 0.00 |
| random_open_loop | N09_M07_F10 | N15_M01_F10 | OR | 5 | 66.67 | 66.67 | 0.00 |
| random_open_loop | N09_M07_F10 | N15_M07_F04 | IR | 5 | 66.67 | 66.67 | 0.00 |
| random_open_loop | N09_M07_F10 | N15_M07_F04 | OR | 5 | 66.67 | 66.67 | 0.00 |
| random_open_loop | N09_M07_F10 | N15_M07_F10 | IR | 5 | 66.67 | 66.67 | 0.00 |
| random_open_loop | N09_M07_F10 | N15_M07_F10 | OR | 5 | 66.67 | 66.67 | 0.00 |
| random_open_loop | N15_M01_F10 | N09_M07_F10 | IR | 5 | -40.00 | 40.00 | 0.00 |
| random_open_loop | N15_M01_F10 | N09_M07_F10 | OR | 5 | -40.00 | 40.00 | 0.00 |
| random_open_loop | N15_M01_F10 | N15_M07_F04 | IR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M01_F10 | N15_M07_F04 | OR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M01_F10 | N15_M07_F10 | IR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M01_F10 | N15_M07_F10 | OR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M07_F04 | N09_M07_F10 | IR | 5 | -40.00 | 40.00 | 0.00 |
| random_open_loop | N15_M07_F04 | N09_M07_F10 | OR | 5 | -40.00 | 40.00 | 0.00 |
| random_open_loop | N15_M07_F04 | N15_M01_F10 | IR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M07_F04 | N15_M01_F10 | OR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M07_F04 | N15_M07_F10 | IR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M07_F04 | N15_M07_F10 | OR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M07_F10 | N09_M07_F10 | IR | 5 | -40.00 | 40.00 | 0.00 |
| random_open_loop | N15_M07_F10 | N09_M07_F10 | OR | 5 | -40.00 | 40.00 | 0.00 |
| random_open_loop | N15_M07_F10 | N15_M01_F10 | IR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M07_F10 | N15_M01_F10 | OR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M07_F10 | N15_M07_F04 | IR | 5 | 0.00 | 0.00 | 0.00 |
| random_open_loop | N15_M07_F10 | N15_M07_F04 | OR | 5 | 0.00 | 0.00 | 0.00 |
| rule | N09_M07_F10 | N15_M01_F10 | OR | 5 | 66.67 | 66.67 | 0.00 |
| rule | N09_M07_F10 | N15_M07_F04 | IR | 5 | 66.67 | 66.67 | 0.00 |
| rule | N09_M07_F10 | N15_M07_F04 | OR | 5 | 66.67 | 66.67 | 0.00 |
| rule | N09_M07_F10 | N15_M07_F10 | IR | 4 | 66.67 | 66.67 | 0.00 |
| rule | N09_M07_F10 | N15_M07_F10 | OR | 2 | 66.67 | 66.67 | 0.00 |
| rule | N15_M01_F10 | N09_M07_F10 | IR | 1 | -40.00 | 40.00 | 0.00 |
| rule | N15_M01_F10 | N09_M07_F10 | OR | 1 | -40.00 | 40.00 | 0.00 |
| rule | N15_M01_F10 | N15_M07_F04 | IR | 5 | 0.00 | 0.00 | 0.00 |
| rule | N15_M01_F10 | N15_M07_F04 | OR | 4 | 0.00 | 0.00 | 0.00 |
| rule | N15_M01_F10 | N15_M07_F10 | IR | 2 | 0.00 | 0.00 | 0.00 |
| rule | N15_M01_F10 | N15_M07_F10 | OR | 5 | 0.00 | 0.00 | 0.00 |
| rule | N15_M07_F04 | N09_M07_F10 | IR | 1 | -40.00 | 40.00 | 0.00 |
| rule | N15_M07_F04 | N09_M07_F10 | OR | 7 | -40.00 | 40.00 | 0.00 |
| rule | N15_M07_F04 | N15_M01_F10 | OR | 5 | 0.00 | 0.00 | 0.00 |
| rule | N15_M07_F04 | N15_M07_F10 | IR | 5 | 0.00 | 0.00 | 0.00 |
| rule | N15_M07_F04 | N15_M07_F10 | OR | 9 | 0.00 | 0.00 | 0.00 |
| rule | N15_M07_F10 | N09_M07_F10 | OR | 7 | -40.00 | 40.00 | 0.00 |
| rule | N15_M07_F10 | N15_M01_F10 | OR | 6 | 0.00 | 0.00 | 0.00 |
| rule | N15_M07_F10 | N15_M07_F04 | IR | 10 | 0.00 | 0.00 | 0.00 |
| rule | N15_M07_F10 | N15_M07_F04 | OR | 7 | 0.00 | 0.00 | 0.00 |

## Interpretation
- v1 is physically mismatched for cross-speed LOCO: recipes rendered at 1500 rpm are about +66.7% high when deployed against N09 900 rpm, while recipes rendered at 900 rpm are about -40.0% low when deployed against N15 1500 rpm.
- This supports the v2 protocol change: use held-out condition metadata to set `fr_hz`, BPFO/BPFI impact rate, and current fault frequency while still using zero held-out signal or label data.
