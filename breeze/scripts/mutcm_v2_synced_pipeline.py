"""MU-TCM v2 synced-MAT no-API pipeline.

This script is a pre-preregistration audit only.  It:

- extracts only `full_dataset/signals_synced/*.mat` from the archive;
- builds Scheme-A metadata and feature NPZ files;
- builds a capped window-level NPZ from synced MAT signals;
- constructs grouped inner-validation diagnostics;
- runs no-API baselines.

It never extracts `signals_unsynced`, never calls an LLM/API, and never runs a
formal held-out test.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import loadmat
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


FILENAME_RE = re.compile(
    r"Insert(?P<insert>\d+)Edge(?P<edge>\d+)_Vc(?P<Vc>[-+0-9.]+)_fz(?P<fz>[-+0-9.]+)_"
    r"ap(?P<ap>[-+0-9.]+)_VB(?P<VB>[-+0-9.]+)_Rep(?P<rep>\d+)\.mat$"
)
CLASSES = ["healthy", "worn"]
TARGET_FS_HZ = 2000.0
WINDOW_SECS = [0.5, 1.0]
OVERLAP = 0.5
MAX_WINDOWS_PER_EXPERIMENT = 12
SIGNAL_CHANNELS = [
    "Fx",
    "Fy",
    "Fz",
    "Ax",
    "Ay",
    "Az",
    "AE_RMS",
    "SREAL",
    "CV3_S",
    "CV3_X",
    "CV3_Y",
    "CV3_Z",
    "TV2_S",
    "TV2_X",
    "TV2_Y",
    "TV2_Z",
    "TV50",
    "TV51",
    "FREAL",
]
CNC_CHANNELS = [
    "SREAL",
    "CV3_S",
    "CV3_X",
    "CV3_Y",
    "CV3_Z",
    "TV2_S",
    "TV2_X",
    "TV2_Y",
    "TV2_Z",
    "TV50",
    "TV51",
    "FREAL",
]
FAST_CHANNELS = ["Fx", "Fy", "Fz", "Ax", "Ay", "Az"]
AE_CHANNELS = ["AE_RMS"]
META_DROP = {
    "_file_name",
    "RPM_avg",
    "material",
    "Vc",
    "fz",
    "ap",
    "ae",
    "VB",
    "Insert",
    "Edge",
    "Repetition",
    "experiment_id",
    "sample_id",
    "rounded_VB",
    "label_scheme_A",
    "condition_id",
    "insert_edge_id",
    "Lubrication",
}
LEAK_PATTERNS = ("vb", "file", "filename", "_name", "label")
SIGNAL_SUFFIXES = (
    "_rms",
    "_var",
    "_max",
    "_kurt",
    "_skew",
    "_ptp",
    "_speckurt",
    "_specskew",
    "_wavenergy",
)


def parse_filename(name: str) -> dict[str, Any]:
    m = FILENAME_RE.match(name)
    if not m:
        return {"filename_parse_ok": False}
    out: dict[str, Any] = {"filename_parse_ok": True}
    for key, value in m.groupdict().items():
        out[key] = int(value) if key in {"insert", "edge", "rep"} else float(value)
    return out


def rounded_vb(vb: float) -> float:
    return round(float(vb), 1)


def label_scheme_a(vb: float) -> str:
    level = rounded_vb(vb)
    if level in {0.0, 0.1}:
        return "healthy"
    if level in {0.2, 0.3}:
        return "worn"
    return "unlabeled"


def lubrication_from_material(material: str) -> str:
    if "CastIron" in material:
        return "Dry"
    if "StainlessSteel" in material:
        return "MQL"
    return "unknown"


def read_stats(csv_dir: Path) -> pd.DataFrame:
    path = csv_dir / "signals_stats.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, sep=";")


def build_metadata(stats: pd.DataFrame, extract_root: Path) -> pd.DataFrame:
    rows = []
    for i, row in stats.reset_index(drop=True).iterrows():
        fname = str(row["_file_name"])
        parsed = parse_filename(fname)
        insert = int(parsed.get("insert", -1))
        edge = int(parsed.get("edge", -1))
        rep = int(parsed.get("rep", -1))
        material = str(row["material"])
        vb = float(row["VB"])
        label = label_scheme_a(vb)
        if label == "unlabeled":
            raise RuntimeError(f"Scheme A produced unlabeled row for {fname} VB={vb}")
        condition_id = f"{material}|Vc{float(row['Vc']):g}|fz{float(row['fz']):g}|ap{float(row['ap']):g}|ae{float(row['ae']):g}"
        insert_edge_id = f"Insert{insert}_Edge{edge}"
        rows.append(
            {
                "sample_id": f"mutcm_{i:03d}",
                "file_name": fname,
                "experiment_id": Path(fname).stem,
                "mat_path": str(extract_root / "full_dataset" / "signals_synced" / fname),
                "Insert": insert,
                "Edge": edge,
                "Repetition": rep,
                "material": material,
                "Lubrication": lubrication_from_material(material),
                "Vc": float(row["Vc"]),
                "fz": float(row["fz"]),
                "ap": float(row["ap"]),
                "ae": float(row["ae"]),
                "VB": vb,
                "rounded_VB": rounded_vb(vb),
                "label_scheme_A": label,
                "y": CLASSES.index(label),
                "condition_id": condition_id,
                "insert_edge_id": insert_edge_id,
                "group_experiment": fname,
                "filename_parse_ok": bool(parsed.get("filename_parse_ok", False)),
            }
        )
    return pd.DataFrame(rows)


def safe_feature_cols(stats: pd.DataFrame) -> list[str]:
    cols = []
    for col in stats.columns:
        low = col.lower()
        if col in META_DROP:
            continue
        if any(p in low for p in LEAK_PATTERNS):
            continue
        if col.endswith("_start") or col.endswith("_end"):
            continue
        if col.endswith(SIGNAL_SUFFIXES):
            cols.append(col)
    return cols


def feature_matrix(stats: pd.DataFrame, cols: list[str]) -> np.ndarray:
    X = stats[cols].replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median(numeric_only=True)).fillna(0.0)
    return X.to_numpy(dtype=np.float32)


def archive_listing(archive: Path) -> list[str]:
    proc = subprocess.run(["bsdtar", "-tf", str(archive)], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "bsdtar archive listing failed")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def extract_synced(archive: Path, extract_root: Path, expected_files: set[str], out_dir: Path) -> None:
    synced_dir = extract_root / "full_dataset" / "signals_synced"
    synced_dir.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in synced_dir.glob("*.mat")}
    missing = sorted(expected_files - existing)
    t0 = time.time()
    if missing:
        cmd = [
            "bsdtar",
            "-xf",
            str(archive),
            "-C",
            str(extract_root),
            "full_dataset/signals_synced",
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "bsdtar synced extraction failed")
    final = {p.name for p in synced_dir.glob("*.mat")}
    rows = []
    for name in sorted(expected_files):
        path = synced_dir / name
        rows.append({"file_name": name, "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else 0})
    with (out_dir / "mutcm_v2_synced_file_sizes.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file_name", "exists", "size_bytes"])
        writer.writeheader()
        writer.writerows(rows)
    missing_after = sorted(expected_files - final)
    extra = sorted(final - expected_files)
    lines = [
        "# MU-TCM v2 Synced MAT Extract Report",
        "",
        "- Mode: extracted only `full_dataset/signals_synced` from `full_dataset.7z`.",
        "- `signals_unsynced` was not extracted.",
        f"- Expected synced MAT from `signals_stats.csv`: `{len(expected_files)}`",
        f"- Existing before extraction: `{len(existing)}`",
        f"- Present after extraction: `{len(final & expected_files)}`",
        f"- Missing after extraction: `{missing_after}`",
        f"- Extra synced MAT files: `{extra}`",
        f"- Elapsed seconds: `{time.time() - t0:.1f}`",
        f"- File-size table: `mutcm_v2_synced_file_sizes.csv`",
    ]
    (out_dir / "mutcm_v2_synced_extract_report.md").write_text("\n".join(lines) + "\n")


def save_metadata_index(meta: pd.DataFrame, out_dir: Path) -> None:
    meta.to_csv(out_dir / "mutcm_v2_metadata_index.csv", index=False)
    counts = Counter(meta["label_scheme_A"])
    lines = [
        "# MU-TCM v2 Metadata Index Report",
        "",
        f"- Rows: `{len(meta)}`",
        f"- Labels: `{dict(counts)}`",
        f"- Conditions: `{meta['condition_id'].nunique()}`",
        f"- Insert-edge groups: `{meta['insert_edge_id'].nunique()}`",
        f"- Repetitions: `{sorted(int(v) for v in meta['Repetition'].unique())}`",
        f"- Missing MAT files: `{int((~meta['mat_path'].map(lambda p: Path(str(p)).exists())).sum())}`",
        "- Insert/Edge/Repetition are group/diagnostic fields, not safe model features.",
    ]
    (out_dir / "mutcm_v2_metadata_index_report.md").write_text("\n".join(lines) + "\n")


def save_experiment_npz(stats: pd.DataFrame, meta: pd.DataFrame, out_dir: Path, proc_dir: Path) -> tuple[np.ndarray, list[str]]:
    cols = safe_feature_cols(stats)
    X = feature_matrix(stats, cols)
    y = meta["y"].to_numpy(dtype=np.int64)
    proc_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        proc_dir / "mutcm_v2_schemeA_experiment_features.npz",
        X=X,
        y=y,
        class_names=np.asarray(CLASSES),
        feature_names=np.asarray(cols),
        sample_id=meta["sample_id"].to_numpy(str),
        file_name=meta["file_name"].to_numpy(str),
        condition_id=meta["condition_id"].to_numpy(str),
        insert_edge_id=meta["insert_edge_id"].to_numpy(str),
        group_experiment=meta["group_experiment"].to_numpy(str),
        material=meta["material"].to_numpy(str),
        lubrication=meta["Lubrication"].to_numpy(str),
        Vc=meta["Vc"].to_numpy(float),
        fz=meta["fz"].to_numpy(float),
        ap=meta["ap"].to_numpy(float),
        ae=meta["ae"].to_numpy(float),
        VB=meta["VB"].to_numpy(float),
        rounded_VB=meta["rounded_VB"].to_numpy(float),
        Insert=meta["Insert"].to_numpy(int),
        Edge=meta["Edge"].to_numpy(int),
        Repetition=meta["Repetition"].to_numpy(int),
        feature_definition=np.asarray(
            ["signals_stats.csv signal statistics only; removed filename/VB/labels/metadata/start/end leakage columns"]
        ),
    )
    lines = [
        "# MU-TCM v2 Experiment Feature Report",
        "",
        f"- Output NPZ: `proc/mutcm_v2_schemeA_experiment_features.npz`",
        f"- Shape: `{X.shape}`",
        f"- Signal feature columns: `{len(cols)}`",
        f"- Class counts: `{dict(Counter(meta['label_scheme_A']))}`",
        "- Feature source: official `signals_stats.csv` time/frequency/time-frequency statistics.",
        "- Removed fields: `_file_name`, `VB`, rounded VB, labels, Insert/Edge/Repetition, material/Vc/fz/ap/ae/Lubrication and start/end sync fields.",
    ]
    (out_dir / "mutcm_v2_experiment_feature_report.md").write_text("\n".join(lines) + "\n")
    return X, cols


def mat_scalar(value: Any) -> Any:
    arr = np.asarray(value)
    if arr.size == 1:
        return arr.reshape(-1)[0].item()
    return value


def resample_channel(x: np.ndarray, src_fs: float, duration: float, target_fs: float) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    x = x[np.isfinite(x)]
    if x.size < 2 or duration <= 0:
        return np.zeros((0,), dtype=np.float32)
    target_len = int(duration * target_fs)
    if target_len < 2:
        return np.zeros((0,), dtype=np.float32)
    src_t = np.linspace(0.0, duration, num=x.size, endpoint=False, dtype=np.float64)
    tgt_t = np.arange(target_len, dtype=np.float64) / target_fs
    return np.interp(tgt_t, src_t, x).astype(np.float32)


def channel_source_fs(ch: str, mat: dict[str, Any]) -> float:
    if ch in AE_CHANNELS:
        time1 = np.asarray(mat.get("time1", []), dtype=float).reshape(-1)
        return float(1.0 / np.median(np.diff(time1[: min(len(time1), 10000)]))) if len(time1) > 2 else 1_000_000.0
    if ch in FAST_CHANNELS:
        time2 = np.asarray(mat.get("time2", []), dtype=float).reshape(-1)
        return float(1.0 / np.median(np.diff(time2[: min(len(time2), 10000)]))) if len(time2) > 2 else 50_000.0
    return 250.0


def load_resampled_matrix(mat_path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    mat = loadmat(mat_path, squeeze_me=True, struct_as_record=False, variable_names=SIGNAL_CHANNELS + ["time1", "time2", "VB", "Vc", "fz", "ap", "ae", "Insert", "Edge"])
    durations = []
    for ch in SIGNAL_CHANNELS:
        if ch not in mat:
            continue
        fs = channel_source_fs(ch, mat)
        x = np.asarray(mat[ch]).reshape(-1)
        if len(x) > 2 and fs > 0:
            durations.append(len(x) / fs)
    duration = float(min(durations)) if durations else 0.0
    channels = []
    for ch in SIGNAL_CHANNELS:
        if ch in mat:
            fs = channel_source_fs(ch, mat)
            y = resample_channel(np.asarray(mat[ch]), fs, duration, TARGET_FS_HZ)
        else:
            y = np.zeros((int(duration * TARGET_FS_HZ),), dtype=np.float32)
        channels.append(y)
    min_len = min((len(c) for c in channels), default=0)
    if min_len == 0:
        return np.zeros((len(SIGNAL_CHANNELS), 0), dtype=np.float32), {"duration_sec": duration}
    M = np.stack([c[:min_len] for c in channels]).astype(np.float32)
    return M, {"duration_sec": duration}


def window_tag(window_sec: float) -> str:
    return str(window_sec).replace(".", "p")


def sample_windows(M: np.ndarray, window_sec: float) -> np.ndarray:
    win = int(window_sec * TARGET_FS_HZ)
    step = int(win * (1.0 - OVERLAP))
    if M.shape[1] < win or step <= 0:
        return np.zeros((0, M.shape[0], win), dtype=np.float32)
    starts = np.arange(0, M.shape[1] - win + 1, step)
    if len(starts) > MAX_WINDOWS_PER_EXPERIMENT:
        idx = np.linspace(0, len(starts) - 1, MAX_WINDOWS_PER_EXPERIMENT).round().astype(int)
        starts = starts[idx]
    return np.stack([M[:, s : s + win] for s in starts]).astype(np.float32)


def build_window_npz(meta: pd.DataFrame, out_dir: Path, proc_dir: Path) -> None:
    out_paths = {sec: proc_dir / f"mutcm_v2_schemeA_window_signal_{window_tag(sec)}s.npz" for sec in WINDOW_SECS}
    canonical_sec = 1.0
    canonical_path = proc_dir / "mutcm_v2_schemeA_window_signal.npz"
    if all(p.exists() for p in out_paths.values()) and canonical_path.exists():
        lines = ["# MU-TCM v2 Window Build Report", "", "- Existing NPZ files were reused for resumability."]
        for sec, path in out_paths.items():
            data = np.load(path, allow_pickle=True)
            lines.extend(
                [
                    "",
                    f"## {sec:.1f}s Windows",
                    "",
                    f"- Output NPZ: `{path}`",
                    f"- Shape: `{tuple(data['X'].shape)}`",
                    f"- Window sec: `{float(data['window_sec'])}`",
                    f"- Target fs: `{float(data['fs_hz'])}`",
                ]
            )
        lines.extend(["", f"- Canonical NPZ: `{canonical_path}` mirrors `{out_paths[canonical_sec]}`."])
        (out_dir / "mutcm_v2_window_build_report.md").write_text("\n".join(lines) + "\n")
        return
    per_sec: dict[float, dict[str, Any]] = {}
    for sec in WINDOW_SECS:
        per_sec[sec] = {
            "Xs": [],
            "ys": [],
            "sample_ids": [],
            "condition_ids": [],
            "insert_edges": [],
            "file_names": [],
        }
    report_rows = []
    channel_values = defaultdict(list)
    for row in meta.to_dict(orient="records"):
        mat_path = Path(str(row["mat_path"]))
        M, info = load_resampled_matrix(mat_path)
        finite = np.isfinite(M)
        nan_inf = int((~finite).sum())
        if nan_inf:
            M = np.nan_to_num(M, nan=0.0, posinf=0.0, neginf=0.0)
        for ci, ch in enumerate(SIGNAL_CHANNELS):
            if M.shape[1]:
                vals = M[ci]
                channel_values[ch].append((float(np.min(vals)), float(np.max(vals)), float(np.mean(vals)), float(np.std(vals))))
        for sec in WINDOW_SECS:
            W = sample_windows(M, sec)
            n = len(W)
            store = per_sec[sec]
            store["Xs"].append(W)
            store["ys"].append(np.full(n, int(row["y"]), dtype=np.int64))
            store["sample_ids"].extend([str(row["sample_id"])] * n)
            store["condition_ids"].extend([str(row["condition_id"])] * n)
            store["insert_edges"].extend([str(row["insert_edge_id"])] * n)
            store["file_names"].extend([str(row["file_name"])] * n)
            report_rows.append(
                {
                    "sample_id": row["sample_id"],
                    "file_name": row["file_name"],
                    "label": row["label_scheme_A"],
                    "condition_id": row["condition_id"],
                    "insert_edge_id": row["insert_edge_id"],
                    "window_sec": sec,
                    "duration_sec": info.get("duration_sec", 0.0),
                    "resampled_samples": int(M.shape[1]),
                    "windows": n,
                    "too_short": bool(n == 0),
                    "nan_inf_count": nan_inf,
                }
            )
    saved: dict[float, tuple[Path, tuple[int, ...], dict[str, int], Counter[str], Counter[str], int, int]] = {}
    for sec, store in per_sec.items():
        win = int(sec * TARGET_FS_HZ)
        X = np.concatenate(store["Xs"]).astype(np.float32) if store["Xs"] else np.zeros((0, len(SIGNAL_CHANNELS), win), dtype=np.float32)
        y = np.concatenate(store["ys"]).astype(np.int64) if store["ys"] else np.zeros((0,), dtype=np.int64)
        out_path = out_paths[sec]
        np.savez_compressed(
            out_path,
            X=X,
            y=y,
            class_names=np.asarray(CLASSES),
            channels=np.asarray(SIGNAL_CHANNELS),
            fs_hz=np.asarray(TARGET_FS_HZ),
            window_sec=np.asarray(sec),
            overlap=np.asarray(OVERLAP),
            max_windows_per_experiment=np.asarray(MAX_WINDOWS_PER_EXPERIMENT),
            sample_id=np.asarray(store["sample_ids"]),
            file_name=np.asarray(store["file_names"]),
            condition_id=np.asarray(store["condition_ids"]),
            insert_edge_id=np.asarray(store["insert_edges"]),
            group_experiment=np.asarray(store["file_names"]),
            window_definition=np.asarray(
                [
                    f"synced MAT only; channels resampled to 2 kHz; {sec:.1f} s windows; 50% overlap; max 12 windows per experiment; split by experiment"
                ]
            ),
        )
        if sec == canonical_sec:
            np.savez_compressed(
                canonical_path,
                X=X,
                y=y,
                class_names=np.asarray(CLASSES),
                channels=np.asarray(SIGNAL_CHANNELS),
                fs_hz=np.asarray(TARGET_FS_HZ),
                window_sec=np.asarray(sec),
                overlap=np.asarray(OVERLAP),
                max_windows_per_experiment=np.asarray(MAX_WINDOWS_PER_EXPERIMENT),
                sample_id=np.asarray(store["sample_ids"]),
                file_name=np.asarray(store["file_names"]),
                condition_id=np.asarray(store["condition_ids"]),
                insert_edge_id=np.asarray(store["insert_edges"]),
                group_experiment=np.asarray(store["file_names"]),
                window_definition=np.asarray(
                    [
                        f"synced MAT only; channels resampled to 2 kHz; {sec:.1f} s windows; 50% overlap; max 12 windows per experiment; split by experiment"
                    ]
                ),
            )
        class_counts = {CLASSES[i]: int((y == i).sum()) for i in range(len(CLASSES))}
        condition_counts = Counter(store["condition_ids"])
        insert_counts = Counter(store["insert_edges"])
        too_short = sum(1 for r in report_rows if float(r["window_sec"]) == sec and r["too_short"])
        nan_inf_total = sum(int(r["nan_inf_count"]) for r in report_rows if float(r["window_sec"]) == sec)
        saved[sec] = (out_path, tuple(X.shape), class_counts, condition_counts, insert_counts, too_short, nan_inf_total)
    pd.DataFrame(report_rows).to_csv(out_dir / "mutcm_v2_window_counts_by_experiment.csv", index=False)
    channel_rows = []
    for ch, vals in channel_values.items():
        arr = np.asarray(vals, dtype=float)
        channel_rows.append(
            {
                "channel": ch,
                "min": float(np.min(arr[:, 0])),
                "max": float(np.max(arr[:, 1])),
                "mean_of_means": float(np.mean(arr[:, 2])),
                "max_std": float(np.max(arr[:, 3])),
            }
        )
    pd.DataFrame(channel_rows).to_csv(out_dir / "mutcm_v2_window_channel_stats.csv", index=False)
    lines = [
        "# MU-TCM v2 Window Build Report",
        "",
        f"- Window secs: `{WINDOW_SECS}`",
        f"- Overlap: `{OVERLAP}`",
        f"- Target fs: `{TARGET_FS_HZ}`",
        f"- Max windows per experiment: `{MAX_WINDOWS_PER_EXPERIMENT}`",
        f"- Canonical NPZ: `{canonical_path}` mirrors `{out_paths[canonical_sec]}`.",
        "- Per-experiment window table: `mutcm_v2_window_counts_by_experiment.csv`",
        "- Channel statistic table: `mutcm_v2_window_channel_stats.csv`",
    ]
    for sec in WINDOW_SECS:
        out_path, shape, class_counts, condition_counts, insert_counts, too_short, nan_inf_total = saved[sec]
        lines.extend(
            [
                "",
                f"## {sec:.1f}s Windows",
                "",
                f"- Output NPZ: `{out_path}`",
                f"- Shape: `{shape}`",
                f"- Class window counts: `{class_counts}`",
                f"- Conditions: `{len(condition_counts)}`",
                f"- Insert-edge groups: `{len(insert_counts)}`",
                f"- Experiments too short: `{too_short}`",
                f"- NaN/Inf total: `{nan_inf_total}`",
            ]
        )
    (out_dir / "mutcm_v2_window_build_report.md").write_text("\n".join(lines) + "\n")


def choose_inner_split(meta: pd.DataFrame) -> tuple[set[str], pd.DataFrame]:
    conds = sorted(meta["condition_id"].unique())
    target = 0.25 * len(meta)
    best: tuple[float, float, tuple[str, ...]] | None = None
    best_subset: tuple[str, ...] | None = None
    for r in range(2, min(4, len(conds)) + 1):
        for subset in combinations(conds, r):
            val = meta[meta["condition_id"].isin(subset)]
            train = meta[~meta["condition_id"].isin(subset)]
            if val["material"].nunique() < 2 or train["material"].nunique() < 2:
                continue
            val_counts = Counter(val["label_scheme_A"])
            train_counts = Counter(train["label_scheme_A"])
            if any(val_counts.get(label, 0) < 2 for label in CLASSES):
                continue
            if any(train_counts.get(label, 0) < 10 for label in CLASSES):
                continue
            balance_err = abs(val_counts["healthy"] - val_counts["worn"]) + abs(train_counts["healthy"] - train_counts["worn"])
            size_err = abs(len(val) - target)
            key = (size_err, balance_err, subset)
            if best is None or key < best:
                best = key
                best_subset = subset
    if best_subset is None:
        raise RuntimeError("could not construct condition-aware inner split")
    rows = []
    for split_name, frame in [("inner_train", meta[~meta["condition_id"].isin(best_subset)]), ("inner_val", meta[meta["condition_id"].isin(best_subset)])]:
        for _, row in frame.iterrows():
            rows.append(
                {
                    "sample_id": row["sample_id"],
                    "file_name": row["file_name"],
                    "split": split_name,
                    "label": row["label_scheme_A"],
                    "condition_id": row["condition_id"],
                    "insert_edge_id": row["insert_edge_id"],
                    "material": row["material"],
                    "rounded_VB": row["rounded_VB"],
                }
            )
    return set(best_subset), pd.DataFrame(rows)


def write_split_report(meta: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    val_conditions, split_df = choose_inner_split(meta)
    split_df.to_csv(out_dir / "mutcm_v2_inner_split_assignments.csv", index=False)
    lines = [
        "# MU-TCM v2 Split Report",
        "",
        "- Split A: condition-aware grouped inner split, group unit is experiment/MAT file, validation selected by condition groups.",
        f"- Validation conditions: `{sorted(val_conditions)}`",
        "- Split B: GroupKFold by condition is used as a diagnostic baseline protocol.",
        "- Split C: GroupKFold by insert_edge is used to diagnose tool identity leakage.",
        "- Random window split is forbidden and not used.",
        "",
        "## Split A Counts",
        "",
    ]
    for split in ["inner_train", "inner_val"]:
        sub = split_df[split_df["split"] == split]
        lines.append(f"- {split} labels: `{dict(Counter(sub['label']))}`")
        lines.append(f"- {split} conditions: `{dict(Counter(sub['condition_id']))}`")
        lines.append(f"- {split} insert_edge: `{dict(Counter(sub['insert_edge_id']))}`")
        counts = Counter(sub["label"])
        lines.append(f"- {split} supports n_real=2/5/10: `{counts.get('healthy',0)>=10 and counts.get('worn',0)>=10}`")
    (out_dir / "mutcm_v2_split_report.md").write_text("\n".join(lines) + "\n")
    return split_df


def meta_matrix(meta: pd.DataFrame, leaky: bool) -> np.ndarray:
    categorical = ["material", "Lubrication"]
    numeric = ["Vc", "fz", "ap", "ae"]
    if leaky:
        categorical += ["insert_edge_id"]
        numeric += ["Insert", "Edge", "Repetition"]
    enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    Xc = enc.fit_transform(meta[categorical].astype(str))
    Xn = meta[numeric].astype(float).to_numpy()
    return np.concatenate([Xc, Xn], axis=1).astype(np.float32)


def make_et(seed: int) -> ExtraTreesClassifier:
    return ExtraTreesClassifier(n_estimators=300, class_weight="balanced", random_state=seed, min_samples_leaf=1)


def select_n_per_class(train_idx: np.ndarray, y: np.ndarray, n_real: int, rng: np.random.Generator) -> np.ndarray:
    if n_real >= 9999:
        return train_idx
    selected = []
    for ci in range(len(CLASSES)):
        cls_idx = train_idx[y[train_idx] == ci]
        if len(cls_idx) < n_real:
            raise RuntimeError(f"not enough class {ci}: need {n_real}, have {len(cls_idx)}")
        selected.extend(rng.choice(cls_idx, size=n_real, replace=False).tolist())
    return np.asarray(selected, dtype=int)


def eval_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, dict[str, float], list[list[int]]]:
    acc = float(accuracy_score(y_true, y_pred))
    macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    _, _, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=list(range(len(CLASSES))), zero_division=0)
    return acc, macro, {CLASSES[i]: float(f1[i]) for i in range(len(CLASSES))}, confusion_matrix(y_true, y_pred, labels=list(range(len(CLASSES))).copy()).tolist()


def majority_predict(y_train: np.ndarray, n: int) -> np.ndarray:
    maj = Counter(y_train).most_common(1)[0][0]
    return np.full(n, int(maj), dtype=int)


def noise_augment(X: np.ndarray, y: np.ndarray, seed: int, target_per_class: int = 20) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    std = np.std(X, axis=0, keepdims=True) + 1e-6
    Xs = [X]
    ys = [y]
    for ci in range(len(CLASSES)):
        cls = X[y == ci]
        if len(cls) == 0:
            continue
        need = max(0, target_per_class - len(cls))
        if need == 0:
            continue
        base = cls[rng.integers(0, len(cls), size=need)]
        Xs.append(base + rng.normal(0.0, 0.05, size=base.shape).astype(np.float32) * std)
        ys.append(np.full(need, ci, dtype=int))
    return np.concatenate(Xs).astype(np.float32), np.concatenate(ys).astype(int)


def random_open_loop_aug(X: np.ndarray, y: np.ndarray, seed: int, target_per_class: int = 20) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    mu = np.mean(X, axis=0)
    std = np.std(X, axis=0) + 1e-6
    Xs = [X]
    ys = [y]
    for ci in range(len(CLASSES)):
        need = max(0, target_per_class - int((y == ci).sum()))
        if need:
            Xs.append((mu + rng.normal(0.0, 1.5, size=(need, X.shape[1])) * std).astype(np.float32))
            ys.append(np.full(need, ci, dtype=int))
    return np.concatenate(Xs).astype(np.float32), np.concatenate(ys).astype(int)


def physical_rule_score(feature_names: list[str], X: np.ndarray) -> np.ndarray:
    names = np.asarray(feature_names)
    groups = []
    for token in ["_rms", "_ptp", "_wavenergy", "_kurt"]:
        idx = np.asarray([i for i, name in enumerate(names) if name.endswith(token) and any(prefix in name for prefix in ["Fx", "Fy", "Fz", "Ax", "Ay", "Az", "AE_"])])
        if len(idx):
            Z = X[:, idx]
            Z = (Z - np.median(Z, axis=0)) / (np.std(Z, axis=0) + 1e-6)
            groups.append(np.mean(Z, axis=1))
    if not groups:
        return np.zeros((len(X),), dtype=float)
    return np.mean(np.stack(groups, axis=1), axis=1)


def run_inner_baselines(
    X_signal: np.ndarray,
    X_meta_safe: np.ndarray,
    X_meta_leaky: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    meta: pd.DataFrame,
    split_df: pd.DataFrame,
    out_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_ids = set(split_df[split_df["split"] == "inner_train"]["sample_id"])
    val_ids = set(split_df[split_df["split"] == "inner_val"]["sample_id"])
    train_idx = np.asarray([i for i, sid in enumerate(meta["sample_id"]) if sid in train_ids], dtype=int)
    val_idx = np.asarray([i for i, sid in enumerate(meta["sample_id"]) if sid in val_ids], dtype=int)
    rows = []
    f1_rows = []
    cm_rows = []
    n_reals = [2, 5, 10, 9999]
    score_all = physical_rule_score(feature_names, X_signal)
    for n_real in n_reals:
        for seed in range(20):
            rng = np.random.default_rng(seed)
            sel = select_n_per_class(train_idx, y, n_real, rng)
            configs = []
            configs.append(("majority", None, X_signal))
            configs.append(("metadata_safe", "meta", X_meta_safe))
            configs.append(("metadata_leaky_diagnostic", "meta", X_meta_leaky))
            configs.append(("real_only", "signal", X_signal))
            configs.append(("noise_aug", "noise", X_signal))
            configs.append(("random_open_loop", "random", X_signal))
            for baseline, mode, Xbase in configs:
                if baseline == "majority":
                    pred = majority_predict(y[sel], len(val_idx))
                elif mode == "noise":
                    Xa, ya = noise_augment(Xbase[sel], y[sel], seed)
                    clf = make_et(seed)
                    clf.fit(Xa, ya)
                    pred = clf.predict(Xbase[val_idx])
                elif mode == "random":
                    Xa, ya = random_open_loop_aug(Xbase[sel], y[sel], seed)
                    clf = make_et(seed)
                    clf.fit(Xa, ya)
                    pred = clf.predict(Xbase[val_idx])
                elif mode == "meta":
                    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed))
                    clf.fit(Xbase[sel], y[sel])
                    pred = clf.predict(Xbase[val_idx])
                else:
                    clf = make_et(seed)
                    clf.fit(Xbase[sel], y[sel])
                    pred = clf.predict(Xbase[val_idx])
                acc, macro, f1, cm = eval_predictions(y[val_idx], pred)
                rows.append(
                    {
                        "baseline": baseline,
                        "n_real": n_real,
                        "seed": seed,
                        "acc": acc,
                        "macro_f1": macro,
                        "majority_acc_val": max(Counter(y[val_idx]).values()) / len(val_idx),
                        "train_real_count": int(len(sel)),
                    }
                )
                for cls, value in f1.items():
                    f1_rows.append({"baseline": baseline, "n_real": n_real, "seed": seed, "class": cls, "f1": value})
                for i, actual in enumerate(CLASSES):
                    for j, predicted in enumerate(CLASSES):
                        cm_rows.append({"baseline": baseline, "n_real": n_real, "seed": seed, "actual": actual, "predicted": predicted, "n": int(cm[i][j])})
            # Rule is deterministic from signal score; threshold uses train score median only.
            thr = float(np.median(score_all[sel]))
            pred = (score_all[val_idx] > thr).astype(int)
            acc, macro, f1, cm = eval_predictions(y[val_idx], pred)
            rows.append(
                {
                    "baseline": "rule",
                    "n_real": n_real,
                    "seed": seed,
                    "acc": acc,
                    "macro_f1": macro,
                    "majority_acc_val": max(Counter(y[val_idx]).values()) / len(val_idx),
                    "train_real_count": int(len(sel)),
                }
            )
            for cls, value in f1.items():
                f1_rows.append({"baseline": "rule", "n_real": n_real, "seed": seed, "class": cls, "f1": value})
            for i, actual in enumerate(CLASSES):
                for j, predicted in enumerate(CLASSES):
                    cm_rows.append({"baseline": "rule", "n_real": n_real, "seed": seed, "actual": actual, "predicted": predicted, "n": int(cm[i][j])})
    summary = pd.DataFrame(rows)
    per_class = pd.DataFrame(f1_rows)
    confusions = pd.DataFrame(cm_rows)
    summary.to_csv(out_dir / "mutcm_v2_noapi_baseline_summary.csv", index=False)
    per_class.to_csv(out_dir / "mutcm_v2_noapi_per_class_f1.csv", index=False)
    confusions.to_csv(out_dir / "mutcm_v2_noapi_confusions.csv", index=False)
    return summary, per_class, confusions


def groupkfold_signal_check(X: np.ndarray, y: np.ndarray, groups: np.ndarray, seed: int = 0) -> dict[str, float]:
    n_splits = min(5, len(np.unique(groups)))
    preds = np.full_like(y, -1)
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        clf = make_et(seed)
        clf.fit(X[tr], y[tr])
        preds[te] = clf.predict(X[te])
    acc, macro, _, _ = eval_predictions(y, preds)
    return {"acc": acc, "macro_f1": macro, "majority_acc": max(Counter(y).values()) / len(y)}


def write_gate_report(summary: pd.DataFrame, meta: pd.DataFrame, X_signal: np.ndarray, y: np.ndarray, out_dir: Path) -> None:
    means = summary.groupby(["baseline", "n_real"], as_index=False).agg(mean_acc=("acc", "mean"), mean_macro_f1=("macro_f1", "mean"))
    means.to_csv(out_dir / "mutcm_v2_noapi_baseline_means.csv", index=False)
    def get(baseline: str, n_real: int) -> tuple[float, float]:
        row = means[(means["baseline"] == baseline) & (means["n_real"] == n_real)].iloc[0]
        return float(row["mean_acc"]), float(row["mean_macro_f1"])
    real_full = get("real_only", 9999)
    real_n10 = get("real_only", 10)
    meta_full = get("metadata_safe", 9999)
    rule_full = get("rule", 9999)
    cond_check = groupkfold_signal_check(X_signal, y, meta["condition_id"].to_numpy(str))
    edge_check = groupkfold_signal_check(X_signal, y, meta["insert_edge_id"].to_numpy(str))
    conditions = {
        "real_only_full_acc_macro": real_full[0] >= 0.75 and real_full[1] >= 0.70,
        "real_only_n10_acc_macro": real_n10[0] > 0.60 and real_n10[1] > 0.60,
        "metadata_safe_not_close_to_signal": meta_full[0] < 0.95 and meta_full[0] < real_full[0] - 0.05,
        "insert_edge_group_signal_above_majority": edge_check["acc"] > edge_check["majority_acc"] and edge_check["macro_f1"] > 0.60,
        "condition_group_signal_above_majority": cond_check["acc"] > cond_check["majority_acc"] and cond_check["macro_f1"] > 0.60,
        "rule_not_saturated": rule_full[0] <= 0.95,
    }
    passed = all(conditions.values())
    lines = [
        "# MU-TCM v2 No-API Gate Report",
        "",
        "Status: no LLM/API, no preregistration, no formal test.",
        f"- Gate passed: `{passed}`",
        "",
        "## Key Metrics",
        "",
        f"- real_only full Acc/Macro-F1: `{real_full[0]:.4f}/{real_full[1]:.4f}`",
        f"- real_only n_real=10 Acc/Macro-F1: `{real_n10[0]:.4f}/{real_n10[1]:.4f}`",
        f"- metadata_safe full Acc/Macro-F1: `{meta_full[0]:.4f}/{meta_full[1]:.4f}`",
        f"- rule full Acc/Macro-F1: `{rule_full[0]:.4f}/{rule_full[1]:.4f}`",
        f"- signal GroupKFold by condition Acc/Macro-F1: `{cond_check['acc']:.4f}/{cond_check['macro_f1']:.4f}` majority `{cond_check['majority_acc']:.4f}`",
        f"- signal GroupKFold by insert_edge Acc/Macro-F1: `{edge_check['acc']:.4f}/{edge_check['macro_f1']:.4f}` majority `{edge_check['majority_acc']:.4f}`",
        "",
        "## Conditions",
        "",
    ]
    for key, value in conditions.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Decision",
            "",
        ]
    )
    if passed:
        lines.extend(
            [
                "- No-API gate passed. MU-TCM may proceed to a separate v3 LLM inner-val attack only after freezing label scheme, split protocol, feature/window strategy, baselines, n_real/n_syn search, success criterion, Holm protocol, and API budget.",
                "- Formal held-out test is still forbidden until preregistration is written.",
            ]
        )
        (out_dir / "mutcm_v2_noapi_gate_pass.md").write_text("\n".join(lines) + "\n")
    else:
        lines.append("- No-API gate failed. Stop before LLM synthetic generation.")
        (out_dir / "mutcm_v2_noapi_gate_fail.md").write_text("\n".join(lines) + "\n")
    (out_dir / "mutcm_v2_noapi_gate_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", default="data/MU-TCM face-milling dataset/full_dataset.7z")
    parser.add_argument("--csv-dir", default="breeze/results/mutcm_full_light_audit_2026-07-09/extracted_csv/full_dataset")
    parser.add_argument("--extract-root", default="data/MU-TCM face-milling dataset")
    parser.add_argument("--out-dir", default="breeze/results/mutcm_v2_synced_2026-07-09")
    parser.add_argument("--proc-dir", default="proc")
    args = parser.parse_args()
    archive = Path(args.archive)
    csv_dir = Path(args.csv_dir)
    extract_root = Path(args.extract_root)
    out_dir = Path(args.out_dir)
    proc_dir = Path(args.proc_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = read_stats(csv_dir)
    meta = build_metadata(stats, extract_root)
    expected = set(meta["file_name"])
    extract_synced(archive, extract_root, expected, out_dir)
    # Rebuild after extraction so mat_path exists in reports.
    meta = build_metadata(stats, extract_root)
    save_metadata_index(meta, out_dir)
    X_signal, feature_names = save_experiment_npz(stats, meta, out_dir, proc_dir)
    build_window_npz(meta, out_dir, proc_dir)
    split_df = write_split_report(meta, out_dir)
    X_meta_safe = meta_matrix(meta, leaky=False)
    X_meta_leaky = meta_matrix(meta, leaky=True)
    y = meta["y"].to_numpy(dtype=int)
    summary, _, _ = run_inner_baselines(X_signal, X_meta_safe, X_meta_leaky, y, feature_names, meta, split_df, out_dir)
    write_gate_report(summary, meta, X_signal, y, out_dir)
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
