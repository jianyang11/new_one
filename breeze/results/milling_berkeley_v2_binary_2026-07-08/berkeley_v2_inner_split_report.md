# berkeley_v2 Inner Validation Split

- Source train NPZ: `proc/milling_berkeley_v2_binary_train.npz`
- Split unit: case/run source unit, never random windows.
- Seed: `20260708`
- Validation fraction by class: `0.2`
- inner_train window counts: {'healthy': 510, 'degraded': 969}
- inner_train unit counts: {'healthy': 30, 'degraded': 57}
- inner_val window counts: {'degraded': 238, 'healthy': 119}
- inner_val unit counts: {'degraded': 14, 'healthy': 7}
