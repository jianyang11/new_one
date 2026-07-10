"""Block 5: physical fidelity + diversity metrics, acceptance statistics,
and statistical tests. Outputs CSVs to results/.

Usage: python metrics.py
"""
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).parent))
from config import CLASSES, MAIN_COND, RUNS_DIR, RESULTS_DIR, FS
from data import load_file_split
from pools import build_pool
from verifier.features import time_stats, psd, envelope_spectrum

RESULTS = RESULTS_DIR
RESULTS.mkdir(exist_ok=True)
PHYS_RUN = RUNS_DIR / "pool_physics_file_k3"
BASIC_RUN = RUNS_DIR / "pool_basic_file_k0"
DOWNSTREAM_CSV = RESULTS / "downstream_file.csv"


def feature_vec(w):
    st = time_stats(w[0])
    v = [st["rms"], st["kurtosis"], st["crest"], st["skewness"]]
    f, p = psd(w[0], FS)
    tot = np.trapezoid(p, f) + 1e-12
    for a, b in [(0, 500), (500, 1500), (1500, 2500), (2500, 4000)]:
        m = (f >= a) & (f < b)
        v.append(np.trapezoid(p[m], f[m]) / tot)
    return np.array(v)


def pool_metrics(X, y, Xr, yr, name):
    """Fidelity (feature MMD to real) + diversity (mean pairwise NN dist)."""
    rows = []
    for ci, cls in enumerate(CLASSES):
        Xs = X[y == ci]
        Xrc = Xr[yr == ci]
        if len(Xs) < 2:
            continue
        rng = np.random.default_rng(0)
        Fs = np.array([feature_vec(w) for w in Xs[:150]])
        Fr = np.array([feature_vec(Xrc[i]) for i in
                       rng.choice(len(Xrc), min(150, len(Xrc)), replace=False)])
        mu, sd = Fr.mean(0), Fr.std(0) + 1e-9
        Zs, Zr = (Fs - mu) / sd, (Fr - mu) / sd
        # MMD^2 with RBF kernel (median heuristic)
        def k(A, B, g):
            d = ((A[:, None] - B[None]) ** 2).sum(-1)
            return np.exp(-d / (2 * g ** 2))
        allZ = np.vstack([Zs, Zr])
        g = np.median(np.sqrt(((allZ[:, None] - allZ[None]) ** 2).sum(-1) + 1e-12))
        mmd2 = k(Zs, Zs, g).mean() + k(Zr, Zr, g).mean() - 2 * k(Zs, Zr, g).mean()
        # diversity: mean NN distance among synthetic (feature space, real-z)
        D = np.sqrt(((Zs[:, None] - Zs[None]) ** 2).sum(-1))
        np.fill_diagonal(D, np.inf)
        nn = D.min(1)
        # real-real reference diversity
        Dr = np.sqrt(((Zr[:, None] - Zr[None]) ** 2).sum(-1))
        np.fill_diagonal(Dr, np.inf)
        rows.append({"pool": name, "class": cls, "n": len(Xs),
                     "mmd2": mmd2, "nn_div": nn.mean(),
                     "nn_div_real": Dr.min(1).mean()})
    return rows


def acceptance_stats(run_dir, name):
    """Per-K acceptance rate and LLM-call cost."""
    rows = []
    recs = [json.loads(f.read_text()) for f in Path(run_dir).glob("*.json")]
    for k in range(4):
        acc = calls = tot = 0
        for d in recs:
            tot += 1
            used = 0
            ok = False
            for h in d["history"]:
                if h["round"] > k:
                    break
                used += 1
                if h.get("feasible"):
                    ok = True
                    break
            acc += ok
            calls += max(used, min(k + 1, len(d["history"])))
        if tot:
            rows.append({"run": name, "K": k, "acceptance": acc / tot,
                         "mean_llm_calls": calls / tot, "n_slots": tot})
    return rows


def downstream_tests():
    df = pd.read_csv(DOWNSTREAM_CSV)
    out = []
    for nr in sorted(df.n_real.unique()):
        d = df[df.n_real == nr]
        base = d[d.baseline == "breeze_k3"].sort_values("seed")["acc"].values
        for bl in d.baseline.unique():
            if bl == "breeze_k3":
                continue
            o = d[d.baseline == bl].sort_values("seed")["acc"].values
            n = min(len(base), len(o))
            if n < 5:
                continue
            try:
                stat, p = wilcoxon(base[:n], o[:n])
            except ValueError:
                stat, p = np.nan, 1.0
            out.append({"n_real": nr, "baseline": bl,
                        "breeze_mean": base[:n].mean(), "other_mean": o[:n].mean(),
                        "delta": base[:n].mean() - o[:n].mean(), "p_wilcoxon": p})
    pd.DataFrame(out).to_csv(RESULTS / "significance.csv", index=False)


def main():
    Xr, yr, _ = load_file_split("train", MAIN_COND)
    rows = []
    for name, args in [("open_loop_basic", (BASIC_RUN, "open_loop_basic", 3)),
                       ("open_loop_phys", (PHYS_RUN, "open_loop_phys", 3)),
                       ("stats_only", (PHYS_RUN, "stats_only", 3)),
                       ("envelope_only", (PHYS_RUN, "envelope_only", 3)),
                       ("breeze_k0", (PHYS_RUN, "breeze", 0)),
                       ("breeze_k1", (PHYS_RUN, "breeze", 1)),
                       ("breeze_k2", (PHYS_RUN, "breeze", 2)),
                       ("breeze_k3", (PHYS_RUN, "breeze", 3))]:
        X, y = build_pool(args[0], args[1], k=args[2])
        rows += pool_metrics(X, y, Xr, yr, name)
        print(name, "done", flush=True)
    pd.DataFrame(rows).to_csv(RESULTS / "pool_metrics.csv", index=False)
    arows = acceptance_stats(PHYS_RUN, "physics_file_k3")
    pd.DataFrame(arows).to_csv(RESULTS / "acceptance.csv", index=False)
    if DOWNSTREAM_CSV.exists():
        downstream_tests()
    print("metrics done")


if __name__ == "__main__":
    main()
