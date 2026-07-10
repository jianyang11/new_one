# MU-TCM v3 Inner Split Report

- Source: v2 fixed `mutcm_v2_inner_split_assignments.csv`; no split was selected from LLM results.
- Group unit: MAT experiment/file; all windows from one MAT stay in one split.
- Window count: `783`
- Experiment count: `67`
- Max split count per file: `1`

## Window Counts

- inner_train labels: `{'healthy': 291, 'worn': 288}`
- inner_train conditions: `{'CastIron.GG30|Vc100|fz0.2|ap1.5|ae58.4': 96, 'CastIron.GG30|Vc200|fz0.1|ap1.5|ae58.4': 120, 'CastIron.GG30|Vc200|fz0.2|ap1.5|ae58.4': 75, 'StainlessSteel.316L|Vc100|fz0.05|ap1.5|ae58.4': 96, 'StainlessSteel.316L|Vc100|fz0.1|ap1.5|ae58.4': 96, 'StainlessSteel.316L|Vc50|fz0.1|ap1.5|ae58.4': 96}`
- inner_train insert_edge: `{'Insert0_Edge2': 24, 'Insert0_Edge3': 56, 'Insert1_Edge1': 72, 'Insert2_Edge1': 67, 'Insert3_Edge1': 72, 'Insert4_Edge1': 66, 'Insert6_Edge1': 150, 'Insert9_Edge1': 24, 'Insert9_Edge2': 48}`
- inner_val labels: `{'healthy': 96, 'worn': 108}`
- inner_val conditions: `{'CastIron.GG30|Vc100|fz0.1|ap1.5|ae58.4': 96, 'StainlessSteel.316L|Vc50|fz0.05|ap1.5|ae58.4': 108}`
- inner_val insert_edge: `{'Insert0_Edge2': 12, 'Insert0_Edge3': 12, 'Insert1_Edge1': 24, 'Insert2_Edge1': 24, 'Insert3_Edge1': 36, 'Insert4_Edge1': 24, 'Insert6_Edge1': 48, 'Insert9_Edge1': 24}`

## Experiment Counts

- inner_train labels: `{'healthy': 25, 'worn': 25}`
- inner_train conditions: `{'CastIron.GG30|Vc100|fz0.2|ap1.5|ae58.4': 8, 'CastIron.GG30|Vc200|fz0.1|ap1.5|ae58.4': 10, 'CastIron.GG30|Vc200|fz0.2|ap1.5|ae58.4': 8, 'StainlessSteel.316L|Vc100|fz0.05|ap1.5|ae58.4': 8, 'StainlessSteel.316L|Vc100|fz0.1|ap1.5|ae58.4': 8, 'StainlessSteel.316L|Vc50|fz0.1|ap1.5|ae58.4': 8}`
- inner_train supports n_real=2/5/10 in train: `True`
- inner_val labels: `{'healthy': 8, 'worn': 9}`
- inner_val conditions: `{'CastIron.GG30|Vc100|fz0.1|ap1.5|ae58.4': 8, 'StainlessSteel.316L|Vc50|fz0.05|ap1.5|ae58.4': 9}`
- inner_val supports n_real=2/5/10 in train: `False`
