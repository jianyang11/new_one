# PU LOCO v2 Preregistration: Condition-Aware Generation

## Motivation From v1

PU LOCO v1 failed the uniform superiority gate. The follow-up diagnostic `pu_loco_v1_frequency_mismatch_report.md` shows a systematic kinematic mismatch: many accepted OR/IR synthetic recipes were rendered at training-condition BPFO/BPFI instead of the held-out deployment-condition BPFO/BPFI. Cross-speed recipes have fixed fault-rate errors of +66.7% when 1500 rpm recipes are used for N09 900 rpm, and -40.0% when N09 900 rpm recipes are used for N15 1500 rpm.

## Legal Information Boundary

Allowed:

- Held-out condition metadata: rpm, torque, radial load.
- PU 6203 bearing geometry from the existing configuration.
- Training-condition real windows and labels for prompt exemplars, non-frequency morphology profiles, and verifier calibration.
- Previously accepted LLM recipes as morphology templates.

Forbidden:

- Held-out vibration/current windows.
- Held-out labels or per-window statistics.
- Held-out downstream results for selecting prompts, budgets, verifier thresholds, or stopping rules.

## v2 Generation Rule

For each held-out condition and class:

1. Reuse accepted v1 LLM recipe morphology when possible.
2. Replace condition-dependent kinematic fields using the held-out condition rpm:
   - `fr_hz`
   - `impacts.rate_hz` for OR/IR
   - `currents.fault_freq_hz` for OR/IR
3. Keep non-frequency morphology parameters unchanged unless an inner-training-fold validation experiment is explicitly run and selected before held-out evaluation.
4. Render multiple seeds per recipe and apply the same diversity filter.

This is a zero-API first strategy. New LLM calls are allowed only if reused recipes cannot reach the pre-registered class-balanced pool target under the v2 verifier.

## v2 Verifier Rule

The verifier may not be calibrated on held-out windows. The v2 verifier is a training-fold extrapolation:

- Train-supported statistical, spectrum-shape, PSD-W1, and diversity boundaries are calibrated from training-condition real windows only.
- Kinematic/envelope targets are computed from held-out rpm and PU bearing geometry.
- The report must state that verifier boundaries are an extrapolation from training conditions to known deployment metadata, not a held-out-data calibration.

## Pool Target

- Primary downstream synthetic budget: `n_syn=20` per class.
- Each v2 LLM fold pool must contain at least 20 kept windows per class before downstream evaluation.
- If a fold cannot reach the target with reused accepted recipes and zero API calls, stop and report the bottleneck before spending API.

## Downstream Evaluation

- New output root only: `breeze/results/pu_loco_v2_2026-07-08/`.
- Do not overwrite `breeze/results/pu_loco_2026-07-07/` or its frozen copy.
- Protocol: 4 LOCO folds, methods `real_only`, `noise_aug`, `random_open_loop`, `rule`, `llm`, n_real={5,10,25}, 40 seeds, CNN epochs=20.
- Statistical family: each `(heldout condition, n_real, metric)` is one Holm family.
- Registered superiority comparisons: `llm>rule`, `llm>random_open_loop`, `llm>noise_aug`; `llm>real_only` is reported as context.

## Pass/Fail Interpretation

Pass:

- v2 LLM significantly outperforms rule and random_open_loop in few-shot settings n={5,10} for both Accuracy and Macro-F1 after Holm correction.
- Against noise_aug, v2 LLM must be at least non-inferior by positive mean delta or no significant negative gap; superiority is reported only where Holm-significant.

Fail:

- If v2 still underperforms noise_aug/rule broadly, PU LOCO remains a limitation and the paper claim is restricted to within-condition/few-shot settings plus CWRU LOLO evidence.
