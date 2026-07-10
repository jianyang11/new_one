# BREEZE Figure and Skill Revision Snapshot

Timestamp: 2026-07-04 23:11 CST

## Scope

This snapshot records the figure/literature revision performed after the hard
instruction to use the Nature-style figure workflow, the Nuwa domain-pattern
extraction workflow, and the AI research-writing workflow. It does not claim
that the remaining dataset, LLM API, or strong-baseline requirements are
complete.

## Skills Used

- `nature-figure`: read and applied the figure contract, Python backend,
  design/QA references, and export requirements. The figures now use a shared
  style module, restrained palette, panel labels, consistent line widths, and
  PDF/SVG/PNG/TIFF outputs.
- `huashu-nuwa`: read and applied the extraction framework to distill common
  figure patterns from similar fault-diagnosis generation papers. It was used
  as a domain-pattern workflow, not as a fabricated expert persona.
- `awesome-ai-research-writing`: read and applied writing/logic prompts for
  claim checking, figure captions, and avoiding unsupported LLM-generation
  claims.

## Literature and Figure-Style Evidence

Detailed review: `analysis/literature_figure_style_review_2026-07-04.md`.

Current figure gap audit: `analysis/figure_gap_audit_2026-07-04.md`.

Verified or locally inspected sources include BearGen / AEI 2026 from the user
PDF and DOI `10.1016/j.aei.2026.104400`, MST 2025 physics-guided multimodal
GAN DOI `10.1088/1361-6501/ae1a04`, MSSP 2022 GAN DOI
`10.1016/j.ymssp.2021.108139`, MSSP 2025 diffusion DOI
`10.1016/j.ymssp.2025.113170`, and JVC 2026 physics-informed diffusion DOI
`10.1177/10775463261455715`. HAWAN-PIR 2025 remains unverified and is not used
as factual evidence.

## Code Changes

- Added shared figure style: `breeze/src/figure_style.py`.
- Redrew framework and responsibility-boundary figures:
  `breeze/src/fig_framework.py`.
- Redrew experiment figures and added a concrete failure-case figure:
  `breeze/src/figures.py`.
- Updated CAS synchronization for the downloaded Elsevier CAS template:
  `breeze/scripts/sync_cas_from_main.py`.
- Inserted new figures and cautious captions into:
  `breeze/paper/main.tex` and synchronized `breeze/paper/main_cas.tex`.

## Figure Outputs

Each figure is exported as PDF, SVG, PNG, and TIFF under `breeze/paper/figs/`.

- `framework`: closed-loop physical-gate admission.
- `responsibility_boundary`: LLM recipe / renderer / verifier boundary.
- `failure_reasons`: rejected-slot gate failures and slot-window accounting.
- `failure_case`: concrete rejected healthy candidate from
  `runs/rescreen_v2_full/records/healthy_0013.json`.
- `waveforms`: real vs gate-admitted time, FFT, and envelope spectra.
- `boxplots`: RMS and kurtosis distributions.
- `metric_distances`: MMD2 and nearest-neighbour diversity.
- `downstream_bars`: selected downstream baselines.
- `acceptance_k`: feedback-round acceptance, call cost, and downstream trend.
- `cross_condition_heatmap`: PU real-window verifier audit across conditions.

## Verification

- Ran `breeze/.venv-breeze/bin/python breeze/src/fig_framework.py`.
- Ran `breeze/.venv-breeze/bin/python breeze/src/figures.py --only failure_case`
  after adding the failure-case figure.
- Compiled `breeze/paper/main.tex` to `breeze/paper/main.pdf`:
  21 pages, no undefined references, natbib warnings, or overfull boxes in the
  final log check.
- Synchronized and compiled `breeze/paper/main_cas.tex` to
  `breeze/paper/main_cas.pdf`: 15 pages, no undefined references/citations or
  duplicate anchors. The only remaining warning is the CAS front-matter
  overfull caused by placeholder author metadata.
- Rendered and visually checked representative pages with `pdftoppm`,
  including the framework page, failure-breakdown/failure-case page,
  waveform/spectrum page, feature-distribution page, ablation page, and
  cross-condition page.

## Remaining Blockers

- No LLM API key or complete prompt/API log is available in the workspace, so
  the paper must not claim a newly rerun v2 closed-loop LLM experiment.
- Additional public datasets and full strong-baseline expansion remain pending;
  current cross-condition evidence is a verifier audit, not synthetic
  cross-condition augmentation.
- Author names, affiliations, ORCID metadata, funding, competing interests, and
  final MechaForge bibliographic metadata still require author input.
