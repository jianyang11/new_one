# API Budget Estimate at 2 s Serial Throttle

Generated: 2026-07-07 Asia/Shanghai.

## Current Counter

- Total API cap: 3000 requests after the 2026-07-08 user budget patch.
- Cumulative requests already used: 866.
- Remaining requests: 2134.
- Local throttling requirement: serial requests with a minimum 2.0 s interval.
- Minimum wall-clock for all remaining requests: 2134 x 2.0 s = 4268 s = 71.1 min, before network latency, retries, rendering, verification, and checkpoint I/O.

## 2026-07-08 Revised Allocation

| block | reserved API requests | note |
|---|---:|---|
| Milling attack, Berkeley + UMich | <=600 | Use inner-train/inner-val only for iteration; formal held-out test is one-shot after inner-val gate. |
| XJTU-SY | <=250 | Wait until download is complete and split/specification are frozen. |
| PU LOCO v2 supplemental generation | <=50 | Zero-API condition-aware rerender first; spend only if preregistered pool target cannot be reached. |
| Phase E ablations | <=400 | Run after dataset lines close. |

## Per-Block Estimate

| block | planned API requests | throttle-only minimum | execution note |
|---|---:|---:|---|
| PU LOCO LLM small smoke | <=30 | <=1.0 min | Run before any fold-level scaling; sleep about 6-8 min before checking because rendering, verifier, and possible retries add overhead. |
| PU LOCO fold pools, budget-disciplined plan | 168-240 | 5.6-8.0 min | For four held-out conditions, enough to target downstream n_syn=20/class with class-balanced accepted slots under the >=30% smoke acceptance gate. |
| PU LOCO fold pools, maximum 100 recipes/class/fold | 1200 | 40.0 min | This alone would leave only 163 requests for XJTU and milling, so it is not compatible with the remaining 1363-request budget unless the user explicitly reallocates budget. |
| Berkeley/NASA milling smoke + full pool | <=330 | <=11.0 min | 30-call smoke, then at most 100 recipes/class for 3 VB classes if real-only is not saturated and verifier smoke passes. |
| UMich CNC smoke + full pool | <=230 | <=7.7 min | 30-call smoke, then at most 100 recipes/class for 2 classes if real-only is not saturated and verifier smoke passes. |
| XJTU-SY smoke + provisional full pool | <=330 | <=11.0 min | Deferred until the user download is complete and split/specification are frozen; provisional estimate assumes 3 classes with <=100 recipes/class. |

## Budget Decision

The budget-disciplined plan uses about 989-1061 additional requests after the current 770 used calls, for a projected cumulative total of 1759-1831/2000 and a remaining buffer of 169-241 requests.

The maximum PU LOCO plan plus Berkeley, UMich, and XJTU would require about 2090 additional requests, projecting 2727/2000 total. That exceeds the hard budget by about 727 requests, so it must not be launched without an explicit budget increase.

For scheduling, use the throttle-only minimum as a lower bound and assume 1.5-2.0x wall-clock for real runs because retries, response latency, rendering, verification, and checkpoint writing are not covered by the 2 s interval.
