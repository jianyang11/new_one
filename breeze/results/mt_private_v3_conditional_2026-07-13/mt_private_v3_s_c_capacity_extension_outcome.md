# Private machine-tool v3 — S-C amendment-3 capacity outcome

## Frozen outcome

The amendment-3 base-only extension formed an exactly balanced S-C pool:

| class | admitted / target |
|---|---:|
| normal machining | 20 / 20 |
| lead-screw anomaly | 20 / 20 |
| base imbalance | 20 / 20 |

At the previous 98-request boundary, only base imbalance was deficient
(`18/20`). The two predeclared base replacement slots (20 and 21) were both
admitted on their initial requests. The final cumulative ledger therefore
contains 100 counted requests, not the 200-request ceiling. No unused API
authorization was spent.

## Protocol checks

- The target remains 20 admitted samples per class; no normal or lead-screw
  slot was added and no exhausted slot was reopened.
- Each new accepted sample passed the unchanged exact recipe schema,
  deterministic renderer, three-expansion rule, class-identity certificate,
  verifier, duplicate check, and diversity rule.
- No rejected waveform was repaired or post-processed.
- Formal file IDs `7` and `8` read: **0**.

The S-C pool is now eligible for the predeclared inner downstream comparison
only. It has no downstream metric or formal result at this checkpoint.
