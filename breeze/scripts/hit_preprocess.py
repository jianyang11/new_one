"""Preprocess the GitHub-hosted HIT-dataset channel-1 example files."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import scipy.io as sio


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "hit" / "raw"
PROC = ROOT / "proc"
ANALYSIS = ROOT / "analysis"
REPORTS = ROOT / "reports"


def load_var(path: Path, key: str) -> np.ndarray:
    mat = sio.loadmat(path)
    if key not in mat:
        keys = [k for k in mat if not k.startswith("__")]
        raise KeyError(f"{path}: missing {key}, got {keys}")
    return np.asarray(mat[key])


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    train_xs, train_ys, rows = [], [], []
    for i in range(1, 5):
        x_path = RAW / f"xtrain_{i}.mat"
        y_path = RAW / f"ytrain_{i}.mat"
        X = load_var(x_path, f"xtrain_{i}").astype(np.float32)
        y = load_var(y_path, f"ytrain_{i}").reshape(-1).astype(np.int64)
        if X.shape != (len(y), 2048):
            raise RuntimeError(f"shape mismatch shard {i}: {X.shape} vs {y.shape}")
        train_xs.append(X)
        train_ys.append(y)
        labels, counts = np.unique(y, return_counts=True)
        rows.append(
            {
                "split": "train",
                "shard": i,
                "x_file": x_path.name,
                "y_file": y_path.name,
                "samples": len(X),
                "shape": "x".join(str(v) for v in X.shape),
                "label_counts": json.dumps({int(k): int(v) for k, v in zip(labels, counts)}, sort_keys=True),
            }
        )
    X_train = np.concatenate(train_xs, axis=0)[:, None, :]
    y_train = np.concatenate(train_ys, axis=0)
    X_test = load_var(RAW / "xtest.mat", "xtest").astype(np.float32)[:, None, :]
    y_test = load_var(RAW / "ytest.mat", "ytest").reshape(-1).astype(np.int64)
    if X_test.shape != (len(y_test), 1, 2048):
        raise RuntimeError(f"test shape mismatch: {X_test.shape} vs {y_test.shape}")
    labels, counts = np.unique(y_test, return_counts=True)
    rows.append(
        {
            "split": "test",
            "shard": "test",
            "x_file": "xtest.mat",
            "y_file": "ytest.mat",
            "samples": len(X_test),
            "shape": "x".join(str(v) for v in X_test.shape),
            "label_counts": json.dumps({int(k): int(v) for k, v in zip(labels, counts)}, sort_keys=True),
        }
    )
    PROC.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        PROC / "hit_channel1_train.npz",
        X=X_train,
        windows=X_train,
        y=y_train,
        class_names=np.array(["class_0", "class_1", "class_2"]),
        channel_names=np.array(["channel_1_example"]),
    )
    np.savez_compressed(
        PROC / "hit_channel1_test.npz",
        X=X_test,
        windows=X_test,
        y=y_test,
        class_names=np.array(["class_0", "class_1", "class_2"]),
        channel_names=np.array(["channel_1_example"]),
    )
    write_csv(ANALYSIS / "hit_channel1_manifest_2026-07-05.csv", rows)
    train_counts = {int(k): int(v) for k, v in zip(*np.unique(y_train, return_counts=True))}
    test_counts = {int(k): int(v) for k, v in zip(*np.unique(y_test, return_counts=True))}
    report = f"""# HIT Channel-1 Preprocess

Date: 2026-07-05

Source: `https://github.com/HouLeiHIT/HIT-dataset`

The repository README describes these files as Channel 1 example data from an
inter-shaft bearing fault diagnosis dataset. The full dataset is linked through
Google Drive, but the GitHub repository itself contains four train shards,
one test shard, and labels.

Outputs:

- `proc/hit_channel1_train.npz`: {tuple(X_train.shape)}
- `proc/hit_channel1_test.npz`: {tuple(X_test.shape)}
- `analysis/hit_channel1_manifest_2026-07-05.csv`

Label counts:

- train: {json.dumps(train_counts, sort_keys=True)}
- test: {json.dumps(test_counts, sort_keys=True)}

Limitation: the README does not define the physical meaning of labels 0/1/2 in
the GitHub channel-1 example. This subset can support classifier plumbing and a
supervised benchmark with anonymous classes, but it cannot support a physical
fault-generation claim until label semantics and full-channel metadata are
verified.
"""
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "hit_channel1_preprocess_2026-07-05.md").write_text(report)
    print(f"train={X_train.shape} test={X_test.shape}")
    print(f"train_counts={train_counts} test_counts={test_counts}")


if __name__ == "__main__":
    main()
