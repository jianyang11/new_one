# BREEZE Writing-Only Revision Log

Status: in progress (2026-07-15, Asia/Shanghai)

## Scope and controls

- Target: `breeze/paper/main_cas.tex`.
- Writing standard: `awesome-ai-research-writing` skill, especially its
  polishing, logic-check, experiment-analysis, reviewer-view, and
  humanization guidance.
- PDF validation standard: `pdf` skill, including compile, Poppler rendering,
  and page-by-page visual inspection.
- Numerical source of truth: `breeze/paper/generated/*.tex` (read-only for this
  revision).
- Claim boundary: `analysis/evidence_ledger.md` (read-only; wording may be
  reorganized but neither broadened nor narrowed).
- Figures, tables, equations, citations, protocols, numerical values, and
  generated macros remain unchanged. No API call is permitted or required.
- Frozen start point: local `main` = `origin/main` = `1f06c842379111e23f42b92e39af5e2a7a864aaa`.
- Frozen SHA-256: evidence ledger
  `637752db3cad59a727ce84a4de6dcf3095cc152c9f8108ef7fcf82b85be3767d`;
  source manuscript
  `cd10ba9e98a3c1a8c0b3a64073ab98161a370c4aa66de593fd6a7e5d2c583f09`.

## Baseline acceptance measures

- Abstract length: 235 words under the repository word-count script.
- Negative-qualifier sentences: 67. Counting scope is manuscript prose from
  the abstract through the conclusion, excluding figures, tables, algorithms,
  equations, keyword blocks, and comments. A sentence is counted when it
  contains `not`, `no`, `cannot`, `does not`, `do not`, `is not`, `are not`,
  `rather than`, `neither`, or `nor` as a word or phrase.
- PDF length: 17 pages.
- Compile baseline: zero fatal errors and zero undefined-reference/citation
  warnings. Existing box diagnostics are one overfull box at the title/front
  matter boundary and 23 underfull boxes in the fixed positioning and dataset
  tables. The writing-only revision must introduce no additional diagnostic.
- Acceptance targets: abstract at most 220 words; at most two negative
  limitations in the abstract; at most 33 negative-qualifier sentences under
  the same counting scope; final PDF at most 18 pages; no new compile warning,
  undefined reference, citation failure, overlap, clipping, or illegible page.

## P1--P6 diagnosis before editing

| Problem | Representative locations in the baseline | Planned correction |
|---|---|---|
| P1: defence precedes the claim | Abstract 45--48 and 62--65; Introduction 89--95 and 97--104; Results 530--535, 565--567, 571--586, and 642--646; Discussion 761--773; Conclusion 820--824 | State the contribution or result first. Move one necessary boundary to the paragraph's final sentence or consolidate it in Sections 6--7. Remove repeated `not/does not/rather than` formulations. |
| P2: missing claim topic sentences | Introduction 78--87 and 89--95; Related work 157--168; Method 236--251, 272--276, 301--317, and 339--359; Results 521--526, 550--561, 571--579, 590--596, and 650--659 | Make each prose paragraph's first sentence its local claim. Place evidence and numbers in the middle, then use the final sentence as a transition or scope statement. |
| P3: new-to-old information order | Method 236--249 and 253--268; Setup 479--500; Results 550--561, 631--638, and 673--680 | Begin sentences with the current component, dataset, or comparison, and place the new metric, decision, or numerical result at the end. Keep subjects adjacent to their verbs. |
| P4: one paragraph handles several jobs | Method 386--402 combines unit definitions, renderer multiplicity, cost interpretation, provider metadata, and reproducibility; Setup 434--444 combines all three datasets; Results 650--659 combines accounting, rates, the random control, and interpretation | Split slot/window accounting from generation provenance; split dataset-specific details; separate accounting evidence from recipe-source interpretation. Add the reason the slot/window distinction matters. |
| P5: missing motivation before mechanism | Subsection openings at 234, 270, 299, 337, 361, 407, 446, 477, and 502 | Start each Method/Experimental Design subsection by naming the unresolved problem that motivates the component or protocol before presenting definitions, equations, gates, or hyperparameters. |
| P6: noun-phrase Results headings | Results headings at 519, 548, 569, 588, and 648; boundary heading at 695 | Rewrite Results headings as evidence-bounded conclusions. Keep Method headings nominal. Replace the PU/CWRU contrast heading with a positive CWRU conclusion followed by the PU boundary. |

## Required before/after diff examples

These examples define the intended logic transformation. Final wording may be
line-edited, but its evidence boundary must remain identical.

