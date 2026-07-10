"""Build train-bearing-only internal LOCO splits for PU v3 development."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "src"))

from config import CLASSES, CONDITIONS, PROC_DIR, SPLIT  # noqa: E402


def class_for_bearing(bearing: str) -> str:
    if bearing.startswith("K0"):
        return "healthy"
    if bearing.startswith("KA"):
        return "OR"
    if bearing.startswith("KI"):
        return "IR"
    raise ValueError(f"unknown bearing id: {bearing}")


def load_condition_train_bearings(cond: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    source: list[str] = []
    for path in sorted(PROC_DIR.glob(f"{cond}_*.npz")):
        data = np.load(path, allow_pickle=True)
        bearing = str(data["bearing"])
        cls = class_for_bearing(bearing)
        if bearing not in set(SPLIT["train"][cls]):
            continue
        W = data["windows"].astype(np.float32)
        xs.append(W)
        ys.append(np.full(len(W), CLASSES.index(cls), dtype=np.int64))
        source.extend([path.name] * len(W))
    if not xs:
        raise FileNotFoundError(f"no train-bearing windows for {cond}")
    return np.concatenate(xs), np.concatenate(ys), np.asarray(source)


def counts(y: np.ndarray) -> dict[str, int]:
    return {CLASSES[i]: int((y == i).sum()) for i in range(len(CLASSES))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="proc")
    parser.add_argument("--report", default="breeze/results/pu_loco_v3_2026-07-08/internal_split_report.md")
    args = parser.parse_args()

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    loaded = {cond: load_condition_train_bearings(cond) for cond in CONDITIONS}
    report = [
        "# PU LOCO v3 Internal Splits",
        "",
        "These splits use only `config.SPLIT['train']` bearing IDs. The pseudo held-out condition is used only for internal development evaluation.",
        "",
        "| pseudo heldout | train counts | pseudo-test counts |",
        "|---|---:|---:|",
    ]
    for heldout in CONDITIONS:
        train_conds = [c for c in CONDITIONS if c != heldout]
        Xtr = np.concatenate([loaded[c][0] for c in train_conds]).astype(np.float32)
        ytr = np.concatenate([loaded[c][1] for c in train_conds]).astype(np.int64)
        src_tr = np.concatenate([loaded[c][2] for c in train_conds])
        Xte, yte, src_te = loaded[heldout]
        train_path = out_dir / f"pu_loco_v3_internal_{heldout}_train.npz"
        test_path = out_dir / f"pu_loco_v3_internal_{heldout}_test.npz"
        np.savez_compressed(
            train_path,
            X=Xtr,
            y=ytr,
            source_files=src_tr,
            class_names=np.asarray(CLASSES),
            split="internal_train",
            pseudo_heldout_condition=heldout,
            train_conditions=np.asarray(train_conds),
        )
        np.savez_compressed(
            test_path,
            X=Xte.astype(np.float32),
            y=yte.astype(np.int64),
            source_files=src_te,
            class_names=np.asarray(CLASSES),
            split="internal_pseudo_test",
            pseudo_heldout_condition=heldout,
        )
        report.append(f"| {heldout} | `{json.dumps(counts(ytr), sort_keys=True)}` | `{json.dumps(counts(yte), sort_keys=True)}` |")
    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n")
    print(json.dumps({"report": str(report_path), "folds": len(CONDITIONS)}, sort_keys=True))


if __name__ == "__main__":
    main()
