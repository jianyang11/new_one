"""Downstream few-shot diagnosis experiments (checkpoint-resumable).

For each (baseline, n_real, seed): sample n_real real train windows per class,
add the baseline's synthetic pool (capped at N_SYN per class), train SimpleCNN,
evaluate on the held-out test bearings. Results appended to results/downstream.csv.

Usage: python train.py --baselines all --seeds 8 --n_real 10 25 50
"""
import argparse
import csv
import sys
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import CLASSES, MAIN_COND, RUNS_DIR, RESULTS_DIR
from data import load_split, load_file_split
from models import SimpleCNN, train_vae_per_class, train_gan_per_class
from pools import build_pool

RESULTS = RESULTS_DIR
RESULTS.mkdir(exist_ok=True)
CSV = RESULTS / "downstream.csv"
N_SYN = 200  # synthetic windows added per class (capped)
PHYS_RUN = RUNS_DIR / "pool_physics_file_k3"
BASIC_RUN = RUNS_DIR / "pool_basic_file_k0"

BASELINES = ["real_only", "noise_aug", "vae", "gan", "vae_fs", "gan_fs",
             "open_loop_basic", "open_loop_phys",
             "stats_only", "envelope_only",
             "breeze_k0", "breeze_k1", "breeze_k2", "breeze_k3"]


def few_shot_subset(X, y, n_per_class, rng):
    idx = []
    for ci in range(len(CLASSES)):
        c = np.where(y == ci)[0]
        idx.extend(rng.choice(c, min(n_per_class, len(c)), replace=False))
    idx = np.array(idx)
    return X[idx], y[idx]


