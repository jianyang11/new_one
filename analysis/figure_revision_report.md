# BREEZE Fig. 3+ Revision Preview Report

Date: 2026-07-16

Baseline: `origin/main@621dfe7`

Phase: preview only; formal integration has not started

Status: seven figures complete, Figure 6 blocked by missing frozen round records

## Scope and method

This revision uses the local `nature-figure` workflow for figure contracts,
183 mm layout, editable/raster export, and visual QA. The local Nuwa skill was
used as a cross-paper synthesis method: primary-source verification, recurring
evidence patterns, anti-patterns, and explicit scope boundaries. It was not
used to imitate an author or invent expert approval.

The evidence order is downstream effectiveness, physical credibility,
admission mechanism, and generalization boundary. Only PU, CWRU, and Berkeley
formal public protocols appear. No private data, smoke/partial run,
trained-generator baseline, unfinished classifier backbone, or empty future
method slot enters a preview or manifest.

## Figure 3: downstream diagnostic effects

**Question.** How much does the admitted LLM-recipe pool change Accuracy and
Macro-F1 relative to rule and the completed non-structured comparator?

The old seed cloud is replaced by a 2x3 paired-effect forest plot. The top row
uses one shared `+/-12 pp` scale for LLM-rule on PU, CWRU, and Berkeley. The
bottom row declares its separate ranges because the non-structured gaps are
larger. Each point is a paired mean effect; each line is a 95% percentile
bootstrap interval from 20,000 resamples over paired seeds. Filled markers pass
the registered Holm correction and hollow markers are non-significant.

The snapshot contains 36 effect cells and 1,200 paired seed rows. PU uses 20
seeds at 5/10/25 shots; CWRU uses 40 at 5/10/25; Berkeley uses 40 at 2/5/10.
LLM-rule effects span 4.94--8.50 pp on PU, 1.33--3.65 pp on CWRU, and
0.02--0.47 pp on Berkeley. Three of six Berkeley LLM-rule cells pass Holm; all
other displayed comparison families pass in all six cells.

**Boundary.** Seeds repeat few-shot subset selection and CNN initialization
around a fixed synthetic pool. The interval is not uncertainty over independent
LLM pool generations.

## Figure 4 and Supplementary Figure S2: auditable signal morphology

**Question.** Do representative waveforms and population envelope spectra
show the registered OR/IR structure without choosing the first or most
attractive sample?

For every class/source, the selected waveform is the actual window nearest the
within-source robust center in a class-real-train-scaled feature space of
three-channel log-RMS and PSD-CDF coordinates. Zero-MAD coordinates are
removed exactly, and ties resolve to the lowest source index. The selected
indices and distances are stored in `medoids.csv`; no held-out/test window is
read. Figure 4 contains eight medoids and S2 contains four healthy medoids.

Waveforms retain raw vibration amplitude and share class-specific y limits.
Envelope spectra summarize every source/class window with median and IQR under
one 500--2000 Hz FIR demodulation, squared envelope, Hann FFT, and absolute
scaling. BPFO is 46.1 Hz and BPFI is 73.9 Hz. OR/IR remain in the main preview;
healthy is isolated in S2.

**Boundary.** A medoid is an auditable representative, not fidelity proof.
Population spectra and Figure 5 provide the distribution-level evidence.

## Figure 5 and Supplementary Figure S1: physical credibility

**Question.** For which class-specific observables is a completed pool closer
to the real reference than rule, and where is it worse?

Three matrices show `log2(method distance / rule distance)` for RMS-W1,
kurtosis-W1, PSD-W1, band-energy error, and fault-frequency alignment. Negative
values favor the method; positive values favor rule. All unfavorable cells are
retained. PU has 42/45 available cells, CWRU 38/40, and Berkeley 18/30.
Berkeley kurtosis and bearing-frequency cells are explicitly NA; its TPF metric
is not relabeled as bearing physics.

Within-pool NN diversity is shown in a separate raw log-axis point panel because
it has no universal optimum. It does not share the fidelity-error color scale.
The source snapshots retain numerator, rule denominator, raw NN values, and all
NA statuses.

S1 moves the raw PU RMS/kurtosis distributions to six ECDF panels. Sample sizes
are printed: Real has 1200/1202/1444 windows by class, and each synthetic
source has 150/class. The first grayscale audit found that color alone was not
sufficient; the accepted revision adds fixed solid/dashed/dotted source line
styles.

**Boundary.** These are empirical diagnostic distances from one frozen pool
per source, so no inferential physical-validity test is invented.

## Figure 6: admission mechanism blocker

Figure 6 was not generated. The dated freeze contains 450 final slot rows and
286 admitted LLM slots, but it does not contain each slot's first passing round.
`n_candidates` is archive depth rather than a K=0/1/2/3 round label. The local
round JSON files are outside the dated SHA-256 freeze and therefore cannot be
silently promoted into formal evidence.

