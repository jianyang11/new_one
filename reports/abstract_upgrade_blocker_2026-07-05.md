# Abstract Upgrade Blocker

Date: 2026-07-05

## Requested Abstract Claims

The requested abstract standard requires all three claims:

1. BREEZE reaches the highest or tied-highest Accuracy/Macro-F1 across multiple
   public datasets, multiple operating conditions, and multiple baselines.
2. The abstract reports an LLM-contribution ordering:
   LLM recipe > random recipe > rule recipe.
3. The abstract reports gains and significance against the strongest baseline,
   not only against real-only training.

## Current Evidence Check

These claims are not supported by the current frozen workspace.

- The current completed public-dataset result is centered on PU
  `N09_M07_F10`; other PU conditions are only verifier audits, not completed
  synthetic augmentation experiments.
- No completed random-recipe or rule-recipe verifier comparison exists in the
  current results.
- Current PU downstream accuracy does not show BREEZE v2 beating the strongest
  baseline:
  - 10/class: BREEZE v2 = 0.7880, envelope-only = 0.7964.
  - 25/class: BREEZE v2 = 0.8082, noise augmentation = 0.8225.
  - 50/class: BREEZE v2 = 0.8456, noise augmentation = 0.8616.
- The strongest supported significance claim is BREEZE v2 vs real-only after
  Benjamini-Hochberg correction, not BREEZE v2 vs the strongest baseline.

Therefore the requested abstract cannot be written into the formal manuscript
without fabricating results or contradicting the result tables.

## Pending Target Abstract Sentence Pattern

Use this only after the missing experiments are completed and the result tables
support it:

> Across PU, [DATASET-2], and [DATASET-3], covering [N] operating conditions
> and [M] diagnostic baselines, BREEZE achieves the highest or tied-highest
> Accuracy and Macro-F1 in [X]/[Y] settings. Against the strongest non-BREEZE
> baseline, BREEZE improves Accuracy by [A] percentage points and Macro-F1 by
> [B] percentage points on average, with paired tests significant after
> Benjamini-Hochberg correction ([p/q details]). Recipe-source ablation shows
> that LLM-guided recipes outperform random and rule-based recipes
> ([LLM score] > [random score] > [rule score]), confirming that the LLM
> contributes beyond the deterministic renderer and verifier.

## Full Target Abstract Draft

The full LaTeX draft has been written to:

`breeze/paper/abstract_sota_template.tex`

All unverified quantities are explicit placeholders, including dataset names,
condition counts, number of baselines, strongest-baseline gains, statistical
test summaries, recipe-ablation metrics, and discriminator AUROC. This file is
ready to replace the active abstract only after the corresponding experiments
produce matching tables and statistics.

## Required Experiments Before Formal Abstract Replacement

- Complete at least one additional public dataset with the same downstream
  protocol.
- Complete multi-condition augmentation, not only verifier audit.
- Run and report random recipe + verifier, rule recipe + verifier, and LLM
  recipe + verifier under the same synthetic budget.
- Compute paired tests for BREEZE vs the strongest baseline per setting, with
  multi-test correction.
- Update tables, figures, result CSVs, and manuscript text before changing the
  abstract.
