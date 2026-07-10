# UMich v4 Learnability Audit

## Scope

- Source audit NPZ: `proc/milling_umich_v4_stage_multi_train.npz`
- Clean inner-train NPZ: `proc/milling_umich_v4_stage_multi_clean_inner_train.npz`
- Clean inner-val NPZ: `proc/milling_umich_v4_stage_multi_clean_inner_val.npz`
- No formal held-out test split is read.

## Label Quadrants

- Experiment-level quadrants: `{'clean_unworn': 4, 'ambiguous_unworn_missing_visual': 2, 'clean_worn': 2, 'ambiguous_worn_pass': 4, 'ambiguous_worn_missing_visual': 1}`
- Active-stage window quadrants: `{'clean_unworn': 73, 'ambiguous_unworn_missing_visual': 7, 'clean_worn': 19, 'ambiguous_worn_pass': 82, 'ambiguous_worn_missing_visual': 3}`
- All stage-contiguous windows before active-stage filter: `260`
- Active-stage windows after cutting-only filter: `184`
- Active-stage clean supervised windows: `92`
- Non-active or ambiguous windows removed before clean supervised learning: `168`

## Diagnostic Baselines

| baseline | Acc | Macro-F1 | F1 unworn | F1 worn |
|---|---:|---:|---:|---:|
| metadata_only | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| stage_only | 0.4500 | 0.4486 | 0.4762 | 0.4211 |
| signal_feature_only | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Interpretation rule: if metadata-only or stage-only is comparable to signal-only, the split is confounded and must not proceed directly to synthetic formal testing.
