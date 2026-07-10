# IMS Bearing Dataset Audit

Date: 2026-07-05

## Source

- Official repository page: `https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/`
- Official archive URL: `https://phm-datasets.s3.amazonaws.com/NASA/4.+Bearings.zip`
- Local archive: `data/ims/raw/4_Bearings.zip`
- Inner archives: `data/ims/raw/1st_test.rar`, `data/ims/raw/2nd_test.rar`, `data/ims/raw/3rd_test.rar`
- Readme: `data/ims/raw/Readme Document for IMS Bearing Data.pdf`

## Archive Manifest

| set | archive | files listed | sample shape | terminal failure description | classification readiness |
| --- | --- | ---: | --- | --- | --- |
| 1 | 1st_test.rar | 2156 | 20480x8 | inner-race defect in bearing 3 and roller-element defect in bearing 4 at experiment end | blocked_without_explicit_run_to_failure_protocol |
| 2 | 2nd_test.rar | 984 | 20480x4 | outer-race failure in bearing 1 at experiment end | blocked_without_explicit_run_to_failure_protocol |
| 3 | 3rd_test.rar | 6324 | 20480x4 | outer-race failure in bearing 3 at experiment end | blocked_without_explicit_run_to_failure_protocol |

File-level manifest rows: 9464

## Interpretation

The IMS archive is available locally and the three RAR archives can be read by
`bsdtar` without bulk extraction. Each member file is a 1-second ASCII vibration
snapshot with 20,480 samples at 20 kHz. The readme gives terminal failure
descriptions for each run-to-failure experiment, but it does not provide
per-file fault-onset labels.

Therefore IMS should not be counted as a CWRU-style supervised multi-class fault
classification dataset unless a separate, explicitly justified run-to-failure
protocol is defined. Acceptable uses are dataset registry reporting,
unsupervised/temporal degradation analysis, or a separately labeled
early-vs-terminal protocol that is clearly described as such and not presented
as ground-truth fault onset.
