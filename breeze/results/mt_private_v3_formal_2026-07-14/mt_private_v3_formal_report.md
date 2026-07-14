# Private machine-tool v3 — formal result

## Protocol integrity

- Candidate: the sole preregistered S-C (`s_c_llm`) pool, frozen at 20
  verifier-admitted samples/class before formal data were read.
- Formal train: file IDs `1/2/4/5/10`; formal test: IDs `7/8` only.
- The preregistration lock checked the pool-manifest SHA-256, inner-decision
  SHA-256, and both source-file SHA-256 values before any formal file loaded.
- All `3 methods × 3 n_real cells × 40 fixed seeds = 360` rows exist exactly
  once. There was no API call, candidate change, retry, or post-formal union.

## Formal S-C versus noise augmentation

| `n_real` | S-C Acc / Macro-F1 | `noise_aug` Acc / Macro-F1 | mean delta Acc / Macro-F1 | Holm q Acc / Macro-F1 |
|---:|---:|---:|---:|---:|
| 10 | 0.4559 / 0.4535 | 0.3957 / 0.3848 | +0.0602 / +0.0687 | 5.21e-6 / 2.19e-7 |
| 25 | 0.5556 / 0.5551 | 0.5484 / 0.5421 | +0.0072 / +0.0130 | 0.7268 / 0.5532 |
| 50 | 0.6864 / 0.6883 | 0.7305 / 0.7308 | -0.0441 / -0.0425 | 1.0000 / 1.0000 |

The six primary one-sided paired tests form one Holm family. At `n_real=10`,
S-C significantly exceeds `noise_aug` on both accuracy and Macro-F1. At 25,
the mean differences are positive but not significant. At 50, S-C is worse
than `noise_aug` in both metrics.

## Honest conclusion

This is a **low-shot-specific formal success**, not evidence that S-C is
uniformly superior. The defensible claim is that discriminatively conditioned,
verifier-admitted S-C augmentation improves this private machine-tool task in
the 10-real-samples-per-class regime; its advantage vanishes by 25 and reverses
by 50, where the ordinary noise baseline benefits more from abundant real
carriers. The manuscript must report all three shot levels, the nonsignificant
25-shot comparison, and the 50-shot reversal; it must not claim an overall or
high-data advantage.

The final artifacts are the 360 seed rows, per-method summaries, the full
Wilcoxon-plus-Holm table, and the file-level integrity record in this directory.
