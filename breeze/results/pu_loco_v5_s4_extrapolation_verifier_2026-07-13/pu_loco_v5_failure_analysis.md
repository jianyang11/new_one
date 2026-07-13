# PU LOCO v5 failure analysis — S4 extrapolation admission is not valid

## Frozen outcome

S4 does not reopen BREEZE pool construction. No S1, S2, S5, internal
downstream, preregistration, or registered formal held-out experiment was
run. This is an honest stop at the admission-validity layer, not a downstream
failure hidden by an unreported selection.

All evidence is train-bearing-only internal development evidence. The target
condition enters only through configured rpm/torque/radial-load metadata; no
target-condition waveform and no formal held-out waveform was read. API usage
for v5: **0**; cumulative ledger remains 1131/3000.

## Why S4 was attempted

v4's carrier-only audit showed that an in-domain v2 verifier patched to target
kinematics admitted only 0--1 of 100 real source healthy windows per source.
S4 therefore separated predictable source-to-target morphology intervals from
weak/not-predictable report-only background features, while retaining hard
sanity and rate-based physical gates.

## S4 sanity results

| regime | target | raw healthy rate | prohibited negatives admitted / 800 | status |
|---|---|---:|---:|---|
| v1 | N09_M07_F10 | 0.290 | 221 | fail |
| v1 | N15_M01_F10 | 0.877 | 311 | fail |
| v1 | N15_M07_F04 | 0.883 | 319 | fail |
| v1 | N15_M07_F10 | 0.920 | 350 | fail |
| v1.1 | N09_M07_F10 | 0.783 | 103 | fail |
| v1.1 | N15_M01_F10 | 0.867 | 203 | fail |
| v1.1 | N15_M07_F04 | 0.883 | 180 | fail |
| v1.1 | N15_M07_F10 | 0.923 | 231 | fail |

The frozen requirements were pooled raw healthy rate >=0.60, every-source raw
rate >=0.40, and exactly zero admission among 800 wrong-label/white-noise/
constant controls per target. v1.1 repairs v1's target-frequency healthy
calibration error and meets the healthy requirement in all four targets, but
still admits 103--231 prohibited negatives per target. It is therefore not a
valid verifier even though its healthy pass rate is plausible.

## Why v1.2 is not proposed

The source-only physical-feature diagnostic tested asserted fault prominence,
asserted-versus-competing-rate contrast, second harmonic prominence, shaft
prominence, and IR modulation sideband prominence. A feature would require
true-class q10 above both wrong-class and white-noise q90 before it could
support a new strict physical gate. No OR or IR feature met that condition.
For example, the OR q10 gap is negative for all tested features; the IR q10
gaps are likewise negative, including IR modulation (`-1.799` versus the
wrong class and `-0.786` versus white noise).

Raising a quantile until the observed negative controls disappear would trade
source true-fault coverage for an outcome-chosen threshold. That would be a
gate-tuning heuristic, not a training-free extrapolation rule. It is rejected
by the protocol.

## Interpretation

The data support a narrower conclusion than v4 alone: source-supported
cross-condition morphology intervals can recover real healthy admission, but
the available single-window envelope rate/harmonic/modulation evidence does
not simultaneously establish OR/IR identity and reject white noise across the
PU operating conditions. Under the stated evidence boundary, an
extrapolation-regime verifier cannot be used to certify BREEZE synthetic pools.

## Manuscript-safe language

> Cross-condition PU LOCO was treated as a stress test rather than a claimed
> generalization result. Although a source-only extrapolation regime restored
> admission of real healthy carriers, its required wrong-class and white-noise
> controls revealed insufficient class-discriminative physical evidence. We
> therefore froze the analysis before synthetic-pool construction and did not
> run a formal held-out comparison. This negative result delineates the scope
> of certificate-based training-free augmentation: plausible marginal
> morphology is not sufficient when fault-rate evidence is not reliably
> discriminative across operating conditions.

The methodological contribution is the falsifiable admission audit itself:
real carrier admission, wrong-label controls, white-noise controls, and
source-only separability must all pass before a cross-condition pool is
evaluated downstream.
