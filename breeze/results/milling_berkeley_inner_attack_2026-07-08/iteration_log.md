# Berkeley Milling Inner-Val Attack Log

## Iteration 1: Current Pool Diagnosis

- API calls: 0.
- Result: current held-out-smoke LLM pool is only diagnostic and was built before the inner split.
- Main issue: synthetic LLM/rule pools placed most channel energy in `smcAC`, while inner-train real data places most process energy in `smcDC`.
- Decision: renderer must preserve process-signal DC offsets and channel-level dynamic scale.

## Iteration 2: Mean/Std Renderer

- API calls: 0.
- Code change: `milling_generation.py` now separates channel mean/DC offset from dynamic standard deviation. Real exemplars provide PSD/phase background; recipe multipliers control mean, std, harmonics, trend, and correlation.
- Smoke: rule pool with inner-train calibration reached `sharp=15, worn=15, severe=15` in 15 slots. Previous rule smoke had `sharp=0`.
- Pool rebuild: rule `100/class`, random open-loop `40/class`, LLM rescreen `sharp=60, worn=70, severe=40`.
- Inner-val 5-seed summary at `n_syn=20/class`: LLM beats `noise_aug` and `random_open_loop`, but remains tied/slightly below `rule`.

## Iteration 3: Fresh Inner-Train LLM Smoke

- API calls: 15; cumulative API usage updated to 881/3000.
- Prompt change: added train-only class-order hints for total RMS and AE-channel TPF ratios; no held-out test data used.
- Pool: `sharp=25, worn=25, severe=25`, accepted slots `15/15`.
- Inner-val result: fresh LLM still does not beat rule; n=5 and n=10 remain slightly below or tied.

## Iteration 4: Budget Sweep

- API calls: 0.
- LLM pool: combined rescreen + fresh (`sharp=85, worn=95, severe=65`).
- Budgets: `n_syn=10/20/40`, 5 seeds, n_real=2/5/10.
- Result: LLM is consistently above `noise_aug` and `random_open_loop`, but still not above rule. Best budget is `n_syn=20/class` or `40/class`; `n_syn=10` is unstable and underperforms at n=10.
- Decision: do not run formal held-out test. Next Berkeley work must create an LLM-only advantage over the rule recipe, not just improve renderer quality shared by all recipe sources.

## Iteration 5: Step-0 Gap Diagnosis Refresh

- API calls: 0.
- Added report: `berkeley_gap_diagnosis.md`.
- Re-ran zero-API diagnostics for `llm_v4_contrastive` and `llm_v5_proto` against inner-train only.
- Finding: v4 is the better base; v5 worsens PSD-W1 and channel-correlation distance. The downstream weak point is the `worn` class. LLM and rule have nearly identical confusion geometry; noise_aug preserves a stronger worn decision region at n=10.

## Iteration 6: Per-Channel Exemplar + Per-Band EQ

- API calls: 0.
- Code changes:
  - `milling_generation.py` now supports train-only per-class/channel band fractions and recipe-controlled `band_eq_strength`.
  - Added `rerender_milling_llm_eq_pool.py` for zero-API rerendering of accepted LLM compact recipes.
- Pools:
  - `v6_eq_keep`: 30/class.
  - `v6_eq_coherent`: 30/class.
- Inner-val 10-seed result at `n_syn=20/class`: improved over old v4/v5 and above noise_aug, but still below rule in all six Acc/Macro-F1 checks. Best v6 coherent means: n=2 Acc/F1 0.5668/0.5414; n=5 0.5880/0.5796; n=10 0.5754/0.5652. Rule means: n=2 0.5690/0.5459; n=5 0.5998/0.5935; n=10 0.5783/0.5698.

## Iteration 7: Class-Ordering / Prototype Repair

- API calls: 0.
- Added `high_margin_coherent` template policy, selecting train-only high-margin class exemplars.
- Pool: `v7_ordered_highmargin_eq`, 120/class.
- Finding: this did not fix severe-class prototype placement. Severe positive-margin counts remained low under train-only class-prototype distance, so this policy was not promoted.
- EQ strength scan (`0.50`, `0.75`, `1.00`) did not beat rule at `n_syn=20/class`.

## Iteration 8: Exemplar-Grounded Mixed Background

