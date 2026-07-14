# Private machine-tool v3 formal preregistration

**Frozen locally:** 2026-07-14, before loading any formal file ID `7` or `8`.

## Candidate selection

The sole formal candidate is **S-C (`s_c_llm`)**. Its immutable 20/class pool
and the inner development decision are hash-locked below. On the frozen
inner grid, S-C reached Acc and Macro-F1 at least `noise_aug` in all `6/6`
shot-by-metric cells. S-A directional (`4/6`) and S-B carrier mix (`2/6`) do
not meet the required `5/6` rule. Thus no union method is constructed or
selected.

## Formal split and fixed training protocol

- Formal-train file IDs: `1, 2, 4, 5, 10` for every class.
- Formal-test file IDs: `7, 8` for every class; they have not been read when
  this document is frozen.
- Methods: `real_only`, unchanged no-replacement `noise_aug`, and frozen
  `s_c_llm`; all three are evaluated at every cell.
- `n_real` per class: `10, 25, 50`.
- `n_syn` per class: 10 at `n_real=10`; 20 at `n_real=25` and `50`, for both
  `noise_aug` and S-C. The first deterministic admitted S-C manifest rows per
  class are used; no post-pool selection or filtering occurs.
- Seeds: the fixed sequence `0` through `39`, used for real-subset selection,
  noise generation, and CNN initialization through the deterministic formal
  seed namespace. Interrupted execution may write only missing rows; it may
  not replace an existing row.
- Normalization: channel-wise mean/std estimated from each method's training
  tensor only and applied to its formal-test tensor. Model: the frozen v2
  `SimpleCNN`, 60 epochs, Adam learning rate `3e-4`, weight decay `1e-4`,
  cross-entropy, batch size 32.
- `noise_aug` remains distinct-carrier, 5%-of-full-formal-train class-std
  additive Gaussian augmentation. It does not permit carrier replacement.

## Outcomes and testing family

For every seed row, record accuracy, Macro-F1, all three class F1 values, and
the 3-by-3 confusion matrix. The primary reported comparisons are the six
one-sided paired Wilcoxon tests `s_c_llm > noise_aug` (Acc and Macro-F1 at
each of three `n_real` values), with Holm adjustment over this six-test family.
Means, standard deviations, raw p-values, and Holm q-values are all reported
regardless of their direction. No formal result changes a pool, prompt,
renderer, verifier, threshold, candidate identity, seed, or data split.

## Hash and code lock

- Local pre-formal code commit: `567108a62ea7c0241135c99314e6dadc1326ea65`.
- `breeze/scripts/mt_private_v3_formal.py` SHA-256:
  `5edb6a69ab081c604e2b2707d4575c1bcf665956af8ea4cbb12300a467aae1ef`.
- `breeze/scripts/mt_private_v3_conditional.py` SHA-256:
  `74d9e151fd80a5cd78252f5a876f94dd21b8cd1cb445b8fbda701f5dbf00805b`.
- S-C pool manifest SHA-256:
  `f55df09ccbe34007833be0e5691f6ec3c4dc765e7c2ad9aaf1f232fe50b8e7ec`.
- S-C inner-decision SHA-256:
  `d2a982ef3364db96a015583e5afbf42832d6506b5072525bcb0d7e8ed8a98d84`.

The accompanying `mt_private_v3_formal_lock.json` is read by the formal
runner before it can load any formal file. The formal output directory is
`breeze/results/mt_private_v3_formal_2026-07-14/`. No API call is permitted
in the formal stage.