The blocker artifact is in
`breeze/paper/figs/revision_preview/fig6_admission_mechanism_BLOCKED/`.
Unblocking requires a separate audited round-level freeze whose aggregation
reproduces exactly 450 slots and 286 final admissions. Only then can the
cumulative panel and the traceable final-rate/failure panels be drawn. No
partial figure, empty panel, or inferred curve was emitted.

## Figure 7 and Supplementary Figure S3: transfer and boundary

**Question.** Does a CWRU load0 source pool transfer to held-out loads, and what
boundary is exposed by the PU LOCO protocols?

The left panels show the signed LLM-rule effect in percentage points for
`source load0 -> held-out load 1--3`, with one zero-centered scale and a filled
Holm marker in every one of the 18 Accuracy/Macro-F1 cells. The invalid
`lolo_load0` cell is excluded. The right panels use a separate discrete scale
for the number of positive Holm passes out of four in PU v1/v2. Observed states
range from 0/4 to 3/4; no continuous-effect palette is reused.

S3 preserves the complete v1--v6 chain. Only v1 and v2 are formal held-out
protocols. v3--v6 remain visible as development/admission/source-evidence
stops and are explicitly labelled `NO HELD-OUT TEST`.

**Boundary.** This is not described as strict four-fold CWRU LOLO, and PU
development stops are not converted into downstream effects.

## Provenance and tests

- Every complete figure directory contains independent CSV snapshots and a
  `source-manifest.json` with source/code/output SHA-256 values, filters,
  sample counts, UTC generation time, and Git baseline.
- Manifest audit verified 16 code, 90 source, and 45 output entries: all 151
  files exist and every hash matches.
- `breeze/tests/test_figure_revision_preview.py` passes 9/9 tests. Coverage
  includes protocol/shot/metric completeness, exact paired counts,
  deterministic bootstrap, train-only medoids, fixed demodulation, raw
  amplitude preservation, NA propagation, ratio recomputation, Fig. 6 stop,
  CWRU load0 exclusion, discrete PU states, export dimensions, and manifest
  integrity.
- The source-to-figure mapping is in `analysis/figure_source_map.md`; scientific
  contracts are in `analysis/figure_contracts.md`; the eight-paper visual
  benchmark is in `analysis/figure_style_benchmark.md`.

## Export and visual QA

All seven complete figures export editable PDF/SVG, 300 dpi review PNG, and
600 dpi LZW TIFF. Audit results in `qa/export_audit.csv` show a PDF width of
182.9999 mm, PNG width 2161 px, TIFF width 4322 px, embedded PDF fonts, and SVG
`<text>` elements for every figure.

Full-severity protanopia, deuteranopia, and tritanopia screens use the Machado
et al. (2009) matrices in linear sRGB as a visual check, not as a formal
accessibility guarantee. The figures retain meaning through marker shape and
fill, numeric annotations, line style, panel separation, and explicit NA text.
Grayscale and CVD outputs are under `revision_preview/qa/`.

A temporary CAS document embeds every complete preview at full text width:
`revision_preview/qa/cas_reading_size/cas_figure_qa.pdf`. Its rendered pages
show no overlap, clipping, illegible axis label, or displaced legend. The only
LaTeX warning is the CAS template's empty first-page hyperlink anchor.

The old/new contact sheet is
`revision_preview/qa/old_new/old_new_contact_sheet.png`. The Figure 6 entry is
clearly labelled as a QA blocker and is not a manuscript figure.

## Formal-integration gate

The formal manuscript has not been edited. SHA-256 comparison confirms all 42
baseline `main_cas.tex`, `main_cas.pdf`, and formal `paper/figs/*` files are
byte-unchanged. Formal replacement, captions, numbering, and manuscript
compilation must wait for author approval and a decision on the Figure 6
round-level freeze.

## Requirement audit

| Requirement | Status |
|---|---|
| Read skill, manuscript, plotting code, and sources | Pass |
| Benchmark 5--8 verified papers | Pass: 8 papers |
| PU/CWRU/Berkeley only | Pass |
| Exclude unfinished generators/backbones | Pass |
| Figure 3 paired forest plot | Pass |
| Figure 4 medoids plus population spectra | Pass |
| Figure 5 error matrices plus separate diversity | Pass |
| Figure 6 cumulative frozen-round mechanism | **Blocked** |
| Figure 7 mixed cross-condition/boundary evidence | Pass |
| S1/S2/S3 supporting figures | Pass |
| CSV snapshots and manifests | Pass for complete figures; blocker manifest for Fig. 6 |
| Statistical/source tests | Pass: 9 tests |
| PDF/SVG/TIFF/PNG export | Pass for complete figures |
| CVD, grayscale, final-size, CAS QA | Pass |
| Formal manuscript remains unchanged | Pass |

