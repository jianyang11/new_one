# §A Evidence-Freeze Report

Date: 2026-07-14 (Asia/Shanghai)

## Decision

§A is complete. `analysis/evidence_ledger.md` now defines the manuscript claim
boundary. No frozen result directory, result file, split manifest, or API log
was modified; no experiment or API call was run.

## Integrity checks

- `HEAD` and `origin/main` both resolve to `345cbbd` after synchronizing the
  remote tracking reference.
- The repository had user-owned untracked items before §A. They remain
  unmodified and were excluded from formal evidence.
- CWRU's frozen Wilcoxon CSV contains 90 registered rows, all with
  `passed_holm=True`.
- The latest centrally recorded API cumulative value is 1131, but the later
  private-machine-tool S-C API log adds 100 recorded requests. The reconciled
  total is 1231/3000, not the historical UMich-v4 value of 1020/3000.

## Mandatory claim corrections

1. Berkeley is partial/no-go (15/18), not a passed milling result. Its LLM-rule
   claim must be metric-specific: only n=2 Accuracy and both n=5 metrics pass;
   n=2 Macro-F1 and n=10 Accuracy/Macro-F1 do not.
2. The Berkeley formal evidence cannot establish a significance claim for rule
   versus unstructured baselines because those pairwise tests were not run.
3. UMich stopped because the signal task is confounded by stage/metadata. The
   near-chance all-label raw variants are not a sufficient standalone summary.
4. PU LOCO v1--v6 is a boundary result. v3--v6 are train-only diagnostic or
   admission-stage failures and must not be presented as formal held-out tests.

## Deferred framework work

The planned Layer-1 and Layer-2 redesign tasks (L1.1--L1.9 and L2.1--L2.9)
are marked deferred in `todos.md` as post-submission work. They are excluded
from this manuscript and must not be cited as implemented methodology.

## Next permitted work

Proceed only with the closing-stage trained baselines, ablation/physics-metric
reports, and manuscript rewrite. Each new result must be reconciled against
the evidence ledger before it can be introduced into the paper.
