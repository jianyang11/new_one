# Phase-B CWRU Cross-Condition Schedule Report

Generated: 2026-07-06T16:13:59

Split: `train_load0_test_load1`. Synthetic pool: `breeze/runs/phaseB_cwru_within_load0_llm_full_v1_combined/pool.npz`. Rule pool: `breeze/runs/phaseB_cwru_within_load0_rule_pilot_v1/pool.npz`.

Registered schedule: n=5/10 use 38 synthetic samples per class; n=25 uses 20 synthetic samples per class. CNN, 20 epochs, seeds 0-19. Paired one-sided Wilcoxon tests use LLM > comparator; Holm correction is applied within each (n_real, metric) family across rule, noise_aug, and real_only comparisons.

## Means

### n_real=5
| method | Acc mean±sd | Macro-F1 mean±sd | count |
|---|---:|---:|---:|
| llm | 0.6373±0.0227 | 0.6464±0.0247 | 20 |
| rule | 0.5938±0.0282 | 0.5973±0.0360 | 20 |
| noise_aug | 0.5613±0.0547 | 0.5518±0.0717 | 20 |
| real_only | 0.2355±0.0706 | 0.1304±0.0595 | 20 |

### n_real=10
| method | Acc mean±sd | Macro-F1 mean±sd | count |
|---|---:|---:|---:|
| llm | 0.6505±0.0312 | 0.6599±0.0385 | 20 |
| rule | 0.6111±0.0270 | 0.6142±0.0393 | 20 |
| noise_aug | 0.6119±0.0562 | 0.6048±0.0665 | 20 |
| real_only | 0.3070±0.1164 | 0.2276±0.1443 | 20 |

### n_real=25
| method | Acc mean±sd | Macro-F1 mean±sd | count |
|---|---:|---:|---:|
| llm | 0.6943±0.0469 | 0.6955±0.0438 | 20 |
| rule | 0.6670±0.0321 | 0.6641±0.0318 | 20 |
| noise_aug | 0.6635±0.0505 | 0.6607±0.0564 | 20 |
| real_only | 0.5486±0.0746 | 0.5070±0.0742 | 20 |

## Paired Tests

| n_real | metric | comparison | delta | p | Holm q | pass |
|---:|---|---|---:|---:|---:|---|
| 5 | acc | llm>rule | 0.0434 | 4.76837e-06 | 9.53674e-06 | yes |
| 5 | acc | llm>noise_aug | 0.0760 | 0.000157333 | 0.000157333 | yes |
| 5 | acc | llm>real_only | 0.4018 | 9.53674e-07 | 2.86102e-06 | yes |
| 5 | macro_f1 | llm>rule | 0.0492 | 9.53674e-06 | 1.90735e-05 | yes |
| 5 | macro_f1 | llm>noise_aug | 0.0947 | 1.81198e-05 | 1.90735e-05 | yes |
| 5 | macro_f1 | llm>real_only | 0.5161 | 9.53674e-07 | 2.86102e-06 | yes |
| 10 | acc | llm>rule | 0.0394 | 8.12137e-05 | 0.000162427 | yes |
| 10 | acc | llm>noise_aug | 0.0385 | 0.0076561 | 0.0076561 | yes |
| 10 | acc | llm>real_only | 0.3435 | 9.53674e-07 | 2.86102e-06 | yes |
| 10 | macro_f1 | llm>rule | 0.0458 | 1.33514e-05 | 2.67029e-05 | yes |
| 10 | macro_f1 | llm>noise_aug | 0.0551 | 0.00060463 | 0.00060463 | yes |
| 10 | macro_f1 | llm>real_only | 0.4323 | 9.53674e-07 | 2.86102e-06 | yes |
| 25 | acc | llm>rule | 0.0274 | 2.86102e-06 | 8.58307e-06 | yes |
| 25 | acc | llm>noise_aug | 0.0309 | 0.0119472 | 0.0119472 | yes |
| 25 | acc | llm>real_only | 0.1457 | 4.76837e-06 | 9.53674e-06 | yes |
| 25 | macro_f1 | llm>rule | 0.0314 | 8.13208e-05 | 0.000162642 | yes |
| 25 | macro_f1 | llm>noise_aug | 0.0348 | 0.0147877 | 0.0147877 | yes |
| 25 | macro_f1 | llm>real_only | 0.1885 | 2.86102e-06 | 8.58307e-06 | yes |

## Decision

PASS for this cross-condition smoke: LLM has higher mean Accuracy and Macro-F1 than rule, noise_aug, and real_only at n_real=5, 10, and 25, with Holm q<0.05 for every registered comparison.