"""Verifier self-test: coverage on real train/test, rejection of corruptions."""
import sys, time
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import MAIN_COND, CLASSES, RUNS_DIR
from data import load_split
from verifier.verifier import BreezeVerifier

rng = np.random.default_rng(0)
Xtr, ytr, btr = load_split("train", MAIN_COND)
Xte, yte, bte = load_split("test", MAIN_COND)
print("train", Xtr.shape, "test", Xte.shape)

t0 = time.time()
v = BreezeVerifier(coverage=0.90)
v.calibrate(Xtr, ytr, MAIN_COND)
print(f"calibrated in {time.time()-t0:.1f}s; freqs={ {k: round(f,1) for k,f in v.freqs.items()} }")
for cls in CLASSES:
    c = v.calib[cls]
    print(cls, "band=", c.get("band"), "alpha=", round(c["alpha"], 4))

RUNS_DIR.mkdir(exist_ok=True)
v.save(RUNS_DIR / "verifier_main.json")

def pass_rate(X, y, sub=150):
    rates = {}
    for ci, cls in enumerate(CLASSES):
        W = X[y == ci]
        idx = rng.choice(len(W), min(sub, len(W)), replace=False)
        ok = sum(v.verify(W[i], cls)["feasible"] for i in idx)
        rates[cls] = ok / len(idx)
    return rates

t0 = time.time()
print("real-train pass rates:", pass_rate(Xtr, ytr))
print("real-test  pass rates:", pass_rate(Xte, yte))
print(f"({time.time()-t0:.1f}s)")

# corruption checks: these MUST be rejected
w = Xtr[ytr == 1][0].copy()
tests = {
    "gauss_noise_as_OR": rng.normal(0, w.std(), w.shape).astype(np.float32),
    "scaled_3x_OR": (3 * w),
    "healthy_window_as_OR": Xtr[ytr == 0][0],
    "OR_window_as_IR": w,  # verify under IR
}
for name, ww in tests.items():
    cls = "IR" if name == "OR_window_as_IR" else "OR"
    r = v.verify(ww, cls)
    fails = [m for gr in r["gates"].values() for m in gr["messages"]]
    print(f"{name}: feasible={r['feasible']} | {fails[:2]}")
