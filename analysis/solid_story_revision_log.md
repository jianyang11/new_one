# BREEZE Solid-Story Narrative Revision Log

Status: complete (2026-07-16, Asia/Shanghai)

## Scope and immutable evidence

- Target: `breeze/paper/main_cas.tex` and verified bibliography metadata in
  `breeze/paper/references.bib`.
- Writing standard: local `awesome-ai-research-writing` skill, with emphasis on
  claim-first logic, literature synthesis, evidence-calibrated comparison, and
  removal of generic gap language.
- PDF standard: local `pdf` skill, using a clean LaTeX/BibTeX build, Poppler
  rendering, and page-by-page visual inspection.
- Figure standard: `nature-figure` is applied as an immutability and visual-QA
  constraint. The task prohibits figure changes, so no plotting backend is
  selected and no figure is redrawn.
- Claim boundary: `analysis/evidence_ledger.md` and
  `analysis/claim_evidence_map.md`. Literature supports the motivation; it does
  not turn the unavailable matched TimeGAN/DDPM experiment into evidence.
- Numerical source: `breeze/paper/generated/*.tex`, which is read-only in this
  revision. No experiment or LLM API call is permitted.
- Synchronized start: local `main` = `origin/main` =
  `bfb6f8facfcc7ad79b864caed6eefc5f5016cf26`.
- Python interpreter: `breeze/.venv-breeze/bin/python`, Python 3.12.13.

## Frozen baseline

| Artifact | SHA-256 |
|---|---|
| `breeze/paper/main_cas.tex` | `85e8515a50b539fd34679fb876a223baefc7ec14899fa7fa10b4a02bda5d7c23` |
| `breeze/paper/references.bib` | `a8cbec9c0328f0898dfaf3a8dba49363952311fbb3407dfc0865b33a6b33bd7d` |
| `analysis/evidence_ledger.md` | `637752db3cad59a727ce84a4de6dcf3095cc152c9f8108ef7fcf82b85be3767d` |
| `analysis/claim_evidence_map.md` | `68433aa58f2a93331e0426c99ae515936ee78962db15a10dab79f7a77cecd8a5` |
| `generated/berkeley.tex` | `da45c87c0981957317fba89fca9427f70c092c86c9c4dc5a2f5bdc6b752c1671` |
| `generated/cwru.tex` | `fac914f7d9484d3372acda93335dfc17c5df0d8d90ece0d5e82cfe483f604073` |
| `generated/numbers.tex` | `f3842d75114b11ad7391f9ee0cec988b24da9299551335d0986987248e126bb8` |
| `generated/physics.tex` | `d76af78447ae6accf994d1fac695372e528370ce239c26c7683f18fc98236621` |
| `generated/pu_phasea.tex` | `60646a9ee482e5e7f343ab4d86664e389468a4f6d13a273fd151ec03ed730311` |

The source contains 10 figure environments, 2 inline table environments, 5
equation/align environments, 1 algorithm, and 5 generated-file inputs. The
revision may alter the prose and the explicitly requested positioning-table
column only. All ten figure PDFs are hash-frozen separately in the final audit.

The clean baseline compiles to 17 pages with no fatal error or undefined
reference/citation. It has 9 pre-existing BibTeX warnings for proceedings
records without canonical page ranges, 1 title/front-matter overfull box, and
23 underfull boxes in fixed-width tables. No page number will be invented to
suppress a bibliography-style warning; the final build may not add a warning
or layout diagnostic.

## Causal story contract

The revision uses one argument from Abstract through Conclusion:

1. **S1, operating problem:** few labelled fault windows make target-specific
   generator training and selection difficult.
2. **S2, root cause:** trained generators place signal knowledge in weights
   learned from data, while the stated few-shot operating point supplies too
   little target evidence for reliable distribution learning and model
   selection.
3. **S3, components:** BREEZE supplies explicit recipe knowledge without
   target-generator optimization, renders it with fixed equations, and moves
   physical control from a training objective to train-calibrated admission
   with bounded feedback and per-sample audit records.
4. **S4, matched tests:** random and rule recipe controls probe the proposal
   component; open-loop and verifier accounting probe admission; downstream
   tests probe the complete admitted pool.
5. **S5, boundary:** positive PU/CWRU and qualified Berkeley evidence coexists
   with the six-stage PU LOCO failure chain. Explicit recipes address target
   distribution learning; they do not identify an unknown
   morphology--condition map.

