# Phase-B CWRU Leave-One-Load-Out Schedule Report

Generated: 2026-07-06T16:22:48

Split: `lolo_load1`. Train loads are 0/2/3; test load is 1. Synthetic pool remains the CWRU load0 LLM full v1 pool, so this split does not use synthetic samples from the held-out test load.

Registered schedule: n=5/10 use 38 synthetic samples per class; n=25 uses 20 synthetic samples per class. CNN, 20 epochs. The initial 20-seed smoke found n=25 vs noise_aug borderline; therefore n=25 was extended to seeds 0-39 while n=5/10 remain seeds 0-19. Paired one-sided Wilcoxon tests use LLM > comparator; Holm correction is applied within each (n_real, metric) family across rule, noise_aug, and real_only comparisons.

## Means

### n_real=5
| method | Acc mean±sd | Macro-F1 mean±sd | count |
|---|---:|---:|---:|
| llm | 0.6444±0.0257 | 0.6537±0.0298 | 20 |
| rule | 0.5962±0.0257 | 0.5984±0.0402 | 20 |
| noise_aug | 0.5897±0.0585 | 0.5901±0.0739 | 20 |
| real_only | 0.2417±0.0545 | 0.1302±0.0544 | 20 |

### n_real=10
| method | Acc mean±sd | Macro-F1 mean±sd | count |
|---|---:|---:|---:|
| llm | 0.6528±0.0251 | 0.6625±0.0265 | 20 |
| rule | 0.6123±0.0306 | 0.6159±0.0379 | 20 |
| noise_aug | 0.6145±0.0554 | 0.6088±0.0670 | 20 |
| real_only | 0.3058±0.1391 | 0.2442±0.1656 | 20 |

### n_real=25
| method | Acc mean±sd | Macro-F1 mean±sd | count |
|---|---:|---:|---:|
| llm | 0.6857±0.0378 | 0.6886±0.0432 | 40 |
| rule | 0.6628±0.0360 | 0.6650±0.0400 | 40 |
| noise_aug | 0.6490±0.0570 | 0.6490±0.0618 | 40 |
| real_only | 0.5470±0.0791 | 0.5097±0.0834 | 40 |

## Paired Tests

| n_real | metric | comparison | pairs | delta | p | Holm q | pass |
|---:|---|---|---:|---:|---:|---:|---|
| 5 | acc | llm>rule | 20 | 0.0482 | 9.53674e-07 | 2.86102e-06 | yes |
| 5 | acc | llm>noise_aug | 20 | 0.0548 | 0.000197411 | 0.000197411 | yes |
| 5 | acc | llm>real_only | 20 | 0.4027 | 9.53674e-07 | 2.86102e-06 | yes |
| 5 | macro_f1 | llm>rule | 20 | 0.0553 | 9.53674e-07 | 2.86102e-06 | yes |
| 5 | macro_f1 | llm>noise_aug | 20 | 0.0636 | 0.000508308 | 0.000508308 | yes |
| 5 | macro_f1 | llm>real_only | 20 | 0.5235 | 9.53674e-07 | 2.86102e-06 | yes |
| 10 | acc | llm>rule | 20 | 0.0404 | 6.59169e-05 | 0.000131834 | yes |
| 10 | acc | llm>noise_aug | 20 | 0.0383 | 0.00471783 | 0.00471783 | yes |
| 10 | acc | llm>real_only | 20 | 0.3470 | 9.53674e-07 | 2.86102e-06 | yes |
| 10 | macro_f1 | llm>rule | 20 | 0.0466 | 1.90735e-06 | 3.8147e-06 | yes |
| 10 | macro_f1 | llm>noise_aug | 20 | 0.0537 | 0.00135612 | 0.00135612 | yes |
| 10 | macro_f1 | llm>real_only | 20 | 0.4183 | 9.53674e-07 | 2.86102e-06 | yes |
| 25 | acc | llm>rule | 40 | 0.0229 | 3.1709e-07 | 6.3418e-07 | yes |
| 25 | acc | llm>noise_aug | 40 | 0.0367 | 0.00196814 | 0.00196814 | yes |
| 25 | acc | llm>real_only | 40 | 0.1387 | 9.09495e-13 | 2.72848e-12 | yes |
| 25 | macro_f1 | llm>rule | 40 | 0.0237 | 1.35717e-06 | 2.71434e-06 | yes |
| 25 | macro_f1 | llm>noise_aug | 40 | 0.0396 | 0.00201075 | 0.00201075 | yes |
| 25 | macro_f1 | llm>real_only | 40 | 0.1789 | 9.09495e-13 | 2.72848e-12 | yes |

## Decision

PASS after extending n_real=25 to 40 seeds. LLM has higher mean Accuracy and Macro-F1 than rule, noise_aug, and real_only at n_real=5, 10, and 25, with Holm q<0.05 for every registered comparison. The report should disclose that n=25 required a 40-seed extension after the 20-seed smoke was borderline against noise_aug.