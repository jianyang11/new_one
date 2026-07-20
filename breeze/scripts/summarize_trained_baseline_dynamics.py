"""Create a threshold-free audit table from trained-generator loss histories."""

from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable


KEYS = ("method", "train_mode", "n_real", "seed", "class_id", "stage")
METRICS = (
    "reconstruction_loss",
    "supervisor_loss",
    "discriminator_loss",
    "generator_loss",
    "noise_prediction_mse",
)


def summarize(rows: Iterable[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = tuple(row[name] for name in KEYS)
        groups[key].append(row)
    output: list[dict[str, object]] = []
    for key in sorted(groups):
        history = sorted(groups[key], key=lambda row: int(row["epoch"]))
        epochs = [int(row["epoch"]) for row in history]
        if len(epochs) != len(set(epochs)):
            raise ValueError(f"duplicate epoch in dynamics group {key}")
        for metric in METRICS:
            raw = [row.get(metric, "") for row in history]
            values = [float(value) for value in raw if value not in ("", None)]
            if not values:
                continue
            finite = [value for value in values if math.isfinite(value)]
            base = dict(zip(KEYS, key))
            output.append(
                {
                    **base,
                    "metric": metric,
                    "n_epochs": len(values),
                    "first": values[0],
                    "last": values[-1],
                    "minimum": min(finite) if finite else float("nan"),
                    "maximum": max(finite) if finite else float("nan"),
                    "median": statistics.median(finite) if finite else float("nan"),
                    "all_finite": len(finite) == len(values),
                }
            )
    return output


def write_atomic(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [*KEYS, "metric", "n_epochs", "first", "last", "minimum", "maximum", "median", "all_finite"]
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.input.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"no dynamics rows in {args.input}")
    summary = summarize(rows)
    write_atomic(args.output, summary)
    print(f"wrote {len(summary)} rows to {args.output}")


if __name__ == "__main__":
    main()