### P1: lead with the contribution

```diff
- The verifier rejects rather than repairs a failed waveform, and its pass
- decision is an auditable train-calibrated admissibility statement rather
- than a formal guarantee of physical validity.
+ The resulting pass decision is an auditable, train-calibrated admissibility
+ statement. Rejected candidates remain unchanged, and the statement provides
+ no formal guarantee of physical validity.
```

### P2: make the first sentence the paragraph claim

```diff
- Table~\ref{tab:pu-phasea} answers the primary source-ablation question.
- LLM recipes exceed rule and random open-loop recipes at every shot count ...
+ LLM recipes exceed rule and random open-loop recipes at every registered PU
+ shot count for both diagnostic metrics. Table~\ref{tab:pu-phasea} reports ...
```

### P3: put given information before new information

```diff
- Across that split and the three provenance-valid transfer folds,
- \BreezeCWRUPassedTests/\BreezeCWRURegisteredTests{} registered tests ...
+ The within-load0 split and three provenance-valid transfer folds yield
+ \BreezeCWRUPassedTests/\BreezeCWRURegisteredTests{} positive Holm-corrected
+ LLM--comparator decisions.
```

### P4: give each paragraph one job

```diff
- A slot is ... Slot counts measure ... The CWRU archive records ...
+ A slot is ... This distinction matters because slot counts measure proposal
+ cost, whereas window counts measure the classifier's augmentation budget.
+
+ The generation archive records the model controls needed for replay ...
```

### P5: explain why before what

```diff
- The verifier evaluates the following active evidence:
+ Recipe legality alone cannot protect the pool from train-unsupported signal
+ evidence, so the verifier evaluates six complementary gate families:
```

### P6: turn labels into bounded conclusions

```diff
- \subsection{Berkeley milling: a qualified result}
+ \subsection{LLM recipes beat non-structured Berkeley controls and converge
+ with rule recipes at ten shots}
```

## Section-by-section execution record

| Stage | Source lines at baseline | Edit status | Compile status | Claim/numerical audit |
|---|---:|---|---|---|
| Abstract | 39--66 | complete: six sentences, 190 words, zero negative-qualifier sentences | pass: 17 pages, zero errors/undefined references, no new box diagnostics | all original result macros and protocol boundaries retained |
| Introduction | 75--150 | complete: required eight-part argument chain and verb-led contributions | pass: 17 pages, zero errors/undefined references, no new box diagnostics | seed counts, datasets, questions, and final scope match the ledger |
| Related work | 152--229 | complete: claim-led synthesis and explicit BREEZE contrast at every subsection close | pass: 17 pages, zero errors/undefined references, no new box diagnostics | citations and positioning table unchanged |
| Method | 231--402 | complete: motivation-first subsections, equation-purpose prose, separated accounting/provenance | pass: 17 pages, zero errors/undefined references, no new box diagnostics | equations, renderer parameters, prompts, provider fields, and component boundaries preserved |
| Experimental design | 404--514 | complete: motivated controls and dataset-specific split paragraphs | pass after one prose line-break correction: 17 pages, one baseline overfull and 23 baseline table underfull boxes | all splits, counts, budgets, seeds, hyperparameters, tests, and excluded-baseline boundaries preserved |
| Results | 516--690 | complete: conclusion headings, claim-first paragraphs, Berkeley registered order | pass: 17 pages, one baseline overfull and 23 baseline table underfull boxes | all generated tables/macros untouched; Berkeley rule-vs-unstructured significance remains unclaimed |
| Boundaries and negative results | 692--754 | complete: one applicability frame, localized PU chain, distinct milling stops | pass: 17 pages, one baseline overfull and 23 baseline table underfull boxes | v1/v2 formal versus v3--v6 development distinction and both milling stop reasons preserved |
| Discussion | 756--810 | complete: three questions answered first, 0-slot random control leads | pass: 18 pages, one baseline overfull and 23 baseline table underfull boxes | positive/qualified/failed protocol pattern and remaining blockers match the ledger |
| Conclusion and final prose | 812--849 | complete: positive synthesis plus one scope sentence; availability paragraph made claim-first | pass: 17 pages, one baseline overfull and 23 baseline table underfull boxes | PU/CWRU/Berkeley pattern, PU LOCO boundary, formal-guarantee boundary, and release contents preserved |

## Final paragraph-first-sentence audit

Scope: 81 paragraph-like prose units from the abstract through the declarations,
including contribution/control/gate list items and excluding captions, tables,
figures, equations, and Algorithm 1. Read in sequence, the openings reconstruct
the problem, mechanism, protocol, evidence, boundary, and conclusion.

