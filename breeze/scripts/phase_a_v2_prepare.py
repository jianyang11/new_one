"""Prepare balanced Phase-A v2 pools.

The revised Phase-A protocol requires equal synthetic budgets across recipe
sources. This script builds exact per-class balanced pools with a fixed sampling
seed and records the selected sample manifest.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RUNS = BREEZE / "runs"
RESULTS = BREEZE / "results"

sys.path.insert(0, str(BREEZE / "src"))
from config import CLASSES  # noqa: E402


OUT_DIR = RUNS / "phaseA_v2_balanced"
SEED = 20260705
PREFERRED_B = 150


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_npz_pool(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(path, allow_pickle=True)
    return data["X"].astype(np.float32), data["y"].astype(np.int64)


def counts(y: np.ndarray) -> dict[str, int]:
    return {cls: int((y == ci).sum()) for ci, cls in enumerate(CLASSES)}


def choose_balanced_npz(
    source: str,
    path: Path,
    b_per_class: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    X, y = load_npz_pool(path)
    xs, ys, rows = [], [], []
    for ci, cls in enumerate(CLASSES):
        idx = np.where(y == ci)[0]
        if len(idx) < b_per_class:
            raise RuntimeError(f"{source} {cls}: need {b_per_class}, got {len(idx)}")
        chosen = np.sort(rng.choice(idx, size=b_per_class, replace=False))
        xs.append(X[chosen])
        ys.append(np.full(b_per_class, ci, dtype=np.int64))
        for rank, pool_index in enumerate(chosen.tolist()):
            rows.append(
                {
                    "balanced_pool": source,
                    "class": cls,
                    "rank_in_class": rank,
                    "source_kind": "verified_pool_npz",
                    "source_path": str(path.relative_to(ROOT)),
                    "source_index": pool_index,
                }
            )
    return np.concatenate(xs).astype(np.float32), np.concatenate(ys), rows


def choose_random_open_loop(
    b_per_class: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    base = RUNS / "recipe_ablation_random_v2_full"
    xs, ys, rows = [], [], []
    for ci, cls in enumerate(CLASSES):
        files = sorted(base.glob(f"{cls}_*_r0.npy"))
        if len(files) < b_per_class:
            raise RuntimeError(f"random_open_loop {cls}: need {b_per_class}, got {len(files)}")
        chosen_idx = np.sort(rng.choice(np.arange(len(files)), size=b_per_class, replace=False))
        class_x = []
        for rank, file_pos in enumerate(chosen_idx.tolist()):
            path = files[file_pos]
            class_x.append(np.load(path).astype(np.float32))
            rows.append(
                {
                    "balanced_pool": "phaseA_v2_random_open_loop_B150",
                    "class": cls,
                    "rank_in_class": rank,
                    "source_kind": "random_recipe_r0_without_verifier",
                    "source_path": str(path.relative_to(ROOT)),
                    "source_index": file_pos,
                }
            )
        xs.append(np.stack(class_x).astype(np.float32))
        ys.append(np.full(b_per_class, ci, dtype=np.int64))
    return np.concatenate(xs).astype(np.float32), np.concatenate(ys), rows


def save_pool(name: str, X: np.ndarray, y: np.ndarray, manifest: list[dict[str, Any]]) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = OUT_DIR / f"{name}.npz"
    manifest_path = OUT_DIR / f"{name}_manifest.csv"
    np.savez_compressed(npz_path, X=X, y=y, class_names=np.array(CLASSES))
    write_csv(manifest_path, manifest)
    c = counts(y)
    return {
        "pool": name,
        "path": str(npz_path.relative_to(ROOT)),
        "manifest": str(manifest_path.relative_to(ROOT)),
        "n": int(len(y)),
        "healthy": c["healthy"],
        "OR": c["OR"],
        "IR": c["IR"],
    }


def main() -> None:
    rule_path = RUNS / "recipe_ablation_rule_v2_full" / "pool_v2.npz"
    llm_path = RUNS / "rescreen_v2_full" / "pool_v2.npz"
    random_verified_summary = json.loads((RUNS / "recipe_ablation_random_v2_full" / "summary.json").read_text())
    X_rule, y_rule = load_npz_pool(rule_path)
    X_llm, y_llm = load_npz_pool(llm_path)
    available = {
        "rule": counts(y_rule),
        "llm": counts(y_llm),
        "random_open_loop": {
            cls: len(sorted((RUNS / "recipe_ablation_random_v2_full").glob(f"{cls}_*_r0.npy")))
            for cls in CLASSES
        },
    }
    b_per_class = min(
        PREFERRED_B,
        min(min(v.values()) for v in available.values()),
    )
    if b_per_class <= 0:
        raise RuntimeError(f"invalid b_per_class={b_per_class}, available={available}")

    rng = np.random.default_rng(SEED)
    summaries: list[dict[str, Any]] = []
    X, y, manifest = choose_balanced_npz("phaseA_v2_rule_B150", rule_path, b_per_class, rng)
    summaries.append(save_pool("phaseA_v2_rule_B150", X, y, manifest))
    X, y, manifest = choose_balanced_npz("phaseA_v2_llm_k3_B150", llm_path, b_per_class, rng)
    summaries.append(save_pool("phaseA_v2_llm_k3_B150", X, y, manifest))
    X, y, manifest = choose_random_open_loop(b_per_class, rng)
    summaries.append(save_pool("phaseA_v2_random_open_loop_B150", X, y, manifest))

    budget_rows = []
    for source, cdict in available.items():
        budget_rows.append(
            {
                "source": source,
                "available_healthy": cdict["healthy"],
                "available_OR": cdict["OR"],
                "available_IR": cdict["IR"],
                "selected_B_per_class": b_per_class,
                "selection_seed": SEED,
            }
        )
    budget_rows.append(
        {
            "source": "random_plus_verifier",
            "available_healthy": random_verified_summary["kept_counts"]["healthy"],
            "available_OR": random_verified_summary["kept_counts"]["OR"],
            "available_IR": random_verified_summary["kept_counts"]["IR"],
            "selected_B_per_class": 0,
            "selection_seed": SEED,
        }
    )
    write_csv(RESULTS / "phaseA_v2_budget_summary.csv", budget_rows)
    write_csv(RESULTS / "phaseA_v2_balanced_pool_summary.csv", summaries)
    print(f"B={b_per_class}")
    for row in summaries:
        print(row)
    print(f"wrote {RESULTS / 'phaseA_v2_budget_summary.csv'}")
    print(f"wrote {RESULTS / 'phaseA_v2_balanced_pool_summary.csv'}")


if __name__ == "__main__":
    main()
