# S4 v1 sanity failure — stop before pool construction

## Scope

This is the first target checkpoint of the preregistered S4 audit:
`N09_M07_F10` is the morphology target, and only the train-bearing windows of
`N15_M01_F10`, `N15_M07_F04`, and `N15_M07_F10` were loaded. No pseudo-held-out
or registered formal held-out waveform was read. API requests: 0.

The complete aggregate certificate is `s4_target_N09_M07_F10.json`.

## Predeclared stop criteria and observed result

| criterion | required | observed | status |
|---|---:|---:|---|
| pooled raw healthy admission | >= 0.600 | 87/300 = 0.290 | fail |
| per-source raw healthy admission | >= 0.400 each | 0.310, 0.240, 0.320 | fail |
| wrong-label/white-noise/constant admission | 0/800 | 221/800 | fail |

The unhealthy v1 behavior is bidirectional rather than a shortage of
admission: `real_OR_labeled_IR` admitted 76/100, `real_IR_labeled_OR` admitted
62/100, and `white_noise_labeled_OR` admitted 83/100. Constant controls and
healthy-labeled white noise were rejected, so this is not a reporting error.

## Diagnosis

The v1 implementation did not faithfully operationalize two strict statements
of `s4_design.md`:

1. Healthy fault absence was calibrated at each source condition's BPFO/BPFI
   but evaluated at the target BPFO/BPFI. This mixes frequency references and
   turned source-background peaks into false target-fault evidence; it caused
   371 healthy/noise rejection messages.
2. A fault envelope check searched for the largest peak *inside* the asserted
   local frequency window. Any waveform has such a local maximum, so a low
   source q01 amplitude floor did not establish that the asserted BPFO/BPFI is
   more plausible than the competing fault rate. This explains the wrong-label
   and OR-white-noise admissions.

No S1/S2/S5 pool is built from this regime. The v1 target result remains in the
repository as an audit artifact and is not used for candidate selection.

## Permitted next action

Before recalibration, `s4_design_amendment_1.md` freezes a stricter source-only
correction: target-frequency healthy calibration and fault-rate exclusivity.
It does not access a target waveform, lower an acceptance requirement, repair
a rejected waveform, or alter historical in-domain v2 results.
