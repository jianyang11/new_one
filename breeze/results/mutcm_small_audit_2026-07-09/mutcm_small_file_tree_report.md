# MU-TCM Small Subset File Tree

- Extracted directory: `data/MU-TCM face-milling dataset/small_subset`
- Archive path: `data/MU-TCM face-milling dataset/small_subset.7z`
- Archive present: `True`
- Archive listing: not read; local `7z/7zz` and `py7zr` are unavailable, extracted directory is present and used.

## Tree

- `.DS_Store` (6148 bytes)
- `VB_images/`
- `VB_images/.DS_Store` (8196 bytes)
- `VB_images/Insert1_Edge1/`
- `VB_images/Insert1_Edge1/VB0.139_Vc100.0_fz0.1.jpg` (106257 bytes)
- `VB_images/Insert1_Edge1/VB0.139_Vc100.0_fz0.1_tag.jpg` (122563 bytes)
- `VB_images/Insert2_Edge1/`
- `VB_images/Insert2_Edge1/VB0.120_Vc100.0_fz0.1.jpg` (113628 bytes)
- `VB_images/Insert2_Edge1/VB0.120_Vc100.0_fz0.1_tag.jpg` (130204 bytes)
- `VB_images/Insert3_Edge1/`
- `VB_images/Insert3_Edge1/VB0.213_Vc100.0_fz0.1.jpg` (115023 bytes)
- `VB_images/Insert3_Edge1/VB0.213_Vc100.0_fz0.1_tag.jpg` (132345 bytes)
- `VB_images/Insert4_Edge1/`
- `VB_images/Insert4_Edge1/VB0.201_Vc100.0_fz0.1.jpg` (111886 bytes)
- `VB_images/Insert4_Edge1/VB0.201_Vc100.0_fz0.1_tag.jpg` (129422 bytes)
- `VB_images/Insert6_Edge1/`
- `VB_images/Insert6_Edge1/VB0.276_Vc100.0_fz0.1.jpg` (105559 bytes)
- `VB_images/Insert6_Edge1/VB0.276_Vc100.0_fz0.1_tag.jpg` (123310 bytes)
- `VB_images/Insert6_Edge1/VB0.291_Vc100.0_fz0.1.jpg` (106830 bytes)
- `VB_images/Insert6_Edge1/VB0.291_Vc100.0_fz0.1_tag.jpg` (124328 bytes)
- `VB_images/Insert9_Edge2/`
- `VB_images/Insert9_Edge2/VB0.039_Vc100.0_fz0.1.jpg` (108067 bytes)
- `VB_images/Insert9_Edge2/VB0.039_Vc100.0_fz0.1_tag.jpg` (121244 bytes)
- `signals_stats.csv` (20989 bytes)
- `signals_sync.csv` (3146 bytes)
- `signals_synced/`
- `signals_synced/Insert0Edge2_Vc100.0_fz0.1_ap1.5_VB0.0_Rep1.mat` (237058360 bytes)
- `signals_synced/Insert1Edge1_Vc100.0_fz0.1_ap1.5_VB0.139_Rep1.mat` (250982336 bytes)
- `signals_synced/Insert2Edge1_Vc100.0_fz0.1_ap1.5_VB0.12_Rep1.mat` (236478632 bytes)
- `signals_synced/Insert3Edge1_Vc100.0_fz0.1_ap1.5_VB0.213_Rep2.mat` (237855920 bytes)
- `signals_synced/Insert4Edge1_Vc100.0_fz0.1_ap1.5_VB0.201_Rep1.mat` (237102232 bytes)
- `signals_synced/Insert6Edge1_Vc100.0_fz0.1_ap1.5_VB0.276_Rep1.mat` (250800424 bytes)
- `signals_synced/Insert6Edge1_Vc100.0_fz0.1_ap1.5_VB0.291_Rep1.mat` (244002000 bytes)
- `signals_synced/Insert9Edge2_Vc100.0_fz0.1_ap1.5_VB0.039_Rep2.mat` (248971696 bytes)
- `signals_unsynced/`
- `signals_unsynced/Insert0Edge2_Vc100.0_fz0.1_ap1.5_VB0.0_Rep1.mat` (268327160 bytes)
- `signals_unsynced/Insert1Edge1_Vc100.0_fz0.1_ap1.5_VB0.139_Rep1.mat` (268328960 bytes)
- `signals_unsynced/Insert2Edge1_Vc100.0_fz0.1_ap1.5_VB0.12_Rep1.mat` (268308344 bytes)
- `signals_unsynced/Insert3Edge1_Vc100.0_fz0.1_ap1.5_VB0.213_Rep2.mat` (268337664 bytes)
- `signals_unsynced/Insert4Edge1_Vc100.0_fz0.1_ap1.5_VB0.201_Rep1.mat` (268302840 bytes)
- `signals_unsynced/Insert6Edge1_Vc100.0_fz0.1_ap1.5_VB0.276_Rep1.mat` (268326392 bytes)
- `signals_unsynced/Insert6Edge1_Vc100.0_fz0.1_ap1.5_VB0.291_Rep1.mat` (268335360 bytes)
- `signals_unsynced/Insert9Edge2_Vc100.0_fz0.1_ap1.5_VB0.039_Rep2.mat` (268335616 bytes)

## File Type Counts

{
  ".csv": 2,
  ".jpg": 14,
  ".mat": 16,
  "<no_suffix>": 2
}

## Auto-Identified Artifacts

- Metadata / experiment info: MAT metadata fields plus `signals_stats.csv`.
- Wear labels / VB: `VB` MAT field, filename `VB...`, and `VB_images/`.
- Signal files: `signals_synced/*.mat` and `signals_unsynced/*.mat`.
- Preferred audit signals: synced MAT files, one experiment per file.

## Experiment Count

- Synced MAT experiments: `8`
- Unique materials: `['CastIron.GG30', 'StainlessSteel.316L']`
- Unique cutting speeds: `[100.0]`
- Unique feed rates: `[0.1]`
- Unique depths of cut: `[1.5]`
- Unique rounded VB levels: `[0.0, 0.1, 0.2, 0.3]`

## Condition Wear Summary

- Conditions with multiple rounded VB levels: `2/2`
