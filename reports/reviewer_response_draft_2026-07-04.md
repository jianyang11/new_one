# Reviewer Response Draft

Date: 2026-07-04

This draft summarizes the manuscript changes made in response to the supplied
review. Line numbers are not fixed because the LaTeX source may still change
after author metadata are inserted.

## General Response

We revised the manuscript to reduce over-strong claims and to present BREEZE as
a train-calibrated physical-gate admission framework rather than a formal
certification method. The title, abstract, problem formulation, method
description, result interpretation, discussion, and conclusion now state that
an admitted sample has passed deterministic train-calibrated gates, but this is
not a proof of physical correctness, distribution coverage, or downstream
generalization.

We also clarified that v2 is an offline rescreening of the frozen original
K=3 generated slots, not a new v2 closed-loop LLM generation experiment. No new
v2 LLM-call cost is claimed. Additional analyses were added for slot/window
mapping, v2 failure reasons, full paired tests with Benjamini-Hochberg
correction, MMD2 implementation details, and a PU cross-condition real-window
verifier audit.

## Main Changes

- Changed title from "Certified Admission" to "Physical-Gate Admission".
- Rewrote the abstract to state v2 is offline rescreening of the same 450
  slots and to report 286 accepted slots, 761 accepted items before diversity,
  757 kept windows, and 42-test BH correction.
- Rewrote Eq. 1 as a mixed gate family covering interval, upper-bound,
  lower-bound, healthy fault-peak suppression, and diversity-distance rules.
- Added explicit wording that "certificate" means an auditable
  gate-compliance record, not formal proof.
- Expanded related work to include C-RNN-GAN, RCGAN, TimeGAN, TimeGrad, CSDI,
  physics-informed learning, LLM time-series forecasting, and inference-time
  verifier loops.
- Added v2 terminal rejected-slot failure distribution.
- Added the 192+200+200=592 synthetic-window cap explanation.
- Added full v2-vs-all-main-baselines paired Wilcoxon tests with BH correction
  across 42 tests.
- Added MMD2 feature/kernel/bandwidth details.
- Added a PU four-condition real-window verifier audit, explicitly framed as
  verifier coverage rather than synthetic augmentation.
- Downgraded the private machine-tool experiment to schema-level verifier
  audit only.
- Revised Figure 4 as horizontal bars and shortened Figure 3 labels.
- Updated MechaForge citation authors from the local PDF metadata; final DOI
  or volume/pages still require author confirmation.

## Questions for Authors

1. LLM generator details and reproducibility.

Response draft: The current workspace records the generator as a black-box LLM
recipe generator and deterministic renderer, with local source files and run
records retained. The revision no longer claims complete reproducibility for
unknown API-side state. We list the local code, prompts/gate reports, and run
outputs that can be shared subject to institutional constraints. Any missing
model-version/API seed metadata will be disclosed as a limitation unless the
authors provide it.

2. Is v2 a new closed-loop generation or offline screening?

Response draft: v2 is offline rescreening of the frozen original K=3 generated
slots. The manuscript now states this in the abstract, setup, results, and
discussion. No new v2 LLM-call cost is claimed.

3. How do 286 slots become 757 windows?

Response draft: A slot is one requested LLM generation unit. A feasible slot
can contribute the selected round window and feasible expansion windows from
the same slot recipe. In v2, 286/450 slots passed, producing 761 accepted items
before diversity and 757 kept windows after diversity.

4. Why does v2 use 592 synthetic samples?

Response draft: The downstream protocol caps synthetic additions at 200
windows/class. The v2 pool contains 192 healthy, 304 OR, and 261 IR windows,
so the actual capped budget is 192+200+200=592.

5. Why not report v2 vs strong baselines?

Response draft: The revision adds a full paired-test CSV for all 14 main
baselines across three few-shot settings, with Benjamini-Hochberg correction
across all 42 tests. The main table reports representative strong comparisons
and the full CSV is listed in reproducibility notes.

6. Was v2 adjusted after seeing results?

Response draft: v2 was motivated by diagnostics of v1 failure modes and is
reported as an offline redesign/rescreening. The manuscript now avoids treating
v2 as independent confirmation and adds a limitation that full cross-condition
generation and independent validation are still needed.

7. What is MMD2?

Response draft: The manuscript now defines the feature vector, standardization,
RBF kernel, and median bandwidth heuristic used by `metrics.py::pool_metrics`.
It also states that MMD2 is not the sole selection metric and that open-loop
physics-guided/envelope-only remain competitive on this metric.

8. What does the private dataset support?

Response draft: The private dataset is now framed as a schema-level verifier
audit, not as portability of augmentation. No synthetic pool or augmentation
gain is claimed for that dataset.

9. Are certificates and failure reports available?

Response draft: The reproducibility notes now list gate thresholds, v2
manifests, slot summaries, failure-reason CSVs, and pass/fail records. Sharing
will follow institutional and private-data constraints.

10. How are multiple tests handled?

Response draft: The revision reports exact p-values and BH-adjusted q-values.
The strongest defensible claim is that v2 improves real-only under all three
few-shot settings after correction. It is not claimed to be uniformly superior
to all augmentation baselines.

## Remaining Author Inputs

- Replace `Author One`, `Author Two`, and placeholder affiliation.
- Confirm final MechaForge publication metadata, especially DOI/volume/pages.
- Provide any missing LLM API model/version/prompt/temperature/seed metadata if
  available.
- Confirm whether private machine-tool labels can replace MT-1/MT-2/MT-3.
