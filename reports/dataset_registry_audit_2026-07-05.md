# BREEZE Dataset Registry Audit

Date: 2026-07-05

CSV: `analysis/dataset_registry_2026-07-05.csv`

## Local Public Data

| dataset | condition | local_status | rpm | torque_nm | radial_force_n | analysis_fs_hz | channels | split_status | claim_readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PU | N09_M07_F10 | present | 900 | 0.7 | 1000 | 8000 | vibration_1;phase_current_1;phase_current_2 | file_split_available | main_condition_augmentation_results_exist |
| PU | N15_M01_F10 | present | 1500 | 0.1 | 1000 | 8000 | vibration_1;phase_current_1;phase_current_2 | file_split_available | verifier_audit_ready; augmentation_pool_only_for_main_condition |
| PU | N15_M07_F04 | present | 1500 | 0.7 | 400 | 8000 | vibration_1;phase_current_1;phase_current_2 | file_split_available | verifier_audit_ready; augmentation_pool_only_for_main_condition |
| PU | N15_M07_F10 | present | 1500 | 0.7 | 1000 | 8000 | vibration_1;phase_current_1;phase_current_2 | file_split_available | verifier_audit_ready; augmentation_pool_only_for_main_condition |

Interpretation: all four PU operating conditions are present as processed windows. Only N09_M07_F10 currently has completed synthetic-pool downstream augmentation results; the other PU conditions support verifier audits unless new generated pools and downstream evaluations are run.

## Private Data

| dataset | condition | split_status | split_counts | claim_readiness |
| --- | --- | --- | --- | --- |
| private_machine_tool | MT-1 | train_file_split | train MT-1: 675 windows, shape=(4, 2048) | schema_audit_only_no_public_core_claim |
| private_machine_tool | MT-2 | train_file_split | train MT-2: 383 windows, shape=(4, 2048) | schema_audit_only_no_public_core_claim |
| private_machine_tool | MT-3 | train_file_split | train MT-3: 679 windows, shape=(4, 2048) | schema_audit_only_no_public_core_claim |
| private_machine_tool | MT-1 | test_file_split | test MT-1: 166 windows, shape=(4, 2048) | schema_audit_only_no_public_core_claim |
| private_machine_tool | MT-2 | test_file_split | test MT-2: 166 windows, shape=(4, 2048) | schema_audit_only_no_public_core_claim |
| private_machine_tool | MT-3 | test_file_split | test MT-3: 154 windows, shape=(4, 2048) | schema_audit_only_no_public_core_claim |

The private machine-tool data must not be used as a core public augmentation claim because the physical label mapping, operating speed, geometry, and audited synthetic pools are unavailable in the workspace.

## Additional Public Data and Candidates

| dataset | condition | local_status | split_status | claim_readiness | notes |
| --- | --- | --- | --- | --- | --- |
| CWRU | 12k_drive_end_full | present | within-load; leave-one-load-out; train-load0-to-target-load | preprocessed_public_dataset_ready_for_smoke_downstream_and_cwru_schema_design | Official CWRU 12 kHz drive-end files. Full protocol uses DE-only because official 0.028 inch files lack FE/BA fields; no missing-channel padding is used. |
| IMS | run_to_failure_set_1 | present | archive_manifest_ready_no_supervised_fault_split | blocked_without_explicit_run_to_failure_protocol | NASA/IMS run-to-failure archive is local. The readme gives terminal failure descriptions, not per-file labels; do not use as CWRU-style multiclass fault classification without a separately justified protocol. |
| IMS | run_to_failure_set_2 | present | archive_manifest_ready_no_supervised_fault_split | blocked_without_explicit_run_to_failure_protocol | NASA/IMS run-to-failure archive is local. The readme gives terminal failure descriptions, not per-file labels; do not use as CWRU-style multiclass fault classification without a separately justified protocol. |
| IMS | run_to_failure_set_3 | present | archive_manifest_ready_no_supervised_fault_split | blocked_without_explicit_run_to_failure_protocol | NASA/IMS run-to-failure archive is local. The readme gives terminal failure descriptions, not per-file labels; do not use as CWRU-style multiclass fault classification without a separately justified protocol. |
| DIRG | VariableSpeedAndLoad | present | leave-one-speed-load-condition-out | preprocessed_public_supervised_dataset_ready_for_downstream; synthetic_schema_pending | Zenodo record 3559553, CC-BY-4.0. VariableSpeedAndLoad has seven labelled bearing conditions across 17 speed-load operating conditions; splits are frozen by held-out operating condition. |
| HIT | github_channel1_example | present | provided_train_test_split | supervised_channel1_example_ready_for_classifier_plumbing; physical_label_semantics_pending | GitHub README identifies these files as Channel 1 example data for inter-shaft bearing fault diagnosis, but does not define the physical meaning of labels 0/1/2. Do not use this subset for physical fault-generation claims until label semantics and full metadata are verified. |
| JUST | JUST_Dataset_1 | metadata_present_partial_raw | official_metadata_ready_raw_download_incomplete | blocked_until_condition_zip_download_sha256_extract_smoke_preprocess_split | https://data.mendeley.com/datasets/hwg8v5j8t6; DOI 10.17632/hwg8v5j8t6.1; Mendeley Dataset ID hwg8v5j8t6; files=condition1.zip;condition2.zip;condition3.zip;condition4.zip;condition5.zip;condition6.zip; license parsed from page as CC-BY-4.0. |
| JUST | JUST_Dataset_2 | metadata_present | official_metadata_ready_raw_download_incomplete | blocked_until_condition_zip_download_sha256_extract_smoke_preprocess_split | https://data.mendeley.com/datasets/rcxgmdxhbr; DOI 10.17632/rcxgmdxhbr.1; Mendeley Dataset ID rcxgmdxhbr; files=condition7.zip;condition8.zip;condition9.zip; license parsed from page as CC-BY-4.0. |
| MFPT |  | official_endpoint_blocked | not_available | blocked_until_download_preprocess_and_protocol | https://www.mfpt.org/fault-data-sets/ / Historical entry now redirects to ASNT/MFPT information page; no public .mat/.zip/.csv endpoint was found on 2026-07-05. |
| XJTU-SY |  | skipped_by_user | not_available | blocked_until_download_preprocess_and_protocol | Xi'an Jiaotong University / Sumyoung bearing accelerated degradation data / User instructed to skip XJTU-SY on 2026-07-05 after repository/link audit. Do not count it as an included public dataset. |
| NCEPU |  | source_unverified | not_available | blocked_until_download_preprocess_and_protocol | public source not verified in this workspace / Mentioned in BearGen-style coverage targets; local files and official metadata are absent. |

## Claim Consequence

- The current workspace can support PU multi-condition metadata reporting, CWRU and DIRG supervised public-data preprocessing, IMS run-to-failure archive auditing, and HIT Channel-1 classifier-plumbing checks with anonymous classes.
- It cannot support a BearGen-style 5--8 public-dataset augmentation claim until each public dataset is downloaded, parsed, split, generated, verified, and evaluated under a dataset-specific protocol.
- Any abstract statement about highest or tied-highest Accuracy/Macro-F1 across multiple public datasets remains blocked by data availability and downstream experiments.
