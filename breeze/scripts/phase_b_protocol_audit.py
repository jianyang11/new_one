"""Audit Phase-B candidate dataset protocols before running new experiments.

The audit is intentionally read-only. It checks local processed NPZ files for
class balance, split semantics, operating-condition coverage, and obvious
train/test leakage keys before any Phase-B downstream or generation jobs run.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
PROC = ROOT / "proc"
RESULTS = BREEZE / "results"

sys.path.insert(0, str(BREEZE / "src"))
from config import BEARINGS, CLASSES as PU_CLASSES, CONDITIONS  # noqa: E402


CWRU_CLASSES = ("healthy", "IR", "B", "OR")
DIRG_DEFAULT_SPLITS = (
    (
        "loco_speed300_load1400",
        PROC / "dirg_variable_loco_speed300_load1400_train.npz",
        PROC / "dirg_variable_loco_speed300_load1400_test.npz",
    ),
)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def counts_json(y: np.ndarray, class_names: tuple[str, ...] | list[str] | np.ndarray) -> str:
    names = [str(x) for x in class_names]
    counts = {names[i]: int((y == i).sum()) for i in range(len(names))}
    return json.dumps(counts, sort_keys=True, separators=(",", ":"))


def meta_rows(npz: np.lib.npyio.NpzFile) -> list[dict[str, Any]]:
    return [json.loads(str(item)) for item in npz["metadata"]]


def summarize_cwru_pair(split_name: str, train_path: Path, test_path: Path) -> dict[str, Any]:
    train = np.load(train_path, allow_pickle=True)
    test = np.load(test_path, allow_pickle=True)
    y_train, y_test = train["y"], test["y"]
    m_train, m_test = meta_rows(train), meta_rows(test)
    train_window_keys = {(int(m["file_id"]), int(m["window_index"])) for m in m_train}
    test_window_keys = {(int(m["file_id"]), int(m["window_index"])) for m in m_test}
    train_files = {int(m["file_id"]) for m in m_train}
    test_files = {int(m["file_id"]) for m in m_test}
    train_loads = sorted({int(m["load_hp"]) for m in m_train})
    test_loads = sorted({int(m["load_hp"]) for m in m_test})
    train_rpm = sorted({int(m["rpm"]) for m in m_train})
    test_rpm = sorted({int(m["rpm"]) for m in m_test})
    train_fault_sizes = sorted({str(m["fault_diameter_in"]) for m in m_train})
    test_fault_sizes = sorted({str(m["fault_diameter_in"]) for m in m_test})
    shared_windows = train_window_keys & test_window_keys
    shared_files = train_files & test_files
    return {
        "dataset": "CWRU",
        "split": split_name,
        "train_path": str(train_path.relative_to(ROOT)),
        "test_path": str(test_path.relative_to(ROOT)),
        "sampling_rate_hz": 12000,
        "channels": int(train["X"].shape[1]),
        "window": int(train["X"].shape[2]),
        "train_n": int(len(y_train)),
        "test_n": int(len(y_test)),
        "train_counts": counts_json(y_train, CWRU_CLASSES),
        "test_counts": counts_json(y_test, CWRU_CLASSES),
        "train_conditions": json.dumps({"load_hp": train_loads, "rpm": train_rpm}, sort_keys=True),
        "test_conditions": json.dumps({"load_hp": test_loads, "rpm": test_rpm}, sort_keys=True),
        "fault_sizes_train": json.dumps(train_fault_sizes),
        "fault_sizes_test": json.dumps(test_fault_sizes),
        "shared_file_ids": len(shared_files),
        "shared_window_ids": len(shared_windows),
        "leakage_status": "PASS" if not shared_windows else "FAIL",
        "split_semantics": "chronological_within_file" if shared_files else "file_or_condition_disjoint",
    }


def audit_cwru() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    train_files = sorted(PROC.glob("cwru_de12k_*_train.npz"))
    for train_path in train_files:
        split_name = train_path.name.replace("cwru_de12k_", "").replace("_train.npz", "")
        test_path = PROC / train_path.name.replace("_train.npz", "_test.npz")
        if not test_path.exists():
            continue
        if "smoke" in split_name:
            continue
        rows.append(summarize_cwru_pair(split_name, train_path, test_path))
    return rows


def summarize_dirg_pair(split_name: str, train_path: Path, test_path: Path) -> dict[str, Any]:
    train = np.load(train_path, allow_pickle=True)
    test = np.load(test_path, allow_pickle=True)
    y_train, y_test = train["y"], test["y"]
    class_names = [str(x) for x in train["class_names"]]
    train_conditions = sorted(
        {(int(s), int(l)) for s, l in zip(train["speed_hz"], train["nominal_load_n"])}
    )
    test_conditions = sorted(
        {(int(s), int(l)) for s, l in zip(test["speed_hz"], test["nominal_load_n"])}
    )
    train_files = {int(x) for x in train["file_index"]}
    test_files = {int(x) for x in test["file_index"]}
    shared_files = train_files & test_files
    return {
        "dataset": "DIRG",
        "split": split_name,
        "train_path": str(train_path.relative_to(ROOT)),
        "test_path": str(test_path.relative_to(ROOT)),
        "sampling_rate_hz": 51200,
        "channels": int(train["X"].shape[1]),
        "window": int(train["X"].shape[2]),
        "train_n": int(len(y_train)),
        "test_n": int(len(y_test)),
        "train_counts": counts_json(y_train, class_names),
        "test_counts": counts_json(y_test, class_names),
        "train_conditions": json.dumps(train_conditions),
        "test_conditions": json.dumps(test_conditions),
        "fault_sizes_train": "severity_um=" + json.dumps(sorted({int(x) for x in train["severity_um"]})),
        "fault_sizes_test": "severity_um=" + json.dumps(sorted({int(x) for x in test["severity_um"]})),
        "shared_file_ids": len(shared_files),
        "shared_window_ids": 0,
        "leakage_status": "PASS" if not shared_files else "FAIL",
        "split_semantics": "leave_one_speed_load_condition_out",
    }


def audit_dirg() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split_name, train_path, test_path in DIRG_DEFAULT_SPLITS:
        if train_path.exists() and test_path.exists():
            rows.append(summarize_dirg_pair(split_name, train_path, test_path))
    return rows


def audit_pu() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cond in CONDITIONS:
        train_n = test_n = 0
        y_train: list[int] = []
        y_test: list[int] = []
        train_keys: set[tuple[str, int]] = set()
        test_keys: set[tuple[str, int]] = set()
        bearing_counts = {"train": 0, "test": 0}
        for ci, cls in enumerate(PU_CLASSES):
            for bearing in BEARINGS[cls]:
                path = PROC / f"{cond}_{bearing}.npz"
                if not path.exists():
                    raise FileNotFoundError(path)
                data = np.load(path, allow_pickle=True)
                windows = data["windows"]
                file_ids = data["file_ids"]
                unique_files = np.unique(file_ids)
                cut = unique_files[int(len(unique_files) * 0.8)]
                train_mask = file_ids < cut
                test_mask = file_ids >= cut
                train_n += int(train_mask.sum())
                test_n += int(test_mask.sum())
                y_train.extend([ci] * int(train_mask.sum()))
                y_test.extend([ci] * int(test_mask.sum()))
                train_keys.update((bearing, int(fid)) for fid in np.unique(file_ids[train_mask]))
                test_keys.update((bearing, int(fid)) for fid in np.unique(file_ids[test_mask]))
                bearing_counts["train"] += int(train_mask.any())
                bearing_counts["test"] += int(test_mask.any())
                if windows.shape[1:] != (3, 2048):
                    raise RuntimeError(f"unexpected PU shape in {path}: {windows.shape}")
        shared_file_keys = train_keys & test_keys
        rpm, torque_nm, radial_force_n = CONDITIONS[cond]
        rows.append(
            {
                "dataset": "PU",
                "split": f"{cond}_file_split",
                "train_path": "proc/{condition}_{bearing}.npz file_id<80pct cut",
                "test_path": "proc/{condition}_{bearing}.npz file_id>=80pct cut",
                "sampling_rate_hz": 8000,
                "channels": 3,
                "window": 2048,
                "train_n": train_n,
                "test_n": test_n,
                "train_counts": counts_json(np.asarray(y_train), PU_CLASSES),
                "test_counts": counts_json(np.asarray(y_test), PU_CLASSES),
                "train_conditions": json.dumps({"rpm": rpm, "torque_nm": torque_nm, "radial_force_n": radial_force_n}),
                "test_conditions": json.dumps({"rpm": rpm, "torque_nm": torque_nm, "radial_force_n": radial_force_n}),
                "fault_sizes_train": "PU real bearing IDs, not single geometric notch size",
                "fault_sizes_test": "PU real bearing IDs, not single geometric notch size",
                "shared_file_ids": len(shared_file_keys),
                "shared_window_ids": 0,
                "leakage_status": "PASS" if not shared_file_keys else "FAIL",
                "split_semantics": "file_chronological_within_each_bearing",
            }
        )
    return rows


def write_report(all_rows: list[dict[str, Any]]) -> None:
    report = RESULTS / "phaseB_protocol_audit.md"
    lines = [
        "# Phase-B Protocol Audit",
        "",
        "Date: 2026-07-05",
        "",
        "This audit is a read-only preflight check before Phase-B generation or downstream training. It verifies local processed splits, class counts, operating-condition coverage, and simple train/test leakage keys.",
        "",
        "## Dataset Decision",
        "",
        "- Main Phase-B candidates: PU, CWRU, DIRG.",
        "- XJTU-SY remains skipped per user instruction.",
        "- IMS is retained as a run-to-failure audit dataset unless a transparent fault-onset labelling protocol is defined.",
        "- HIT and JUST are not counted toward the main physical-generation claim at this point.",
        "",
        "## Split Summary",
        "",
        "| dataset | split | train_n | test_n | leakage_status | split_semantics | train_counts | test_counts |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in all_rows:
        lines.append(
            f"| {row['dataset']} | {row['split']} | {row['train_n']} | {row['test_n']} | {row['leakage_status']} | {row['split_semantics']} | `{row['train_counts']}` | `{row['test_counts']}` |"
        )
    lines.extend(
        [
            "",
            "## Phase-B Budget Note",
            "",
            "No new LLM API calls are required for this audit. Any CWRU/DIRG LLM recipe generation must be separately budgeted before execution because it would require new dataset-specific prompts and verifier boundaries.",
        ]
    )
    report.write_text("\n".join(lines) + "\n")


def main() -> None:
    cwru = audit_cwru()
    dirg = audit_dirg()
    pu = audit_pu()
    write_csv(RESULTS / "phaseB_cwru_protocol_summary.csv", cwru)
    write_csv(RESULTS / "phaseB_dirg_protocol_summary.csv", dirg)
    write_csv(RESULTS / "phaseB_pu_protocol_summary.csv", pu)
    all_rows = pu + cwru + dirg
    write_csv(RESULTS / "phaseB_dataset_protocol_summary.csv", all_rows)
    write_report(all_rows)
    print(f"wrote {RESULTS / 'phaseB_cwru_protocol_summary.csv'} ({len(cwru)} rows)")
    print(f"wrote {RESULTS / 'phaseB_dirg_protocol_summary.csv'} ({len(dirg)} rows)")
    print(f"wrote {RESULTS / 'phaseB_pu_protocol_summary.csv'} ({len(pu)} rows)")
    print(f"wrote {RESULTS / 'phaseB_dataset_protocol_summary.csv'} ({len(all_rows)} rows)")
    print(f"wrote {RESULTS / 'phaseB_protocol_audit.md'}")


if __name__ == "__main__":
    main()
