"""Preprocess CWRU bearing data into BREEZE-style NPZ splits.

The smoke protocol uses official CWRU 12 kHz drive-end files at 0 load and
0.007 inch faults:

- 97: normal baseline;
- 105: inner-race fault;
- 118: ball fault;
- 130: outer-race fault at 6 o'clock.

All four files share DE and FE vibration channels. BA is not present in the
normal file, so it is intentionally excluded rather than padded.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import scipy.io as sio


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "cwru"
RAW_SMOKE = DATA / "raw" / "smoke"
RAW_FULL = DATA / "raw" / "de12k_full"
PROC = ROOT / "proc"
ANALYSIS = ROOT / "analysis"
REPORTS = ROOT / "reports"
FULL_MANIFEST = ANALYSIS / "cwru_de12k_full_manifest_2026-07-05.csv"

FS = 12_000
WIN = 2048
HOP = 2048
SMOKE_CHANNELS = ("DE", "FE")
FULL_CHANNELS = ("DE",)
CLASSES = ("healthy", "IR", "B", "OR")


@dataclass(frozen=True)
class CwruFile:
    file_id: int
    filename: str
    label: str
    fault_diameter_in: str
    load_hp: int
    rpm_nominal: int
    fault_location: str
    source_url: str


SMOKE_FILES = [
    CwruFile(
        97,
        "97.mat",
        "healthy",
        "none",
        0,
        1797,
        "none",
        "https://engineering.case.edu/sites/default/files/97.mat",
    ),
    CwruFile(
        105,
        "105.mat",
        "IR",
        "0.007",
        0,
        1797,
        "inner_race",
        "https://engineering.case.edu/sites/default/files/105.mat",
    ),
    CwruFile(
        118,
        "118.mat",
        "B",
        "0.007",
        0,
        1797,
        "ball",
        "https://engineering.case.edu/sites/default/files/118.mat",
    ),
    CwruFile(
        130,
        "130.mat",
        "OR",
        "0.007",
        0,
        1797,
        "outer_race_6",
        "https://engineering.case.edu/sites/default/files/130.mat",
    ),
]


def _find_key(keys: list[str], file_id: int, suffix: str) -> str:
    exact = f"X{file_id:03d}_{suffix}_time"
    if exact in keys:
        return exact
    candidates = [k for k in keys if k.endswith(f"_{suffix}_time")]
    if candidates:
        return candidates[0]
    raise KeyError(f"missing {suffix}_time in keys={keys}")


def _rpm_value(mat: dict, file_id: int) -> int | None:
    candidates = [f"X{file_id:03d}RPM"] + [k for k in mat if k.endswith("RPM")]
    for key in candidates:
        if key in mat:
            return int(np.asarray(mat[key]).ravel()[0])
    return None


def load_file(path: Path, file_id: int, channels_to_use: tuple[str, ...]) -> tuple[np.ndarray, int | None]:
    mat = sio.loadmat(path)
    keys = [k for k in mat.keys() if not k.startswith("__")]
    channels = []
    for channel in channels_to_use:
        key = _find_key(keys, file_id, channel)
        channels.append(np.asarray(mat[key]).ravel().astype(np.float64))
    n = min(len(x) for x in channels)
    arr = np.stack([x[:n] for x in channels]).astype(np.float32)
    rpm = _rpm_value(mat, file_id)
    return arr, rpm


def window_signal(x: np.ndarray) -> np.ndarray:
    n_win = (x.shape[1] - WIN) // HOP + 1
    if n_win <= 0:
        return np.zeros((0, x.shape[0], WIN), dtype=np.float32)
    return np.stack([x[:, i * HOP : i * HOP + WIN] for i in range(n_win)]).astype(np.float32)


def build_smoke_split(train_frac: float = 0.70) -> dict[str, object]:
    PROC.mkdir(parents=True, exist_ok=True)
    X_train, y_train, meta_train = [], [], []
    X_test, y_test, meta_test = [], [], []
    file_rows = []
    for item in SMOKE_FILES:
        path = RAW_SMOKE / item.filename
        if not path.exists():
            raise FileNotFoundError(path)
        signal, rpm = load_file(path, item.file_id, SMOKE_CHANNELS)
        windows = window_signal(signal)
        if len(windows) < 4:
            raise RuntimeError(f"too few windows in {path}: {len(windows)}")
        cut = max(1, min(len(windows) - 1, int(len(windows) * train_frac)))
        label_id = CLASSES.index(item.label)
        for split, block, out_x, out_y, out_meta in (
            ("train", windows[:cut], X_train, y_train, meta_train),
            ("test", windows[cut:], X_test, y_test, meta_test),
        ):
            out_x.append(block)
            out_y.append(np.full(len(block), label_id, dtype=np.int64))
            out_meta.extend(
                {
                    "split": split,
                    "file_id": item.file_id,
                    "label": item.label,
                    "load_hp": item.load_hp,
                    "fault_diameter_in": item.fault_diameter_in,
                    "fault_location": item.fault_location,
                    "rpm": rpm if rpm is not None else item.rpm_nominal,
                    "window_index": int(i),
                }
                for i in range(len(block))
            )
        file_rows.append(
            {
                **asdict(item),
                "local_path": str(path),
                "rpm_in_file": rpm,
                "n_samples": signal.shape[1],
                "n_windows": len(windows),
                "train_windows": cut,
                "test_windows": len(windows) - cut,
            }
        )
    train = {
        "X": np.concatenate(X_train, axis=0),
        "y": np.concatenate(y_train, axis=0),
        "metadata": np.asarray([json.dumps(m, separators=(",", ":")) for m in meta_train]),
    }
    test = {
        "X": np.concatenate(X_test, axis=0),
        "y": np.concatenate(y_test, axis=0),
        "metadata": np.asarray([json.dumps(m, separators=(",", ":")) for m in meta_test]),
    }
    np.savez_compressed(PROC / "cwru_smoke_train.npz", **train)
    np.savez_compressed(PROC / "cwru_smoke_test.npz", **test)
    write_manifest(file_rows)
    write_report(file_rows, train, test)
    return {"files": file_rows, "train": train, "test": test}


def read_full_manifest() -> list[dict[str, str]]:
    with FULL_MANIFEST.open() as fh:
        return list(csv.DictReader(fh))


def build_full_windows() -> dict[str, np.ndarray]:
    rows = read_full_manifest()
    X_blocks, y_blocks, metadata = [], [], []
    file_rows = []
    for row in rows:
        item = CwruFile(
            int(row["file_id"]),
            row["filename"],
            row["class"],
            row["fault_diameter_in"],
            int(row["load_hp"]),
            int(row["rpm"]),
            row["fault_location"],
            row["source_url"],
        )
        path = RAW_FULL / item.filename
        if not path.exists():
            raise FileNotFoundError(path)
        signal, rpm = load_file(path, item.file_id, FULL_CHANNELS)
        windows = window_signal(signal)
        label_id = CLASSES.index(item.label)
        X_blocks.append(windows)
        y_blocks.append(np.full(len(windows), label_id, dtype=np.int64))
        metadata.extend(
            {
                "file_id": item.file_id,
                "filename": item.filename,
                "label": item.label,
                "load_hp": item.load_hp,
                "fault_diameter_in": item.fault_diameter_in,
                "fault_location": item.fault_location,
                "rpm": rpm if rpm is not None else item.rpm_nominal,
                "window_index": int(i),
            }
            for i in range(len(windows))
        )
        file_rows.append(
            {
                **asdict(item),
                "local_path": str(path),
                "rpm_in_file": rpm,
                "n_samples": signal.shape[1],
                "n_windows": len(windows),
            }
        )
    X = np.concatenate(X_blocks, axis=0)
    y = np.concatenate(y_blocks, axis=0)
    meta = np.asarray([json.dumps(m, separators=(",", ":")) for m in metadata])
    PROC.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(PROC / "cwru_de12k_all.npz", X=X, y=y, metadata=meta)
    write_full_file_manifest(file_rows)
    write_full_splits(X, y, metadata)
    write_full_report(file_rows, X, y)
    return {"X": X, "y": y, "metadata": meta}


def write_full_file_manifest(file_rows: list[dict[str, object]]) -> None:
    path = ANALYSIS / "cwru_de12k_full_file_summary_2026-07-05.csv"
    with path.open("w", newline="") as fh:
        fieldnames = list(file_rows[0].keys())
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(file_rows)


def save_split(name: str, X: np.ndarray, y: np.ndarray, metadata: list[dict[str, object]], idx: np.ndarray) -> None:
    meta = np.asarray([json.dumps(metadata[int(i)], separators=(",", ":")) for i in idx])
    np.savez_compressed(PROC / f"{name}.npz", X=X[idx], y=y[idx], metadata=meta)


def write_full_splits(X: np.ndarray, y: np.ndarray, metadata: list[dict[str, object]], train_frac: float = 0.70) -> None:
    rows = []
    by_file: dict[int, list[int]] = {}
    for i, m in enumerate(metadata):
        by_file.setdefault(int(m["file_id"]), []).append(i)

    for load in sorted({int(m["load_hp"]) for m in metadata}):
        train_idx, test_idx = [], []
        for file_id, idxs in by_file.items():
            if int(metadata[idxs[0]]["load_hp"]) != load:
                continue
            cut = max(1, min(len(idxs) - 1, int(len(idxs) * train_frac)))
            train_idx.extend(idxs[:cut])
            test_idx.extend(idxs[cut:])
        if train_idx and test_idx:
            train_idx_arr = np.asarray(train_idx, dtype=int)
            test_idx_arr = np.asarray(test_idx, dtype=int)
            save_split(f"cwru_de12k_within_load{load}_train", X, y, metadata, train_idx_arr)
            save_split(f"cwru_de12k_within_load{load}_test", X, y, metadata, test_idx_arr)
            rows.append(split_row(f"within_load{load}", train_idx_arr, test_idx_arr, y))

    loads = sorted({int(m["load_hp"]) for m in metadata})
    for held in loads:
        train_idx = np.asarray([i for i, m in enumerate(metadata) if int(m["load_hp"]) != held], dtype=int)
        test_idx = np.asarray([i for i, m in enumerate(metadata) if int(m["load_hp"]) == held], dtype=int)
        save_split(f"cwru_de12k_lolo_load{held}_train", X, y, metadata, train_idx)
        save_split(f"cwru_de12k_lolo_load{held}_test", X, y, metadata, test_idx)
        rows.append(split_row(f"leave_load{held}_out", train_idx, test_idx, y))

    base_load = 0
    base_idx = np.asarray([i for i, m in enumerate(metadata) if int(m["load_hp"]) == base_load], dtype=int)
    for target in [l for l in loads if l != base_load]:
        target_idx = np.asarray([i for i, m in enumerate(metadata) if int(m["load_hp"]) == target], dtype=int)
        save_split(f"cwru_de12k_train_load{base_load}_test_load{target}_train", X, y, metadata, base_idx)
        save_split(f"cwru_de12k_train_load{base_load}_test_load{target}_test", X, y, metadata, target_idx)
        rows.append(split_row(f"train_load{base_load}_test_load{target}", base_idx, target_idx, y))

    path = ANALYSIS / "cwru_de12k_split_summary_2026-07-05.csv"
    with path.open("w", newline="") as fh:
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def split_row(name: str, train_idx: np.ndarray, test_idx: np.ndarray, y: np.ndarray) -> dict[str, object]:
    row = {
        "split": name,
        "train_n": len(train_idx),
        "test_n": len(test_idx),
    }
    for i, cls in enumerate(CLASSES):
        row[f"train_{cls}"] = int((y[train_idx] == i).sum())
        row[f"test_{cls}"] = int((y[test_idx] == i).sum())
    return row


def write_full_report(file_rows: list[dict[str, object]], X: np.ndarray, y: np.ndarray) -> None:
    rows_by_class = {cls: int((y == i).sum()) for i, cls in enumerate(CLASSES)}
    lines = [
        "# CWRU Full Preprocessing Report",
        "",
        "Date: 2026-07-05",
        "",
        "Protocol: official CWRU 12 kHz drive-end bearing-fault files parsed from the saved CWRU pages. Full preprocessing uses the DE vibration channel only because the official 0.028 inch files do not contain FE or BA fields. Missing channels are not padded.",
        "",
        f"Files: {len(file_rows)}",
        f"Sampling rate: {FS} Hz",
        f"Window: {WIN}; hop: {HOP}",
        f"All-window array: {tuple(X.shape)}",
        "Class counts: " + ", ".join(f"{k}:{v}" for k, v in rows_by_class.items()),
        "",
        "Generated artifacts:",
        "",
        "- `proc/cwru_de12k_all.npz`",
        "- `proc/cwru_de12k_within_load*_train/test.npz`",
        "- `proc/cwru_de12k_lolo_load*_train/test.npz`",
        "- `proc/cwru_de12k_train_load0_test_load*_train/test.npz`",
        "- `analysis/cwru_de12k_full_file_summary_2026-07-05.csv`",
        "- `analysis/cwru_de12k_split_summary_2026-07-05.csv`",
        "",
        "The within-load splits are chronological within each source file and are useful for comparability with common CWRU window-level protocols. The leave-one-load-out and train-load0-to-target-load splits are stricter condition-generalization protocols and should be preferred for strong claims.",
    ]
    (REPORTS / "cwru_full_preprocess_2026-07-05.md").write_text("\n".join(lines) + "\n")


def write_manifest(file_rows: list[dict[str, object]]) -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    path = ANALYSIS / "cwru_smoke_manifest_2026-07-05.csv"
    with path.open("w", newline="") as fh:
        fieldnames = list(file_rows[0].keys())
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(file_rows)


def _counts(y: np.ndarray) -> str:
    return ", ".join(f"{cls}:{int((y == i).sum())}" for i, cls in enumerate(CLASSES))


def write_report(file_rows: list[dict[str, object]], train: dict[str, np.ndarray], test: dict[str, np.ndarray]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    lines = [
        "# CWRU Smoke Preprocessing Report",
        "",
        "Date: 2026-07-05",
        "",
        "Protocol: official CWRU 12 kHz drive-end 0-load smoke subset using common DE and FE vibration channels. BA is excluded because the normal baseline file does not contain BA.",
        "",
        f"Sampling rate: {FS} Hz",
        f"Window: {WIN} samples",
        f"Hop: {HOP} samples",
        "Classes: " + ", ".join(CLASSES),
        "",
        "## Files",
        "",
        "| file | label | fault diameter | load | rpm | windows | train | test |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in file_rows:
        lines.append(
            f"| {row['filename']} | {row['label']} | {row['fault_diameter_in']} | {row['load_hp']} | {row['rpm_in_file']} | {row['n_windows']} | {row['train_windows']} | {row['test_windows']} |"
        )
    lines.extend(
        [
            "",
            "## Split",
            "",
            f"Train shape: {tuple(train['X'].shape)}; counts: {_counts(train['y'])}",
            f"Test shape: {tuple(test['X'].shape)}; counts: {_counts(test['y'])}",
            "",
            "This smoke split is chronological within each source file and is used only to validate loaders, classifiers, and metric scripts. It is not a leakage-free final CWRU benchmark because each class currently has one source file. Full CWRU experiments must use multiple loads/fault sizes/locations with explicit file- or condition-held-out splits.",
        ]
    )
    (REPORTS / "cwru_smoke_preprocess_2026-07-05.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        summary = build_smoke_split()
        print("wrote", PROC / "cwru_smoke_train.npz", summary["train"]["X"].shape)
        print("wrote", PROC / "cwru_smoke_test.npz", summary["test"]["X"].shape)
        print("wrote", ANALYSIS / "cwru_smoke_manifest_2026-07-05.csv")
        print("wrote", REPORTS / "cwru_smoke_preprocess_2026-07-05.md")
    if args.full:
        summary = build_full_windows()
        print("wrote", PROC / "cwru_de12k_all.npz", summary["X"].shape)
        print("wrote", ANALYSIS / "cwru_de12k_full_file_summary_2026-07-05.csv")
        print("wrote", ANALYSIS / "cwru_de12k_split_summary_2026-07-05.csv")
        print("wrote", REPORTS / "cwru_full_preprocess_2026-07-05.md")
    if not args.smoke and not args.full:
        raise SystemExit("Pass --smoke and/or --full.")


if __name__ == "__main__":
    main()
