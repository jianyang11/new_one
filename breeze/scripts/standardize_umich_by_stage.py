"""Apply train-fold per-stage z-score normalization to UMich NPZ files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


BASE_KEYS = {"X"}


def load(path: Path) -> dict[str, np.ndarray]:
    data = np.load(path, allow_pickle=True)
    return {k: data[k] for k in data.files}


def compute_stats(train: dict[str, np.ndarray]) -> dict[str, dict[str, np.ndarray]]:
    if "stage" not in train:
        raise RuntimeError("stage metadata missing; use preprocess_umich_v4_task_repair.py output")
    X = train["X"].astype(np.float32)
    stages = np.asarray([str(s) for s in train["stage"]])
    stats: dict[str, dict[str, np.ndarray]] = {}
    for stage in sorted(set(stages)):
        W = X[stages == stage]
        if len(W) == 0:
            continue
        mean = W.mean(axis=(0, 2), keepdims=True).astype(np.float32)
        std = (W.std(axis=(0, 2), keepdims=True) + 1e-8).astype(np.float32)
        stats[stage] = {"mean": mean, "std": std, "n": np.asarray([len(W)], dtype=np.int64)}
    global_mean = X.mean(axis=(0, 2), keepdims=True).astype(np.float32)
    global_std = (X.std(axis=(0, 2), keepdims=True) + 1e-8).astype(np.float32)
    stats["__global__"] = {"mean": global_mean, "std": global_std, "n": np.asarray([len(X)], dtype=np.int64)}
    return stats


def transform(data: dict[str, np.ndarray], stats: dict[str, dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    out = {k: v for k, v in data.items() if k != "X"}
    X = data["X"].astype(np.float32).copy()
    stages = np.asarray([str(s) for s in data["stage"]])
    for stage in sorted(set(stages)):
        st = stats.get(stage, stats["__global__"])
        mask = stages == stage
        X[mask] = (X[mask] - st["mean"]) / st["std"]
    out["X"] = X.astype(np.float32)
    out["stage_zscore_definition"] = np.asarray(
        ["per-stage channel z-score; mean/std estimated from the supplied train NPZ only"]
    )
    return out


def save(path: Path, payload: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-npz", required=True)
    parser.add_argument("--eval-npz", required=True)
    parser.add_argument("--out-train", required=True)
    parser.add_argument("--out-eval", required=True)
    parser.add_argument("--stats-json", default="")
    args = parser.parse_args()

    train = load(Path(args.train_npz))
    eval_data = load(Path(args.eval_npz))
    stats = compute_stats(train)
    save(Path(args.out_train), transform(train, stats))
    save(Path(args.out_eval), transform(eval_data, stats))
    if args.stats_json:
        serial = {
            stage: {"n": int(st["n"][0]), "mean": st["mean"].reshape(-1).tolist(), "std": st["std"].reshape(-1).tolist()}
            for stage, st in stats.items()
        }
        Path(args.stats_json).write_text(json.dumps(serial, indent=2) + "\n")
    print(f"wrote {args.out_train}")
    print(f"wrote {args.out_eval}")


if __name__ == "__main__":
    main()