- API calls: 0.
- Added `full_train_margin` template policy: use full inner-train real backgrounds ranked by train-only class-prototype margin, then overlay LLM recipe wear features and re-verify.
- Pool: `v8_fulltrain_margin_eq`, counts sharp=117, worn=119, severe=57.
- Diagnostics: mean PSD-W1=3.6593 and mean corr Frobenius delta=0.3179, both close to or better than rule on structure.
- Inner-val scan:
  - `n_syn=10`: passed 2/6 checks.
  - `n_syn=20`: passed 0/6 checks.
  - `n_syn=40`: passed 0/6 checks.
- Decision: still not eligible for preregistration or formal held-out testing.

## Iteration 9: Repair Prompt Smoke

- API calls: 15; cumulative API usage updated to 914/3000.
- Prompt change: added LLM-only repair constraints on top of the v4 base: preserve per-band EQ/background gains, keep `worn` intermediate but separable, prevent `severe` collapsing into `worn`, and avoid using `smcDC` high-frequency AC as the main wear cue.
- Raw pool: accepted slots `15/15`, raw kept counts `sharp=25, worn=25, severe=25`.
- Raw diagnostics were worse than the EQ rerenders, so the accepted recipes were rerendered through train-only coherent exemplar backgrounds and per-band EQ.
- Pool promoted for downstream: `v9_repair_eq_coherent`, `100/class`.
- Inner-val scan:
  - `n_syn=10`: passed 2/6 checks.
  - `n_syn=20`: passed 0/6 checks.
  - `n_syn=40`: passed 0/6 checks.
- Decision: repair prompt improved the low-shot n=2 edge but did not meet the 5/6 preregistration gate.

## Iteration 10: Combined v6/v8/v9 Pool

- API calls: 0.
- Pool: `v10_combined_v6_v8_v9`, combining coherent EQ, full-train-margin EQ, and repair-EQ candidates; counts `sharp=337, worn=339, severe=277`.
- Added missing inner-val summary/gate CSVs from the existing raw downstream files:
  - `berkeley_v10_inner_val_scan_summary.csv`
  - `berkeley_v10_inner_val_gate_table.csv`
- Inner-val scan:
  - `n_syn=10`: passed 1/6 checks.
  - `n_syn=20`: passed 0/6 checks.
  - `n_syn=40`: passed 0/6 checks.
- Decision: pool concatenation did not create a stable LLM advantage over rule.

## Iteration 11: Repair Prompt Supplement

- API calls: 15; cumulative API usage updated to 929/3000.
- Same repair prompt and rate limit. The raw repair run now has total accepted slots `30/30`, raw kept counts `sharp=50, worn=50, severe=50`.
- Rerendered pool: `v11_repair_eq_coherent_30slots`, `200/class`.
- Inner-val scan:
  - `n_syn=10`: passed 2/6 checks.
  - `n_syn=20`: passed 0/6 checks.
  - `n_syn=40`: passed 0/6 checks.
- Best close result: at `n_syn=40`, n=2 nearly matched rule (`Acc 0.59838` vs `0.60108`, `Macro-F1 0.59772` vs `0.60161`), but still failed both rule comparisons.
- Decision: increasing the repair pool did not pass the formal inner-val threshold.

## Iteration 12: Prototype-Admitted Combined Pool

- API calls: 0.
- Pool: `v12_prototype_admitted`, formed by combining v6/v8/v11 candidates and admitting the top `160/class` by train-only class-prototype margin.
- This is a train-only verifier soft gate; no inner-val metrics were used for admission.
- Inner-val scan:
  - `n_syn=10`: passed 0/6 checks.
  - `n_syn=20`: passed 0/6 checks.
  - `n_syn=40`: passed 0/6 checks.
- Decision: train-prototype admission reduced diversity in a way that did not improve downstream generalization.

## Iteration 13: Final Gate Decision

- API calls: 0.
- Steps 1-4 were exhausted under the requested route: per-channel exemplar/EQ, class-order constraints, exemplar-grounded mixed backgrounds, repair LLM prompt, pool combination, prototype admission, and `n_syn in {10,20,40}` scans with 10 seeds.
- Best candidate by gate count was the historical v7 scan at 3/6; final repair/prototype families reached at most 2/6. All remained below the required 5/6.
- Formal preregistration was not written, and the formal 40-seed held-out Berkeley test was not run.
- Stop condition: report full attack log, inner-val curves, and API usage for user decision.
