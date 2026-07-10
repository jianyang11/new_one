"""Build a clean-label UMich v4 inner split.

The source NPZ is the outer training split.  The output keeps only clean
supervised windows:

- unworn + passed_visual_inspection=yes
- worn + passed_visual_inspection=no

Split units remain experiments.  Candidate validation unit sets are enumerated
and scored by class-wise validation fraction and condition balance, with hard
constraints that both train and validation contain both classes.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np


BASE_KEYS = {"X", "y", "class_names", "source_units", "fs_hz", "window", "channels"}


def norm(values: np.ndarray) -> np.ndarray:
    return np.asarray([str(v).strip().lower() for v in values])


def clean_mask(data: np.lib.npyio.NpzFile) -> np.ndarray:
    if "pure_exemplar" in data.files:
        return data["pure_exemplar"].astype(bool)
    tool = norm(data["tool_condition"])
    visual = norm(data["passed_visual_inspection"])
    return ((tool == "unworn") & (visual == "yes")) | ((tool == "worn") & (visual == "no"))


def per_window_extras(data: np.lib.npyio.NpzFile, mask: np.ndarray) -> dict[str, np.ndarray]:
    n = data["y"].shape[0]
    out: dict[str, np.ndarray] = {}
    for key in data.files:
        if key in BASE_KEYS:
            continue
        arr = data[key]
        if arr.shape[:1] == (n,):
            out[key] = arr[mask]
        else:
            out[key] = arr
    return out


def counts_by_class(y: np.ndarray, class_names: list[str]) -> dict[str, int]:
    return {cls: int((y == i).sum()) for i, cls in enumerate(class_names)}


def condition_distribution(data: np.lib.npyio.NpzFile, mask: np.ndarray) -> Counter[tuple[float, float]]:
    dist: Counter[tuple[float, float]] = Counter()
    if "feedrate" not in data.files or "clamp_pressure" not in data.files:
        return dist
    feed = data["feedrate"].astype(float)
    clamp = data["clamp_pressure"].astype(float)
    for f, c in zip(feed[mask], clamp[mask], strict=False):
        dist[(float(f), float(c))] += 1
    return dist


def l1_distribution_distance(a: Counter[tuple[float, float]], b: Counter[tuple[float, float]]) -> float:
    total_a = sum(a.values())
    total_b = sum(b.values())
    if total_a == 0 or total_b == 0:
        return 0.0
    keys = set(a) | set(b)
    return float(sum(abs(a[k] / total_a - b[k] / total_b) for k in keys))


def select_val_units(
    data: np.lib.npyio.NpzFile,
    mask: np.ndarray,
    val_frac: float,
    min_train_per_class: int,
    min_val_per_class: int,
) -> set[str]:
    y = data["y"]
    units = np.asarray([str(u) for u in data["source_units"]])
    class_names = [str(c) for c in data["class_names"]]
    clean_units = sorted(set(units[mask]))
    total_counts = np.asarray([int(((y == i) & mask).sum()) for i in range(len(class_names))], dtype=float)
    if np.any(total_counts == 0):
        raise RuntimeError(f"clean set is missing a class: {dict(zip(class_names, total_counts.astype(int), strict=False))}")

    unit_masks = {u: mask & (units == u) for u in clean_units}
    all_dist = condition_distribution(data, mask)
    best_units: set[str] | None = None
    best_key: tuple[float, float, float, int, tuple[str, ...]] | None = None
    for r in range(1, len(clean_units)):
        for subset in combinations(clean_units, r):
            val_mask = np.zeros_like(mask, dtype=bool)
            for u in subset:
                val_mask |= unit_masks[u]
            train_mask = mask & ~val_mask
            val_counts = np.asarray([int(((y == i) & val_mask).sum()) for i in range(len(class_names))])
            train_counts = np.asarray([int(((y == i) & train_mask).sum()) for i in range(len(class_names))])
            if np.any(val_counts < min_val_per_class) or np.any(train_counts < min_train_per_class):
                continue
            class_frac_err = float(np.max(np.abs(val_counts / total_counts - val_frac)))
            total_frac_err = float(abs(float(val_mask.sum()) / float(mask.sum()) - val_frac))
            cond_dist = l1_distribution_distance(condition_distribution(data, val_mask), all_dist)
            key = (class_frac_err, total_frac_err, cond_dist, len(subset), tuple(subset))
            if best_key is None or key < best_key:
                best_key = key
                best_units = set(subset)
    if best_units is None:
        raise RuntimeError(
            "No clean experiment-level split satisfies both-class train/val constraints; "
            "UMich v4 clean task has insufficient clean support."
        )
    return best_units


def save_split(path: Path, data: np.lib.npyio.NpzFile, mask: np.ndarray, split_note: str) -> None:
    payload = {
        "X": data["X"][mask].astype(np.float32),
        "y": data["y"][mask].astype(np.int64),
        "class_names": data["class_names"],
        "source_units": data["source_units"][mask],
        "fs_hz": data["fs_hz"],
        "window": data["window"],
        "channels": data["channels"],
        "clean_supervised_definition": np.asarray(
            ["unworn+passed_visual_inspection=yes or worn+passed_visual_inspection=no"]
        ),
        "inner_split_definition": np.asarray([split_note]),
    }
    payload.update(per_window_extras(data, mask))
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-npz", required=True)
    parser.add_argument("--out-prefix", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--val-frac", type=float, default=0.20)
    parser.add_argument("--min-train-per-class", type=int, default=10)
    parser.add_argument("--min-val-per-class", type=int, default=1)
    args = parser.parse_args()

    data = np.load(args.train_npz, allow_pickle=True)
    y = data["y"].astype(np.int64)
    units = np.asarray([str(u) for u in data["source_units"]])
    class_names = [str(c) for c in data["class_names"]]
    mask = clean_mask(data)
    val_units = select_val_units(data, mask, args.val_frac, args.min_train_per_class, args.min_val_per_class)
    val_mask = mask & np.asarray([u in val_units for u in units], dtype=bool)
    train_mask = mask & ~val_mask
    split_note = (
        "clean supervised experiment-level split; validation units chosen by exhaustive class-fraction and "
        "feedrate/clamp-pressure balance on the outer training split only"
    )
    save_split(Path(f"{args.out_prefix}_train.npz"), data, train_mask, split_note)
    save_split(Path(f"{args.out_prefix}_val.npz"), data, val_mask, split_note)

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for unit in sorted(set(units[mask])):
        unit_mask = mask & (units == unit)
        rows.append(
            {
                "unit": unit,
                "inner_split": "val" if unit in val_units else "train",
                **counts_by_class(y[unit_mask], class_names),
                "feedrate": ";".join(str(float(v)) for v in sorted(set(data["feedrate"][unit_mask]))),
                "clamp_pressure": ";".join(str(float(v)) for v in sorted(set(data["clamp_pressure"][unit_mask]))),
            }
        )
    with (report_dir / "umich_v4_clean_inner_split_units.csv").open("w", newline="") as f:
        fieldnames = ["unit", "inner_split", *class_names, "feedrate", "clamp_pressure"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    train_counts = counts_by_class(y[train_mask], class_names)
    val_counts = counts_by_class(y[val_mask], class_names)
    all_counts = counts_by_class(y[mask], class_names)
    condition_train = condition_distribution(data, train_mask)
    condition_val = condition_distribution(data, val_mask)
    lines = [
        "# UMich v4 Clean Inner Split",
        "",
        f"- Source NPZ: `{args.train_npz}`",
        f"- Clean definition: `unworn+passed_visual_inspection=yes` or `worn+passed_visual_inspection=no`.",
        "- Split unit: experiment/source unit; no random window split.",
        f"- Validation units: `{sorted(val_units)}`",
        f"- All clean counts: `{all_counts}`",
        f"- Inner-train clean counts: `{train_counts}`",
        f"- Inner-val clean counts: `{val_counts}`",
        f"- Inner-train feedrate/clamp distribution: `{dict(condition_train)}`",
        f"- Inner-val feedrate/clamp distribution: `{dict(condition_val)}`",
        "",
        "This split is for UMich v4 learnability repair only. It uses no held-out test labels or windows.",
    ]
    (report_dir / "umich_v4_clean_inner_split_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
