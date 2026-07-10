# Berkeley v2 Binary Formal Gate Report

Status: FAILED.
Registered comparisons passed: 15/18.

## Summary Means

| method | n_real | rows | mean_acc | std_acc | mean_macro_f1 | std_macro_f1 |
| --- | --- | --- | --- | --- | --- | --- |
| llm | 2 | 40 | 0.785992 | 0.020717 | 0.777772 | 0.018362 |
| noise_aug | 2 | 40 | 0.695355 | 0.109671 | 0.675013 | 0.1119 |
| random_open_loop | 2 | 40 | 0.52419 | 0.147368 | 0.45037 | 0.127144 |
| real_only | 2 | 40 | 0.68023 | 0.091063 | 0.641382 | 0.101007 |
| rule | 2 | 40 | 0.783325 | 0.021797 | 0.775707 | 0.019333 |
| llm | 5 | 40 | 0.78394 | 0.029507 | 0.773228 | 0.031445 |
| noise_aug | 5 | 40 | 0.723572 | 0.06795 | 0.709305 | 0.070551 |
| random_open_loop | 5 | 40 | 0.61448 | 0.096695 | 0.51378 | 0.105786 |
| real_only | 5 | 40 | 0.727942 | 0.064254 | 0.697758 | 0.080037 |
| rule | 5 | 40 | 0.779262 | 0.030999 | 0.76916 | 0.032267 |
| llm | 10 | 40 | 0.78673 | 0.024424 | 0.776585 | 0.023705 |
| noise_aug | 10 | 40 | 0.74957 | 0.048849 | 0.734123 | 0.055623 |
| random_open_loop | 10 | 40 | 0.65426 | 0.061911 | 0.57197 | 0.081126 |
| real_only | 10 | 40 | 0.74547 | 0.053898 | 0.721857 | 0.071472 |
| rule | 10 | 40 | 0.786183 | 0.023701 | 0.776382 | 0.022668 |

## Wilcoxon/Holm

| n_real | metric | comparison | n_pairs | mean_llm | mean_comparator | mean_delta | median_delta | p_raw | statistic | holm_q | pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | Acc | llm>noise_aug | 40 | 0.7859925 | 0.695355 | 0.0906375 | 0.0635 | 0.0 | 792.0 | 0.0 | True |
| 2 | Acc | llm>rule | 40 | 0.7859925 | 0.783325 | 0.0026675 | 0.0015 | 0.04625562 | 374.5 | 0.04625562 | True |
| 2 | Acc | llm>random_open_loop | 40 | 0.7859925 | 0.52419 | 0.2618025 | 0.1857 | 2e-08 | 820.0 | 4e-08 | True |
| 2 | Macro-F1 | llm>noise_aug | 40 | 0.7777725 | 0.6750125 | 0.10276 | 0.0724 | 0.0 | 801.0 | 0.0 | True |
| 2 | Macro-F1 | llm>rule | 40 | 0.7777725 | 0.7757075 | 0.002065 | 0.0012 | 0.10295773 | 413.5 | 0.10295773 | False |
| 2 | Macro-F1 | llm>random_open_loop | 40 | 0.7777725 | 0.45037 | 0.3274025 | 0.3245 | 0.0 | 820.0 | 0.0 | True |
| 5 | Acc | llm>noise_aug | 40 | 0.78394 | 0.7235725 | 0.0603675 | 0.0472 | 8.5e-07 | 733.0 | 1.7e-06 | True |
| 5 | Acc | llm>rule | 40 | 0.78394 | 0.7792625 | 0.0046775 | 0.0031 | 0.0001631 | 507.5 | 0.0001631 | True |
| 5 | Acc | llm>random_open_loop | 40 | 0.78394 | 0.61448 | 0.16946 | 0.14475 | 2e-08 | 820.0 | 5e-08 | True |
| 5 | Macro-F1 | llm>noise_aug | 40 | 0.7732275 | 0.709305 | 0.0639225 | 0.0565 | 5.7e-07 | 772.0 | 1.14e-06 | True |
| 5 | Macro-F1 | llm>rule | 40 | 0.7732275 | 0.76916 | 0.0040675 | 0.0029 | 0.00035919 | 521.5 | 0.00035919 | True |
| 5 | Macro-F1 | llm>random_open_loop | 40 | 0.7732275 | 0.51378 | 0.2594475 | 0.2535 | 0.0 | 820.0 | 0.0 | True |
| 10 | Acc | llm>noise_aug | 40 | 0.78673 | 0.74957 | 0.03716 | 0.02715 | 6.7e-07 | 769.5 | 1.35e-06 | True |
| 10 | Acc | llm>rule | 40 | 0.78673 | 0.7861825 | 0.0005475 | 0.00075 | 0.28766457 | 388.5 | 0.28766457 | False |
| 10 | Acc | llm>random_open_loop | 40 | 0.78673 | 0.65426 | 0.13247 | 0.13625 | 2e-08 | 820.0 | 5e-08 | True |
| 10 | Macro-F1 | llm>noise_aug | 40 | 0.776585 | 0.7341225 | 0.0424625 | 0.0281 | 1e-08 | 776.0 | 4e-08 | True |
| 10 | Macro-F1 | llm>rule | 40 | 0.776585 | 0.7763825 | 0.0002025 | 0.0007 | 0.38588633 | 390.5 | 0.38588633 | False |
| 10 | Macro-F1 | llm>random_open_loop | 40 | 0.776585 | 0.57197 | 0.204615 | 0.2005 | 2e-08 | 820.0 | 4e-08 | True |

## Protocol

- Formal held-out test executed once after preregistration.
- n_syn=20/class, n_real={2,5,10}, 40 seeds, CNN epochs=20.
- Comparisons are one-sided paired Wilcoxon with Holm correction within each (n_real, metric) family.