The root-cause sentence is a literature-grounded design thesis, not an
experimental claim that BREEZE already outperforms matched trained generators.
The latter comparison remains a blocker until a formal frozen study enters the
evidence ledger.

## Primary-source literature verification

| Prompt study | Verified primary record | Mechanism and failure used in the narrative | Knowledge residence | Decision |
|---|---|---|---|---|
| DFE-GAN | Liu et al., *Mechanical Systems and Signal Processing* 163, 108139, DOI `10.1016/j.ymssp.2021.108139` | Adversarial instability/mode collapse motivates a pull-away loss, self-attention, and an automatic filter | Learned weights and objective | Cite; existing BibTeX verified |
| TSDM | Yi et al., *Mechanical Systems and Signal Processing* 216, 111481, DOI `10.1016/j.ymssp.2024.111481` | The original DDPM fails to generate high-quality vibration signals; an attention/ResBlock U-Net adapts denoising to one-dimensional frequency structure | Learned denoiser weights and architecture | Add verified BibTeX and cite |
| ReF-DDPM | Yu et al., *Reliability Engineering & System Safety* 251, 110343, DOI `10.1016/j.ress.2024.110343` | GAN augmentation struggles to balance quality and diversity; reparameterized residual denoising strengthens intra/inter-level features | Learned denoiser weights | Add verified BibTeX and cite |
| TII DDPM augmentation | Yang et al., *IEEE Transactions on Industrial Informatics* 20(5), 7820--7831, DOI `10.1109/TII.2024.3366991` | DDPM replaces unstable adversarial training but remains a trained data-augmentation model evaluated for quality, diversity, and diagnosis | Learned denoiser weights | Add verified BibTeX and cite |
| FaultDiffusion | Xu et al., arXiv:2511.15174 | Few-shot time-series models fail to learn fault distributions because of normal--fault domain gap and high intra-class diversity; a normal-pretrained model is adapted with a difference adapter and diversity loss | Pretrained and adapted weights plus loss | Add verified preprint record and cite with preprint status |
| ACS-DM | Tong et al., *Journal of Vibration and Control*, DOI `10.1177/10775463251414180` | Few-shot synthesis must balance frequency fidelity and temporal diversity; nested U-Net, dynamic convolution, attention, and conditional sampling are trained with DDPM loss | Learned denoiser weights and sampling architecture | Add verified online-first record and cite |
| MR-DDIM | Xu et al., *Sensors* 26(10), 3091, DOI `10.3390/s26103091` | Few-shot high-speed-train signals motivate WT-UNet, conditional modulation, log-sigma regularization, and multi-resolution STFT consistency | Learned weights and physics-related objective | Add verified BibTeX and cite |
| Physics-constrained multimodal GAN | Gao et al., *Measurement Science and Technology* 36(11), 116109, DOI `10.1088/1361-6501/ae1a04` | Bearing impact response and speed modulation enter the differentiable training constraints of a multimodal GAN | Learned weights plus physical loss | Cite; existing BibTeX verified |

All eight records have stable primary publisher or arXiv identifiers. Their
reported methods may establish literature motivation and the
knowledge-residence spectrum. Cross-paper accuracy values will not be compared
with BREEZE because split units, tasks, budgets, and test protocols differ.

## Planned section trace

| Section | Required role in the same story | Evidence guard |
|---|---|---|
| Abstract | S1 -> root cause -> explicit recipe/fixed renderer -> calibrated closed loop -> frozen results -> PU LOCO boundary -> significance | Preserve all current macros and registered scopes |
| Introduction | Name concrete trained-generator failures, state the shared root cause, map three components and three questions to it | Present the root cause as a design thesis; no trained-baseline win |
| Related Work | Organize methods by where signal/physical knowledge resides | At least six verified prompt studies; no protocol-incompatible ranking |
| Method | Explain how each component moves knowledge/control outside target-generator training | Equations, algorithm, parameters, and responsibilities unchanged |
| Results | Treat recipe-source and admission controls as component tests, then report complete-pool utility | Preserve PU/CWRU/Berkeley qualifications and all numbers |
| Boundaries | Explain PU LOCO as an unknown morphology--condition map outside the explicit recipe | Keep v1/v2 formal versus v3--v6 stop distinction |
| Discussion | Answer the three questions and give an operating guide | Trained-generator choice is conditional guidance, not measured superiority |
| Conclusion | Positive mechanism/evidence synthesis plus one boundary sentence | No zero-data, SOTA, formal-validity, or universal-superiority claim |

