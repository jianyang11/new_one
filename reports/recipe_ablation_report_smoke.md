# Recipe-Source Ablation

Tag: `smoke`

Summary CSV: `breeze/results/recipe_ablation_summary_smoke.csv`
Fail-reason CSV: `breeze/results/recipe_ablation_fail_reasons_smoke.csv`

## Summary

| source | class | slots | accepted slots | acceptance | items before diversity | kept after diversity |
| --- | --- | --- | --- | --- | --- | --- |
| random | all | 15 | 0 | 0.0000 | 0 | 0 |
| random | healthy | 5 | 0 | 0.0000 | 0 | 0 |
| random | OR | 5 | 0 | 0.0000 | 0 | 0 |
| random | IR | 5 | 0 | 0.0000 | 0 | 0 |
| rule | all | 15 | 1 | 0.0667 | 5 | 5 |
| rule | healthy | 5 | 1 | 0.2000 | 5 | 5 |
| rule | OR | 5 | 0 | 0.0000 | 0 | 0 |
| rule | IR | 5 | 0 | 0.0000 | 0 | 0 |

## Interpretation Guardrail

This ablation compares recipe sources under the same deterministic renderer and v2 verifier. It does not create new LLM calls. A downstream or acceptance advantage of LLM recipes over these non-LLM recipes is required before the manuscript can claim that LLM-guided generation is independently reliable.
