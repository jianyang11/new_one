# umich Inner Validation Split

- Source train NPZ: `proc/milling_umich_v4_stage_layer1up_train.npz`
- Split unit: case/run source unit, never random windows.
- Seed: `20260708`
- Validation fraction by class: `0.2`
- Balance target: `windows`
- inner_train window counts: {'unworn': 19, 'worn': 17}
- inner_train unit counts: {'unworn': 5, 'worn': 5}
- inner_val window counts: {'worn': 4, 'unworn': 5}
- inner_val unit counts: {'worn': 2, 'unworn': 1}
