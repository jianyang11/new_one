# UMich CNC Milling v2 Attack Report

Date: 2026-07-08

## Decision

UMich CNC is evaluated as a binary classification task: `unworn` vs `worn`.
It is not evaluated with Berkeley labels `sharp/worn/severe`.

The UMich v2 inner-validation attack did not meet the preregistration gate.
The best LLM variant passed only 2 of 6 registered inner-val combinations
(`n_syn=10`, Accuracy at `n_real=2` and `n_real=5`). Macro-F1 failed for all
`n_real` values. Therefore no UMich preregistration was written and the formal
40-seed held-out test was not run.

## Protocol

- Dataset: local UMich/Kaggle CNC data in `data/archive/`.
- Labels: `tool_condition` from `train.csv`, classes `unworn` and `worn`.
- Split unit: experiment-level, not random windows.
- Held-out test experiments: `[1, 2, 6, 7, 8]`.
- Train counts: `unworn=91`, `worn=117`.
- Test counts: `unworn=31`, `worn=27`.
- Inner split: train `unworn=74`, `worn=93`; validation `unworn=17`, `worn=24`.
- Channels: dynamic process-current channels only:
  `X1_CurrentFeedback`, `Y1_CurrentFeedback`, `S1_CurrentFeedback`,
  `X1_OutputCurrent`, `Y1_OutputCurrent`, `S1_OutputCurrent`.
- Excluded channels: `Z1_CurrentFeedback` and `Z1_OutputCurrent`; both were
  constant in the training windows and caused verifier sanity failures.
- Kinematics: no auditable tooth count was found locally, so no TPF cue was
  fabricated. UMich verifier and prompts used process statistics, PSD shape,
  trend, channel energy/correlation, and PSD-W1 style support checks.

Key protocol artifacts:

- `milling_dataset_specs.md`
- `umich_inner_split_report.md`
- `umich_inner_split_units.csv`

## Iteration Log

### 0. Dynamic-channel rebuild

The initial 8-channel UMich preprocessing included constant Z-axis current
channels. Rule generation was rejected by the sanity gate with `constant
channel`. A v2 preprocessing path was added with the six dynamic current
channels above. This is a data-schema correction, not a post-hoc metric
stabilization.

### 1. Real-only and controls

Real-only few-shot inner-val was not saturated. Accuracy and Macro-F1 varied
roughly in the 0.3-0.7 range across seeds, leaving room for augmentation.

Control pools:

- rule: `accepted_slots=39/40`, `n=169`, counts `unworn=84`, `worn=85`.
- random_open_loop: `accepted_slots=40/40`, `n=200`, counts `unworn=100`, `worn=100`.
- noise_aug: no synthetic pool; downstream perturbation baseline.

At `n_syn=20`, control means were:

| n_real | method | Accuracy | Macro-F1 |
|---:|---|---:|---:|
| 2 | noise_aug | 0.4610 | 0.4384 |
| 2 | random_open_loop | 0.4390 | 0.4008 |
| 2 | rule | 0.3415 | 0.3111 |
| 5 | noise_aug | 0.4658 | 0.4444 |
| 5 | random_open_loop | 0.4951 | 0.4374 |
| 5 | rule | 0.3415 | 0.2980 |
| 10 | noise_aug | 0.4341 | 0.4179 |
| 10 | random_open_loop | 0.4024 | 0.3703 |
| 10 | rule | 0.3439 | 0.3121 |

### 2. LLM smoke v1

LLM smoke v1 used the UMich binary prompt with no TPF and real-exemplar
backgrounds.

- API: 30 successful requests.
- Acceptance: `30/30` slots.
- Pool: `n=150`, counts `unworn=75`, `worn=75`.
- Inner-val result: failed all 6 gate combinations at `n_syn=20`.

Diagnosis: accepted LLM samples over-supported the `worn` class. At `n_syn=10`,
`unworn` F1 was only `0.0707`, `0.0929`, `0.1538` for `n_real=2/5/10`, while
`worn` F1 stayed around `0.53-0.58`.

