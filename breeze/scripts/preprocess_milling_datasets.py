"""Preprocess public milling datasets into NPZ train/test splits.

Splits are by experimental case/run files, never by random windows.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io as sio


BERKELEY_CHANNELS = ["smcAC", "smcDC", "vib_table", "vib_spindle", "AE_table", "AE_spindle"]
BERKELEY_CLASSES_LEGACY = ["sharp", "worn", "severe"]
BERKELEY_CLASSES_LITERATURE = ["healthy", "degradation", "failure"]
BERKELEY_CLASSES_BINARY = ["healthy", "degraded"]
BERKELEY_TEST_CASES = {2, 4, 8, 14, 15}
BERKELEY_FS = 250.0
BERKELEY_WIN = 512

UMICH_CHANNELS = [
    "X1_CurrentFeedback",
    "Y1_CurrentFeedback",
    "Z1_CurrentFeedback",
    "S1_CurrentFeedback",
    "X1_OutputCurrent",
    "Y1_OutputCurrent",
    "Z1_OutputCurrent",
    "S1_OutputCurrent",
]
UMICH_CHANNELS_DYNAMIC = [
    "X1_CurrentFeedback",
    "Y1_CurrentFeedback",
    "S1_CurrentFeedback",
    "X1_OutputCurrent",
    "Y1_OutputCurrent",
    "S1_OutputCurrent",
]
UMICH_CLASSES = ["unworn", "worn"]
UMICH_TEST_EXPERIMENTS = {1, 2, 6, 7, 8}
UMICH_ACTIVE = {
    "Layer 1 Up",
    "Layer 1 Down",
    "Layer 2 Up",
    "Layer 2 Down",
    "Layer 3 Up",
    "Layer 3 Down",
}
UMICH_FS = 10.0
UMICH_WIN = 64


def clean_umich_meta(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def is_umich_pure_exemplar(tool_condition: str, passed_visual_inspection: str) -> bool:
    return (
        (tool_condition == "unworn" and passed_visual_inspection == "yes")
        or (tool_condition == "worn" and passed_visual_inspection == "no")
    )


def berkeley_classes(label_scheme: str) -> list[str]:
    if label_scheme == "legacy_0p2_0p45":
        return BERKELEY_CLASSES_LEGACY
    if label_scheme == "literature_0p2_0p7":
        return BERKELEY_CLASSES_LITERATURE
    if label_scheme == "binary_healthy_degraded":
        return BERKELEY_CLASSES_BINARY
    raise ValueError(label_scheme)


def berkeley_label_definition(label_scheme: str) -> str:
    if label_scheme == "legacy_0p2_0p45":
        return "sharp VB<0.2; worn 0.2<=VB<=0.45; severe VB>0.45; measured VB only"
    if label_scheme == "literature_0p2_0p7":
        return "healthy VB<0.2; degradation 0.2<=VB<0.7; failure VB>=0.7; measured VB only"
    if label_scheme == "binary_healthy_degraded":
        return "healthy VB<0.2; degraded VB>=0.2; measured VB only"
    raise ValueError(label_scheme)


def label_vb(vb: float, label_scheme: str = "legacy_0p2_0p45") -> str:
    if label_scheme == "legacy_0p2_0p45":
        if vb < 0.2:
            return "sharp"
        if vb <= 0.45:
            return "worn"
        return "severe"
    if label_scheme == "literature_0p2_0p7":
        if vb < 0.2:
            return "healthy"
        if vb < 0.7:
            return "degradation"
        return "failure"
    if label_scheme == "binary_healthy_degraded":
        return "healthy" if vb < 0.2 else "degraded"
    raise ValueError(label_scheme)


def windows(arr: np.ndarray, win: int) -> np.ndarray:
    n = arr.shape[1] // win
    if n < 1:
        return np.zeros((0, arr.shape[0], win), dtype=np.float32)
    return np.stack([arr[:, i * win : (i + 1) * win] for i in range(n)]).astype(np.float32)


def preprocess_berkeley(
    data_dir: Path,
    proc_dir: Path,
    label_scheme: str = "legacy_0p2_0p45",
    prefix: str = "milling_berkeley",
) -> list[dict[str, object]]:
    classes = berkeley_classes(label_scheme)
    mat = sio.loadmat(data_dir / "mill.mat", squeeze_me=True, struct_as_record=False)["mill"]
    rows: list[dict[str, object]] = []
    split_data = {
        "train": {"X": [], "y": [], "unit": []},
        "test": {"X": [], "y": [], "unit": []},
    }
    for idx, rec in enumerate(mat):
        vb_arr = np.asarray(rec.VB, dtype=float).ravel()
        if not vb_arr.size or np.isnan(vb_arr[0]):
            continue
        vb = float(vb_arr[0])
        cls = label_vb(vb, label_scheme)
        case = int(rec.case)
        run = int(rec.run)
        sig = np.vstack([np.asarray(getattr(rec, ch), dtype=np.float32).ravel() for ch in BERKELEY_CHANNELS])
        W = windows(sig, BERKELEY_WIN)
        if len(W) == 0:
            continue
        split = "test" if case in BERKELEY_TEST_CASES else "train"
        yi = classes.index(cls)
        split_data[split]["X"].append(W)
        split_data[split]["y"].append(np.full(len(W), yi, dtype=np.int64))
        split_data[split]["unit"].extend([f"case{case:02d}_run{run:02d}"] * len(W))
        rows.append(
            {
                "dataset": "Berkeley_NASA_milling",
                "split": split,
                "case": case,
                "run": run,
                "VB": vb,
                "label": cls,
                "label_scheme": label_scheme,
                "windows": len(W),
                "samples": sig.shape[1],
            }
        )
    for split, data in split_data.items():
        X = np.concatenate(data["X"]).astype(np.float32)
        y = np.concatenate(data["y"]).astype(np.int64)
        np.savez_compressed(
            proc_dir / f"{prefix}_{split}.npz",
            X=X,
            y=y,
            class_names=np.asarray(classes),
            source_units=np.asarray(data["unit"]),
            fs_hz=BERKELEY_FS,
            window=BERKELEY_WIN,
            channels=np.asarray(BERKELEY_CHANNELS),
        )
    return rows


def preprocess_umich(
    data_dir: Path,
    proc_dir: Path,
    channels: list[str] | None = None,
    prefix: str = "milling_umich",
) -> list[dict[str, object]]:
    channels = channels or UMICH_CHANNELS
    meta = pd.read_csv(data_dir / "train.csv")
    rows: list[dict[str, object]] = []
    split_data = {
        "train": {"X": [], "y": [], "unit": [], "experiment": [], "tool_condition": [], "passed_visual_inspection": [], "machining_finalized": [], "pure_exemplar": []},
        "test": {"X": [], "y": [], "unit": [], "experiment": [], "tool_condition": [], "passed_visual_inspection": [], "machining_finalized": [], "pure_exemplar": []},
    }
    for _, rec in meta.iterrows():
        exp_no = int(rec["No"])
        label = clean_umich_meta(rec["tool_condition"])
        passed_visual = clean_umich_meta(rec.get("passed_visual_inspection", ""))
        machining_finalized = clean_umich_meta(rec.get("machining_finalized", ""))
        pure_exemplar = is_umich_pure_exemplar(label, passed_visual)
        df = pd.read_csv(data_dir / f"experiment_{exp_no:02d}.csv")
        active = df[df["Machining_Process"].isin(UMICH_ACTIVE)].copy()
        if active.empty:
            continue
        sig = active[channels].apply(pd.to_numeric, errors="coerce").interpolate(limit_direction="both").fillna(0.0).to_numpy(dtype=np.float32).T
        W = windows(sig, UMICH_WIN)
        if len(W) == 0:
            continue
        split = "test" if exp_no in UMICH_TEST_EXPERIMENTS else "train"
        yi = UMICH_CLASSES.index(label)
        split_data[split]["X"].append(W)
        split_data[split]["y"].append(np.full(len(W), yi, dtype=np.int64))
        split_data[split]["unit"].extend([f"experiment_{exp_no:02d}"] * len(W))
        split_data[split]["experiment"].extend([exp_no] * len(W))
        split_data[split]["tool_condition"].extend([label] * len(W))
        split_data[split]["passed_visual_inspection"].extend([passed_visual] * len(W))
        split_data[split]["machining_finalized"].extend([machining_finalized] * len(W))
        split_data[split]["pure_exemplar"].extend([pure_exemplar] * len(W))
        rows.append(
            {
                "dataset": "UMich_CNC",
                "split": split,
                "experiment": exp_no,
                "label": label,
                "passed_visual_inspection": passed_visual,
                "machining_finalized": machining_finalized,
                "pure_exemplar": pure_exemplar,
                "active_rows": len(active),
                "windows": len(W),
                "feedrate": rec["feedrate"],
                "clamp_pressure": rec["clamp_pressure"],
            }
        )
    for split, data in split_data.items():
        X = np.concatenate(data["X"]).astype(np.float32)
        y = np.concatenate(data["y"]).astype(np.int64)
        np.savez_compressed(
            proc_dir / f"{prefix}_{split}.npz",
            X=X,
            y=y,
            class_names=np.asarray(UMICH_CLASSES),
            source_units=np.asarray(data["unit"]),
            fs_hz=UMICH_FS,
            window=UMICH_WIN,
            channels=np.asarray(channels),
            experiment=np.asarray(data["experiment"], dtype=np.int64),
            tool_condition=np.asarray(data["tool_condition"]),
            passed_visual_inspection=np.asarray(data["passed_visual_inspection"]),
            machining_finalized=np.asarray(data["machining_finalized"]),
            pure_exemplar=np.asarray(data["pure_exemplar"], dtype=bool),
        )
    return rows


def counts_for_npz(path: Path) -> dict[str, int]:
    data = np.load(path, allow_pickle=True)
    y = data["y"]
    classes = [str(x) for x in data["class_names"]]
    return {classes[i]: int((y == i).sum()) for i in range(len(classes))}


def write_specs(
    proc_dir: Path,
    berkeley_rows: list[dict[str, object]],
    umich_rows: list[dict[str, object]],
    out_dir: Path,
    berkeley_label_scheme: str,
    berkeley_prefix: str,
    umich_prefix: str,
    umich_channels: list[str],
    include_berkeley: bool,
    include_umich: bool,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "milling_preprocess_units.csv").open("w", newline="") as f:
        fieldnames = sorted({k for row in berkeley_rows + umich_rows for k in row})
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(berkeley_rows + umich_rows)

    spec_rows = []
    if include_berkeley:
        spec_rows.append(
            {
            "dataset": "Berkeley_NASA_milling",
            "fs_hz": BERKELEY_FS,
            "channels": ";".join(BERKELEY_CHANNELS),
            "window": BERKELEY_WIN,
            "window_seconds": BERKELEY_WIN / BERKELEY_FS,
            "label_definition": berkeley_label_definition(berkeley_label_scheme),
            "split": f"case-level; test_cases={sorted(BERKELEY_TEST_CASES)}",
            "train_counts": counts_for_npz(proc_dir / f"{berkeley_prefix}_train.npz"),
            "test_counts": counts_for_npz(proc_dir / f"{berkeley_prefix}_test.npz"),
            }
        )
    if include_umich:
        spec_rows.append(
            {
            "dataset": "UMich_CNC",
            "fs_hz": UMICH_FS,
            "channels": ";".join(umich_channels),
            "window": UMICH_WIN,
            "window_seconds": UMICH_WIN / UMICH_FS,
            "label_definition": "tool_condition binary label; active machining rows only",
            "split": f"experiment-level; test_experiments={sorted(UMICH_TEST_EXPERIMENTS)}",
            "train_counts": counts_for_npz(proc_dir / f"{umich_prefix}_train.npz"),
            "test_counts": counts_for_npz(proc_dir / f"{umich_prefix}_test.npz"),
            }
        )
    if not spec_rows:
        raise RuntimeError("no datasets selected")
    with (out_dir / "milling_dataset_specs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(spec_rows[0]))
        writer.writeheader()
        writer.writerows(spec_rows)

    lines = ["# Milling Dataset Preprocessing", ""]
    for row in spec_rows:
        lines.append(f"## {row['dataset']}")
        for key, value in row.items():
            if key != "dataset":
                lines.append(f"- {key}: {value}")
        lines.append("")
    (out_dir / "milling_dataset_specs.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proc-dir", default="proc")
    parser.add_argument("--out-dir", default="breeze/results/milling_preprocess_2026-07-07")
    parser.add_argument("--berkeley-dir", default="data/3. Milling-mill")
    parser.add_argument("--umich-dir", default="data/archive")
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=["berkeley", "umich"],
        default=["berkeley", "umich"],
        help="Datasets to preprocess. Use this to avoid rewriting unrelated NPZ files.",
    )
    parser.add_argument(
        "--berkeley-label-scheme",
        choices=["legacy_0p2_0p45", "literature_0p2_0p7", "binary_healthy_degraded"],
        default="legacy_0p2_0p45",
    )
    parser.add_argument("--berkeley-prefix", default="milling_berkeley")
    parser.add_argument("--umich-prefix", default="milling_umich")
    parser.add_argument("--umich-channel-set", choices=["all_currents", "dynamic_currents"], default="all_currents")
    args = parser.parse_args()
    proc_dir = Path(args.proc_dir)
    proc_dir.mkdir(parents=True, exist_ok=True)
    include_berkeley = "berkeley" in args.datasets
    include_umich = "umich" in args.datasets
    umich_channels = UMICH_CHANNELS_DYNAMIC if args.umich_channel_set == "dynamic_currents" else UMICH_CHANNELS
    berkeley_rows = (
        preprocess_berkeley(Path(args.berkeley_dir), proc_dir, args.berkeley_label_scheme, args.berkeley_prefix)
        if include_berkeley
        else []
    )
    umich_rows = preprocess_umich(Path(args.umich_dir), proc_dir, umich_channels, args.umich_prefix) if include_umich else []
    write_specs(
        proc_dir,
        berkeley_rows,
        umich_rows,
        Path(args.out_dir),
        args.berkeley_label_scheme,
        args.berkeley_prefix,
        args.umich_prefix,
        umich_channels,
        include_berkeley,
        include_umich,
    )
    if include_berkeley:
        print("Berkeley train", counts_for_npz(proc_dir / f"{args.berkeley_prefix}_train.npz"))
        print("Berkeley test", counts_for_npz(proc_dir / f"{args.berkeley_prefix}_test.npz"))
    if include_umich:
        print("UMich train", counts_for_npz(proc_dir / f"{args.umich_prefix}_train.npz"))
        print("UMich test", counts_for_npz(proc_dir / f"{args.umich_prefix}_test.npz"))


if __name__ == "__main__":
    main()
