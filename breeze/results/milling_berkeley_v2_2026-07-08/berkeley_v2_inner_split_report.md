# berkeley_v2 Inner Validation Split

- Source train NPZ: `proc/milling_berkeley_v2_train.npz`
- Split unit: case/run source unit, never random windows.
- Seed: `20260708`
- Validation fraction by class: `0.2`
- inner_train window counts: {'healthy': 510, 'degradation': 850, 'failure': 119}
- inner_train unit counts: {'healthy': 30, 'degradation': 50, 'failure': 7}
- inner_val window counts: {'degradation': 204, 'healthy': 119, 'failure': 34}
- inner_val unit counts: {'degradation': 12, 'healthy': 7, 'failure': 2}
