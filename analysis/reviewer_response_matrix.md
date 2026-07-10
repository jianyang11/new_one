# BREEZE Reviewer Response Matrix

Date: 2026-07-04

Purpose: map the review comments to auditable manuscript edits, local evidence,
and remaining author inputs. This file is part of the revision snapshot and
must be updated whenever the paper or experiments are changed.

## Revision Principles

- Do not inflate claims beyond the available evidence.
- Treat BREEZE as train-calibrated rule-based admission/rejection, not formal
  proof of physical validity.
- Keep v2 clearly labelled as offline rescreening unless a complete new
  closed-loop LLM generation run is performed.
- Report strong baselines honestly, including cases where envelope-only,
  open-loop physics-guided, or noise augmentation are stronger.
- Prefer simple claim correction and traceable statistics over extra
  complexity.

## Comment Mapping

| ID | Reviewer concern | Required action | Evidence/source | Status |
| --- | --- | --- | --- | --- |
| C1 | "certified" is too strong and not a formal guarantee. | Replace guarantee-like wording with "verified/admitted under train-calibrated gates"; add explicit limitation that certificates are rule-compliance records. | `breeze/paper/main.tex`; `breeze/paper/main_cas.tex`; verifier JSON/records. | Completed |
| C2 | Eq. 1 cannot express mixed constraints. | Rewrite formulation as a mixed gate family covering intervals, upper/lower bounds, healthy fault-peak suppression, reliability-gated MCSA, and diversity distance. | `breeze/paper/main.tex`; `breeze/src/verifier/verifier.py`; `breeze/src/verifier/v2.py`. | Completed |
| C3 | v2 is offline rescreening, not full v2 closed-loop generation. | State this in abstract, setup, results, table captions, and limitations; avoid reporting new v2 LLM cost. | `reports/breeze_v2_rescreen_report_2026-07-04.md`; `breeze/paper/main.tex`. | Completed |
| C4 | v2 lacks failure-reason distribution. | Recompute from `slot_summary.csv` and records; write result to a revision statistics report. | `reports/revision_statistics_2026-07-04.md`; `breeze/results/revision_v2_rejected_slot_fail_reasons.csv`. | Completed |
| C5 | v2 does not stably beat envelope-only/open-loop physics/noise. | Add full paired tests with BH-adjusted q-values and soften claims. | `breeze/results/revision_v2_significance_all_baselines_bh.csv`; `breeze/paper/main.tex`. | Completed |
| C6 | Slot/window relation is unclear. | Define slot, recipe, rendered window, accepted item/window, diversity-kept window; explain 286 slots -> 761 accepted items -> 757 kept windows. | `reports/revision_statistics_2026-07-04.md`; `breeze/results/revision_v2_slot_window_mapping.csv`. | Completed |
| C7 | 592 v2 training samples need explanation. | State cap rule: max 200 synthetic windows/class, giving 192+200+200 = 592. | `reports/revision_statistics_2026-07-04.md`; `breeze/paper/main.tex`; `eval_custom_pool.py`. | Completed |
| C8 | MCSA claim does not match active constraints. | Clarify MCSA is reliability-gated; in PU it may be certificate evidence rather than hard admission. | `breeze/paper/main.tex`; `breeze/src/verifier/v2.py`; v2 report. | Completed |
| C9 | Private machine-tool dataset cannot support full portability claim. | Downgrade to schema-level portability/smoke-test and generic train-calibrated constraints; no augmentation claim. | `reports/machine_tool_experiment_2026-07-04.md`; `breeze/paper/main.tex`. | Completed |
| C10 | Related work is insufficient. | Add verified references for time-series GANs, TimeGAN, RCGAN/C-RNN-GAN, time-series diffusion, conditional fault augmentation, physics-informed generation, LLM/time-series synthesis, and rejection/verifier-guided generation. | Bibliography and related-work section in `breeze/paper/main.tex`. | Completed |
| C11 | MMD2 definition is underspecified. | Add feature set, normalization, kernel, bandwidth, and interpretation boundary. | `reports/revision_statistics_2026-07-04.md`; `breeze/src/metrics.py`; `results/pool_metrics*.csv`. | Completed |
| C12 | Baselines may be weak or unfair. | Describe current baseline budgets and cap; avoid claiming fair superiority to all physics-informed generative models. | `breeze/results/downstream_file.csv`; `breeze/paper/main.tex`; `analysis/main_tables.md`. | Completed |
| C13 | Multiple tests and 8 seeds require caution. | Add BH correction and replace "significant" with exact p/q wording where needed. | `breeze/results/revision_v2_significance_all_baselines_bh.csv`; `breeze/paper/main.tex`. | Completed |
| C14 | Figure 4 labels are crowded. | Revise figure layout and visually verify rendered PDF/PNG. | `breeze/src/figures.py`; `breeze/paper/figs/waveforms.pdf`; `breeze/paper/figs/downstream_bars.pdf`; rendered PNG checks under `/private/tmp/breeze_main_failure_pages-*`. | Completed |
| C15 | Author placeholders and MechaForge citation are incomplete. | Keep placeholders as author-input items; do not invent metadata. | `breeze/paper/submission_checklist.md`; author input. | Partially completed: MechaForge authors updated from local PDF metadata; final author metadata still required. |
| C16 | Core figures should match field conventions and show failure evidence, not only aggregate results. | Added literature figure-style review; redrew framework, boundary, waveform/spectrum, distribution, ablation, cross-condition, failure-breakdown, and concrete failure-case figures. | `analysis/literature_figure_style_review_2026-07-04.md`; `analysis/figure_gap_audit_2026-07-04.md`; `reports/figure_revision_snapshot_2026-07-04.md`; `breeze/paper/figs/*.pdf`. | Completed to current-data boundary |

## Questions for Authors

| Q | Planned answer |
| --- | --- |
| 1 | Provide all locally known LLM/rendering settings and clearly mark missing API/model/prompt metadata if not present in the workspace. |
| 2 | Answer that v2 is offline rescreening of the existing 450 slots; no new v2 closed-loop LLM cost is claimed. |
| 3 | Explain slot/recipe/window mapping using local run manifests. |
| 4 | Confirm 592 = 192 healthy + 200 OR + 200 IR after the 200/class cap. |
| 5 | Added v2 vs all 14 main baselines across 3 few-shot settings, with BH-adjusted q-values over the 42-test family. |
| 6 | Disclose that v2 design was motivated by v1 diagnostics and existing results; add limitation about needing independent cross-condition validation. |
| 7 | Specify MMD2 implementation and why it is not the sole selection metric. |
| 8 | Downgrade private-data portability to schema-level verifier smoke test. |
| 9 | List certificate, failure report, threshold, and pass/fail paths available in the workspace. |
| 10 | Use exact p-values plus BH correction; avoid broad significance claims from eight seeds. |
