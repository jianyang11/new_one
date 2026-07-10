"""Cross-condition real-data verifier audit for the BREEZE revision.

This is not a synthetic-data generation experiment. It calibrates the v2
verifier independently on each PU operating condition using train windows only,
then reports real train/test pass rates and failure distributions. Outputs are
checkpointed per condition for resume-safe execution.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from config import CLASSES, CONDITIONS, RESULTS_DIR, RUNS_DIR
from data import load_file_split
from verifier.v2 import BreezeVerifierV2


def failed_gates(report: dict) -> list[str]:
    return [k for k, v in report.get("gates", {}).items() if v.get("passed") is False]


def verify_one(args):
    verifier, window, cls = args
    report = verifier.verify(window, cls)
    gates = failed_gates(report)
    return bool(report["feasible"]), gates


def condition_paths(out_dir: Path, cond: str) -> dict[str, Path]:
    return {
        "calib": out_dir / f"verifier_v2_{cond}.json",
        "details": out_dir / f"details_{cond}.csv",
        "summary": out_dir / f"summary_{cond}.json",
    }


def sample_split(X: np.ndarray, y: np.ndarray, max_per_class: int | None, seed: int) -> tuple[np.ndarray, np.ndarray]:
    if max_per_class is None:
        return X, y
    rng = np.random.default_rng(seed)
    idx = []
    for ci in range(len(CLASSES)):
        pool = np.where(y == ci)[0]
        keep = min(max_per_class, len(pool))
        idx.extend(rng.choice(pool, keep, replace=False).tolist())
    idx = np.array(sorted(idx), dtype=int)
    return X[idx], y[idx]


def run_condition(cond: str, out_dir: Path, max_per_class: int | None, workers: int, force: bool) -> list[dict]:
    paths = condition_paths(out_dir, cond)
    if paths["summary"].exists() and paths["details"].exists() and not force:
        return json.loads(paths["summary"].read_text())["rows"]

    Xtr, ytr, btr = load_file_split("train", cond)
    verifier = BreezeVerifierV2(coverage=0.90, profile="soft_w1")
    if paths["calib"].exists() and not force:
        verifier = BreezeVerifierV2.load(paths["calib"])
    else:
        verifier.calibrate(Xtr.astype(np.float32), ytr, cond, bearings=btr)
        paths["calib"].parent.mkdir(parents=True, exist_ok=True)
        verifier.save(paths["calib"])

    rows = []
    detail_rows = []
    for split in ("train", "test"):
        X, y, _ = load_file_split(split, cond)
        X, y = sample_split(X, y, max_per_class, seed=1000 + len(cond) + (0 if split == "train" else 1))
        for ci, cls in enumerate(CLASSES):
            W = X[y == ci].astype(np.float32)
            if len(W) == 0:
                continue
            tasks = [(verifier, W[i], cls) for i in range(len(W))]
            if workers > 1:
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    outs = list(ex.map(verify_one, tasks))
            else:
                outs = [verify_one(t) for t in tasks]
            ok = sum(1 for feasible, _ in outs if feasible)
            fail_counts = Counter(g for feasible, gates in outs if not feasible for g in gates)
            rows.append(
                {
                    "cond": cond,
                    "split": split,
                    "class": cls,
                    "n": len(W),
                    "pass_rate": ok / len(W),
                    "fail_sanity": fail_counts.get("sanity", 0),
                    "fail_stats_union": fail_counts.get("stats_union", 0),
                    "fail_soft_spectrum": fail_counts.get("soft_spectrum", 0),
                    "fail_psd_w1": fail_counts.get("psd_w1", 0),
                    "fail_envelope_multi": fail_counts.get("envelope_multi", 0),
                    "fail_vector_mcsa": fail_counts.get("vector_mcsa", 0),
                }
            )
            for idx, (feasible, gates) in enumerate(outs):
                detail_rows.append(
                    {
                        "cond": cond,
                        "split": split,
                        "class": cls,
                        "index": idx,
                        "feasible": feasible,
                        "failed_gates": ";".join(gates),
                    }
                )

    pd.DataFrame(detail_rows).to_csv(paths["details"], index=False)
    paths["summary"].write_text(json.dumps({"rows": rows}, indent=2))
    return rows


def write_report(rows: list[dict], out_dir: Path, smoke: bool) -> None:
    df = pd.DataFrame(rows)
    suffix = "smoke" if smoke else "full"
    result_path = RESULTS_DIR / f"cross_condition_verifier_{suffix}.csv"
    df.to_csv(result_path, index=False)

    lines = [
        "# PU Cross-Condition Verifier Audit",
        "",
        "Date: 2026-07-04",
        "",
        "This audit calibrates BREEZE-v2 independently on each PU operating condition",
        "using train windows only and evaluates real train/test pass rates. It is a",
        "verifier coverage check, not a cross-condition synthetic generation result.",
        "",
        f"Run directory: `{out_dir}`",
        f"Result CSV: `{result_path}`",
        "",
        "## Pass Rates",
        "",
        "| cond | split | class | n | pass_rate | fail_stats | fail_soft_spec | fail_psd_w1 | fail_env |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {cond} | {split} | {class} | {n} | {pass_rate:.4f} | {fail_stats_union} | {fail_soft_spectrum} | {fail_psd_w1} | {fail_envelope_multi} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("Interpretation boundary: these numbers show that the train-calibrated")
    lines.append("verifier can be instantiated under multiple PU operating conditions, but")
    lines.append("they do not demonstrate cross-condition LLM generation or downstream")
    lines.append("augmentation benefits.")
    report = out_dir / f"cross_condition_verifier_{suffix}_report.md"
    report.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conditions", nargs="*", default=list(CONDITIONS.keys()))
    parser.add_argument("--max-per-class-split", type=int, default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    smoke = args.max_per_class_split is not None
    out_dir = args.out or (RUNS_DIR / ("cross_condition_verifier_smoke" if smoke else "cross_condition_verifier"))
    out_dir.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    all_rows = []
    for cond in args.conditions:
        if cond not in CONDITIONS:
            raise ValueError(f"Unknown condition: {cond}")
        all_rows.extend(run_condition(cond, out_dir, args.max_per_class_split, args.workers, args.force))
    write_report(all_rows, out_dir, smoke)


if __name__ == "__main__":
    main()