def get_synth(baseline, Xr, yr, seed, rng):
    if baseline == "real_only":
        return None
    if baseline == "noise_aug":
        Xs = Xr + rng.normal(0, 0.05 * Xr.std(), Xr.shape).astype(np.float32)
        reps = max(1, N_SYN // max(1, (yr == 0).sum()))
        Xs = np.concatenate([Xr + rng.normal(0, 0.05 * Xr.std(), Xr.shape)
                             .astype(np.float32) for _ in range(reps)])
        ys = np.concatenate([yr] * reps)
        return Xs, ys
    if baseline == "vae_fs":
        return train_vae_per_class(Xr, yr, N_SYN, seed=seed)
    if baseline == "gan_fs":
        return train_gan_per_class(Xr, yr, N_SYN, seed=seed)
    if baseline in ("vae", "gan"):
        # full-corpus generative baselines: same real-data access as the
        # BREEZE exemplars/verifier (pools precomputed once per method)
        d = np.load(RUNS_DIR / f"{baseline}_fullcorpus_pool.npz")
        X, y = d["X"], d["y"]
        keep = []
        for ci in range(len(CLASSES)):
            c = np.where(y == ci)[0]
            keep.extend(rng.choice(c, min(N_SYN, len(c)), replace=False))
        keep = np.array(keep)
        return X[keep], y[keep]
    if baseline in ("open_loop_basic",):
        X, y = build_pool(BASIC_RUN, "open_loop_basic")
    elif baseline == "open_loop_phys":
        X, y = build_pool(PHYS_RUN, "open_loop_phys")
    elif baseline in ("stats_only", "envelope_only"):
        X, y = build_pool(PHYS_RUN, baseline)
    elif baseline.startswith("breeze_k"):
        from pools import diversity_filter
        X, y = build_pool(PHYS_RUN, "breeze", k=int(baseline[-1]))
        if len(X):
            X, y = diversity_filter(X, y, Xr, yr)
    else:
        raise ValueError(baseline)
    # cap at N_SYN per class (random subsample per seed)
    keep = []
    for ci in range(len(CLASSES)):
        c = np.where(y == ci)[0]
        keep.extend(rng.choice(c, min(N_SYN, len(c)), replace=False))
    keep = np.array(keep)
    return X[keep], y[keep]


def standardize(Xtr, *rest):
    m = Xtr.mean(axis=(0, 2), keepdims=True)
    s = Xtr.std(axis=(0, 2), keepdims=True) + 1e-8
    return [(x - m) / s for x in (Xtr,) + rest]


def fit(Xtr, ytr, seed, epochs=60):
    """Train SimpleCNN; returns (model, mean, std) for later evaluation."""
    torch.manual_seed(seed)
    m = Xtr.mean(axis=(0, 2), keepdims=True)
    s = Xtr.std(axis=(0, 2), keepdims=True) + 1e-8
    Xtr_ = (Xtr - m) / s
    model = SimpleCNN()
    opt = torch.optim.Adam(model.parameters(), lr=3e-4, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()
    Xt = torch.tensor(Xtr_, dtype=torch.float32)
    yt = torch.tensor(ytr, dtype=torch.long)
    n = len(Xt)
    g = torch.Generator().manual_seed(seed)
    for _ in range(epochs):
        perm = torch.randperm(n, generator=g)
        for b in range(0, n, 32):
            idx = perm[b:b + 32]
            opt.zero_grad()
            loss = crit(model(Xt[idx]), yt[idx])
            loss.backward(); opt.step()
    model.eval()
    return model, m, s


def evaluate(model, m, s, Xte, yte):
    Xte_ = (Xte - m) / s
    preds = []
    with torch.no_grad():
        Xe = torch.tensor(Xte_, dtype=torch.float32)
        for b in range(0, len(Xe), 256):
            preds.append(model(Xe[b:b + 256]).argmax(1).numpy())
    preds = np.concatenate(preds)
    acc = (preds == yte).mean()
    from sklearn.metrics import f1_score
    f1 = f1_score(yte, preds, average="macro")
    return acc, f1, preds


def done_keys():
    if not CSV.exists():
        return set()
    with open(CSV) as f:
        return {(r["baseline"], int(r["n_real"]), int(r["seed"]))
                for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baselines", nargs="+", default=["all"])
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--n_real", type=int, nargs="+", default=[10, 25, 50])
    ap.add_argument("--cross", action="store_true",
                    help="also evaluate on the other operating conditions")
    ap.add_argument("--split", default="file", choices=["file", "bearing"],
                    help="main protocol: held-out measurement sessions "
                         "(file) or held-out bearing units (bearing)")
    a = ap.parse_args()
    global CSV
    if a.split == "file":
        CSV = RESULTS / "downstream_file.csv"
    bls = BASELINES if a.baselines == ["all"] else a.baselines

    if a.split == "file":
        Xtr, ytr, _ = load_file_split("train", MAIN_COND)
        Xte, yte, _ = load_file_split("test", MAIN_COND)
    else:
        Xtr, ytr, _ = load_split("train", MAIN_COND)
        Xte, yte, _ = load_split("test", MAIN_COND)
    Xtr = Xtr.astype(np.float32); Xte = Xte.astype(np.float32)
    cross = {}
    if a.cross:
        from config import CONDITIONS
        for cond in CONDITIONS:
            if cond == MAIN_COND:
                continue
            Xc, yc, _ = load_split("test", cond)
            cross[cond] = (Xc.astype(np.float32), yc)
        xcsv = RESULTS / "cross_condition.csv"
        newx = not xcsv.exists()
        fx = open(xcsv, "a", newline="")
        wrx = csv.writer(fx)
        if newx:
            wrx.writerow(["baseline", "n_real", "seed", "cond", "acc", "f1"])
    done = done_keys()
    new_file = not CSV.exists()
    fout = open(CSV, "a", newline="")
    wr = csv.writer(fout)
    if new_file:
        wr.writerow(["baseline", "n_real", "seed", "n_syn", "acc", "f1"])
    for bl in bls:
        for nr in a.n_real:
            for seed in range(a.seeds):
                if (bl, nr, seed) in done:
                    continue
                rng = np.random.default_rng(1000 * nr + seed)
                Xr, yr = few_shot_subset(Xtr, ytr, nr, rng)
                syn = get_synth(bl, Xr, yr, seed, rng)
                if syn is not None and len(syn[0]) > 0:
                    Xs, ys = syn
                    Xa = np.concatenate([Xr, Xs.astype(np.float32)])
                    ya = np.concatenate([yr, ys])
                    nsyn = len(Xs)
                else:
                    Xa, ya, nsyn = Xr, yr, 0
                model, m, s = fit(Xa, ya, seed)
                acc, f1, _ = evaluate(model, m, s, Xte, yte)
                wr.writerow([bl, nr, seed, nsyn, f"{acc:.4f}", f"{f1:.4f}"])
                fout.flush()
                print(f"{bl} n_real={nr} seed={seed} n_syn={nsyn} "
                      f"acc={acc:.4f} f1={f1:.4f}", flush=True)
                if a.cross:
                    for cond, (Xc, yc) in cross.items():
                        acc2, f12, _ = evaluate(model, m, s, Xc, yc)
                        wrx.writerow([bl, nr, seed, cond,
                                      f"{acc2:.4f}", f"{f12:.4f}"])
                        fx.flush()
    fout.close()


if __name__ == "__main__":
    main()