### Abstract

- L40: Scarce labelled faults make it costly to train and select a signal generator for every machine and operating regime.

### Introduction

- L72: Industrial fault diagnosis faces a structural data imbalance.
- L78: Existing augmentation routes trade modelling capacity for target-data cost.
- L86: LLM-authored recipes create an inference-time alternative to target-specific generator training.
- L92: The recipe interface also creates a reliability gap between valid syntax and supported signal evidence.
- L98: BREEZE closes this gap through train-calibrated admission.
- L117: Three evaluation questions organize the evidence.
- L126: The paper makes four contributions.
- L128: Separate LLM time-series generation into a recipe--renderer--verifier system.
- L131: Integrate mixed physical gates into a bounded rejection/resampling loop.
- L135: Establish the contribution of LLM recipes under matched few-shot protocols on three public datasets.
- L139: Report negative evidence as part of the method boundary.
- L144: The evidence supports a deliberately bounded admission claim.

### Related Work

- L155: Trainable models dominate general time-series generation.
- L169: Physics-informed generation embeds equations, mechanisms, or physical penalties in a trainable model.
- L176: Generated-data filtering provides a complementary control mechanism.
- L184: LLMs provide emerging interfaces to time-series and machinery knowledge.
- L215: Established diagnostic observables expose complementary aspects of rolling-element faults.

### Method

- L229: Reliable admission requires a decision rule calibrated entirely within the outer training split.
- L250: Admission must represent interval support, one-sided evidence, healthy suppression, and diversity in one decision.
- L271: Attributing an observed gain requires explicit boundaries between proposal, waveform construction, admission, and diagnosis.
- L290: The structured recipe exposes every LLM-controlled degree of freedom.
- L303: A fixed renderer is needed to compare recipe sources under identical waveform construction.
- L323: When two phase currents are available, the equation makes carrier, fault modulation, harmonics, and channel noise explicit.
- L335: Berkeley requires a dataset-specific milling renderer under the same component responsibility principle.
- L344: Reliable pool construction requires evidence beyond recipe legality.
- L347: Legality covers shape, finite samples, non-degenerate channels, and repeated runs.
- L349: Robust statistics use class- and channel-conditional training domains.
- L352: Spectral shape uses Welch-PSD fractions and PSD-CDF Wasserstein-1 distance.
- L354: Envelope evidence measures class-relevant prominence, harmonics, and healthy suppression.
- L357: Current evidence becomes active when training data establish class separability.
- L360: Diversity uses a lower nearest-neighbour bound in the physical feature embedding.
- L363: PU training data leave the MCSA score audit-only.
- L368: Closed-loop admission must bound proposal cost while preserving every decision needed for audit and replay.
- L395: A slot is one requested recipe unit, whereas a window is the tensor supplied to the classifier.
- L404: Generation provenance determines which stages can be replayed exactly.

### Experimental Design

- L419: Leakage-resistant evaluation requires splitting acquisition units before sampling windows.
- L444: The PU protocol isolates measurement files within each bearing.
- L449: The CWRU protocol tests both within-load diagnosis and source-load transfer.
- L456: The Berkeley protocol isolates machining case/run groups before windowing.
- L463: Testing the LLM contribution requires changing the proposal source while holding every downstream factor fixed.
- L467: LLM plus verifier uses a class- and condition-aware recipe, admission, and bounded feedback.
- L469: Rule plus verifier uses an engineer-written template with the same renderer and verifier.
- L472: Random open-loop renders random legal recipe values without feedback.
- L475: Noise augmentation applies channel-scaled jitter and amplitude scaling to real few-shot windows.
- L477: Real only uses the paired few-shot subset without synthetic data.
- L479: The completed formal families match these controls to each dataset.
- L484: The available baseline archive fixes the quantitative comparison boundary.
- L495: Matched downstream evaluation requires a fixed classifier and paired sources of randomness.
- L505: The dataset-specific budgets define the registered comparison cells.
- L513: Registered inference preserves the pairing used in training.
- L524: Physical and distribution diagnostics complement downstream accuracy against each outer-training reference.

### Results

