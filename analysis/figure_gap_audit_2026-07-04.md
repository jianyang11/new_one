# BREEZE Figure Gap Audit

Date: 2026-07-04

This audit translates the literature review into concrete figure changes. It follows the `nature-figure` contract: each figure must have a one-sentence claim, a defined evidence chain, source data, and export-quality vector outputs.

## Current Figure Inventory

| Existing figure | Source script | Current role | Main gap |
|---|---|---|---|
| `framework.pdf` | `breeze/src/fig_framework.py` | Method overview | Uses over-strong "Certified" wording and does not clearly separate LLM, renderer, verifier, and feedback responsibilities. |
| `waveforms.pdf` | `breeze/src/figures.py` | Real/synthetic waveform and envelope examples | Four-column layout is less aligned with the closest literature than a time/FFT/envelope grid; no FFT row; limited panel labels. |
| `boxplots.pdf` | `breeze/src/figures.py` | RMS/kurtosis distributions | Basic boxplot styling; lacks a companion distance/diversity plot. |
| `downstream_bars.pdf` | `breeze/src/figures.py` | Selected downstream accuracy baselines | Needs consistent palette and explicit visual cue that v2 is not uniformly best. |
| `acceptance_k.pdf` | `breeze/src/figures.py` | Acceptance/cost/K ablation | Needs style unification; failure reason breakdown is still separate only as a table. |

## Required Additions from the Hard Instruction

| Required figure | Status | Data source | Implementation decision |
|---|---|---|---|
| Overall framework | Existing, must redraw | Method description and code modules | Redraw in a BearGen-like phase layout, replacing "Certified" with "gate-admitted". |
| LLM recipe / renderer / verifier boundary | Missing | `llm.py`, `renderer.py`, verifier modules | Add `responsibility_boundary.pdf` as a mechanism figure. |
| Closed-loop feedback flow | Partly existing | `acceptance.csv`, method pipeline | Embed in red feedback path in `framework.pdf`; keep quantitative K ablation in `acceptance_k.pdf`. |
| Waveform + envelope spectrum | Existing, must redraw | train split, v2 pool, verifier bands | Redraw as time/FFT/envelope grid with real and admitted synthetic examples. |
| Physical metrics distribution | Existing and table-only | `pool_metrics.csv`, `pool_metrics_v2.csv`, train real windows | Keep `boxplots.pdf`; add `metric_distances.pdf` for MMD2 and NN diversity. |
| Cross-condition results | Table-only | `cross_condition_verifier_full.csv` | Add `cross_condition_heatmap.pdf`, labelled as a verifier audit. |
| Ablation | Existing | `acceptance.csv`, `downstream_file.csv` | Restyle `acceptance_k.pdf`; keep as K ablation. |
| Failure case | Partial | rejected records and fail-reason CSV | Add failure breakdown now. A concrete waveform failure case requires selecting and verifying a representative rejected candidate; mark as pending unless added later. |
| Acceptance/failure breakdown | Existing acceptance, missing visual failure breakdown | `acceptance.csv`, `revision_v2_rejected_slot_fail_reasons.csv` | Add `failure_reasons.pdf`. |

## Figure Style Specification

- Backend: Python only, using the specified `.venv-breeze` interpreter.
- Font: sans-serif stack with editable SVG text and TrueType PDF text.
- Export: PDF for LaTeX, SVG for editable source, PNG/TIFF for visual QA.
- Palette: one neutral family for baselines, deep blue for real/reference evidence, muted orange/rose for BREEZE/v2, red only for failed gates or reference fault peaks.
- Labels: small bold lowercase panel letters near top-left; no decorative frames.
- Captions: state what is shown, source data, and limitations; no claim that a verifier pass is a formal certificate.

## Claims That Cannot Be Drawn Yet

- "LLM is irreplaceable": missing random recipe + renderer, rule recipe + renderer, open-loop LLM, and LLM + verifier matched-budget experiments.
- "SOTA across baselines": local downstream results do not uniformly beat envelope-only, open-loop physics-guided, or noise augmentation across all shot settings.
- "Cross-dataset synthetic augmentation": no audited generated pool exists for additional public datasets or the private machine-tool dataset.
- "Physical correctness": gates support train-calibrated admissibility, not formal correctness.

## Immediate Edit Plan

1. Add shared Python figure style utilities.
2. Redraw `framework.pdf` and generate `responsibility_boundary.pdf`.
3. Redraw `waveforms.pdf` with time/FFT/envelope panels.
4. Restyle `boxplots.pdf`, `downstream_bars.pdf`, and `acceptance_k.pdf`.
5. Add `metric_distances.pdf`, `cross_condition_heatmap.pdf`, and `failure_reasons.pdf`.
6. Update `main.tex` captions and figure placements without strengthening claims.
7. Re-run figure scripts, render PDF pages to PNG, inspect key figures, then recompile `main.pdf` and sync/compile CAS.
