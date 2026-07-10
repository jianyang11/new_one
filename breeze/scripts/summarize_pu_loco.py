"""Summarize PU leave-one-condition-out downstream evaluations."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import wilcoxon


CONDITIONS = ["N09_M07_F10", "N15_M01_F10", "N15_M07_F04", "N15_M07_F10"]
SPLITS = [f"loco_{cond}" for cond in CONDITIONS]
METHODS = ["llm", "rule", "random_open_loop", "noise_aug", "real_only"]
SHOTS = [5, 10, 25]
SEEDS = list(range(40))
METRICS = ["acc", "macro_f1"]
COMPARATORS = ["rule", "random_open_loop", "noise_aug", "real_only"]
EXPECTED_TOTAL_ROWS = len(SPLITS) * len(METHODS) * len(SHOTS) * len(SEEDS)


def fmt(x: Any) -> str:
    if isinstance(x, float):
        if math.isnan(x):
            return "nan"
        if abs(x) < 1e-4 and x != 0:
            return f"{x:.2e}"
        return f"{x:.4f}"
    return str(x)


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col, "")) for col in cols) + " |")
    return lines


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    out = [1.0] * m
    prev = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * pvals[idx]
        prev = max(prev, val)
        out[idx] = min(prev, 1.0)
    return out


def bh(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i], reverse=True)
    out = [1.0] * m
    prev = 1.0
    for rank_from_end, idx in enumerate(order):
        rank = m - rank_from_end
        val = pvals[idx] * m / rank
        prev = min(prev, val)
        out[idx] = min(prev, 1.0)
    return out


def safe_wilcoxon(diff: np.ndarray) -> tuple[float, float]:
    if np.allclose(diff, 0.0):
        return 0.0, 1.0
    try:
        stat, pval = wilcoxon(diff, alternative="greater", zero_method="wilcox")
    except ValueError:
        return math.nan, 1.0
    return float(stat), float(pval)


def parse_method(path: Path) -> tuple[str, str]:
    stem = path.stem
    for method in METHODS:
        suffix = f"_{method}_nsyn20"
        if stem.endswith(suffix):
            return stem[: -len(suffix)], method
    raise ValueError(f"cannot infer split/method from filename: {path.name}")


def read_rows(downstream: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        for method in METHODS:
            path = downstream / f"{split}_{method}_nsyn20.csv"
            if not path.exists():
                raise FileNotFoundError(f"missing downstream CSV: {path}")
            parsed_split, parsed_method = parse_method(path)
            if parsed_split != split or parsed_method != method:
                raise RuntimeError(f"filename parse mismatch: {path.name}")
            with path.open(newline="") as f:
                reader = csv.DictReader(f)
                for raw in reader:
                    row = dict(raw)
                    row["method"] = method
                    row["source_file"] = path.name
                    row["n_real"] = int(row["n_real"])
                    row["seed"] = int(row["seed"])
                    row["n_syn"] = int(row["n_syn"])
                    row["acc"] = float(row["acc"])
                    row["macro_f1"] = float(row["macro_f1"])
                    rows.append(row)
    return rows


def validate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, int, int]] = set()
    for row in rows:
        key = (row["split"], row["method"], row["n_real"], row["seed"])
        if key in seen:
            raise RuntimeError(f"duplicate row: {key}")
        seen.add(key)
        if row["split"] not in SPLITS:
            raise RuntimeError(f"unexpected split: {row['split']}")
        expected_n_syn = 0 if row["method"] == "real_only" else 60
        if row["n_syn"] != expected_n_syn:
            raise RuntimeError(
                f"unexpected n_syn for {key}: got {row['n_syn']}, expected {expected_n_syn}"
            )
    completeness: list[dict[str, Any]] = []
    for split in SPLITS:
        for method in METHODS:
            for n_real in SHOTS:
                missing = [
                    seed
                    for seed in SEEDS
                    if (split, method, n_real, seed) not in seen
                ]
                n_rows = len(SEEDS) - len(missing)
                completeness.append(
                    {
                        "split": split,
                        "method": method,
                        "n_real": n_real,
                        "rows": n_rows,
                        "expected_rows": len(SEEDS),
                        "complete": not missing,
                        "missing_seeds": json.dumps(missing, separators=(",", ":")),
                    }
                )
                if missing:
                    raise RuntimeError(f"missing rows for {split}/{method}/n={n_real}: {missing}")
    if len(rows) != EXPECTED_TOTAL_ROWS:
        raise RuntimeError(f"expected {EXPECTED_TOTAL_ROWS} rows, found {len(rows)}")
    return completeness


def grouped(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], list[dict[str, Any]]]:
    out: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[(row["split"], row["method"], row["n_real"])].append(row)
    for vals in out.values():
        vals.sort(key=lambda r: r["seed"])
    return out


def values(g: dict[tuple[str, str, int], list[dict[str, Any]]], split: str, method: str, n_real: int, metric: str) -> np.ndarray:
    rows = g[(split, method, n_real)]
    seeds = [row["seed"] for row in rows]
    if seeds != SEEDS:
        raise RuntimeError(f"seed order mismatch for {split}/{method}/n={n_real}: {seeds}")
    return np.asarray([float(row[metric]) for row in rows], dtype=float)


def method_summary(g: dict[tuple[str, str, int], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        for method in METHODS:
            for n_real in SHOTS:
                for metric in METRICS:
                    arr = values(g, split, method, n_real, metric)
                    rows.append(
                        {
                            "split": split,
                            "method": method,
                            "n_real": n_real,
                            "metric": metric,
                            "n_seeds": len(arr),
                            "mean": float(np.mean(arr)),
                            "std": float(np.std(arr, ddof=1)),
                            "median": float(np.median(arr)),
                            "min": float(np.min(arr)),
                            "max": float(np.max(arr)),
                        }
                    )
    return rows


def condition_fold_summary(summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method in METHODS:
        for n_real in SHOTS:
            for metric in METRICS:
                fold_vals = [
                    float(row["mean"])
                    for row in summary
                    if row["method"] == method and row["n_real"] == n_real and row["metric"] == metric
                ]
                if len(fold_vals) != len(SPLITS):
                    raise RuntimeError(f"missing fold means for {method}/n={n_real}/{metric}")
                arr = np.asarray(fold_vals)
                rows.append(
                    {
                        "split_group": "pu_loco_all4",
                        "method": method,
                        "n_real": n_real,
                        "metric": metric,
                        "folds": len(arr),
                        "fold_mean": float(np.mean(arr)),
                        "fold_std": float(np.std(arr, ddof=1)),
                        "fold_min": float(np.min(arr)),
                        "fold_max": float(np.max(arr)),
                    }
                )
    return rows


def tests(g: dict[tuple[str, str, int], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        for n_real in SHOTS:
            for metric in METRICS:
                family_id = f"{split}_n{n_real}_{metric}_superiority"
                llm = values(g, split, "llm", n_real, metric)
                for comp in COMPARATORS:
                    other = values(g, split, comp, n_real, metric)
                    diff = llm - other
                    stat, pval = safe_wilcoxon(diff)
                    rows.append(
                        {
                            "split": split,
                            "family_id": family_id,
                            "metric": metric,
                            "n_real": n_real,
                            "comparison": f"llm>{comp}",
                            "other_method": comp,
                            "alternative": "greater",
                            "n_pairs": len(diff),
                            "mean_llm": float(np.mean(llm)),
                            "mean_other": float(np.mean(other)),
                            "mean_delta": float(np.mean(diff)),
                            "median_delta": float(np.median(diff)),
                            "wins": int(np.sum(diff > 0)),
                            "ties": int(np.sum(diff == 0)),
                            "losses": int(np.sum(diff < 0)),
                            "wilcoxon_stat": stat,
                            "p_value": pval,
                            "holm_q_in_family": "",
                            "bh_q_global": "",
                            "passed_holm": "",
                        }
                    )
    fam: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        fam[str(row["family_id"])].append(idx)
    for idxs in fam.values():
        qvals = holm([float(rows[idx]["p_value"]) for idx in idxs])
        for idx, qval in zip(idxs, qvals):
            rows[idx]["holm_q_in_family"] = qval
            rows[idx]["passed_holm"] = bool(float(rows[idx]["mean_delta"]) > 0 and qval < 0.05)
    qvals = bh([float(row["p_value"]) for row in rows])
    for row, qval in zip(rows, qvals):
        row["bh_q_global"] = qval
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def report(
    rows: list[dict[str, Any]],
    summary: list[dict[str, Any]],
    fold_summary: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    root: Path,
) -> list[str]:
    lines: list[str] = []
    lines.append("# PU LOCO Gate Report")
    lines.append("")
    lines.append("## Protocol")
    lines.append("- Scope: leave-one-condition-out across N09_M07_F10, N15_M01_F10, N15_M07_F04, and N15_M07_F10.")
    lines.append("- Split unit: operating condition; no window-level train/test random split.")
    lines.append("- Seeds: 40 fixed seeds (0-39) for every fold, method, and shot.")
    lines.append("- Shots: n_real = 5, 10, 25 per class.")
    lines.append("- Synthetic budget: uniform n_syn = 20 per class (60 total windows) for LLM/rule/random_open_loop/noise_aug; real_only uses 0 synthetic windows.")
    lines.append("- Statistical family: each (held-out condition, n_real, metric) is one family with Holm correction across llm>rule, llm>random_open_loop, llm>noise_aug, and llm>real_only; global BH is reported as reference.")
    if "v2" in root.name:
        lines.append("- LLM source: v2 condition-aware rerendered pools using held-out condition metadata only; no held-out signals or labels were used during pool construction.")
        lines.append("- API usage for this v2 rerender block: 0 new LLM calls. The reused morphology recipes came from the previously logged v1 PU LOCO LLM pools.")
        lines.append("- Baseline provenance: rule/random_open_loop/noise_aug/real_only CSVs are copied unchanged from the v1 directory because their pools, splits, seeds, and training protocol are identical; v1 LLM CSVs are not reused.")
    else:
        lines.append("- API usage for PU LOCO pool construction: 133 LLM calls; fold-specific LLM pools were generated from training conditions only, and rule/random_open_loop pools used no LLM calls.")
    lines.append("")
    lines.append("## Completeness")
    lines.append(f"- Expected rows: {EXPECTED_TOTAL_ROWS}; observed rows: {len(rows)}.")
    lines.append("- Every fold/method/shot cell contains 40 seeds.")
    lines.append("")
    lines.append("## Four-Fold Mean")
    lines.extend(md_table(fold_summary, ["method", "n_real", "metric", "fold_mean", "fold_std", "fold_min", "fold_max"]))
    lines.append("")
    lines.append("## Per-Fold LLM Comparisons")
    focused = [
        row
        for row in test_rows
        if row["comparison"] in {"llm>rule", "llm>random_open_loop", "llm>noise_aug"}
    ]
    lines.extend(
        md_table(
            focused,
            [
                "split",
                "n_real",
                "metric",
                "comparison",
                "mean_delta",
                "p_value",
                "holm_q_in_family",
                "passed_holm",
            ],
        )
    )
    failed = [row for row in test_rows if not row["passed_holm"]]
    lines.append("")
    lines.append("## Gate Decision")
    if failed:
        lines.append(f"- PU LOCO is not uniformly significant: {len(failed)} of {len(test_rows)} registered comparisons fail Holm q<0.05 with positive delta.")
        lines.append("- Failed rows are retained in `pu_loco_wilcoxon.csv`; do not claim uniform PU LOCO superiority without qualifying these folds/settings.")
    else:
        lines.append("- All registered PU LOCO comparisons pass Holm q<0.05 with positive mean delta.")
    return lines


def freeze_outputs(root: Path, freeze_dir: Path) -> None:
    if freeze_dir.exists():
        raise FileExistsError(f"freeze directory already exists: {freeze_dir}")
    freeze_dir.mkdir(parents=True)
    for path in [
        root / "pu_loco_completeness.csv",
        root / "pu_loco_summary.csv",
        root / "pu_loco_wilcoxon.csv",
        root / "pu_loco_fold_summary.csv",
        root / "pu_loco_report.md",
    ]:
        shutil.copy2(path, freeze_dir / path.name)
    shutil.copytree(root / "downstream", freeze_dir / "downstream")
    files = subprocess.run(
        ["find", str(freeze_dir), "-type", "f"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    digests: list[str] = []
    for filename in sorted(files):
        if filename.endswith("manifest_sha256.txt"):
            continue
        digests.append(
            subprocess.run(
                ["openssl", "dgst", "-sha256", filename],
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
        )
    (freeze_dir / "manifest_sha256.txt").write_text("\n".join(digests) + "\n")
    subprocess.run(["chmod", "-R", "a-w", str(freeze_dir)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="breeze/results/pu_loco_2026-07-07")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--freeze-dir", default="breeze/results/pu_loco_2026-07-07_frozen")
    args = parser.parse_args()
    root = Path(args.root)
    rows = read_rows(root / "downstream")
    completeness = validate_rows(rows)
    g = grouped(rows)
    summary = method_summary(g)
    fold_summary = condition_fold_summary(summary)
    test_rows = tests(g)
    write_csv(root / "pu_loco_completeness.csv", completeness)
    write_csv(root / "pu_loco_summary.csv", summary)
    write_csv(root / "pu_loco_fold_summary.csv", fold_summary)
    write_csv(root / "pu_loco_wilcoxon.csv", test_rows)
    (root / "pu_loco_report.md").write_text("\n".join(report(rows, summary, fold_summary, test_rows, root)) + "\n")
    if args.freeze:
        freeze_outputs(root, Path(args.freeze_dir))


if __name__ == "__main__":
    main()
