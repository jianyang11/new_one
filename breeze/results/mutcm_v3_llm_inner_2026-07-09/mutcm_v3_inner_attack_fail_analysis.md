# MU-TCM v3 Inner-Val Attack Failure Analysis

Status: inner-val only. No preregistration was written and no formal held-out test was run.

## API and Pool

- API attempts counted: 51 total (50 successful HTTP 200, 1 provider/json error attempt).
- Budget: 51/180 for this v3 inner attack, cumulative project API 1071/3000 after this run.
- LLM pool: 121 windows, healthy=60 and worn=61.
- Rule/random pools: 80 windows per class each.

## Main ExtraTrees Gate

- Selected n_syn: 20.
- Core gate: 2/6, below the required 5/6.
- Passed only n_real=10 Acc and Macro-F1.
- LLM consistently beat noise_aug, but did not beat rule and random_open_loop at n_real=2/5.
- Mean deltas at selected n_syn=20:
  - n=2 Acc/Macro-F1 vs rule: -0.0130/-0.0141; vs random: -0.0152/-0.0174.
  - n=5 Acc/Macro-F1 vs rule: -0.0039/-0.0039; vs random: +0.0032/+0.0037.
  - n=10 Acc/Macro-F1 vs rule: +0.0029/+0.0032; vs random: +0.0049/+0.0050.

## Diagnostics

- Class collapse was not observed: healthy and worn F1 stayed above the hard constraints.
- Failure is concentrated in beating strong train-supported rule/random pools, not in beating noise_aug.
- Condition-wise performance is not single-condition-only, but the StainlessSteel validation condition remains the lower-performing side for all methods.
- Removing boundary recipes reduced performance (variant_no_boundary gate 0/6), so boundary recipes are not the primary cause.
- A linear LogisticRegression diagnostic also failed (2/6) and emitted convergence warnings, so it is not a clean alternative classifier path.
- Mean LLM-rule delta is below 0.005 in the successful n=10 setting, so the Berkeley-like weak-gain risk flag remains active.

## Decision

Do not preregister and do not run formal held-out test from this v3 result.
