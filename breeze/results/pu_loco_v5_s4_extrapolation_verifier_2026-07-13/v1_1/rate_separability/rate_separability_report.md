# S4 source-only rate/harmonic/modulation separability

## Boundary

only config.SPLIT train-bearing PU windows are loaded; pseudo-held-out and formal held-out windows are unread

## Interpretation rule

A feature is a candidate for a new strict source-only physical gate only if its true-class q10 exceeds both wrong-class and white-noise q90. This diagnostic does not choose a threshold or change S4 admission.

## Source distribution gaps

| asserted class | feature | q10 true - q90 wrong | q10 true - q90 white | candidate separation |
|---|---|---:|---:|---|
| OR | fund_prominence | -3.386351 | -1.014762 | no |
| OR | rate_contrast | -0.417699 | -0.425947 | no |
| OR | harm2_prominence | -3.456772 | -0.886095 | no |
| OR | shaft_prominence | -4.647515 | -0.950319 | no |
| OR | ir_sideband_prominence | 0.000000 | 0.000000 | no |
| IR | fund_prominence | -1.192175 | -1.174635 | no |
| IR | rate_contrast | -0.659334 | -0.785002 | no |
| IR | harm2_prominence | -1.241495 | -1.015023 | no |
| IR | shaft_prominence | -1.336341 | -1.038397 | no |
| IR | ir_sideband_prominence | -1.799231 | -0.786064 | no |
