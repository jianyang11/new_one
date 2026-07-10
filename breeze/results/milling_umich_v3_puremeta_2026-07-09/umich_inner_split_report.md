# umich Inner Validation Split

- Source train NPZ: `proc/milling_umich_v3_puremeta_train.npz`
- Split unit: case/run source unit, never random windows.
- Seed: `20260708`
- Validation fraction by class: `0.2`
- Balance target: `windows`
- inner_train window counts: {'unworn': 74, 'worn': 93}
- inner_train unit counts: {'unworn': 4, 'worn': 6}
- inner_val window counts: {'unworn': 17, 'worn': 24}
- inner_val unit counts: {'unworn': 2, 'worn': 1}
- UMich pure exemplar NPZ: `proc/milling_umich_v3_puremeta_inner_train_pure_exemplar.npz`
- UMich pure exemplar definition: inner_train only; unworn + passed_visual_inspection=yes; worn + passed_visual_inspection=no
- UMich pure exemplar window counts: {'worn': 24, 'unworn': 68}
- UMich pure exemplar units: ['experiment_09', 'experiment_10', 'experiment_11', 'experiment_12', 'experiment_17']