### 3. Zero-API spectral-surrogate rerender

The v1 compact recipes were rerendered with `background_mode=spectral_surrogate`
instead of exact real-exemplar segment reuse. No new API was used.

- Acceptance: `30/30` slots.
- Pool: `n=142`, counts `unworn=73`, `worn=69`.
- Best effect: improved some Accuracy values but still failed every gate.

Best surrogate rerender at `n_syn=10`:

| n_real | Accuracy | Macro-F1 |
|---:|---:|---:|
| 2 | 0.4512 | 0.3496 |
| 5 | 0.4707 | 0.3400 |
| 10 | 0.4147 | 0.3291 |

Macro-F1 remained below noise_aug and random_open_loop.

### 4. LLM smoke v2 repair

The repair prompt added the inner-val diagnosis: previous accepted LLM pools
overpredicted `worn` and collapsed `unworn` F1. It also defaulted UMich
backgrounds to `spectral_surrogate` when no verified harmonic cues exist.

- API: 30 successful responses plus one provider/proxy transport failure,
  counted conservatively in the budget.
- Acceptance: `30/30` slots.
- Pool: `n=143`, counts `unworn=71`, `worn=72`.

Best LLM v2 result was `n_syn=10`:

| n_real | Accuracy | Macro-F1 | unworn F1 | worn F1 |
|---:|---:|---:|---:|---:|
| 2 | 0.4805 | 0.3431 | 0.0501 | 0.6362 |
| 5 | 0.5024 | 0.3615 | 0.0721 | 0.6508 |
| 10 | 0.4122 | 0.3229 | 0.0931 | 0.5527 |

It passed Accuracy against noise_aug, rule, and random_open_loop for `n_real=2`
and `n_real=5`, but Macro-F1 failed in all three shot settings. This indicates
the classifier is still mostly learning a `worn`-biased boundary from the LLM
pool.

## Final Inner-Val Gate

Registered-style gate: for `n_real={2,5,10}` and metrics Accuracy/Macro-F1,
LLM must be at least as good as noise_aug, rule, and random_open_loop in at
least 5 of 6 combinations before preregistration.

Best observed LLM v2 gate:

| n_syn | n_real | metric | LLM | noise_aug | rule | random_open_loop | pass |
|---:|---:|---|---:|---:|---:|---:|---|
| 10 | 2 | Accuracy | 0.4805 | 0.4683 | 0.4049 | 0.4732 | yes |
| 10 | 2 | Macro-F1 | 0.3431 | 0.4110 | 0.3570 | 0.4289 | no |
| 10 | 5 | Accuracy | 0.5024 | 0.4951 | 0.4317 | 0.4732 | yes |
| 10 | 5 | Macro-F1 | 0.3615 | 0.4393 | 0.3686 | 0.4140 | no |
| 10 | 10 | Accuracy | 0.4122 | 0.4463 | 0.3683 | 0.4488 | no |
| 10 | 10 | Macro-F1 | 0.3229 | 0.4031 | 0.3325 | 0.3971 | no |

Final result: `2/6`, below the required `5/6`.

## API Usage

Starting cumulative count before UMich v2: `929`.

- LLM smoke v1: 30 successful requests.
- LLM smoke v2: 30 successful responses.
- One provider/proxy transport failure was counted conservatively as one
  attempted request.

Conservative cumulative after UMich v2: `990/3000`.

The API key was not written to disk.

## Frozen Outputs

- `umich_v2_final_inner_scan_summary.csv`
- `umich_v2_final_inner_gate_table.csv`
- `umich_v2_inner_scan_summary.csv`
- `umich_v2_inner_scan_per_class_f1.csv`
- `umich_v2_inner_surrogate_gate_table.csv`
- `downstream_llm_v2_nsyn10_10seed/`
- `downstream_llm_v2_nsyn20_10seed/`
- `downstream_llm_v2_nsyn40_10seed/`

No formal held-out UMich test exists for this attack, by design.
