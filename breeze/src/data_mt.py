"""Machine-tool private dataset (MechaForge rig): X/Y/Z accel + motor current.

File-based split per class: files 1,2,4,5,10 -> train, files 7,8 -> test.
Windows of 2048 samples, stride 1024, 4 channels.
"""
import glob
import os
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import PROC_DIR

MT_DIR = Path(__file__).parent.parent / "data_mt"
WIN_MT, STRIDE_MT = 2048, 1024
TRAIN_FILES = {"1", "2", "4", "5", "10"}
TEST_FILES = {"7", "8"}


def _windows(arr):
    n = (len(arr) - WIN_MT) // STRIDE_MT + 1
    return np.stack([arr[i * STRIDE_MT:i * STRIDE_MT + WIN_MT].T
                     for i in range(n)])


def build():
    out = {}
    for f in sorted(glob.glob(str(MT_DIR / "*.csv"))):
        base = os.path.basename(f).replace("_pre", "").replace(".csv", "")
        cls, fid = base.split("_")
        d = np.genfromtxt(f, delimiter=",", skip_header=1)
        split = "train" if fid in TRAIN_FILES else "test"
        out.setdefault((split, cls), []).append(_windows(d))
    for (split, cls), ws in out.items():
        W = np.concatenate(ws).astype(np.float32)
        np.savez_compressed(PROC_DIR / f"mt_{split}_{cls}.npz", windows=W)
        print(split, cls, W.shape)


def load_mt(split):
    Xs, ys = [], []
    for ci, cls in enumerate(["1", "2", "3"]):
        d = np.load(PROC_DIR / f"mt_{split}_{cls}.npz")
        Xs.append(d["windows"])
        ys.append(np.full(len(d["windows"]), ci))
    return np.concatenate(Xs), np.concatenate(ys)


if __name__ == "__main__":
    build()
