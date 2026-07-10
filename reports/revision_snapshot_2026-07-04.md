# BREEZE Revision Snapshot

Date: 2026-07-04

Scope: revision of the BREEZE manuscript in response to the supplied review
comments.

## Active Inputs

- Manuscript sources:
  - `breeze/paper/main.tex`
  - `breeze/paper/main_cas.tex`
- Current PDFs:
  - `breeze/paper/main.pdf`
  - `breeze/paper/main_cas.pdf`
- Result tables:
  - `breeze/results/downstream_file.csv`
  - `breeze/results/custom_pool_eval.csv`
  - `breeze/results/significance_v2_vs_main.csv`
  - `breeze/results/pool_metrics.csv`
  - `breeze/results/pool_metrics_v2.csv`
  - `breeze/results/calibration_sensitivity.csv`
- v2 evidence:
  - `reports/breeze_v2_rescreen_report_2026-07-04.md`
  - `breeze/runs/rescreen_v2_full/summary.json`
  - `breeze/runs/rescreen_v2_full/slot_summary.csv`
  - `breeze/runs/rescreen_v2_full/accepted_manifest.csv`
  - `breeze/runs/rescreen_v2_full/records/*.json`
- Private machine-tool evidence:
  - `reports/machine_tool_experiment_2026-07-04.md`
  - `reports/machine_tool_synthetic_protocol.md`
  - `breeze/results/mt_verifier_real_pass.csv`
  - `breeze/results/mt_real_only_eval.csv`

## Initial Diagnosis

The review is largely aligned with the current evidence. The paper has a
defensible engineering idea but overstates several claims:

- Gate admission currently means compliance with deterministic,
  train-calibrated gates, not formal proof of physical validity.
- v2 is an offline rescreening of the existing 450 generated slots. It is not a
  new v2 closed-loop LLM generation experiment.
- v2 improves real-only and the original BREEZE K=3 pool in selected settings,
  but it is not uniformly stronger than envelope-only, open-loop
  physics-guided, or noise augmentation.
- The private machine-tool experiment supports schema-level verifier
  re-instantiation only; it does not yet demonstrate synthetic-data
  augmentation on that dataset.

## Revision Log

### 2026-07-04 17:56

- Added a new active "审稿意见大修任务" section to `todos.md`.
- Created `analysis/reviewer_response_matrix.md`.
- Created this revision snapshot.

### 2026-07-04 18:05

- Added `breeze/scripts/revision_stats.py`.
- Generated:
  - `breeze/results/revision_v2_slot_window_mapping.csv`
  - `breeze/results/revision_v2_candidate_fail_reasons.csv`
  - `breeze/results/revision_v2_rejected_slot_fail_reasons.csv`
  - `breeze/results/revision_v2_significance_bh.csv`
  - `breeze/results/revision_v2_significance_all_baselines_bh.csv`
  - `reports/revision_statistics_2026-07-04.md`
- Confirmed v2 is offline rescreening of 450 existing slots:
  286 accepted slots, 761 accepted items before diversity, 757 kept windows
  after diversity, and 192+200+200=592 windows after the few-shot cap.
- Confirmed BH correction over all 42 v2-vs-main-baseline paired tests:
  v2 remains significant vs real-only for 10/25/50 real windows per class, but
  it is not uniformly significant vs strong baselines.

### 2026-07-04 18:25

- Added `breeze/scripts/cross_condition_verifier.py`.
- Ran smoke test with 20 windows/class/split under all four PU conditions.
- Ran full real-window verifier audit under all four PU conditions.
- Generated:
  - `breeze/results/cross_condition_verifier_smoke.csv`
  - `breeze/results/cross_condition_verifier_full.csv`
  - `breeze/runs/cross_condition_verifier/cross_condition_verifier_full_report.md`
- Interpretation: this is a train-calibrated verifier coverage audit only, not
  a cross-condition LLM generation or augmentation experiment.

### 2026-07-04 18:43

- Rewrote `breeze/paper/main.tex` in response to the review:
  - changed title and abstract from certified-admission framing to
    physical-gate admission;
  - rewrote the problem formulation as mixed gate predicates;
  - expanded related work;
  - clarified v2 offline rescreening and no new v2 LLM cost;
  - added v2 failure-reason table;
  - added MMD2 protocol details;
  - added PU cross-condition verifier audit table;
  - downgraded private machine-tool data to schema-level audit;
  - strengthened limitations and circular-validation discussion.
- Updated MechaForge citation authors using local PDF metadata, without
  inventing DOI/volume/pages.
- Revised Figure 4 to horizontal bars and Figure 3 to short labels.
- Added `breeze/scripts/sync_cas_from_main.py` and regenerated
  `breeze/paper/main_cas.tex` from `main.tex`.
- Compiled:
  - `breeze/paper/main.pdf`: 17 pages, log grep clean for warnings,
    undefined references/citations, and overfull boxes.
  - `breeze/paper/main_cas.pdf`: 12 pages, no undefined references/citations;
    only the known CAS front-matter `\maketitle` overfull warning remains with
    placeholder author metadata.
- Created `reports/reviewer_response_draft_2026-07-04.md`.

### 2026-07-04 18:46

- Updated `todos.md` to mark the review-driven revision tasks as completed to
  the current data boundary.
- Updated `analysis/reviewer_response_matrix.md` so each review concern maps
  to a completed manuscript/statistics action or an explicit author-input
  requirement.
- Updated `analysis/main_tables.md` to use the same 42-test
  Benjamini-Hochberg correction as the revised manuscript.
- Updated `breeze/paper/submission_checklist.md` with the reviewer-response
  draft, revision statistics, v2 all-baseline q-value table, cross-condition
  verifier audit, and remaining author inputs.

## Completed Computations

- v2 failure-reason distribution from `slot_summary.csv` and JSON records.
- BH-adjusted q-values for v2 vs all main baselines across 42 paired tests.
- MMD2 protocol summary from `breeze/src/metrics.py`.
- Figure 3 and Figure 4 rendering inspection after layout revision.
- PU four-condition real-window verifier audit.

## Author Inputs Still Required

- Real author names, affiliations, corresponding author email, ORCID metadata.
- Exact final MechaForge citation metadata.
- Confirmation of private machine-tool prefix mapping if physical labels should
  replace MT-1/MT-2/MT-3.
- LLM API/model/prompt metadata that is not present in the current workspace.
