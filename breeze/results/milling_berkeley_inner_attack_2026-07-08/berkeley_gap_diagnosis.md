# Berkeley/NASA Milling Gap Diagnosis

Date: 2026-07-08 Asia/Shanghai

Scope: zero-API diagnosis on `proc/milling_berkeley_inner_train.npz` and `proc/milling_berkeley_inner_val.npz` only. No formal held-out Berkeley test results were used for selection or stopping.

## Inputs

- Classes: `sharp`, `worn`, `severe`.
- Inner-train counts: sharp=510, worn=578, severe=374.
- Inner-val counts: sharp=119, worn=153, severe=102.
- Current LLM candidates: `llm_v4_contrastive` and `llm_v5_proto`.
- Baselines inspected: `rule`, `noise_aug`, `random_open_loop`, `real_only`.
- Added diagnostic runs in this window:
  - `v4_contrastive_diagnostics/`
  - `v5_prototype_diagnostics/`
- API calls in this diagnosis: 0.

## Downstream Gap

Latest 5-seed inner-val summary at `n_syn=10/class`:

| method | n_real | Acc | Macro-F1 |
|---|---:|---:|---:|
| llm_v4_contrastive | 2 | 0.5401 | 0.4859 |
| llm_v5_proto | 2 | 0.5391 | 0.4849 |
| rule | 2 | 0.5422 | 0.4933 |
| noise_aug | 2 | 0.4925 | 0.4387 |
| llm_v4_contrastive | 5 | 0.5075 | 0.4661 |
| llm_v5_proto | 5 | 0.5043 | 0.4555 |
| rule | 5 | 0.5112 | 0.4703 |
| noise_aug | 5 | 0.4738 | 0.4501 |
| llm_v4_contrastive | 10 | 0.5546 | 0.5275 |
| llm_v5_proto | 10 | 0.5556 | 0.5280 |
| rule | 10 | 0.5594 | 0.5328 |
| noise_aug | 10 | 0.5642 | 0.5512 |

Interpretation: v4/v5 are now above random open-loop and generally above noise_aug for n=2/5, but they still trail rule at n=2/5 and trail both rule and noise_aug at n=10. This does not meet the preregistration threshold.

## Weak Class And Error Direction

The persistent weak class is `worn`. Mean per-class F1 at `n_syn=10/class`:

| method | n_real | F1 sharp | F1 worn | F1 severe |
|---|---:|---:|---:|---:|
| llm_v4_contrastive | 2 | 0.679 | 0.117 | 0.662 |
| rule | 2 | 0.668 | 0.138 | 0.673 |
| noise_aug | 2 | 0.497 | 0.184 | 0.635 |
| llm_v4_contrastive | 5 | 0.674 | 0.172 | 0.553 |
| rule | 5 | 0.668 | 0.175 | 0.568 |
| noise_aug | 5 | 0.628 | 0.302 | 0.420 |
| llm_v4_contrastive | 10 | 0.716 | 0.269 | 0.597 |
| rule | 10 | 0.714 | 0.271 | 0.613 |
| noise_aug | 10 | 0.741 | 0.381 | 0.532 |

Mean row-normalized confusion at n=10:

| method | true sharp -> sharp/worn/severe | true worn -> sharp/worn/severe | true severe -> sharp/worn/severe |
|---|---|---|---|
| llm_v4_contrastive | 0.899 / 0.074 / 0.027 | 0.441 / 0.201 / 0.358 | 0.059 / 0.259 / 0.682 |
| llm_v5_proto | 0.899 / 0.077 / 0.024 | 0.447 / 0.187 / 0.366 | 0.061 / 0.231 / 0.708 |
| rule | 0.903 / 0.081 / 0.017 | 0.450 / 0.201 / 0.349 | 0.061 / 0.243 / 0.696 |
| noise_aug | 0.817 / 0.160 / 0.024 | 0.288 / 0.353 / 0.359 | 0.020 / 0.394 / 0.586 |

The LLM and rule recipes have almost the same error geometry: `worn` is split between `sharp` and `severe`, and only about 20% of worn validation windows are predicted as worn at n=10. Noise augmentation performs worse on severe separation but preserves a stronger worn decision region, explaining why it wins Macro-F1 at n=10.

## PSD And Band-Energy Structure

