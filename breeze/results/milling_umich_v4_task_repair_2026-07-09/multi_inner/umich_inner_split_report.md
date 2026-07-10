# umich Inner Validation Split

- Source train NPZ: `proc/milling_umich_v4_stage_multi_train.npz`
- Split unit: case/run source unit, never random windows.
- Seed: `20260708`
- Validation fraction by class: `0.2`
- Balance target: `windows`
- inner_train window counts: {'unworn': 63, 'worn': 82}
- inner_train unit counts: {'unworn': 5, 'worn': 6}
- inner_val window counts: {'worn': 22, 'unworn': 17}
- inner_val unit counts: {'worn': 1, 'unworn': 1}
