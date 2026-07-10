# AEI / Elsevier Submission Checklist

Checked against the ScienceDirect Advanced Engineering Informatics guide for
authors on 2026-07-04.

Source:
- https://www.sciencedirect.com/journal/advanced-engineering-informatics/publish/guide-for-authors

## Completed

- Manuscript source is editable LaTeX: `breeze/paper/main.tex`.
- Compiled PDF exists: `breeze/paper/main.pdf`.
- AEI/CAS source is prepared separately:
  `breeze/paper/main_cas.tex`.
- AEI/CAS PDF compiles with the downloaded template bundle:
  `breeze/paper/main_cas.pdf`.
- Stable `main.tex` LaTeX log check is clean: no undefined references, no
  natbib warnings, no overfull boxes.
- CAS log check has no undefined references/citations or duplicate anchor
  warnings; one `cas-sc` `\maketitle` overfull warning remains from front
  matter layout and should be rechecked after real author metadata are inserted.
- Highlights are in a separate editable file:
  `breeze/paper/highlights.txt`.
- Highlights count is 5 and each line is <= 85 characters.
- Figures are supplied as separate vector PDFs, SVGs, PNGs, and TIFFs under
  `breeze/paper/figs/`.
- Core figures have been redrawn with the `nature-figure`, `huashu-nuwa`, and
  `awesome-ai-research-writing` skill constraints and visually checked from
  rendered PDF pages.
- Tables are editable LaTeX tables in the manuscript, not images.
- Data Availability Statement is included before references.
- Generative AI declaration is included before references.
- Supplementary outline is prepared:
  `breeze/paper/supplementary_material.md`.
- Cover letter draft is prepared:
  `breeze/paper/cover_letter.md`.
- Reviewer-response draft is prepared:
  `reports/reviewer_response_draft_2026-07-04.md`.
- Revision snapshot and statistics reports are prepared:
  `reports/revision_snapshot_2026-07-04.md` and
  `reports/revision_statistics_2026-07-04.md`.
- Figure/literature revision snapshot is prepared:
  `reports/figure_revision_snapshot_2026-07-04.md`.
- Full v2-vs-main-baseline paired-test table with BH q-values is prepared:
  `breeze/results/revision_v2_significance_all_baselines_bh.csv`.
- PU cross-condition real-window verifier audit is prepared:
  `breeze/results/cross_condition_verifier_full.csv`.

## Template Status

- Stable draft source uses the older Elsevier article class:
  `\documentclass[review,3p,times]{elsarticle}`.
- The current AEI guide page points authors to Elsevier's LaTeX template
  download, which resolves to the newer CAS bundle (`cas-sc` / `cas-dc`) in the
  local downloaded folder `breeze/els-cas-templates`.
- The CAS submission source has been prepared as `main_cas.tex` using
  `cas-sc` single-column review style. The original `main.tex` is retained as
  the stable `elsarticle` working copy.
- Highlights are intentionally not embedded in `main_cas.tex`; Elsevier/AEI
  expects highlights as a separate submission file, already prepared as
  `highlights.txt`.

## Still Requires Author Input

- Replace `Author One`, `Author Two`, and placeholder affiliation with real
  author information.
- Replace the temporary empty-ORCID suppression in `main_cas.tex` with real
  ORCID metadata if the authors use ORCID IDs.
- Finalize MechaForge citation metadata: authors, venue, volume/pages/DOI if
  available.
- Provide missing LLM API-side metadata if available: exact model endpoint,
  model version, prompt text, temperature, top-p, seed behavior, and API call
  log. The revised manuscript no longer claims complete reproducibility for
  metadata not present in the workspace.
- Add funding statement and declaration of competing interests according to the
  authors' actual situation.
- Decide whether to submit a graphical abstract. AEI encourages one, but it is
  not mandatory in the current guide. If submitted, it should be a separate
  file at least 531 x 1328 px or proportionally larger and readable at 5 x
  13 cm.
- Confirm whether the private machine-tool dataset can be shared or only
  described through aggregate metrics.
- Confirm whether private machine-tool prefixes `1/2/3` may be named as
  normal machining / lead-screw anomaly / base imbalance. Until then, the
  revised manuscript keeps anonymous `MT-1/MT-2/MT-3` labels.
- Run institutional plagiarism/similarity checking outside this workspace.

## Revision Boundary

- The revised manuscript treats BREEZE certificates as auditable
  gate-compliance records, not formal guarantees.
- The figure revision treats BREEZE as a physical-gate admission framework:
  framework, responsibility-boundary, failure-reason, failure-case, waveform,
  feature-distribution, downstream, ablation, and cross-condition figures all
  avoid claiming formal physical correctness.
- The v2 experiment is explicitly an offline rescreening of the frozen 450
  original generated slots. No new v2 closed-loop LLM-call cost is claimed.
- The private machine-tool data support only a schema-level verifier audit and
  real-only baseline in the current manuscript; no machine-tool synthetic
  augmentation result is claimed.
