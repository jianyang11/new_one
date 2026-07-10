# XJTU-SY Skip Audit

Date: 2026-07-05

## Checked Evidence

- User-provided GitHub path `XJTU-SY/XJTU-SY_Bearing_Datasets` returned 404 through the GitHub API.
- GitHub repository search found `WangBiaoXJTU/xjtu-sy-bearing-datasets` as the most relevant public repository.
- Repository metadata:
  - default branch: `master`
  - GitHub license field: empty
  - repository size: small metadata repository, not a data-file repository
- Saved README: `data/xjtu/meta/README.md`
- README states that the XJTU-SY datasets contain complete run-to-failure data of 15 rolling-element bearings and are publicly available for validating bearing prognostics algorithms. It requests citation of Wang et al., IEEE Transactions on Reliability, 2020.
- README download links include author website, Google Drive, Dropbox, MediaFire, MEGA, and Baidu Netdisk.

## Decision

The user instructed to skip this dataset on 2026-07-05. No XJTU-SY files are
downloaded, preprocessed, split, generated, or evaluated in the current
pipeline. XJTU-SY must not be counted as an included public dataset in any
manuscript claim.

## Consequence

The remaining public-dataset expansion work proceeds with other candidate
sources such as DIRG, JUST, and HIT, subject to source availability, license,
download feasibility, and suitability for supervised fault-diagnosis
experiments.
