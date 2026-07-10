# Berkeley Inner Validation Split

- Source train NPZ: `proc/milling_berkeley_train.npz`
- Split unit: case/run source unit, never random windows.
- Seed: `20260708`
- Validation fraction by class: `0.2`
- inner_train window counts: {np.str_('sharp'): 510, np.str_('worn'): 578, np.str_('severe'): 374}
- inner_train unit counts: {np.str_('sharp'): 30, np.str_('worn'): 34, np.str_('severe'): 22}
- inner_val window counts: {np.str_('worn'): 153, np.str_('severe'): 102, np.str_('sharp'): 119}
- inner_val unit counts: {np.str_('worn'): 9, np.str_('severe'): 6, np.str_('sharp'): 7}
