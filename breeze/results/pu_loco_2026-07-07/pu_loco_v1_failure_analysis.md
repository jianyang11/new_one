# PU LOCO v1 Failure Analysis

## Status

- Downstream completeness: 2400/2400 result rows.
- Protocol: 4 leave-one-condition-out folds, 5 methods, n_real={5,10,25}, 40 seeds, n_syn=20/class for synthetic methods.
- LLM pool construction API usage: 133 calls.
- Gate decision: FAIL for uniform PU LOCO superiority.

## Registered Test Outcome

- `pu_loco_wilcoxon.csv` contains 96 registered LLM superiority comparisons.
- Failed comparisons: 57/96.
- Failed comparison counts:
  - `llm>noise_aug`: 24
  - `llm>rule`: 15
  - `llm>random_open_loop`: 11
  - `llm>real_only`: 7

## Main Failure Pattern

The strongest baseline in this PU LOCO run is often `noise_aug`, not rule or random open-loop. Four-fold means show:

| method | n=5 Acc | n=5 Macro-F1 | n=10 Acc | n=10 Macro-F1 | n=25 Acc | n=25 Macro-F1 |
|---|---:|---:|---:|---:|---:|---:|
| LLM | 0.4322 | 0.3373 | 0.5190 | 0.4593 | 0.6075 | 0.5671 |
| noise_aug | 0.5512 | 0.5041 | 0.5897 | 0.5421 | 0.6430 | 0.6009 |
| rule | 0.4169 | 0.3188 | 0.4740 | 0.4120 | 0.6081 | 0.5759 |
| random_open_loop | 0.3751 | 0.2688 | 0.4670 | 0.3885 | 0.6138 | 0.5664 |

Per-class diagnostics indicate class-specific transfer failures:

- Held-out `N09_M07_F10`: LLM IR F1 is very low at n=5/10 and remains weak at n=25.
- Held-out `N15_M01_F10`: LLM IR F1 remains very low across all shots despite good healthy F1 at n=25.
- Held-out `N15_M07_F04`: LLM OR F1 is the bottleneck, especially at n=5/10.
- Held-out `N15_M07_F10`: LLM improves over random/rule in several few-shot settings but does not beat noise_aug.

## Methodological Constraint

These downstream test results must not be used to tune prompts, budgets, verifier boundaries, or selection rules for a re-run in the same protocol. Any PU LOCO v2 improvement must choose changes using training-fold-only validation or pre-registered physical diagnostics, then write outputs to a new directory.

## Next Safe Options

1. Create an inner validation split within each PU LOCO training fold and use it to compare candidate LLM pool variants against noise_aug/rule before touching held-out test evaluation again.
2. Run physical-quality diagnostics on existing LLM pools without changing admission: per-class BPFO/BPFI envelope prominence, PSD-W1, NN distances, and classifier confusion to locate physics mismatch.
3. Continue other datasets while marking PU LOCO v1 as failed evidence, if the user accepts scope qualification.