- L541: LLM recipes outperform rule and random open-loop recipes at every registered PU shot count for both diagnostic metrics.
- L549: Seed-level deltas confirm a positive PU LLM advantage across every registered source comparison.
- L570: Load0-derived LLM recipes outperform every registered comparator within load0 and on provenance-valid held-out loads 1--3.
- L583: This result establishes source-load0 cross-load diagnostic utility for the tested held-out loads 1--3.
- L591: LLM recipes beat the non-structured Berkeley controls in all registered comparisons.
- L603: The Berkeley pattern localizes the additional LLM contribution to lower-shot settings.
- L613: PU diagnostics show that admitted LLM pools combine class-relevant waveform evidence with non-duplicate nearest-neighbour distances.
- L654: Class-averaged PU distances favour LLM recipes over the matched recipe sources on PSD, band energy, and RMS.
- L666: External downstream tests and matched controls provide evidence beyond shared physical features.
- L675: Closed-loop accounting separates proposal cost from the downstream augmentation budget.
- L683: Recipe source determines whether the verifier can construct a balanced pool.
- L700: Terminal failures reveal class- and source-specific rejection mechanisms.

### Boundaries

- L722: These failures define the method's applicability and prevent unsupported extrapolation.
- L728: CWRU source-load0 recipes transfer to tested loads 1--3, whereas PU LOCO remains unsuccessful.
- L748: The six-stage PU audit localizes this boundary from kinematics through source-only evidence.
- L771: The core milling evidence is limited to datasets with complete, auditable protocol metadata.
- L777: UMich and MU-TCM define two distinct protocol stops.

### Discussion

- L792: The source ablations answer the first evaluation question by establishing an LLM recipe contribution within the matched BREEZE pipeline.
- L799: The class-conditional diagnostics answer the second question with complementary train-supported physical evidence.
- L805: The downstream protocols answer the third question by locating both stable utility and its transfer boundary.
- L811: Together, these answers position BREEZE as a train-calibrated control layer around a structured black-box proposal source.
- L818: Train-calibrated gates provide auditable physical evidence within a finite set of observables.
- L827: Matched source controls partially address the circularity created by shared renderer and verifier kinematics.
- L836: The repository supports replay from archived recipes through reported statistics.
- L843: Two provenance and baseline blockers remain.

### Closing Prose

- L856: BREEZE separates LLM recipe proposal, fixed seeded rendering, train-calibrated physical admission, and downstream diagnosis.
- L867: The release package connects each reported result to public data and frozen evidence.
- L880: The authors declare that they have no known competing financial interests or personal relationships that could have influenced the work.
- L886: The authors used OpenAI Codex for code inspection, experiment orchestration, figure/table assembly, and language editing.

## Final verification

- Abstract: pass at six sentences, 166 words, zero counted negative-limit
  sentences, and all original result macros retained.
- Negative-qualifier sentences: 67 before, 8 after; reduction is 88.1%, above
  the required 50%.
- Long sentences: seven prose sentences exceed 30 words; none is consecutive
  with another long sentence. The abstract has one 49-word result sentence
  between sentences of 18 and 28 words.
- Terminology: the process term is `admission`; `verifier` names the component;
  `screening` and process-level `verification` are absent. `physics-verified`
  remains the declared bounded adjective.
- Numbers and macros: no baseline numerical value or `\Breeze...` macro was
  removed or altered. The existing verbal zero-slot result is written as
  `0 admitted slots` in Discussion, as required. The unadjusted `0.05` boundary
  remains explicit.
- Citations: the multiset of citation IDs is unchanged.
- Structure: all ten figure environments, two table environments, Algorithm 1,
  three `align` environments, and two `equation` environments are byte-identical
  to the baseline source. Generated tables and figure files have zero diff.
- Claim audit: every use of `significant`, `transfer`, `training-free`,
  `milling`, and `physical` was rechecked against `analysis/evidence_ledger.md`.
  Berkeley rule-versus-unstructured significance and trained-generator
  superiority remain outside the claims.
- Compile: `latexmk` completes with zero fatal errors, zero LaTeX warnings, and
  zero undefined citations/references. The log retains only the baseline one
  title/front-matter overfull box and 23 underfull boxes in fixed tables.
- Length: 17 pages before and after.
- PDF QA: Poppler rendered all 17 pages at 120 dpi. Page-by-page inspection
  found no clipping, overlap, missing glyph, blank figure, unreadable label, or
  float-order regression relative to the baseline CAS PDF.
- Protected files: the evidence-ledger SHA-256 remains
  `637752db3cad59a727ce84a4de6dcf3095cc152c9f8108ef7fcf82b85be3767d`;
  all five generated-table hashes and all figure hashes match the frozen
  baseline. `git diff` is empty for the ledger, generated tables, figures, and
  bibliography.
- Pending only: staged-diff review, commit, push, and remote-SHA verification.
