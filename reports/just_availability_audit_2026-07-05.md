# JUST Slewing Bearing Availability Audit

Date: 2026-07-05

Sources:

- Dataset 1: `https://data.mendeley.com/datasets/hwg8v5j8t6`
- Dataset 2: `https://data.mendeley.com/datasets/rcxgmdxhbr`

Local metadata:

- `data/just/meta/hwg8v5j8t6.html`
- `data/just/meta/rcxgmdxhbr.html`
- `data/just/meta/hwg8v5j8t6_files.json`
- `data/just/meta/rcxgmdxhbr_files.json`
- `data/just/meta/hwg8v5j8t6_zip.json`
- `data/just/meta/rcxgmdxhbr_zip.json`

Verified metadata:

- Dataset 1 title: JUST Slewing bearing datasets-1
- Dataset 1 DOI: `10.17632/hwg8v5j8t6.1`
- Dataset 2 title: JUST Slewing bearing datasets-2
- Dataset 2 DOI: `10.17632/rcxgmdxhbr.1`
- Contributor: Xiaodie Ren
- Institution: Jiangsu University of Science and Technology
- License: CC BY 4.0
- Page description: vibration and acoustic-emission CSV files for slewing-bearing fault diagnosis. Dataset 1 describes 9 working conditions, 7 CSV columns, labels `N`, `I`, `O`, and `B1`, and filenames carrying collection time, fault type, speed, load, and sample index.

Mendeley file API status:

| Dataset | Files | Listed bytes | Download-all zip bytes | Download-all sha256 |
| --- | --- | ---: | ---: | --- |
| Dataset 1 | condition1.zip; condition2.zip; condition3.zip; condition4.zip; condition5.zip; condition6.zip | 9480676355 | 9483563598 | `5238047f4f51ef92e85688524fd9adef42b96006e85f61fb88a9beedd9239ac6` |
| Dataset 2 | condition7.zip; condition8.zip; condition9.zip | 5047200472 | 5048737712 | `edab1013440e6b65d856d36135b054303522ef7586322f3d54c27774800778e0` |

Per-condition file sizes and sha256 values are stored in the two `*_files.json`
files. The single-file download URL for Dataset 1 `condition1.zip` is available
through the official Mendeley public-files API.

Current local raw status:

- `data/just/raw/hwg8v5j8t6_condition1.zip` exists as a partial download.
- Last observed partial size while writing this report: 200036352 bytes.
- Expected size from the Mendeley file API: 1484330344 bytes.
- Expected sha256 for `condition1.zip`: `27b6add40a742668c52bfe683a23d33de398aaa59dbbd5fa9ec756c576de36e3`.
- Download is being attempted with `curl -C -` and retry/low-speed timeout options.

Claim consequence:

- JUST is verified as a public, licensed, relevant slewing-bearing dataset.
- JUST is not yet a usable local experiment dataset in this workspace because no
  condition zip has completed download, sha256 verification, extraction, CSV
  schema audit, smoke preprocessing, or train/test split freezing.
- Do not count JUST toward multi-public-dataset augmentation results or abstract
  claims until the completed raw file passes checksum and preprocessing checks.
