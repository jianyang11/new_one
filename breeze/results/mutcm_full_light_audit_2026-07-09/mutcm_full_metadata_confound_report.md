# MU-TCM Full Metadata Confound Report

| scheme | baseline | split | status | Acc | Macro-F1 | majority |
|---|---|---|---|---:|---:|---:|
| A | metadata_safe | loeo | ok | 0.0000 | 0.0000 | 0.5075 |
| A | metadata_safe | logo_condition | ok | 0.4925 | 0.4924 | 0.5075 |
| A | metadata_safe | groupkfold_condition | ok | 0.4925 | 0.4924 | 0.5075 |
| A | metadata_safe | groupkfold_insert_edge | ok | 0.2687 | 0.2680 | 0.5075 |
| A | metadata_leaky | loeo | ok | 1.0000 | 1.0000 | 0.5075 |
| A | metadata_leaky | logo_condition | ok | 1.0000 | 1.0000 | 0.5075 |
| A | metadata_leaky | groupkfold_condition | ok | 1.0000 | 1.0000 | 0.5075 |
| A | metadata_leaky | groupkfold_insert_edge | ok | 0.1343 | 0.1184 | 0.5075 |
| B | metadata_safe | loeo | ok | 0.1765 | 0.1500 | 0.6667 |
| B | metadata_safe | logo_condition | ok | 0.5490 | 0.5123 | 0.6667 |
| B | metadata_safe | groupkfold_condition | ok | 0.5490 | 0.5123 | 0.6667 |
| B | metadata_safe | groupkfold_insert_edge | ok | 0.1961 | 0.1639 | 0.6667 |
| B | metadata_leaky | loeo | ok | 1.0000 | 1.0000 | 0.6667 |
| B | metadata_leaky | logo_condition | ok | 1.0000 | 1.0000 | 0.6667 |
| B | metadata_leaky | groupkfold_condition | ok | 1.0000 | 1.0000 | 0.6667 |
| B | metadata_leaky | groupkfold_insert_edge | ok | 0.6667 | 0.4000 | 0.6667 |
| C | metadata_safe | loeo | ok | 0.0000 | 0.0000 | 0.5075 |
| C | metadata_safe | logo_condition | ok | 0.4925 | 0.4924 | 0.5075 |
| C | metadata_safe | groupkfold_condition | ok | 0.4925 | 0.4924 | 0.5075 |
| C | metadata_safe | groupkfold_insert_edge | ok | 0.2687 | 0.2680 | 0.5075 |
| C | metadata_leaky | loeo | ok | 1.0000 | 1.0000 | 0.5075 |
| C | metadata_leaky | logo_condition | ok | 1.0000 | 1.0000 | 0.5075 |
| C | metadata_leaky | groupkfold_condition | ok | 1.0000 | 1.0000 | 0.5075 |
| C | metadata_leaky | groupkfold_insert_edge | ok | 0.1343 | 0.1184 | 0.5075 |

Interpretation: `metadata_safe` excludes insert, edge, and repetition. `metadata_leaky` includes them to test tool identity leakage.
