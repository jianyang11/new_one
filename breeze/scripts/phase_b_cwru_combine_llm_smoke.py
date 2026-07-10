"""Combine CWRU LLM smoke pools without modifying source runs."""

from __future__ import annotations

import csv
import json
import argparse
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RUNS = BREEZE / "runs"
CWRU_CLASSES = ("healthy", "IR", "B", "OR")


def read_manifest(path: Path, allowed_classes: set[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row["class"] in allowed_classes:
                rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--healthy-run", nargs="+", default=["breeze/runs/phaseB_cwru_within_load0_llm_smoke_api_v3_healthy_compact"])
    parser.add_argument("--fault-run", nargs="+", default=["breeze/runs/phaseB_cwru_within_load0_llm_smoke_api_v1"])
    parser.add_argument("--out-dir", default="breeze/runs/phaseB_cwru_within_load0_llm_smoke_combined_v3")
    args = parser.parse_args()

    healthy_runs = [ROOT / item for item in args.healthy_run]
    fault_runs = [ROOT / item for item in args.fault_run]
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    source_rows = []
    for healthy_run in healthy_runs:
        source_rows.extend(read_manifest(healthy_run / "manifest.csv", {"healthy"}))
    for fault_run in fault_runs:
        source_rows.extend(read_manifest(fault_run / "manifest.csv", {"IR", "B", "OR"}))
    if not source_rows:
        raise RuntimeError("no source rows found for combined LLM smoke pool")

    xs, ys = [], []
    manifest_rows = []
    for i, row in enumerate(source_rows):
        cls = row["class"]
        path = row["path"]
        arr = np.load(ROOT / path).astype(np.float32)
        xs.append(arr)
        ys.append(CWRU_CLASSES.index(cls))
        manifest_rows.append(
            {
                "combined_index": i,
                "source": row.get("source", "llm"),
                "class": cls,
                "slot": row["slot"],
                "path": path,
            }
        )

    np.savez_compressed(
        out_dir / "pool.npz",
        X=np.stack(xs),
        y=np.asarray(ys, dtype=np.int64),
        class_names=np.asarray(CWRU_CLASSES),
    )
    write_csv(out_dir / "manifest.csv", manifest_rows)
    counts = Counter(row["class"] for row in manifest_rows)
    summary = {
        "dataset": "CWRU",
        "split": "within_load0",
        "source": "llm_combined_smoke",
        "healthy_source": [str(healthy_run.relative_to(ROOT)) for healthy_run in healthy_runs],
        "fault_source": [str(fault_run.relative_to(ROOT)) for fault_run in fault_runs],
        "pool": str((out_dir / "pool.npz").relative_to(ROOT)),
        "n_items": len(manifest_rows),
        "by_class": {cls: int(counts.get(cls, 0)) for cls in CWRU_CLASSES},
        "note": "Combines healthy accepted items from the requested healthy run with IR/B/OR accepted items from the requested fault run; source runs are not modified.",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
