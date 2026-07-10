# BREEZE

This repository contains the BREEZE research code, experiment configuration,
analysis, reports, compact result tables, and task records.

## Repository scope

Raw dataset releases, processed arrays, virtual environments, checkpoints, and
training-run artifacts are intentionally excluded. They exceed GitHub file-size
limits and some dataset licenses do not permit redistribution. Dataset
provenance and local availability are recorded in
`analysis/dataset_registry_2026-07-05.csv` and the accompanying audit reports.

## Layout

- `breeze/src/` and `breeze/scripts/`: experiment implementation.
- `breeze/results/`: compact experiment outputs, gates, and reports.
- `analysis/` and `reports/`: dataset registry, audits, and research analysis.
- `breeze/paper/`: manuscript sources and supporting material.
- `todos.md` and `breeze/todos.md`: execution state and next tasks.

## Local data

The local directories `data/`, `proc/`, `breeze/data_mt/`, and `breeze/runs/`
are required only for dataset processing and model execution. They are not part
of the Git history. Recreate them from the documented public data sources and
the repository scripts before rerunning an experiment.
