# S4 design amendment 1 — operationally strict rate evidence

## Trigger and status

This amendment is made after the retained v1 first-target sanity failure and
before any v1.1 calibration or pool construction. The original `s4_design.md`
is preserved unchanged as the v1 record. This is a stricter design correction,
not an acceptance-rate adjustment: v1 admitted wrong-class faults and OR white
noise, so it cannot be an admissible extrapolation verifier.

The amendment uses only the three source-condition train-bearing windows and
fixed condition metadata. It does not read pseudo-held-out or formal windows,
and it makes zero API requests.

## Frozen v1.1 corrections

### Healthy absence reference

For a target verifier, every source healthy window is evaluated at the
**target** BPFO/BPFI when calibrating the healthy q99 fault-absence ceiling.
Healthy has no observed defect rate, so this is the only frequency reference
consistent with the target-frequency absence gate stated in the original
design. The q99 tail and hard absence decision are unchanged; only the v1
source/target frequency mismatch is removed.

### Fault-rate exclusivity

For an asserted OR candidate define, in the fixed 600--1200 Hz envelope band,

`C_OR = log(1 + P_BPFO) - log(1 + P_BPFI)`.

For an asserted IR candidate define, in the fixed 3000--3600 Hz envelope band,

`C_IR = log(1 + P_BPFI) - log(1 + P_BPFO)`.

`P` is the existing resolution/2%-tolerance envelope prominence at the named
physical rate. A fault now passes the hard envelope kinematic gate only when:

1. its asserted-rate prominence is at least the pooled source-fault q10;
2. its asserted-rate contrast `C` is at least the pooled source-fault q10;
3. the selected asserted-rate peak is within the existing strict frequency
   tolerance.

The q10 is fixed by the existing v2 `coverage=0.90` contract: it is the lower
tail that retains 90% of source fault evidence, rather than v1's unprincipled
q01 lower tail. It is calculated once from correctly labeled source faults at
their observed kinematics. The competing BPFO/BPFI score is evaluated in the
same fixed physical demodulation band, so the rule tests a rate relationship,
not an arbitrary global spectrum maximum. No target waveform participates.

The vector-current separation rule remains unchanged. If source fault and
healthy current evidence do not separate at its fixed source tails, it remains
report-only rather than creating an arbitrary current threshold.

## Unchanged safeguards and rerun rule

All original predictable-feature interpolation, report-only weak/background
features, sanity gate, source-only boundary, `k=2.0` LOO interval multiplier,
100-per-source healthy schedule, and 100-per-control negative schedule remain
unchanged. The v1.1 audit must again satisfy raw healthy pooled rate >=0.60,
every-source raw rate >=0.40, and exactly zero admitted negative controls in
every internal target before any S1/S2 pool can be reopened. A v1.1 failure
again terminates pooling and is reported rather than loosened.
