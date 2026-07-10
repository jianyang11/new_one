"""Assemble synthetic pools for the different baselines from pipeline runs.

Pool definitions (all derived from the SAME physics-prompt K=3 run, plus a
separate basic-prompt K=0 run):
  open_loop_basic : all round-0 windows of the basic-prompt run (admit all)
  open_loop_phys  : all round-0 windows of the physics-prompt run (admit all)
  stats_only      : round-0 windows passing only sanity+boundary gates
  envelope_only   : round-0 windows passing only sanity+envelope gates
  breeze_k0..k3   : first feasible window among rounds <= k (gate-admitted pool)
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import CLASSES


def _load(run_dir, cls, i, rnd):
    p = Path(run_dir) / f"{cls}_{i:04d}_r{rnd}.npy"
    return np.load(p) if p.exists() else None


def build_pool(run_dir, mode, k=3):
    run_dir = Path(run_dir)
    X, y = [], []
    for f in sorted(run_dir.glob("*.json")):
        d = json.loads(f.read_text())
        cls, i = d["class"], d["slot"]
        ci = CLASSES.index(cls)
        if mode in ("open_loop_basic", "open_loop_phys"):
            for h in d["history"]:
                if "recipe" in h and h["round"] == 0:
                    w = _load(run_dir, cls, i, 0)
                    if w is not None:
                        X.append(w); y.append(ci)
                    break
        elif mode in ("stats_only", "envelope_only"):
            gate = "boundary" if mode == "stats_only" else "envelope"
            for h in d["history"]:
                if "recipe" in h and h["round"] == 0:
                    gp = h.get("gate_pass", {})
                    if gp.get("sanity", False) and gp.get(gate, False):
                        w = _load(run_dir, cls, i, 0)
                        if w is not None:
                            X.append(w); y.append(ci)
                    break
        elif mode == "breeze":
            for h in d["history"]:
                if h.get("feasible") and h["round"] <= k:
                    w = _load(run_dir, cls, i, h["round"])
                    if w is not None:
                        X.append(w); y.append(ci)
                    for px in sorted(run_dir.glob(f"{cls}_{i:04d}_x*.npy")):
                        X.append(np.load(px)); y.append(ci)
                    break
    if not X:
        return np.zeros((0, 3, 2048), np.float32), np.zeros(0, np.int64)
    return np.stack(X).astype(np.float32), np.array(y)


def _feats(X):
    from verifier.features import time_stats
    return np.array([[time_stats(w[j])[k] for j in range(3)
                      for k in ("rms", "kurtosis", "crest")] for w in X])


def diversity_filter(X, y, Xr, yr, pctl=1.0, seed=0):
    """M3 diversity gate: drop synthetic windows whose nearest synthetic
    neighbour (standardized feature space) is closer than the `pctl`-th
    percentile of real--real NN distances of the same class."""
    keep = np.zeros(len(X), bool)
    rng = np.random.default_rng(seed)
    for ci in np.unique(y):
        si = np.where(y == ci)[0]
        ri = np.where(yr == ci)[0]
        ri = rng.choice(ri, min(200, len(ri)), replace=False)
        Fr = _feats(Xr[ri])
        mu, sd = Fr.mean(0), Fr.std(0) + 1e-9
        Zr = (Fr - mu) / sd
        Dr = np.sqrt(((Zr[:, None] - Zr[None]) ** 2).sum(-1))
        np.fill_diagonal(Dr, np.inf)
        thr = np.percentile(Dr.min(1), pctl)
        Zs = (_feats(X[si]) - mu) / sd
        taken = []
        for j, z in enumerate(Zs):
            if not taken or min(np.sqrt(((z - Zs[t]) ** 2).sum())
                                for t in taken) >= thr:
                taken.append(j)
        keep[si[taken]] = True
    return X[keep], y[keep]
