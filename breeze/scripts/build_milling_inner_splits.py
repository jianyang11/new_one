"""Build train-only inner validation splits for milling method development."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np


BASE_NPZ_KEYS = {"X", "y", "class_names", "source_units", "fs_hz", "window", "channels"}


def per_window_extras(data: np.lib.npyio.NpzFile, n_windows: int, mask: np.ndarray) -> dict[str, np.ndarray]:
    extras: dict[str, np.ndarray] = {}
    for key in data.files:
        if key in BASE_NPZ_KEYS:
            continue
        arr = data[key]
        if arr.shape[:1] == (n_windows,):
            extras[key] = arr[mask]
    return extras


def norm_str_array(values: np.ndarray) -> np.ndarray:
    return np.asarray([str(v).strip().lower() for v in values])


def choose_units_by_window_target(cls_units: list[str], unit_counts: dict[str, int], val_frac: float) -> set[str]:
    if len(cls_units) <= 1:
        return set(cls_units)
    total = sum(unit_counts[u] for u in cls_units)
    target = total * val_frac
    best_subset: tuple[str, ...] | None = None
    best_key: tuple[float, int, tuple[str, ...]] | None = None
    for r in range(1, len(cls_units)):
        for subset in combinations(cls_units, r):
            n = sum(unit_counts[u] for u in subset)
            key = (abs(n - target), abs(r - max(1, round(len(cls_units) * val_frac))), tuple(subset))
            if best_key is None or key < best_key:
                best_key = key
                best_subset = subset
    return set(best_subset or cls_units[:1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["berkeley", "berkeley_v2", "umich"], default="berkeley")
    parser.add_argument("--train-npz", default="proc/milling_berkeley_train.npz")
    parser.add_argument("--out-prefix", default="proc/milling_berkeley_inner")
    parser.add_argument("--report-dir", default="breeze/results/milling_berkeley_2026-07-08")
    parser.add_argument("--val-frac", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=20260708)
    parser.add_argument("--balance-by", choices=["units", "windows"], default="units")
    parser.add_argument(
        "--umich-pure-exemplar-out",
        default="",
        help=(
            "Optional NPZ path for UMich LLM/verifier calibration exemplars. "
            "It is filtered from inner_train only with "
            "unworn+passed_visual_inspection=yes or worn+passed_visual_inspection=no."
        ),
    )
    args = parser.parse_args()

    data = np.load(args.train_npz, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    units = np.asarray([str(u) for u in data["source_units"]])
    class_names = [str(c) for c in data["class_names"]]
    rng = np.random.default_rng(args.seed)

    unit_rows = []
    val_units: set[str] = set()
    for ci, cls in enumerate(class_names):
        cls_units = []
        unit_counts_by_name = {}
        for unit in sorted(set(units[y == ci])):
            idx = np.where(units == unit)[0]
            labels = set(int(v) for v in y[idx])
            if labels != {ci}:
                raise RuntimeError(f"unit {unit} has mixed labels: {labels}")
            cls_units.append(unit)
            unit_counts_by_name[unit] = int(len(idx))
        shuffled = np.asarray(cls_units, dtype=object)
        rng.shuffle(shuffled)
        if args.balance_by == "windows":
            chosen = choose_units_by_window_target([str(u) for u in shuffled], unit_counts_by_name, args.val_frac)
        else:
            n_val = max(1, int(round(len(shuffled) * args.val_frac)))
            chosen = set(str(u) for u in shuffled[:n_val])
        val_units |= chosen
        for unit in cls_units:
            unit_rows.append(
                {
                    "unit": unit,
                    "class": str(cls),
                    "n_windows": int(np.sum(units == unit)),
                    "inner_split": "val" if unit in chosen else "train",
                }
            )

    val_mask = np.asarray([u in val_units for u in units], dtype=bool)
    train_mask = ~val_mask
    for split, mask in [("train", train_mask), ("val", val_mask)]:
        payload = {
            "X": X[mask],
            "y": y[mask],
            "class_names": class_names,
            "source_units": units[mask],
            "fs_hz": data["fs_hz"],
            "window": data["window"],
            "channels": data["channels"],
        }
        payload.update(per_window_extras(data, len(y), mask))
        np.savez_compressed(
            f"{args.out_prefix}_{split}.npz",
            **payload,
        )

    pure_mask = None
    if args.umich_pure_exemplar_out:
        missing = [k for k in ["tool_condition", "passed_visual_inspection"] if k not in data.files]
        if args.dataset != "umich":
            raise RuntimeError("--umich-pure-exemplar-out is only valid with --dataset umich")
        if missing:
            raise RuntimeError(
                "UMich pure exemplar filtering requires metadata fields in the source NPZ; "
                f"missing={missing}. Re-run preprocess_milling_datasets.py first."
            )
        tool = norm_str_array(data["tool_condition"])
        visual = norm_str_array(data["passed_visual_inspection"])
        pure_mask = train_mask & (
            ((tool == "unworn") & (visual == "yes"))
            | ((tool == "worn") & (visual == "no"))
        )
        if not np.any(pure_mask):
            raise RuntimeError("UMich pure exemplar filter produced zero windows")
        payload = {
            "X": X[pure_mask],
            "y": y[pure_mask],
            "class_names": class_names,
            "source_units": units[pure_mask],
            "fs_hz": data["fs_hz"],
            "window": data["window"],
            "channels": data["channels"],
            "pure_filter_definition": np.asarray(
                [
                    "inner_train only; absolute_pristine=(tool_condition=unworn and passed_visual_inspection=yes); "
                    "absolute_worn=(tool_condition=worn and passed_visual_inspection=no)"
                ]
            ),
        }
        payload.update(per_window_extras(data, len(y), pure_mask))
        np.savez_compressed(args.umich_pure_exemplar_out, **payload)

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / f"{args.dataset}_inner_split_units.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["unit", "class", "n_windows", "inner_split"])
        writer.writeheader()
        writer.writerows(sorted(unit_rows, key=lambda r: (r["inner_split"], r["class"], r["unit"])))

    lines = [f"# {args.dataset} Inner Validation Split", ""]
    lines.append(f"- Source train NPZ: `{args.train_npz}`")
    lines.append(f"- Split unit: case/run source unit, never random windows.")
    lines.append(f"- Seed: `{args.seed}`")
    lines.append(f"- Validation fraction by class: `{args.val_frac}`")
    lines.append(f"- Balance target: `{args.balance_by}`")
    for split, mask in [("inner_train", train_mask), ("inner_val", val_mask)]:
        counts = Counter(class_names[int(v)] for v in y[mask])
        units_counts = Counter(class_names[int(y[np.where((units == u))[0][0]])] for u in sorted(set(units[mask])))
        lines.append(f"- {split} window counts: {dict(counts)}")
        lines.append(f"- {split} unit counts: {dict(units_counts)}")
    if pure_mask is not None:
        counts = Counter(class_names[int(v)] for v in y[pure_mask])
        pure_units = sorted(str(u) for u in set(units[pure_mask]))
        lines.append(f"- UMich pure exemplar NPZ: `{args.umich_pure_exemplar_out}`")
        lines.append(f"- UMich pure exemplar definition: inner_train only; unworn + passed_visual_inspection=yes; worn + passed_visual_inspection=no")
        lines.append(f"- UMich pure exemplar window counts: {dict(counts)}")
        lines.append(f"- UMich pure exemplar units: {pure_units}")
    (report_dir / f"{args.dataset}_inner_split_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
