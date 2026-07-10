"""PU data preprocessing: .mat -> decimated windowed arrays (resume-safe)."""
import sys
import numpy as np
import scipy.io as sio
from scipy.signal import decimate
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (RAW_DIR, PROC_DIR, DECIM, WIN, HOP, CONDITIONS, BEARINGS,
                    CHANNELS)


def load_mat(path: Path) -> dict:
    m = sio.loadmat(path, squeeze_me=False)
    key = [k for k in m.keys() if not k.startswith("__")][0]
    Y = m[key]["Y"][0, 0]
    out = {}
    for i in range(Y.shape[1]):
        name = str(Y[0, i]["Name"][0])
        if name in CHANNELS:
            out[name] = Y[0, i]["Data"].ravel().astype(np.float64)
    return out


def process_file(path: Path) -> np.ndarray | None:
    """Return windows array (n_win, 3, WIN) at FS, channel order CHANNELS."""
    try:
        sig = load_mat(path)
    except Exception as e:
        print(f"SKIP {path.name}: {e}")
        return None
    if any(c not in sig for c in CHANNELS):
        print(f"SKIP {path.name}: missing channels {set(CHANNELS)-set(sig)}")
        return None
    n = min(len(sig[c]) for c in CHANNELS)
    chans = []
    for c in CHANNELS:
        x = sig[c][:n]
        # zero-phase FIR decimation (anti-aliased)
        x = decimate(x, DECIM, ftype="fir", zero_phase=True)
        chans.append(x)
    arr = np.stack(chans)  # (3, n_ds)
    n_win = (arr.shape[1] - WIN) // HOP + 1
    if n_win < 1:
        return None
    wins = np.stack([arr[:, i * HOP:i * HOP + WIN] for i in range(n_win)])
    return wins.astype(np.float32)


def preprocess_all():
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    for cls, bearings in BEARINGS.items():
        for b in bearings:
            for cond in CONDITIONS:
                out = PROC_DIR / f"{cond}_{b}.npz"
                if out.exists():
                    continue
                files = sorted((RAW_DIR / b).glob(f"{cond}_{b}_*.mat"),
                               key=lambda p: int(p.stem.split("_")[-1]))
                if not files:
                    print(f"WARN no files {cond} {b}")
                    continue
                all_w, file_ids = [], []
                for f in files:
                    w = process_file(f)
                    if w is None:
                        continue
                    all_w.append(w)
                    file_ids += [int(f.stem.split("_")[-1])] * len(w)
                if not all_w:
                    continue
                W = np.concatenate(all_w)
                np.savez_compressed(out, windows=W,
                                    file_ids=np.array(file_ids),
                                    cls=cls, bearing=b, cond=cond)
                print(f"{out.name}: {W.shape}")


def load_split(split: str, cond: str, max_per_bearing: int | None = None,
               rng: np.random.Generator | None = None):
    """Return (X, y, bearing_ids) for a split at a condition."""
    from config import SPLIT, CLASSES
    Xs, ys, bs = [], [], []
    for ci, cls in enumerate(CLASSES):
        for b in SPLIT[split][cls]:
            f = PROC_DIR / f"{cond}_{b}.npz"
            if not f.exists():
                raise FileNotFoundError(f)
            d = np.load(f, allow_pickle=True)
            W = d["windows"]
            if max_per_bearing is not None and len(W) > max_per_bearing:
                idx = (rng or np.random.default_rng(0)).choice(
                    len(W), max_per_bearing, replace=False)
                W = W[idx]
            Xs.append(W)
            ys.append(np.full(len(W), ci))
            bs += [b] * len(W)
    return np.concatenate(Xs), np.concatenate(ys), np.array(bs)


def load_file_split(split: str, cond: str, frac_train: float = 0.8):
    """Session-based split: for EVERY bearing, the chronologically first
    80% of measurement files are train, the last 20% test (no window
    crosses a file boundary, so there is no train/test overlap)."""
    from config import SPLIT, CLASSES
    Xs, ys, bs = [], [], []
    for ci, cls in enumerate(CLASSES):
        for b in SPLIT["train"][cls] + SPLIT["test"][cls]:
            f = PROC_DIR / f"{cond}_{b}.npz"
            if not f.exists():
                raise FileNotFoundError(f)
            d = np.load(f, allow_pickle=True)
            W, fid = d["windows"], d["file_ids"]
            fs = np.unique(fid)
            cut = fs[int(len(fs) * frac_train)]
            m = fid < cut if split == "train" else fid >= cut
            Xs.append(W[m])
            ys.append(np.full(m.sum(), ci))
            bs += [b] * int(m.sum())
    return np.concatenate(Xs), np.concatenate(ys), np.array(bs)


if __name__ == "__main__":
    preprocess_all()
