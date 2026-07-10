"""Build a dataset registry and local-availability audit for BREEZE.

The registry separates three facts that are often conflated in manuscript
drafts:

1. data that are present and usable in this workspace;
2. public datasets that are relevant targets but are not present locally;
3. metadata needed before a dataset can support augmentation claims.

The script is read-only with respect to data. It writes CSV/Markdown summaries
under analysis/ and reports/.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
ANALYSIS = ROOT / "analysis"
REPORTS = ROOT / "reports"

sys.path.insert(0, str(BREEZE / "src"))
from config import BEARINGS, CHANNELS, CLASSES, CONDITIONS, FS, FS_RAW, HOP, PROC_DIR, WIN
from data import load_file_split


PUBLIC_CANDIDATES: list[dict[str, str]] = [
    {
        "dataset": "CWRU",
        "source": "https://engineering.case.edu/bearingdatacenter/download-data-file",
        "status": "not_present_locally",
        "notes": "Public bearing data center with normal, inner-race, ball, and outer-race fault files. A separate CWRU loader is required because the current BREEZE renderer/verifier assumes PU vibration plus two current channels.",
    },
    {
        "dataset": "MFPT",
        "source": "https://www.mfpt.org/fault-data-sets/",
        "status": "official_endpoint_blocked",
        "notes": "Historical entry now redirects to ASNT/MFPT information page; no public .mat/.zip/.csv endpoint was found on 2026-07-05.",
    },
    {
        "dataset": "IMS",
        "source": "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/",
        "status": "not_present_locally",
        "notes": "Run-to-failure bearing data. Its prognostics protocol differs from PU few-shot classification and needs an explicit split design.",
    },
    {
        "dataset": "XJTU-SY",
        "source": "Xi'an Jiaotong University / Sumyoung bearing accelerated degradation data",
        "status": "skipped_by_user",
        "notes": "User instructed to skip XJTU-SY on 2026-07-05 after repository/link audit. Do not count it as an included public dataset.",
    },
    {
        "dataset": "HIT",
        "source": "https://github.com/HouLeiHIT/HIT-dataset",
        "status": "source_unverified",
        "notes": "Mentioned in target standards. The GitHub Channel-1 example can be used only after local download/preprocess; full dataset is linked through Google Drive.",
    },
    {
        "dataset": "DIRG",
        "source": "https://zenodo.org/records/3559553",
        "status": "source_unverified",
        "notes": "Mentioned in BearGen-style coverage targets; local files and official metadata are absent.",
    },
    {
        "dataset": "JUST",
        "source": "https://data.mendeley.com/datasets/hwg8v5j8t6 ; https://data.mendeley.com/datasets/rcxgmdxhbr",
        "status": "source_unverified",
        "notes": "Mentioned in BearGen-style coverage targets; Mendeley metadata and large condition zips must be verified before local preprocessing.",
    },
    {
        "dataset": "NCEPU",
        "source": "public source not verified in this workspace",
        "status": "source_unverified",
        "notes": "Mentioned in BearGen-style coverage targets; local files and official metadata are absent.",
    },
]


def _fmt_float(x: float) -> str:
    return f"{x:.6g}"


def _npz_summary(path: Path) -> dict[str, Any]:
    d = np.load(path, allow_pickle=True)
    windows = d["windows"]
    file_ids = d.get("file_ids")
    return {
        "windows": int(windows.shape[0]),
        "shape": "x".join(str(v) for v in windows.shape[1:]),
        "files": int(len(np.unique(file_ids))) if file_ids is not None else "",
    }


def local_pu_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    bearing_to_class = {b: cls for cls, vals in BEARINGS.items() for b in vals}
    for cond, (rpm, torque, radial_force) in CONDITIONS.items():
        present, missing = [], []
        windows_by_class: dict[str, int] = defaultdict(int)
        files_by_class: dict[str, int] = defaultdict(int)
        for cls, bearings in BEARINGS.items():
            for bearing in bearings:
                path = PROC_DIR / f"{cond}_{bearing}.npz"
                if path.exists():
                    present.append(bearing)
                    summary = _npz_summary(path)
                    windows_by_class[cls] += int(summary["windows"])
                    files_by_class[cls] += int(summary["files"] or 0)
                else:
                    missing.append(bearing)
        split_status = "not_checked"
        split_counts = ""
        try:
            Xtr, ytr, _ = load_file_split("train", cond)
            Xte, yte, _ = load_file_split("test", cond)
            split_status = "file_split_available"
            split_counts = (
                f"train={len(Xtr)} "
                + ",".join(f"{CLASSES[i]}:{int((ytr == i).sum())}" for i in range(len(CLASSES)))
                + f"; test={len(Xte)} "
                + ",".join(f"{CLASSES[i]}:{int((yte == i).sum())}" for i in range(len(CLASSES)))
            )
        except Exception as exc:  # audit output, not runtime fallback for analysis
            split_status = f"split_error:{type(exc).__name__}"
            split_counts = str(exc)
        rows.append(
            {
                "dataset": "PU",
                "condition": cond,
                "public": "yes",
                "local_status": "present" if not missing else "partial",
                "rpm": rpm,
                "torque_nm": torque,
                "radial_force_n": radial_force,
                "raw_fs_hz": FS_RAW,
                "analysis_fs_hz": FS,
                "window": WIN,
                "hop": HOP,
                "channels": ";".join(CHANNELS),
                "classes": ";".join(CLASSES),
                "bearings_present": ";".join(sorted(present)),
                "bearings_missing": ";".join(sorted(missing)),
                "windows_healthy": windows_by_class["healthy"],
                "windows_OR": windows_by_class["OR"],
                "windows_IR": windows_by_class["IR"],
                "files_healthy": files_by_class["healthy"],
                "files_OR": files_by_class["OR"],
                "files_IR": files_by_class["IR"],
                "split_status": split_status,
                "split_counts": split_counts,
                "claim_readiness": (
                    "verifier_audit_ready; augmentation_pool_only_for_main_condition"
                    if cond != "N09_M07_F10"
                    else "main_condition_augmentation_results_exist"
                ),
                "notes": "Processed PU files use one vibration channel plus two phase-current channels; internal X/Y/Z names are not three vibration axes.",
            }
        )
    return rows


def machine_tool_rows() -> list[dict[str, Any]]:
    proc = ROOT / "proc"
    rows: list[dict[str, Any]] = []
    for split in ("train", "test"):
        for cls in ("1", "2", "3"):
            path = proc / f"mt_{split}_{cls}.npz"
            if not path.exists():
                continue
            d = np.load(path, allow_pickle=True)
            X = d["X"] if "X" in d.files else d["windows"]
            rows.append(
                {
                    "dataset": "private_machine_tool",
                    "condition": f"MT-{cls}",
                    "public": "no",
                    "local_status": "present",
                    "rpm": "unknown",
                    "torque_nm": "unknown",
                    "radial_force_n": "unknown",
                    "raw_fs_hz": 4000,
                    "analysis_fs_hz": 4000,
                    "window": X.shape[-1],
                    "hop": 1024,
                    "channels": "X;Y;Z;Current",
                    "classes": "MT-1;MT-2;MT-3",
                    "bearings_present": "",
                    "bearings_missing": "",
                    "windows_healthy": "",
                    "windows_OR": "",
                    "windows_IR": "",
                    "files_healthy": "",
                    "files_OR": "",
                    "files_IR": "",
                    "split_status": f"{split}_file_split",
                    "split_counts": f"{split} MT-{cls}: {len(X)} windows, shape={tuple(X.shape[1:])}",
                    "claim_readiness": "schema_audit_only_no_public_core_claim",
                    "notes": "Private data lack prefix-to-physical-label mapping, speed, geometry, and audited synthetic pools.",
                }
            )
    return rows


def local_cwru_rows() -> list[dict[str, Any]]:
    proc = ROOT / "proc"
    all_path = proc / "cwru_de12k_all.npz"
    split_path = ANALYSIS / "cwru_de12k_split_summary_2026-07-05.csv"
    if not all_path.exists():
        return []
    d = np.load(all_path, allow_pickle=True)
    X, y = d["X"], d["y"]
    counts = {cls: int((y == i).sum()) for i, cls in enumerate(("healthy", "IR", "B", "OR"))}
    split_status = "within-load; leave-one-load-out; train-load0-to-target-load" if split_path.exists() else "all-windows-only"
    return [
        {
            "dataset": "CWRU",
            "condition": "12k_drive_end_full",
            "public": "yes",
            "local_status": "present",
            "rpm": "1730-1797",
            "torque_nm": "",
            "radial_force_n": "",
            "raw_fs_hz": 12000,
            "analysis_fs_hz": 12000,
            "window": X.shape[-1],
            "hop": X.shape[-1],
            "channels": "DE",
            "classes": "healthy;IR;B;OR",
            "bearings_present": "",
            "bearings_missing": "",
            "windows_healthy": counts["healthy"],
            "windows_OR": counts["OR"],
            "windows_IR": counts["IR"],
            "files_healthy": 4,
            "files_OR": 28,
            "files_IR": 16,
            "split_status": split_status,
            "split_counts": f"all={tuple(X.shape)}; healthy={counts['healthy']}, IR={counts['IR']}, B={counts['B']}, OR={counts['OR']}",
            "claim_readiness": "preprocessed_public_dataset_ready_for_smoke_downstream_and_cwru_schema_design",
            "notes": "Official CWRU 12 kHz drive-end files. Full protocol uses DE-only because official 0.028 inch files lack FE/BA fields; no missing-channel padding is used.",
        }
    ]


def local_ims_rows() -> list[dict[str, Any]]:
    manifest = ANALYSIS / "ims_bearing_set_manifest_2026-07-05.csv"
    if not manifest.exists():
        return []
    rows: list[dict[str, Any]] = []
    with manifest.open(newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                {
                    "dataset": "IMS",
                    "condition": f"run_to_failure_set_{row['set_no']}",
                    "public": "yes",
                    "local_status": "present",
                    "rpm": "2000",
                    "torque_nm": "",
                    "radial_force_n": "6000 lbf",
                    "raw_fs_hz": row["sampling_rate_hz"],
                    "analysis_fs_hz": row["sampling_rate_hz"],
                    "window": row["points_per_file"],
                    "hop": "one 1-second snapshot every recorded interval",
                    "channels": row["channel_arrangement"],
                    "classes": "run-to-failure terminal event only; no per-file fault-onset labels",
                    "bearings_present": "",
                    "bearings_missing": "",
                    "windows_healthy": "",
                    "windows_OR": "",
                    "windows_IR": "",
                    "files_healthy": "",
                    "files_OR": "",
                    "files_IR": "",
                    "split_status": "archive_manifest_ready_no_supervised_fault_split",
                    "split_counts": f"files_listed={row['files_listed']}; expected_readme={row['expected_files_readme']}; count_matches_readme={row['file_count_matches_readme']}; first={row['first_timestamp']}; last={row['last_timestamp']}",
                    "claim_readiness": row["classification_claim_readiness"],
                    "notes": "NASA/IMS run-to-failure archive is local. The readme gives terminal failure descriptions, not per-file labels; do not use as CWRU-style multiclass fault classification without a separately justified protocol.",
                }
            )
    return rows


def local_dirg_rows() -> list[dict[str, Any]]:
    all_path = ROOT / "proc" / "dirg_variable_all.npz"
    split_path = ANALYSIS / "dirg_variable_split_summary_2026-07-05.csv"
    if not all_path.exists():
        return []
    d = np.load(all_path, allow_pickle=True)
    X, y = d["X"], d["y"]
    class_names = [str(x) for x in d["class_names"].tolist()]
    counts = {class_names[i]: int((y == i).sum()) for i in range(len(class_names))}
    conditions = sorted({(int(s), int(l)) for s, l in zip(d["speed_hz"], d["nominal_load_n"])})
    split_status = "leave-one-speed-load-condition-out" if split_path.exists() else "all-windows-only"
    return [
        {
            "dataset": "DIRG",
            "condition": "VariableSpeedAndLoad",
            "public": "yes",
            "local_status": "present",
            "rpm": "6000-30000",
            "torque_nm": "",
            "radial_force_n": "0/1000/1400/1800",
            "raw_fs_hz": 51200,
            "analysis_fs_hz": 51200,
            "window": X.shape[-1],
            "hop": X.shape[-1],
            "channels": "A1x;A1y;A1z;A2x;A2y;A2z",
            "classes": ";".join(class_names),
            "bearings_present": "0A;1A;2A;3A;4A;5A;6A",
            "bearings_missing": "",
            "windows_healthy": counts.get("healthy", ""),
            "windows_OR": counts.get("roller450", 0) + counts.get("roller250", 0) + counts.get("roller150", 0),
            "windows_IR": counts.get("IR450", 0) + counts.get("IR250", 0) + counts.get("IR150", 0),
            "files_healthy": 17,
            "files_OR": 51,
            "files_IR": 51,
            "split_status": split_status,
            "split_counts": f"all={tuple(X.shape)}; conditions={len(conditions)}; " + ",".join(f"{k}:{v}" for k, v in counts.items()),
            "claim_readiness": "preprocessed_public_supervised_dataset_ready_for_downstream; synthetic_schema_pending",
            "notes": "Zenodo record 3559553, CC-BY-4.0. VariableSpeedAndLoad has seven labelled bearing conditions across 17 speed-load operating conditions; splits are frozen by held-out operating condition.",
        }
    ]


def local_hit_rows() -> list[dict[str, Any]]:
    train_path = ROOT / "proc" / "hit_channel1_train.npz"
    test_path = ROOT / "proc" / "hit_channel1_test.npz"
    manifest = ANALYSIS / "hit_channel1_manifest_2026-07-05.csv"
    if not train_path.exists() or not test_path.exists():
        return []
    train = np.load(train_path, allow_pickle=True)
    test = np.load(test_path, allow_pickle=True)
    Xtr, ytr = train["X"], train["y"]
    Xte, yte = test["X"], test["y"]
    class_names = [str(x) for x in train["class_names"].tolist()]
    train_counts = {class_names[i]: int((ytr == i).sum()) for i in range(len(class_names))}
    test_counts = {class_names[i]: int((yte == i).sum()) for i in range(len(class_names))}
    split_status = "provided_train_test_split" if manifest.exists() else "processed_npz_only"
    return [
        {
            "dataset": "HIT",
            "condition": "github_channel1_example",
            "public": "yes",
            "local_status": "present",
            "rpm": "see_full_dataset_metadata",
            "torque_nm": "",
            "radial_force_n": "",
            "raw_fs_hz": "not_defined_in_github_readme",
            "analysis_fs_hz": "not_defined_in_github_readme",
            "window": Xtr.shape[-1],
            "hop": "provided_windows",
            "channels": "channel_1_example",
            "classes": ";".join(class_names),
            "bearings_present": "",
            "bearings_missing": "",
            "windows_healthy": "",
            "windows_OR": "",
            "windows_IR": "",
            "files_healthy": "",
            "files_OR": "",
            "files_IR": "",
            "split_status": split_status,
            "split_counts": (
                f"train={tuple(Xtr.shape)} "
                + ",".join(f"{k}:{v}" for k, v in train_counts.items())
                + f"; test={tuple(Xte.shape)} "
                + ",".join(f"{k}:{v}" for k, v in test_counts.items())
            ),
            "claim_readiness": "supervised_channel1_example_ready_for_classifier_plumbing; physical_label_semantics_pending",
            "notes": "GitHub README identifies these files as Channel 1 example data for inter-shaft bearing fault diagnosis, but does not define the physical meaning of labels 0/1/2. Do not use this subset for physical fault-generation claims until label semantics and full metadata are verified.",
        }
    ]


def _load_just_file_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def local_just_rows() -> list[dict[str, Any]]:
    dataset_specs = [
        (
            "JUST_Dataset_1",
            "hwg8v5j8t6",
            "10.17632/hwg8v5j8t6.1",
            "https://data.mendeley.com/datasets/hwg8v5j8t6",
            ANALYSIS / ".." / "data" / "just" / "meta" / "hwg8v5j8t6_files.json",
            ANALYSIS / ".." / "data" / "just" / "meta" / "hwg8v5j8t6_zip.json",
            ROOT / "data" / "just" / "raw" / "hwg8v5j8t6_condition1.zip",
        ),
        (
            "JUST_Dataset_2",
            "rcxgmdxhbr",
            "10.17632/rcxgmdxhbr.1",
            "https://data.mendeley.com/datasets/rcxgmdxhbr",
            ANALYSIS / ".." / "data" / "just" / "meta" / "rcxgmdxhbr_files.json",
            ANALYSIS / ".." / "data" / "just" / "meta" / "rcxgmdxhbr_zip.json",
            ROOT / "data" / "just" / "raw" / "rcxgmdxhbr_condition7.zip",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for condition, dsid, doi, source, files_path, zip_path, partial_raw in dataset_specs:
        files_path = files_path.resolve()
        zip_path = zip_path.resolve()
        files = _load_just_file_list(files_path)
        if not files and not zip_path.exists():
            continue
        total_file_size = sum(int(item.get("size", 0)) for item in files)
        filenames = [str(item.get("filename", "")) for item in files]
        zip_meta = json.loads(zip_path.read_text()) if zip_path.exists() else {}
        raw_note = "no_raw_zip_local"
        if partial_raw.exists():
            raw_note = f"partial_raw_download={partial_raw.name}:{partial_raw.stat().st_size} bytes"
        local_status = "metadata_present_partial_raw" if partial_raw.exists() else "metadata_present"
        rows.append(
            {
                "dataset": "JUST",
                "condition": condition,
                "public": "yes",
                "local_status": local_status,
                "rpm": "multiple conditions, see zip filenames after extraction",
                "torque_nm": "",
                "radial_force_n": "multiple conditions, see zip filenames after extraction",
                "raw_fs_hz": "metadata_pending_extraction",
                "analysis_fs_hz": "metadata_pending_extraction",
                "window": "",
                "hop": "",
                "channels": "vibration;acoustic_emission",
                "classes": "N;I;O;B1 per Mendeley description",
                "bearings_present": "",
                "bearings_missing": "raw_full_archives",
                "windows_healthy": "",
                "windows_OR": "",
                "windows_IR": "",
                "files_healthy": "",
                "files_OR": "",
                "files_IR": "",
                "split_status": "official_metadata_ready_raw_download_incomplete",
                "split_counts": f"{len(files)} condition zips; listed_bytes={total_file_size}; full_zip_bytes={zip_meta.get('size', '')}; {raw_note}",
                "claim_readiness": "blocked_until_condition_zip_download_sha256_extract_smoke_preprocess_split",
                "notes": f"{source}; DOI {doi}; Mendeley Dataset ID {dsid}; files={';'.join(filenames)}; license parsed from page as CC-BY-4.0.",
            }
        )
    return rows


def candidate_rows() -> list[dict[str, Any]]:
    rows = []
    cwru_present = (ROOT / "proc" / "cwru_de12k_all.npz").exists()
    ims_present = (ANALYSIS / "ims_bearing_set_manifest_2026-07-05.csv").exists()
    dirg_present = (ROOT / "proc" / "dirg_variable_all.npz").exists()
    hit_present = (ROOT / "proc" / "hit_channel1_train.npz").exists()
    just_metadata_present = (ROOT / "data" / "just" / "meta" / "hwg8v5j8t6_files.json").exists() or (
        ROOT / "data" / "just" / "meta" / "rcxgmdxhbr_files.json"
    ).exists()
    for item in PUBLIC_CANDIDATES:
        if item["dataset"] == "CWRU" and cwru_present:
            continue
        if item["dataset"] == "IMS" and ims_present:
            continue
        if item["dataset"] == "DIRG" and dirg_present:
            continue
        if item["dataset"] == "HIT" and hit_present:
            continue
        if item["dataset"] == "JUST" and just_metadata_present:
            continue
        rows.append(
            {
                "dataset": item["dataset"],
                "condition": "",
                "public": "yes",
                "local_status": item["status"],
                "rpm": "",
                "torque_nm": "",
                "radial_force_n": "",
                "raw_fs_hz": "",
                "analysis_fs_hz": "",
                "window": "",
                "hop": "",
                "channels": "",
                "classes": "",
                "bearings_present": "",
                "bearings_missing": "all",
                "windows_healthy": "",
                "windows_OR": "",
                "windows_IR": "",
                "files_healthy": "",
                "files_OR": "",
                "files_IR": "",
                "split_status": "not_available",
                "split_counts": "",
                "claim_readiness": "blocked_until_download_preprocess_and_protocol",
                "notes": f"{item['source']} | {item['notes']}",
            }
        )
    return rows


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def write_report(rows: list[dict[str, Any]], path: Path, csv_path: Path) -> None:
    pu = [r for r in rows if r["dataset"] == "PU"]
    private = [r for r in rows if r["dataset"] == "private_machine_tool"]
    external = [r for r in rows if r["dataset"] not in {"PU", "private_machine_tool"}]
    local_external = [r for r in external if r["local_status"] == "present"]
    pending_external = [r for r in external if r["local_status"] != "present"]
    lines = [
        "# BREEZE Dataset Registry Audit",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        f"CSV: `{csv_path.relative_to(ROOT)}`",
        "",
        "## Local Public Data",
        "",
        md_table(
            pu,
            [
                "dataset",
                "condition",
                "local_status",
                "rpm",
                "torque_nm",
                "radial_force_n",
                "analysis_fs_hz",
                "channels",
                "split_status",
                "claim_readiness",
            ],
        ),
        "",
        "Interpretation: all four PU operating conditions are present as processed windows. Only N09_M07_F10 currently has completed synthetic-pool downstream augmentation results; the other PU conditions support verifier audits unless new generated pools and downstream evaluations are run.",
        "",
        "## Private Data",
        "",
        md_table(private, ["dataset", "condition", "split_status", "split_counts", "claim_readiness"]),
        "",
        "The private machine-tool data must not be used as a core public augmentation claim because the physical label mapping, operating speed, geometry, and audited synthetic pools are unavailable in the workspace.",
        "",
        "## Additional Public Data and Candidates",
        "",
        md_table(local_external + pending_external, ["dataset", "condition", "local_status", "split_status", "claim_readiness", "notes"]),
        "",
        "## Claim Consequence",
        "",
        "- The current workspace can support PU multi-condition metadata reporting, CWRU and DIRG supervised public-data preprocessing, IMS run-to-failure archive auditing, and HIT Channel-1 classifier-plumbing checks with anonymous classes.",
        "- It cannot support a BearGen-style 5--8 public-dataset augmentation claim until each public dataset is downloaded, parsed, split, generated, verified, and evaluated under a dataset-specific protocol.",
        "- Any abstract statement about highest or tied-highest Accuracy/Macro-F1 across multiple public datasets remains blocked by data availability and downstream experiments.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    rows = (
        local_pu_rows()
        + local_cwru_rows()
        + local_ims_rows()
        + local_dirg_rows()
        + local_hit_rows()
        + local_just_rows()
        + machine_tool_rows()
        + candidate_rows()
    )
    csv_path = ANALYSIS / "dataset_registry_2026-07-05.csv"
    report_path = REPORTS / "dataset_registry_audit_2026-07-05.md"
    write_csv(rows, csv_path)
    write_report(rows, report_path, csv_path)
    print(f"wrote {csv_path}")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