## Incremental and final verification

### Stage A: Abstract through Method

- Abstract: 189 words; the rendered prose contains the required root-cause
  sentence and all original PU/CWRU/Berkeley result macros.
- Literature coverage: all eight prompt studies #1--8 are cited. Six new
  records have primary DOI or arXiv metadata; DFE-GAN and the physics-constrained
  multimodal GAN reuse verified existing entries.
- Positioning table: the requested knowledge-residence column is present. Its
  left-aligned fixed-width cells produce no overfull or underfull diagnostic.
- Compile: 18 pages, zero fatal error, zero undefined citation/reference, the
  one baseline front-matter overfull box, and 14 dataset-table underfull boxes.
  The revision therefore has fewer layout diagnostics than the 23-underfull
  baseline.
- Structure: all equation, algorithm, figure, label, and generated-input
  identities remain unchanged at this stage.

### Stage B: Results through Conclusion

- Results now follow the component tests in order: recipe-source ablation,
  complete-pool utility, physical/admission evidence, and closed-loop pool
  formation. PU, CWRU, and Berkeley wording remains within the frozen ledger.
- The boundary section opens with the missing morphology--condition map and
  preserves the full PU v1--v6 sequence, including the distinction between the
  v1/v2 formal tests and the v3--v6 development/admission stops.
- Discussion answers the three evaluation questions in order, then gives an
  evidence-bounded operating guide: BREEZE fits few-shot, auditable deployments
  without target-generator optimization; a trained generator is reasonable
  when a representative corpus and compute support fitting and model selection.
- Conclusion states the mechanism and supported public-protocol evidence in two
  positive paragraphs, followed by one boundary sentence.

## Narrative trace audit

Reading the following section openings in sequence reconstructs the same
causal argument without relying on section labels:

| Stage | Opening sentence or claim | Role |
|---|---|---|
| Abstract / S1 | Scarce labelled faults make target-specific generator training and selection compete with the same few examples needed for diagnosis. | Operating problem |
| Abstract and Introduction / S2 | Trained generators store physical knowledge in weights learned from data that few-shot regimes cannot supply. | Shared root cause |
| Introduction / S3 | BREEZE changes where generative knowledge resides. | Explicit recipe, fixed renderer, calibrated admission |
| Related Work | General time-series generators place distributional knowledge in learned weights. | Knowledge-residence spectrum |
| Method | The second component moves physical control out of generator training and into a decision rule calibrated entirely within the outer training split. | Mechanism tied to root cause |
| Results / S4 | The results follow the component chain established in the Introduction. | Matched component tests and complete-pool evidence |
| Boundaries / S5 | The root-cause framework also predicts where BREEZE should fail. | Unknown morphology--condition map |
| Discussion | The source ablations answer the first question by establishing an LLM recipe contribution within the matched BREEZE pipeline. | Answers the three registered questions |
| Conclusion | BREEZE changes where fault-signal knowledge and physical control reside. | Mechanism and evidence synthesis |

The trace closes on the same supported proposition: explicit recipe knowledge
avoids target-generator fitting, while train-calibrated gates determine
admission; neither component supplies an unknown condition-dependent morphology
map or proves full physical truth.

## Final invariant and claim audit

| Audit | Final result |
|---|---|
| Experimental numerical values | Exact multiset match to synchronized `HEAD` after excluding citation-key years, positioning-table layout widths, and the typographic `1-D` to `1D` method descriptor |
| Generated result macros | Exact `\\Breeze...` key-and-count match |
| Equations and align environments | Exact environment-content match |
| Algorithm | Exact environment-content match |
| Figures and captions | All 10 figure environments match byte-for-byte in source; all figure assets are unchanged |
| Generated tables | All five `generated/*.tex` inputs retain their baseline SHA-256 values |
| Other tables | The dataset table is unchanged; only the requested positioning table adds the knowledge-residence column and layout widths |
| Structure | Exact ordered sequence of labels, inputs, figures, tables, equations, aligns, and algorithm environments |
| Claim-sensitive terms | Every use of significant/significance, transfer, milling, physical, state-of-the-art, zero-data, and universal was checked against the ledger |
| Trained baselines | Matched formal TimeGAN/DDPM evidence remains explicitly unavailable in Introduction, Experimental Design, Discussion, and the evidence ledger |
| API | Zero new LLM API calls |

