# Machine-Tool Private Dataset Experiment Report

Date: 2026-07-04

Workspace: `/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2`

Python: `breeze/.venv-breeze/bin/python`

## Status

Local dataset documentation in `sci_llm/论文全文.md` describes the private
machine-tool dataset as a CNC machining dataset collected with an NI acquisition
card, four synchronous channels, and three operating states: normal machining,
lead-screw anomaly, and base imbalance. The local CSV file prefixes identify
classes only as `1`, `2`, and `3`, and the documentation found so far does not
unambiguously map those prefixes to the three physical state names. This report
therefore keeps anonymous labels `MT-1`, `MT-2`, and `MT-3`.

No audited machine-tool synthetic pool exists yet. The downstream experiment
below is a real-only baseline; no BREEZE augmentation result is claimed for the
private dataset.

## Data Schema

Source loader:
- `breeze/src/data_mt.py`
- `breeze/src/mt_verifier.py`

Channels:
- `X`
- `Y`
- `Z`
- `Current`

Acquisition metadata found locally:
- acquisition hardware: NI data acquisition card with four synchronous analog
  input channels
- sensing: triaxial vibration plus Hall-effect current measurement for spindle
  load
- acquisition sampling rate: 4000 Hz
- documented source segmentation: 4096-point windows with 50% overlap

Windowing:
- BREEZE experiment window length: 2048 samples (0.512 s at 4000 Hz)
- BREEZE experiment stride: 1024 samples (0.256 s at 4000 Hz)
- train files per class: `1`, `2`, `4`, `5`, `10`
- test files per class: `7`, `8`

Processed split sizes:

| split | class | windows | shape |
|---|---:|---:|---|
| train | MT-1 | 675 | `(n, 4, 2048)` |
| train | MT-2 | 383 | `(n, 4, 2048)` |
| train | MT-3 | 679 | `(n, 4, 2048)` |
| test | MT-1 | 166 | `(n, 4, 2048)` |
| test | MT-2 | 166 | `(n, 4, 2048)` |
| test | MT-3 | 154 | `(n, 4, 2048)` |

## Machine-Tool Verifier

Implementation:
- `breeze/src/mt_verifier.py`

Outputs:
- calibration: `breeze/runs/mt_verifier_c90.json`
- pass-rate summary: `breeze/results/mt_verifier_real_pass.csv`
- per-window details: `breeze/runs/mt_verifier_real_details.csv`

Design constraints:
- Uses only the machine-tool train split for calibration.
- Uses no PU bearing kinematics, BPFO/BPFI, or envelope-fault-frequency gate.
- Uses normalized frequency for verifier gates because machine geometry,
  spindle speed, and state-prefix mapping are not available in the audited
  workspace metadata; the 4000 Hz sampling rate is used only for dataset and
  window-duration reporting.
- Gates are training-free: time statistics, channel energy ratios, channel
  correlation structure, overlapping normalized PSD bands, and PSD-CDF W1.
- Gate coverage uses `coverage^(1/3) = 0.965489` for a nominal joint target
  around c90.

Full real-window pass rates:

| split | class | n | pass rate | fail stats | fail soft spectrum | fail PSD-W1 |
|---|---:|---:|---:|---:|---:|---:|
| train | MT-1 | 675 | 0.9585 | 4 | 2 | 25 |
| train | MT-2 | 383 | 0.9530 | 2 | 2 | 16 |
| train | MT-3 | 679 | 0.9381 | 4 | 4 | 39 |
| test | MT-1 | 166 | 0.7590 | 38 | 5 | 34 |
| test | MT-2 | 166 | 0.9337 | 0 | 5 | 11 |
| test | MT-3 | 154 | 0.7727 | 0 | 0 | 35 |

File-level verifier pass rates:

| split | file | pass rate |
|---|---:|---:|
| train | 1_1 | 0.9686 |
| train | 1_10 | 0.7887 |
| train | 1_2 | 0.9771 |
| train | 1_4 | 0.9739 |
| train | 1_5 | 1.0000 |
| train | 2_1 | 0.8254 |
| train | 2_10 | 1.0000 |
| train | 2_2 | 1.0000 |
| train | 2_4 | 0.9577 |
| train | 2_5 | 0.9437 |
| train | 3_1 | 0.9701 |
| train | 3_10 | 0.7910 |
| train | 3_2 | 0.9289 |
| train | 3_4 | 0.9652 |
| train | 3_5 | 0.9664 |
| test | 1_7 | 0.5422 |
| test | 1_8 | 0.9759 |
| test | 2_7 | 0.9157 |
| test | 2_8 | 0.9518 |
| test | 3_7 | 0.8101 |
| test | 3_8 | 0.7333 |

Interpretation boundary:
- The verifier calibrates a plausible train-supported admissible region for the
  private dataset.
- MT-1 and MT-3 show test-file distribution shift under the same verifier,
  especially `1_7`. This should be discussed as a limitation or real industrial
  variability, not hidden.

## Downstream Real-Only Baseline

Implementation:
- `breeze/src/eval_mt_real.py`

Output:
- `breeze/results/mt_real_only_eval.csv`

Protocol:
- SimpleCNN with `in_ch=4`, `num_classes=3`
- real-only few-shot train windows per class: 10, 25, 50
- seeds: 8
- epochs: 60
- test split: held-out files `7` and `8`
- metrics: accuracy, macro-F1, per-class F1, confusion matrix

Aggregate results:

| n_real/class | rows | accuracy mean | accuracy std | macro-F1 mean | macro-F1 std | F1 MT-1 | F1 MT-2 | F1 MT-3 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 8 | 0.3431 | 0.0321 | 0.3368 | 0.0318 | 0.3914 | 0.3402 | 0.2788 |
| 25 | 8 | 0.4964 | 0.0566 | 0.4897 | 0.0530 | 0.4792 | 0.4781 | 0.5119 |
| 50 | 8 | 0.7006 | 0.0626 | 0.7021 | 0.0632 | 0.6362 | 0.6750 | 0.7951 |

Across all 24 runs, summed confusion matrix:

```text
[[1956 1486  542]
 [ 988 2188  808]
 [ 845 1007 1844]]
```

## Current Paper-Use Boundary

Safe claims:
- BREEZE's verifier design is portable to a private 4-channel machine-tool
  schema after replacing bearing-specific gates with train-calibrated generic
  signal constraints.
- The private dataset has a real-only baseline that improves with larger
  few-shot support, reaching `0.7006 ± 0.0626` accuracy at 50 real windows per
  class.
- The verifier exposes distribution shift in specific held-out test files.

Unsafe claims:
- Do not claim machine-tool BREEZE augmentation improvement; no audited
  synthetic pool has been generated or screened for this dataset.
- Do not call `MT-1/MT-2/MT-3` by physical fault names until the user provides
  the mapping.
- Do not reuse PU BPFO/BPFI/envelope-fault-frequency conclusions for this
  dataset without machine-tool geometry and speed metadata.
