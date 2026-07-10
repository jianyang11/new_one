# Recipe-Source Ablation

Tag: `full`

Summary CSV: `breeze/results/recipe_ablation_summary_full.csv`
Fail-reason CSV: `breeze/results/recipe_ablation_fail_reasons_full.csv`

## Summary

| source | class | slots | accepted slots | acceptance | items before diversity | kept after diversity |
| --- | --- | --- | --- | --- | --- | --- |
| rule | all | 700 | 204 | 0.2914 | 866 | 785 |
| rule | healthy | 150 | 58 | 0.3867 | 270 | 227 |
| rule | OR | 150 | 87 | 0.5800 | 421 | 407 |
| rule | IR | 400 | 59 | 0.1475 | 175 | 151 |

## Interpretation Guardrail

This ablation compares recipe sources under the same deterministic renderer and v2 verifier. It does not create new LLM calls. A downstream or acceptance advantage of LLM recipes over these non-LLM recipes is required before the manuscript can claim that LLM-guided generation is independently reliable.