The final abstract contains seven sentences and 196 mechanically counted words.
It retains every result macro, the qualified lower-shot Berkeley LLM--rule
advantage, the PU LOCO boundary, and the distinction between calibrated
admissibility and physical truth.

## Final artifact freeze

| Artifact | Final SHA-256 |
|---|---|
| `breeze/paper/main_cas.tex` | `4f641792201f87aee06a53a9347004a7106e14a5f70720d42a42171d73b565d0` |
| `breeze/paper/main_cas.abs` | `9cc7f98ea8a1f2ade1dfc54ccd53be41bb42d1809be81f0c1fa19d54ea35d9d4` |
| `breeze/paper/main_cas.pdf` | `cca9c889ac6c1d00805b3d929dd5f8f159057dbf7454face767e700f6e86f41f` |
| `breeze/paper/references.bib` | `0bbfdfe68dc0db37b52af2e7bdd1407f432f2aefa06bf0ec2ef25c43b6236898` |
| `analysis/evidence_ledger.md` | `637752db3cad59a727ce84a4de6dcf3095cc152c9f8108ef7fcf82b85be3767d` |
| `analysis/claim_evidence_map.md` | `68433aa58f2a93331e0426c99ae515936ee78962db15a10dab79f7a77cecd8a5` |

The ten manuscript figure PDFs remain at their frozen hashes:

| Figure PDF | SHA-256 |
|---|---|
| `acceptance_k.pdf` | `e4ea3b18fa09251cbabe0b7d8041bae4c8f34ad020b68cf86f5419a23d79d785` |
| `boxplots.pdf` | `acaff7aba005a0dcf57752017c27b0656102edd7e048fcc51772d094cb40ea8e` |
| `cross_condition_heatmap.pdf` | `d59be93429ad9fa96a5441199ac80520859d012d74dd83ea6456ea4862ca3d02` |
| `downstream_bars.pdf` | `985d038bd70480aa622c3ef2953ac1722abdc8098d769e16a169bfa6092e126e` |
| `failure_case.pdf` | `8e178e5e5dc0c8b1ff66c6402f2eebb3787686a43d0cd6fa95a4335e429f9b5c` |
| `failure_reasons.pdf` | `26fe46015036afcf3c3cbf1bb7659d77381a0f78595553b82c8f40e8c885872c` |
| `framework.pdf` | `0f10f4c87ba0a6ee94ab477336cc3715955b9f174c1ac27286d8c8675e3a0c22` |
| `metric_distances.pdf` | `c9bcece8a26290b0327cc00259ec4405e96205a26af4ad8532a95ab5e494b240` |
| `responsibility_boundary.pdf` | `41b49fd80a79dce61ec5ae4f58f085de24dfb624acaaf7e33e700d6387577e35` |
| `waveforms.pdf` | `46a824b111f7ad338ebef709309dabf0d9d33c049761703c8f0b3ba4b2fa3a34` |

## Build and visual QA

- Final command: `env LC_ALL=C LANG=C latexmk -g -pdf
  -interaction=nonstopmode -halt-on-error main_cas.tex`. The explicit `C`
  locale is required because the host advertises an unavailable `C.UTF-8`
  locale to Perl.
- Final PDF: 18 pages, CAS single-column page size, no fatal error, no undefined
  citation/reference, no BibTeX warning, and no LaTeX warning after convergence.
- Box diagnostics: one pre-existing CAS front-matter overfull box and 14
  underfull dataset-table cells. The positioning table adds none, and the final
  count is below the 23-underfull frozen baseline.
- Poppler rendered every page at 144 dpi. All 18 pages were inspected for
  clipping, overlap, missing glyphs, table overflow, figure readability, and
  bibliography layout. A missing macro-space on page 3 and a split `1-D`
  descriptor on page 7 were corrected and the affected pages were re-rendered.
- `git diff --check` passes. No generated result file or figure asset changed.
- The existing `Author One`, `Author Two`, and affiliation placeholders remain
  because verified author metadata was not provided; inventing it would violate
  the no-fabrication rule and lies outside this narrative-only revision.
