# Private machine-tool v3 — preregistered inner-development design

**Frozen before v3 candidate/audit execution:** 2026-07-13  
**Purpose:** test whether deterministic, train-supported class-conditional
surrogates add downstream information beyond `noise_aug`.  This is not a
component-physics or formal held-out protocol.

## Corrected starting point and access boundary

The frozen v2 run admitted a balanced five synthetic windows per class.  Its
`BLOCKED` decision was caused by the downstream core comparison (zero of six
real/noise cells), not a lack of admitted candidates.  v3 therefore does not
alter v2's historical admission result or reinterpret it as cross-condition
rejection.

All calibration, directional feature selection, carrier selection, candidate
construction, and zero-API audit use only file IDs `1,2,4,5` of each class.
File ID `10` is read only by the fixed inner-validation downstream stage.
Formal IDs `7,8` are loader-forbidden until a committed formal
preregistration.  API requests are zero for S-A, S-B, S-E, and the first
internal comparison.  S-C can begin only when an eligible zero-API candidate
loses the frozen inner comparison, and then has a counted ceiling of 100
requests.

The factual-data-card search is frozen in
[`mt_private_machine_data_card_search.md`](mt_private_machine_data_card_search.md).
It establishes a 4 kHz four-column schema but no speed, feed, lead,
transmission, sensor-mounting, current-definition, or process metadata.
Consequently no TPF, rotational, 1x imbalance, lead-screw, bearing, or
absolute-frequency term appears in v3.

## Reused admission components

`MachineToolVerifier(coverage=0.90)` and the historical ExtraTrees
class-identity certificate are calibrated exactly as in v2 from the inner
train set.  The verifier's finite/nonconstant, generic statistics,
normalized soft-spectrum, and normalized PSD-W1 gates remain unchanged.  The
ExtraTrees certificate is retained only as the existing exploratory
class-identity check; v3 does not fit another learned certificate.  Neither
component is a physical certificate.

Candidate admission requires all existing hard verifier gates, the historical
identity prediction equal to the requested class, a nonduplicate digest, and
the unchanged real--real diversity lower bound.  Rejected candidates are
discarded.  They are never repaired, re-scaled, filtered, or re-admitted.

## S-A — discriminative-direction conditional surrogate (zero API)

For each target class, compute inner-train medians and pooled robust scales of
the existing directly controllable features only:

- 32 normalized soft-spectrum fractions (`channel × 8` bands);
- four channel standard deviations.

For feature \(j\), let \(d_{c,j}\) be the target median minus the median of
the other two classes, divided by their pooled robust scale.  The deterministic
renderer starts from one target-class carrier, applies a single IAAFT-style
surrogate per channel, and applies these fixed signed controls:

\[
g_{c,j}=\exp(0.08\,\mathrm{clip}(d_{c,j},-2,2))
\]

for each normalized soft band and the analogous channel standard-deviation
multiplier.  `0.08` and the clip interval are frozen renderer-domain constants,
chosen before v3 validation to keep each gain in approximately `[0.85,1.17]`;
they are not selected on inner validation.  Non-controllable correlations,
peaks, RMS, and physical interpretations may be reported but are never turned
into a synthetic control.  Candidate carriers cycle deterministically through
all target-class train windows, with a stable seed and no other-class carrier.

This construction encodes the already observed signed class differences (for
example, the strong current soft-band contrasts) without inventing what a
normalized band means mechanically.

## S-B — same-class real-carrier mix (zero API)

For each target class, select two distinct target-class train windows by a
stable seed and return the channel-wise convex mixture

\[
x_{c}=\alpha x_{c,a}+(1-\alpha)x_{c,b},\qquad
\alpha\in\{0.35,0.50,0.65\},
\]

cycled deterministically by attempt.  This preserves real target-class
background/cross-channel structure while producing a nonidentical candidate.
No validation/formal carrier, cross-class carrier, physical injection,
or after-the-fact waveform adjustment is allowed.

## Four-piece admission audit (precondition for S-A/S-B pools)

The audit uses the reused verifier plus identity check but omits only the
synthetic-only exact-duplicate/diversity rule when the input itself is a real
calibration carrier.  This separation prevents a real source from failing
solely because it is necessarily identical to its own reference.  It does not
relax candidate admission.

| Audit | Fixed inputs | Frozen requirement | Why |
|---|---|---|---|
| Real-carrier sanity | all inner-train windows under their true class | at least 80% core admission in each class and at least one admitted window from each of the four source files | existing c90 generic support should not systematically reject a represented class/source |
| Wrong-label control | each real window submitted under each of the other two labels | exactly zero core admissions | labels must not be exchangeable under the retained identity evidence |
| White-noise control | 100 deterministic four-channel Gaussian windows per requested class, using that target's train mean/std but no temporal structure | exactly zero core admissions | strong nonphysical control that preserves marginal scale |
| Constant control | 100 deterministic four-channel constants at each target's train channel mean | exactly zero core admissions | verifies the finite/nonconstant hard gate |
| Source-only separability report | true and wrong-label identity margins for the preceding real controls | report only; no extra fitted model and no threshold change | exposes whether the existing certificate, rather than a new classifier, supplies class evidence |

The candidate-level four-piece gate is pass only if every table requirement is
met.  Any failure stops S-A/S-B expansion and downstream evaluation.  No
quantile, threshold, renderer constant, or control count may be changed in
response to the audit outcome.

## Pool and internal comparison

Each S-A/S-B method first attempts a one-per-class smoke and then a five-per-
class smoke.  Only an independently balanced five-per-class method may attempt
the frozen `n_syn=20/class` pool.  The capacity ceiling is 80 deterministic
attempts per class per stage.  Every attempt has a certificate, deterministic
seed, carrier provenance, digest, and rejection reason; arrays/checkpoints
remain outside Git.

Every eligible pool is compared on file ID `10` with `real_only` and
`noise_aug` at `n_real={10,25,50}`, ten fixed seeds, the v2 CNN/normalization
settings, and class-balanced `n_syn=20/class`.  Report Acc, Macro-F1,
per-class F1, confusion matrices, seed rows, and paired one-sided Wilcoxon
tests with Holm adjustment.  A zero-API candidate is internally successful
only when its **mean Acc and mean Macro-F1 are each at least `noise_aug` in at
least five of the six shot-by-metric cells**.  All six cells are reported.

S-C is conditionally available only after an eligible S-A/S-B pool fails that
comparison.  S-E is a 50:50 per-class union of `noise_aug` and the one
eligible BREEZE pool at the same total budget; it receives no further
filtering.  If more than one BREEZE pool is eligible, no implicit choice is
made: S-E is not constructed until a separately precommitted selection rule
exists.

## Formal boundary

Only exactly one named candidate satisfying the internal two-metric rule may
lead to `mt_private_v3_preregistration.md`.  It must record the code SHA, pool
digest, all constants, formal split, 40 fixed seeds, both metrics, Wilcoxon
direction, and full Holm family before IDs `7,8` are read.  Otherwise v3 ends
with a failure analysis that states the empirical, metadata-limited boundary.