Diagnostic sample size was 13/class for v4/v5 because v5 has only 13 accepted severe windows.

| candidate | mean PSD-W1 | mean band L1 | mean corr Frobenius delta | mean channel-energy L1 |
|---|---:|---:|---:|---:|
| llm_v4_contrastive | 5.9693 | 0.3827 | 0.5382 | 0.0217 |
| llm_v5_proto | 7.3243 | 0.4150 | 1.1875 | 0.0192 |
| rule | 5.2524 | 0.3592 | 0.2921 | 0.0109 |
| noise_aug | 4.9211 | 0.2287 | 0.2497 | 0.0142 |
| random_open_loop | 6.4474 | 0.3468 | 1.2520 | 0.3394 |

Main PSD mismatch frequencies/channels:

- v4: `worn/AE_spindle`, `worn/vib_spindle`, and `sharp/vib_spindle` dominate LLM PSD-W1 mismatch.
- v5: `worn/vib_spindle`, `worn/vib_table`, `severe/AE_spindle`, `severe/vib_table`, and `severe/AE_table` worsen relative to v4.
- rule is not perfect, but it keeps correlation and channel energy closer to inner-train than v4/v5.
- noise_aug best preserves PSD/band/correlation because it starts from real few-shot windows, but it injects unrealistic high-frequency energy in `smcDC` bands; this is visible in `ch1_band3/4/5_frac` robust z deltas.

Conclusion: v4 is the better LLM base than v5. v5 prototype selection is not a net improvement; it worsens PSD-W1 and channel correlation while producing nearly identical downstream behavior.

## Class-Ordering And Physical Features

Inner-train real ordering:

- Total RMS increases with wear: sharp=1.8646, worn=2.7797, severe=3.3177.
- AE TPF ratios increase with wear:
  - `AE_table`: sharp=0.0608, worn=0.0997, severe=0.1276.
  - `AE_spindle`: sharp=0.0555, worn=0.0838, severe=0.1072.
- Force/current/vibration TPF ratios are not all monotonic; several are U-shaped or decreasing. They should be treated as class-specific profiles, not blindly monotonic constraints.

v4 ordering failures:

- `smcDC` TPF ratio inverts relative to real: real sharp/worn/severe = 0.000883/0.000580/0.000703; v4 = 0.002160/0.002306/0.002406.
- `vib_spindle` TPF ratio also inverts: real = 0.03234/0.03318/0.02832; v4 = 0.02564/0.02280/0.02882.

v5 passes the coarse Spearman check but does so with worse PSD/correlation distances, so the pass is not sufficient for downstream gain.

## What Rule And Noise Preserve That LLM Lacks

- Rule preserves deterministic TPF/spindle structure and train-fold channel correlation closely enough that it remains slightly ahead at n=2/5.
- Noise augmentation preserves local real-window background and the worn decision region better than synthetic recipes, which matters most at n=10 Macro-F1.
- LLM v4/v5 add diversity, but the diversity does not create a stronger worn manifold; it largely reproduces the rule decision boundary.

## Actionable Requirements For The Next Iteration

1. Keep v4 as the base; do not expand v5 prototype as-is.
2. Implement train-only per-channel exemplar PSD selection plus per-band equalization for `vib_table`, `vib_spindle`, `AE_table`, and `AE_spindle`, with channel correlation preserved from coherent real exemplar blocks when possible.
3. Treat AE TPF ratios and total RMS as ordered wear features, but avoid imposing monotonic constraints on every channel TPF ratio.
4. Add a verifier/reporting gate for the worn class: the synthetic pool must keep worn intermediate in total RMS and AE TPF, while maintaining distinct PSD/correlation structure from both sharp and severe.
5. Re-evaluate on inner-val only with at least 10 seeds before any formal held-out test decision.

## Files

- `berkeley_v4_v5_contrastive_summary.csv`
- `v4_contrastive_diagnostics/berkeley_inner_diagnostics_report.md`
- `v5_prototype_diagnostics/berkeley_inner_diagnostics_report.md`
- `downstream_v4_contrastive_nsyn10/berkeley_llm_nsyn10.csv`
- `downstream_v5_prototype_contrastive_nsyn10/berkeley_llm_nsyn10.csv`
- `downstream_budget_nsyn10/`
