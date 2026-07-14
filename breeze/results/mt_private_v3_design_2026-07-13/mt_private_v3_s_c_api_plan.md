# Private machine-tool v3 — S-C API plan

**Frozen:** 2026-07-14, before the first S-C request.

## Trigger and boundary

The shared four-piece admission audit passed, and both zero-API pools filled
20/class. Their frozen inner downstream decisions are S-A `4/6` and S-B
`2/6` cells at least `noise_aug`, below the `5/6` rule. This is the sole
trigger for the conditional S-C branch.

All S-C calibration, prompt statistics, templates, rendering, and admission
use IDs `1/2/4/5`; ID `10` is read only after a balanced pool is built for the
same downstream evaluator. IDs `7/8` remain loader-forbidden. S-C starts at
zero requests, may make at most 100 total attempts, and makes no formal call.
HTTP, format, JSON, schema, renderer, and verifier failures each consume an
attempt. Credentials are process-environment inputs only and never appear in
source, prompts, logs, results, or Git.

## Fixed generation protocol

1. **Smoke:** exactly three requests, one first-round slot per class. It must
   admit one candidate per class through the unchanged verifier, historical
   ExtraTrees identity certificate, exact-duplicate check, and real--real
   diversity rule before full generation is eligible.
2. **Full pool:** target 20 accepted samples per class. Each request may render
   exactly three deterministic expansions; the first admitted expansion is
   retained and all others are recorded. A pending slot receives at most an
   initial request plus three structured-feedback requests. No rejected signal
   is repaired, rescaled, or re-admitted.
3. **Budget:** the request ledger is append-only and capped at 100 across smoke
   and full generation. Restarting resumes slot checkpoints and does not reset
   the count.

The prompt uses the v2 fixed JSON renderer schema and only three kinds of
inner-train evidence: class exemplar statistics, pairwise class-difference
tables, and the v3 signed normalized soft-band/channel-standard-deviation
directions. It tells the model to make its recipe follow those directions but
forbids file IDs, validation/formal information, machine metadata, shaft or
component frequencies, code, and waveform values. The deterministic renderer
is unchanged; no generator is trained and no new certificate is fitted.

## Post-generation rule

Only an admitted balanced 20/class S-C pool may enter the existing downstream
grid. It uses amendment 1's common synthetic budgets (10/class at `n_real=10`,
20/class at `n_real=25/50`) and the unchanged 5-of-6 Acc/Macro-F1 gate. A
shortfall at any class, budget exhaustion, or downstream loss is frozen as a
failure; it never opens formal access.
