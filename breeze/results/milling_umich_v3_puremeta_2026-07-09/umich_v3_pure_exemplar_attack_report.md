# UMich CNC v3 Pure-Exemplar Attack Report

Date: 2026-07-09

## Decision

UMich is still a binary task: `unworn` vs `worn`. The downstream labels are
from `tool_condition`. The v3 change only affects the calibration/exemplar
pool used by LLM and synthetic generation.

The pure-exemplar strategy did not pass the inner-validation gate. Best result
was `1/6` gate at `n_syn=10`, so no preregistration was written and no formal
held-out test was run.

## Pure-Exemplar Definition

Source metadata: `data/archive/train.csv`.

Pure training exemplars are filtered from `inner_train` only:

- Absolute pristine: `tool_condition == unworn` and
  `passed_visual_inspection == yes`.
- Absolute worn: `tool_condition == worn` and
  `passed_visual_inspection == no`.

The field `machining_finalized` is retained in NPZ metadata for audit. In the
actual pure-exemplar output, all retained windows have `machining_finalized=yes`.

Held-out test experiments are not used for exemplar selection, even when they
match the pure definition. In particular, experiments `1`, `2`, `6`, and `8`
remain outside this inner-loop calibration pool.

## Generated Data

New preprocessing artifacts:

- `proc/milling_umich_v3_puremeta_train.npz`
- `proc/milling_umich_v3_puremeta_test.npz`
- `proc/milling_umich_v3_puremeta_inner_train.npz`
- `proc/milling_umich_v3_puremeta_inner_val.npz`
- `proc/milling_umich_v3_puremeta_inner_train_pure_exemplar.npz`

Pure-exemplar counts:

- `unworn=68`
- `worn=24`

Pure-exemplar source units:

- pristine/unworn: `experiment_11`, `experiment_12`, `experiment_17`
- worn: `experiment_09`, `experiment_10`

## Controls

Synthetic control pools calibrated on pure exemplars:

- rule: `accepted_slots=26/40`, counts `unworn=80`, `worn=40`
- random_open_loop: `accepted_slots=40/40`, counts `unworn=100`, `worn=100`

Control summary is frozen in:

- `umich_v3_pure_controls_summary.csv`

At `n_syn=10`, controls were:

| n_real | method | Accuracy | Macro-F1 |
|---:|---|---:|---:|
| 2 | noise_aug | 0.4683 | 0.4110 |
| 2 | random_open_loop | 0.4366 | 0.3965 |
| 2 | rule | 0.4049 | 0.3467 |
| 5 | noise_aug | 0.4951 | 0.4393 |
| 5 | random_open_loop | 0.4366 | 0.3784 |
| 5 | rule | 0.4073 | 0.3241 |
| 10 | noise_aug | 0.4463 | 0.4031 |
| 10 | random_open_loop | 0.4122 | 0.3699 |
| 10 | rule | 0.2903 | 0.2656 |

## LLM Smoke

LLM smoke calibrated on the pure-exemplar NPZ:

- API requests: `30`
- accepted slots: `15/30`
- accepted windows: `unworn=72`, `worn=0`

Failure diagnosis for `worn`:

- main failed gates: `structure_axis`, `psd_w1`
- interpretation: the pure worn support is small and narrow; phase-randomized
  spectral surrogates leave the training-fold support even though rule
  real-exemplar backgrounds can pass.

## Zero-API Rescue Check

A zero-API check rerendered the existing compact LLM recipes with
`real_exemplar` background for `worn`, leaving other multipliers unchanged.
This is an inner-val diagnostic only.

Rescue pool:

- accepted slots: `21`
- accepted windows: `unworn=71`, `worn=18`

Because `worn=18`, only `n_syn=10` was evaluated.

## Inner-Val Gate

Best LLM rescue at `n_syn=10`:

| n_real | metric | LLM | noise_aug | rule | random_open_loop | pass |
|---:|---|---:|---:|---:|---:|---|
| 2 | Accuracy | 0.4585 | 0.4683 | 0.4049 | 0.4366 | no |
| 2 | Macro-F1 | 0.3200 | 0.4110 | 0.3467 | 0.3965 | no |
| 5 | Accuracy | 0.5073 | 0.4951 | 0.4073 | 0.4366 | yes |
| 5 | Macro-F1 | 0.3486 | 0.4393 | 0.3241 | 0.3784 | no |
| 10 | Accuracy | 0.3098 | 0.4463 | 0.2903 | 0.4122 | no |
| 10 | Macro-F1 | 0.2659 | 0.4031 | 0.2656 | 0.3699 | no |

Final gate: `1/6`, below the required `5/6`.

Per-class failure remained:

- `n_real=2`: `unworn F1=0.0416`, `worn F1=0.5983`
- `n_real=5`: `unworn F1=0.0511`, `worn F1=0.6462`
- `n_real=10`: `unworn F1=0.1395`, `worn F1=0.3922`

The LLM pool still drives a worn-biased boundary and does not recover balanced
Macro-F1.

## API Usage

Starting cumulative before v3 pure-exemplar smoke: `990`.

- v3 pure-exemplar LLM smoke: `30` requests.
- New cumulative: `1020/3000`.

The API key was not written to disk.

## Frozen Outputs

- `umich_v3_pure_controls_summary.csv`
- `umich_v3_pure_llm_rescue_summary.csv`
- `umich_v3_pure_llm_rescue_gate.csv`
- `downstream_controls_nsyn10_10seed/`
- `downstream_controls_nsyn20_10seed/`
- `downstream_controls_nsyn40_10seed/`
- `downstream_llm_realbg_rescue_nsyn10_10seed/`

No formal held-out UMich test exists for v3.
