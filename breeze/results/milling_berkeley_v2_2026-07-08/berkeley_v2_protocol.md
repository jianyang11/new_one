# Berkeley Milling v2 Protocol

Date: 2026-07-08 Asia/Shanghai

Status: development protocol, not preregistered formal test.

## Rationale

Berkeley v1 used an internal three-state split: `sharp` for `VB<0.2`, `worn` for `0.2<=VB<=0.45`, and `severe` for `VB>0.45`. The v1 inner-val attack log showed that the middle class was unstable for all synthetic families and controls. This v2 protocol revises the task before any formal held-out Berkeley run.

The revised labels follow the public tool-wear protocol used by the von Hahn / Mechefske codebase:

- `healthy`: `VB < 0.2 mm`
- `degradation`: `0.2 <= VB < 0.7 mm`
- `failure`: `VB >= 0.7 mm`

External references to cite during paper writing:

- `tvhahn/ml-tool-wear`, `data_prep.py`: public code using the `0.2/0.7` three-state definition for the UC Berkeley milling data.
- NASA PCoE / UC Berkeley BEST Lab Milling Data Set: original dataset source; the data include force, vibration, acoustic emission, spindle-motor current, and measured flank wear `VB`.
- ISO 3685 is kept as a tool-life standard background reference only; exact standard text must be checked from an accessible copy before quoting.

## Leakage Boundary

- Label revision is based on external protocol plus Berkeley v1 inner-train/inner-val diagnostics.
- The formal held-out Berkeley test has not been used for prompt, schema, renderer, `n_syn`, `K`, class definition, or stopping decisions.
- The split unit remains case/run. No random window split is introduced.
- All v2 iteration choices must use only `proc/milling_berkeley_v2_inner_train.npz` and `proc/milling_berkeley_v2_inner_val.npz`.

## Frozen v2 Files

- Train: `proc/milling_berkeley_v2_train.npz`
- Test: `proc/milling_berkeley_v2_test.npz`
- Inner train: `proc/milling_berkeley_v2_inner_train.npz`
- Inner val: `proc/milling_berkeley_v2_inner_val.npz`
- Unit audit: `berkeley_v2_inner_split_units.csv`
- Preprocess units: `milling_preprocess_units.csv`
- Dataset spec: `milling_dataset_specs.md`

## Counts

| split | healthy | degradation | failure |
|---|---:|---:|---:|
| train | 629 | 1054 | 153 |
| test | 221 | 374 | 51 |
| inner_train | 510 | 850 | 119 |
| inner_val | 119 | 204 | 34 |

Failure is small but present in both inner and held-out splits. The next step is not formal evaluation; it is inner-val separability smoke.

## Decision Rule

1. Run inner-val smoke for `real_only`, `noise_aug`, `rule`, `random_open_loop`, and zero-API rerendered LLM.
2. Continue the three-class route only if per-class F1 shows no collapsed class; operational continuation signal is mean per-class F1 above `0.4` for every class in the candidate family and controls.
3. If three-class separability fails or failure support is too weak, freeze that result and start a separate binary protocol: `healthy` vs `degraded_or_failure`.
4. Formal held-out testing remains forbidden until an inner-val gate passes and a preregistration document is written.
