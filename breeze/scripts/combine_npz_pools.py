"""Combine class-labeled NPZ synthetic pools."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    xs = []
    ys = []
    class_names = None
    for path_s in args.inputs:
        data = np.load(path_s, allow_pickle=True)
        names = [str(x) for x in data["class_names"]]
        if class_names is None:
            class_names = names
        elif names != class_names:
            raise RuntimeError(f"class mismatch in {path_s}: {names} != {class_names}")
        xs.append(data["X"].astype(np.float32))
        ys.append(data["y"].astype(np.int64))
    X = np.concatenate(xs, axis=0) if xs else np.zeros((0,), dtype=np.float32)
    y = np.concatenate(ys, axis=0) if ys else np.zeros((0,), dtype=np.int64)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, X=X, y=y, class_names=np.asarray(class_names or []))
    print(
        {
            "out": str(out),
            "n": int(len(y)),
            "counts": {class_names[i]: int((y == i).sum()) for i in range(len(class_names or []))},
        }
    )


if __name__ == "__main__":
    main()
