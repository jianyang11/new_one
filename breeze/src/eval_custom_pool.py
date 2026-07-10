"""Evaluate an arbitrary synthetic NPZ pool without touching the main table."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score

sys.path.insert(0, str(Path(__file__).parent))
from config import CLASSES, MAIN_COND, RESULTS_DIR
from data import load_file_split
from train import evaluate, few_shot_subset, fit


def done_keys(path: Path) -> set[tuple[str, int, int]]:
    if not path.exists():
        return set()
    with path.open() as fh:
        return {(r["baseline"], int(r["n_real"]), int(r["seed"])) for r in csv.DictReader(fh)}


def sample_pool(pool_path: Path, n_per_class: int, rng: np.random.Generator):
    d = np.load(pool_path)
    X, y = d["X"].astype(np.float32), d["y"].astype(np.int64)
    keep = []
    for ci in range(len(CLASSES)):
        idx = np.where(y == ci)[0]
        if len(idx) == 0:
            continue
        keep.extend(rng.choice(idx, min(n_per_class, len(idx)), replace=False))
    keep = np.asarray(keep, dtype=int)
    return X[keep], y[keep]


def write_row(writer, baseline, n_real, seed, n_syn, y_true, preds, acc, macro_f1):
    per = f1_score(y_true, preds, average=None, labels=list(range(len(CLASSES))), zero_division=0)
    cm = confusion_matrix(y_true, preds, labels=list(range(len(CLASSES))))
    writer.writerow([
        baseline,
        n_real,
        seed,
        n_syn,
        f"{acc:.4f}",
        f"{macro_f1:.4f}",
        *[f"{v:.4f}" for v in per],
        json.dumps(cm.tolist(), separators=(",", ":")),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--n_real", type=int, nargs="+", default=[10, 25, 50])
    ap.add_argument("--n_syn", type=int, default=200)
    ap.add_argument("--out", default=str(RESULTS_DIR / "custom_pool_eval.csv"))
    ap.add_argument("--include-real-only", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Xtr, ytr, _ = load_file_split("train", MAIN_COND)
    Xte, yte, _ = load_file_split("test", MAIN_COND)
    Xtr = Xtr.astype(np.float32)
    Xte = Xte.astype(np.float32)

    new_file = not out.exists()
    done = done_keys(out)
    with out.open("a", newline="") as fh:
        wr = csv.writer(fh)
        if new_file:
            wr.writerow([
                "baseline",
                "n_real",
                "seed",
                "n_syn",
                "acc",
                "macro_f1",
                *[f"f1_{c}" for c in CLASSES],
                "confusion",
            ])
        baselines = ["real_only", args.baseline] if args.include_real_only else [args.baseline]
        for baseline in baselines:
            for nr in args.n_real:
                for seed in range(args.seeds):
                    if (baseline, nr, seed) in done:
                        continue
                    rng = np.random.default_rng(1000 * nr + seed)
                    Xr, yr = few_shot_subset(Xtr, ytr, nr, rng)
                    if baseline == "real_only":
                        Xa, ya, n_syn = Xr, yr, 0
                    else:
                        Xs, ys = sample_pool(Path(args.pool), args.n_syn, rng)
                        Xa = np.concatenate([Xr, Xs])
                        ya = np.concatenate([yr, ys])
                        n_syn = len(Xs)
                    model, mean, std = fit(Xa, ya, seed)
                    acc, macro_f1, preds = evaluate(model, mean, std, Xte, yte)
                    write_row(wr, baseline, nr, seed, n_syn, yte, preds, acc, macro_f1)
                    fh.flush()
                    print(
                        f"{baseline} n_real={nr} seed={seed} n_syn={n_syn} "
                        f"acc={acc:.4f} macro_f1={macro_f1:.4f}",
                        flush=True,
                    )


if __name__ == "__main__":
    main()
