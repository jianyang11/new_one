# MU-TCM v2 Split Report

- Split A: condition-aware grouped inner split, group unit is experiment/MAT file, validation selected by condition groups.
- Validation conditions: `['CastIron.GG30|Vc100|fz0.1|ap1.5|ae58.4', 'StainlessSteel.316L|Vc50|fz0.05|ap1.5|ae58.4']`
- Split B: GroupKFold by condition is used as a diagnostic baseline protocol.
- Split C: GroupKFold by insert_edge is used to diagnose tool identity leakage.
- Random window split is forbidden and not used.

## Split A Counts

- inner_train labels: `{'healthy': 25, 'worn': 25}`
- inner_train conditions: `{'CastIron.GG30|Vc100|fz0.2|ap1.5|ae58.4': 8, 'CastIron.GG30|Vc200|fz0.1|ap1.5|ae58.4': 10, 'CastIron.GG30|Vc200|fz0.2|ap1.5|ae58.4': 8, 'StainlessSteel.316L|Vc100|fz0.05|ap1.5|ae58.4': 8, 'StainlessSteel.316L|Vc100|fz0.1|ap1.5|ae58.4': 8, 'StainlessSteel.316L|Vc50|fz0.1|ap1.5|ae58.4': 8}`
- inner_train insert_edge: `{'Insert0_Edge2': 2, 'Insert0_Edge3': 5, 'Insert1_Edge1': 6, 'Insert2_Edge1': 6, 'Insert3_Edge1': 6, 'Insert4_Edge1': 6, 'Insert6_Edge1': 13, 'Insert9_Edge1': 2, 'Insert9_Edge2': 4}`
- inner_train supports n_real=2/5/10: `True`
- inner_val labels: `{'healthy': 8, 'worn': 9}`
- inner_val conditions: `{'CastIron.GG30|Vc100|fz0.1|ap1.5|ae58.4': 8, 'StainlessSteel.316L|Vc50|fz0.05|ap1.5|ae58.4': 9}`
- inner_val insert_edge: `{'Insert0_Edge2': 1, 'Insert0_Edge3': 1, 'Insert1_Edge1': 2, 'Insert2_Edge1': 2, 'Insert3_Edge1': 3, 'Insert4_Edge1': 2, 'Insert6_Edge1': 4, 'Insert9_Edge1': 2}`
- inner_val supports n_real=2/5/10: `False`
