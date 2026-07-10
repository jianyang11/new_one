"""Build PU leave-one-condition-out NPZ splits.

The split unit is the operating condition. For each fold, all windows from the
held-out condition are test data, and all windows from the other three
conditions are training data. No window-level random split is used here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import CLASSES, CONDITIONS, PROC_DIR  # noqa: E402


def class_for_bearing(bearing: str) -> str:
    if bearing.startswith("K0"):
        return "healthy"
    if bearing.startswith("KA"):
        return "OR"
    if bearing.startswith("KI"):
        return "IR"
    raise ValueError(f"unknown PU bearing id: {bearing}")


def load_condition(cond: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    files: list[str] = []
    for path in sorted(PROC_DIR.glob(f"{cond}_*.npz")):
        data = np.load(path, allow_pickle=True)
        bearing = str(data["bearing"])
        cls = class_for_bearing(bearing)
        y = CLASSES.index(cls)
        windows = data["windows"].astype(np.float32)
        xs.append(windows)
        ys.append(np.full(len(windows), y, dtype=np.int64))
        files.extend([path.name] * len(windows))
    if not xs:
        raise FileNotFoundError(f"no processed PU files for condition: {cond}")
    return np.concatenate(xs), np.concatenate(ys), np.asarray(files)


def save_npz(path: Path, X: np.ndarray, y: np.ndarray, files: np.ndarray, split: str, heldout: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        X=X.astype(np.float32),
        y=y.astype(np.int64),
        source_files=files.astype("U64"),
        class_names=np.asarray(CLASSES),
        split=split,
        heldout_condition=heldout,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="proc")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)

    by_cond = {cond: load_condition(cond) for cond in CONDITIONS}
    for heldout in CONDITIONS:
        train_xs: list[np.ndarray] = []
        train_ys: list[np.ndarray] = []
        train_files: list[np.ndarray] = []
        for cond, (X, y, files) in by_cond.items():
            if cond == heldout:
                continue
            train_xs.append(X)
            train_ys.append(y)
            train_files.append(files)
        Xtr = np.concatenate(train_xs)
        ytr = np.concatenate(train_ys)
        ftr = np.concatenate(train_files)
        Xte, yte, fte = by_cond[heldout]
        tag = f"pu_loco_{heldout}"
        save_npz(out_dir / f"{tag}_train.npz", Xtr, ytr, ftr, "train", heldout)
        save_npz(out_dir / f"{tag}_test.npz", Xte, yte, fte, "test", heldout)
        train_counts = {CLASSES[i]: int((ytr == i).sum()) for i in range(len(CLASSES))}
        test_counts = {CLASSES[i]: int((yte == i).sum()) for i in range(len(CLASSES))}
        print(f"{tag}: train={train_counts} test={test_counts}")


if __name__ == "__main__":
    main()
