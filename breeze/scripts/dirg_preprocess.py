"""Preprocess DIRG VariableSpeedAndLoad data from the official Zenodo archive.

The VariableSpeedAndLoad session is a supervised bearing-diagnostics dataset:
seven labelled bearing conditions are recorded under multiple speed-load
operating points. Splits are frozen by operating condition to avoid reusing
windows from the same acquisition in both train and test.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import scipy.io as sio


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "dirg" / "raw"
META = ROOT / "data" / "dirg" / "meta"
PROC = ROOT / "proc"
ANALYSIS = ROOT / "analysis"
REPORTS = ROOT / "reports"

FS = 51200
WIN = 4096
HOP = 4096
LOAD_CELL_MV_PER_N = 0.499
NOMINAL_LOADS_N = np.array([0.0, 1000.0, 1400.0, 1800.0], dtype=np.float64)

FILE_RE = re.compile(r"^VariableSpeedAndLoad/C(?P<code>[0-6]A)_(?P<speed>\d{3})_(?P<load_mv>\d{3})_(?P<rep>\d+)\.mat$")


@dataclass(frozen=True)
class ClassSpec:
    label: int
    class_name: str
    location: str
    severity_um: int


CLASS_SPECS = {
    "0A": ClassSpec(0, "healthy", "none", 0),
    "1A": ClassSpec(1, "IR450", "inner_ring", 450),
    "2A": ClassSpec(2, "IR250", "inner_ring", 250),
    "3A": ClassSpec(3, "IR150", "inner_ring", 150),
    "4A": ClassSpec(4, "roller450", "roller", 450),
    "5A": ClassSpec(5, "roller250", "roller", 250),
    "6A": ClassSpec(6, "roller150", "roller", 150),
}

SMOKE_FILES = {
    "VariableSpeedAndLoad/C0A_100_000_1.mat",
    "VariableSpeedAndLoad/C1A_300_702_2.mat",
    "VariableSpeedAndLoad/C4A_300_702_1.mat",
}


def nominal_load_from_mv(load_mv: int) -> int:
    load_n = load_mv / LOAD_CELL_MV_PER_N
    idx = int(np.argmin(np.abs(NOMINAL_LOADS_N - load_n)))
    return int(round(float(NOMINAL_LOADS_N[idx])))


def parse_file(name: str) -> dict[str, object] | None:
    match = FILE_RE.match(name)
    if not match:
        return None
    code = match.group("code")
    spec = CLASS_SPECS[code]
    load_mv = int(match.group("load_mv"))
    return {
        "member": name,
        "code": code,
        "label": spec.label,
        "class_name": spec.class_name,
        "damage_location": spec.location,
        "severity_um": spec.severity_um,
        "speed_hz": int(match.group("speed")),
        "load_mv": load_mv,
        "load_n_measured": load_mv / LOAD_CELL_MV_PER_N if load_mv else 0.0,
        "nominal_load_n": nominal_load_from_mv(load_mv),
        "replicate": int(match.group("rep")),
    }


def load_member(zf: ZipFile, member: str) -> np.ndarray:
    with zf.open(member) as fh:
        mat = sio.loadmat(BytesIO(fh.read()))
    key = Path(member).stem
    if key not in mat:
        keys = [k for k in mat.keys() if not k.startswith("__")]
        if len(keys) != 1:
            raise RuntimeError(f"{member}: expected one data variable, got {keys}")
        key = keys[0]
    arr = np.asarray(mat[key], dtype=np.float32)
    if arr.shape != (512000, 6):
        raise RuntimeError(f"{member}: expected shape (512000, 6), got {arr.shape}")
    return arr


def segment(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    starts = np.arange(0, arr.shape[0] - WIN + 1, HOP, dtype=np.int32)
    windows = np.stack([arr[s : s + WIN].T for s in starts]).astype(np.float32, copy=False)
    return windows, starts


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)


def build(smoke: bool) -> tuple[Path, list[dict[str, object]], dict[str, np.ndarray]]:
    archive = RAW / "VariableSpeedAndLoad.zip"
    if not archive.exists():
        raise FileNotFoundError(archive)
    all_windows: list[np.ndarray] = []
    y: list[np.ndarray] = []
    file_index: list[np.ndarray] = []
    starts_all: list[np.ndarray] = []
    manifest_rows: list[dict[str, object]] = []
    per_window_meta: dict[str, list[np.ndarray]] = {
        "speed_hz": [],
        "load_mv": [],
        "nominal_load_n": [],
        "severity_um": [],
        "damage_location_id": [],
    }
    location_id = {"none": 0, "inner_ring": 1, "roller": 2}
    with ZipFile(archive) as zf:
        parsed = [parse_file(name) for name in zf.namelist()]
        rows = [row for row in parsed if row is not None]
        if smoke:
            rows = [row for row in rows if row["member"] in SMOKE_FILES]
        rows = sorted(rows, key=lambda r: (int(r["label"]), int(r["speed_hz"]), int(r["nominal_load_n"]), int(r["load_mv"]), int(r["replicate"])))
        if not rows:
            raise RuntimeError("no DIRG files selected")
        for idx, row in enumerate(rows):
            arr = load_member(zf, str(row["member"]))
            windows, starts = segment(arr)
            all_windows.append(windows)
            n = len(windows)
            y.append(np.full(n, int(row["label"]), dtype=np.int64))
            file_index.append(np.full(n, idx, dtype=np.int32))
            starts_all.append(starts)
            per_window_meta["speed_hz"].append(np.full(n, int(row["speed_hz"]), dtype=np.int32))
            per_window_meta["load_mv"].append(np.full(n, int(row["load_mv"]), dtype=np.int32))
            per_window_meta["nominal_load_n"].append(np.full(n, int(row["nominal_load_n"]), dtype=np.int32))
            per_window_meta["severity_um"].append(np.full(n, int(row["severity_um"]), dtype=np.int32))
            per_window_meta["damage_location_id"].append(np.full(n, location_id[str(row["damage_location"])], dtype=np.int32))
            manifest_row = dict(row)
            manifest_row.update(
                {
                    "sampling_rate_hz": FS,
                    "samples_per_file": arr.shape[0],
                    "channels": arr.shape[1],
                    "window": WIN,
                    "hop": HOP,
                    "windows": n,
                    "rms_all_channels": float(np.sqrt(np.mean(arr * arr))),
                }
            )
            manifest_rows.append(manifest_row)
    X = np.concatenate(all_windows, axis=0)
    arrays: dict[str, np.ndarray] = {
        "X": X,
        "windows": X,
        "y": np.concatenate(y, axis=0),
        "file_index": np.concatenate(file_index, axis=0),
        "start_sample": np.concatenate(starts_all, axis=0),
        "speed_hz": np.concatenate(per_window_meta["speed_hz"], axis=0),
        "load_mv": np.concatenate(per_window_meta["load_mv"], axis=0),
        "nominal_load_n": np.concatenate(per_window_meta["nominal_load_n"], axis=0),
        "severity_um": np.concatenate(per_window_meta["severity_um"], axis=0),
        "damage_location_id": np.concatenate(per_window_meta["damage_location_id"], axis=0),
        "class_names": np.array([CLASS_SPECS[f"{i}A"].class_name for i in range(7)]),
        "damage_locations": np.array(["none", "inner_ring", "roller"]),
        "file_members": np.array([str(row["member"]) for row in manifest_rows]),
        "file_class_names": np.array([str(row["class_name"]) for row in manifest_rows]),
        "file_speed_hz": np.array([int(row["speed_hz"]) for row in manifest_rows], dtype=np.int32),
        "file_nominal_load_n": np.array([int(row["nominal_load_n"]) for row in manifest_rows], dtype=np.int32),
    }
    out = PROC / ("dirg_variable_smoke.npz" if smoke else "dirg_variable_all.npz")
    save_npz(out, arrays)
    return out, manifest_rows, arrays


def make_split_arrays(arrays: dict[str, np.ndarray], test_speed_hz: int, test_nominal_load_n: int) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    mask = (arrays["speed_hz"] == test_speed_hz) & (arrays["nominal_load_n"] == test_nominal_load_n)
    if int(mask.sum()) == 0:
        raise RuntimeError(f"empty DIRG test condition {test_speed_hz=} {test_nominal_load_n=}")
    keep_keys = [
        "X",
        "windows",
        "y",
        "file_index",
        "start_sample",
        "speed_hz",
        "load_mv",
        "nominal_load_n",
        "severity_um",
        "damage_location_id",
    ]
    train = {k: v[~mask] for k, v in arrays.items() if k in keep_keys}
    test = {k: v[mask] for k, v in arrays.items() if k in keep_keys}
    for meta_key in ("class_names", "damage_locations", "file_members", "file_class_names", "file_speed_hz", "file_nominal_load_n"):
        train[meta_key] = arrays[meta_key]
        test[meta_key] = arrays[meta_key]
    return train, test


def write_split_summary(arrays: dict[str, np.ndarray], path: Path) -> None:
    rows: list[dict[str, object]] = []
    for speed in sorted(set(int(x) for x in arrays["speed_hz"])):
        for load in sorted(set(int(x) for x in arrays["nominal_load_n"])):
            mask = (arrays["speed_hz"] == speed) & (arrays["nominal_load_n"] == load)
            if not int(mask.sum()):
                continue
            labels, counts = np.unique(arrays["y"][mask], return_counts=True)
            by_class = {CLASS_SPECS[f"{int(label)}A"].class_name: int(count) for label, count in zip(labels, counts)}
            rows.append(
                {
                    "split": f"leave_speed{speed}_load{load}_out",
                    "test_speed_hz": speed,
                    "test_nominal_load_n": load,
                    "train_windows": int((~mask).sum()),
                    "test_windows": int(mask.sum()),
                    "test_by_class": json.dumps(by_class, sort_keys=True),
                }
            )
    write_csv(path, rows)


def write_report(out: Path, manifest_rows: list[dict[str, object]], arrays: dict[str, np.ndarray], smoke: bool) -> None:
    labels, counts = np.unique(arrays["y"], return_counts=True)
    by_class = {CLASS_SPECS[f"{int(label)}A"].class_name: int(count) for label, count in zip(labels, counts)}
    unique_conditions = sorted({(int(r["speed_hz"]), int(r["nominal_load_n"])) for r in manifest_rows})
    report = REPORTS / ("dirg_variable_smoke_preprocess_2026-07-05.md" if smoke else "dirg_variable_full_preprocess_2026-07-05.md")
    lines = [
        "# DIRG VariableSpeedAndLoad Preprocess",
        "",
        "Date: 2026-07-05",
        "",
        f"Mode: {'smoke' if smoke else 'full'}",
        f"Output NPZ: `{out.relative_to(ROOT)}`",
        f"Source archive: `data/dirg/raw/VariableSpeedAndLoad.zip`",
        f"Sampling rate: {FS} Hz",
        f"Window/hop: {WIN}/{HOP} samples",
        f"Files processed: {len(manifest_rows)}",
        f"Windows: {int(arrays['X'].shape[0])}",
        f"Shape: {tuple(arrays['X'].shape)}",
        f"Class counts: {json.dumps(by_class, sort_keys=True)}",
        f"Unique speed-load conditions: {len(unique_conditions)}",
        "",
        "Split policy: full-mode splits are frozen by held-out speed-load operating condition. This avoids putting windows from the same acquisition file in both train and test.",
    ]
    report.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--test-speed-hz", type=int, default=300)
    parser.add_argument("--test-load-n", type=int, default=1400)
    args = parser.parse_args()
    out, manifest_rows, arrays = build(smoke=args.smoke)
    manifest_path = ANALYSIS / ("dirg_variable_file_manifest_smoke_2026-07-05.csv" if args.smoke else "dirg_variable_file_manifest_2026-07-05.csv")
    write_csv(manifest_path, manifest_rows)
    if not args.smoke:
        write_split_summary(arrays, ANALYSIS / "dirg_variable_split_summary_2026-07-05.csv")
        train, test = make_split_arrays(arrays, args.test_speed_hz, args.test_load_n)
        save_npz(PROC / f"dirg_variable_loco_speed{args.test_speed_hz}_load{args.test_load_n}_train.npz", train)
        save_npz(PROC / f"dirg_variable_loco_speed{args.test_speed_hz}_load{args.test_load_n}_test.npz", test)
    write_report(out, manifest_rows, arrays, smoke=args.smoke)
    print(f"wrote {out}")
    print(f"wrote {manifest_path}")
    print(f"shape={arrays['X'].shape}")


if __name__ == "__main__":
    main()
