# Private machine-tool v3 — S-C inner downstream report

## Scope and integrity

- Inner train: file IDs `1/2/4/5`; inner validation: ID `10` only.
- Formal IDs `7/8` read: `0`; the S-C API ledger remains at 100 counted
  requests and no API call was made during downstream evaluation.
- Candidate pool: the immutable, verifier-admitted S-C pool at 20/class.
- Ten fixed seeds per cell, v2 CNN/normalization settings, Acc and Macro-F1.
- Under amendment 1, the synthetic budget is 10/class at `n_real=10` and
  20/class at `n_real=25/50` for every non-real method.

## Means over ten seeds

| `n_real` | S-C Acc / Macro-F1 | `noise_aug` Acc / Macro-F1 | Acc / Macro-F1 at least noise |
|---:|---:|---:|---|
| 10 | 0.3132 / 0.3063 | 0.3004 / 0.2884 | yes / yes |
| 25 | 0.3339 / 0.3239 | 0.3117 / 0.3036 | yes / yes |
| 50 | 0.3837 / 0.3820 | 0.3654 / 0.3744 | yes / yes |

The frozen inner success rule requires both metrics to be at least
`noise_aug` in at least five of six shot-by-metric cells. S-C reaches **6/6**.
The previously frozen zero-API counts are S-A `4/6` and S-B `2/6`; therefore
S-C is the unique candidate eligible for a preregistered formal comparison.

## Inferential table and boundary

The paired one-sided S-C-versus-noise Wilcoxon tests have Holm-adjusted
q-values of 0.75 (n=10 Acc), 0.75 (n=10 Macro-F1), 0.6973 (n=25 Acc), 0.75
(n=25 Macro-F1), 0.6973 (n=50 Acc), and 0.75 (n=50 Macro-F1). None is
significant. This does not alter the predeclared inner eligibility rule, which
uses mean non-inferiority in the six cells; it must be reported alongside the
formal result rather than converted into a post-hoc claim of significance.

No S-E union is constructed: S-C is the sole eligible BREEZE pool, so the
design's ambiguity condition for choosing among more than one eligible pool
does not apply. The next permitted action is a committed formal
preregistration before any formal file is loaded.
