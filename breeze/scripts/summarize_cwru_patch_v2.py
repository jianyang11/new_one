"""Summarize the frozen CWRU patch-v2 downstream protocol.

Statistical family registered for this repair:
for each (split, n_real, metric), Holm correction is applied across
LLM > rule, LLM > noise_aug, and LLM > real_only. A global BH value is
also reported across all registered CWRU patch-v2 superiority tests.
"""

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


SPLITS = ["within_load0", "lolo_load0", "lolo_load1", "lolo_load2", "lolo_load3"]
LOLO_SPLITS = ["lolo_load0", "lolo_load1", "lolo_load2", "lolo_load3"]
METHODS = ["llm", "rule", "noise_aug", "real_only"]
SHOTS = [5, 10, 25]
SEEDS = list(range(40))
METRICS = ["acc", "macro_f1"]
COMPARATORS = ["rule", "noise_aug", "real_only"]
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


def safe_wilcoxon(diff: np.ndarray, alternative: str) -> tuple[float, float]:
    if np.allclose(diff, 0.0):
        return 0.0, 1.0
    try:
        stat, pval = wilcoxon(diff, alternative=alternative, zero_method="wilcox")
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
        if row["method"] not in METHODS:
            raise RuntimeError(f"unexpected method: {row['method']}")
        expected_n_syn = 0 if row["method"] == "real_only" else 80
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


def by_key(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["split"], row["method"], row["n_real"])].append(row)
    for vals in grouped.values():
        vals.sort(key=lambda r: r["seed"])
    return grouped


def values(
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]],
    split: str,
    method: str,
    n_real: int,
    metric: str,
) -> np.ndarray:
    rows = grouped[(split, method, n_real)]
    seeds = [row["seed"] for row in rows]
    if seeds != SEEDS:
        raise RuntimeError(f"seed order mismatch for {split}/{method}/n={n_real}: {seeds}")
    return np.asarray([float(row[metric]) for row in rows], dtype=float)


def summarize_methods(grouped: dict[tuple[str, str, int], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for split in SPLITS:
        for method in METHODS:
            for n_real in SHOTS:
                for metric in METRICS:
                    arr = values(grouped, split, method, n_real, metric)
                    out.append(
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
    return out


def wilcoxon_tests(grouped: dict[tuple[str, str, int], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        for n_real in SHOTS:
            for metric in METRICS:
                family_id = f"{split}_n{n_real}_{metric}_superiority"
                llm = values(grouped, split, "llm", n_real, metric)
                for other_method in COMPARATORS:
                    other = values(grouped, split, other_method, n_real, metric)
                    diff = llm - other
                    stat, pval = safe_wilcoxon(diff, alternative="greater")
                    rows.append(
                        {
                            "split": split,
                            "family_id": family_id,
                            "metric": metric,
                            "n_real": n_real,
                            "comparison": f"llm>{other_method}",
                            "other_method": other_method,
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

    family_to_indices: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        family_to_indices[str(row["family_id"])].append(idx)
    for idxs in family_to_indices.values():
        qvals = holm([float(rows[idx]["p_value"]) for idx in idxs])
        for idx, qval in zip(idxs, qvals):
            rows[idx]["holm_q_in_family"] = qval
            rows[idx]["passed_holm"] = bool(float(rows[idx]["mean_delta"]) > 0 and qval < 0.05)
    qvals_global = bh([float(row["p_value"]) for row in rows])
    for row, qval in zip(rows, qvals_global):
        row["bh_q_global"] = qval
    return rows


def lolo_fold_summary(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method in METHODS:
        for n_real in SHOTS:
            for metric in METRICS:
                fold_vals = [
                    float(row["mean"])
                    for row in summary_rows
                    if row["split"] in LOLO_SPLITS
                    and row["method"] == method
                    and row["n_real"] == n_real
                    and row["metric"] == metric
                ]
                if len(fold_vals) != len(LOLO_SPLITS):
                    raise RuntimeError(f"missing LOLO fold means for {method}/n={n_real}/{metric}")
                arr = np.asarray(fold_vals, dtype=float)
                rows.append(
                    {
                        "split_group": "lolo_all4",
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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def report_lines(
    rows: list[dict[str, Any]],
    completeness: list[dict[str, Any]],
    summary: list[dict[str, Any]],
    tests: list[dict[str, Any]],
    lolo_summary: list[dict[str, Any]],
) -> list[str]:
    lines: list[str] = []
    lines.append("# CWRU Patch-v2 Gate Report")
    lines.append("")
    lines.append("## Protocol")
    lines.append("- Scope: CWRU within-load0 plus full leave-one-load-out folds load0/load1/load2/load3.")
    lines.append("- Seeds: 40 fixed seeds (0-39) for every split, method, and shot.")
    lines.append("- Shots: n_real = 5, 10, 25 per class.")
    lines.append("- Synthetic budget: uniform n_syn = 20 per class (80 total windows) for LLM/rule/noise_aug; real_only uses 0 synthetic windows.")
    lines.append("- Budget rationale: fixed a priori for this repair to avoid test-set-tuned per-shot budgets.")
    lines.append("- Statistical family: each (split, n_real, metric) is one family with Holm correction across llm>rule, llm>noise_aug, and llm>real_only; global BH is reported as reference.")
    lines.append("- API usage in this CWRU repair: 0 LLM calls; existing frozen CWRU pools were reused.")
    lines.append("")
    lines.append("## Completeness")
    lines.append(f"- Expected rows: {EXPECTED_TOTAL_ROWS}; observed rows: {len(rows)}.")
    lines.append("- Every split/method/shot cell contains 40 seeds.")
    lines.append("")
    lines.append("## LOLO Four-Fold Mean")
    lolo_view = [
        row
        for row in lolo_summary
        if row["metric"] in METRICS and row["n_real"] in SHOTS
    ]
    lines.extend(md_table(lolo_view, ["method", "n_real", "metric", "fold_mean", "fold_std", "fold_min", "fold_max"]))
    lines.append("")
    lines.append("## Within-Load0 Means")
    within = [
        row
        for row in summary
        if row["split"] == "within_load0" and row["metric"] in METRICS
    ]
    lines.extend(md_table(within, ["method", "n_real", "metric", "mean", "std", "median"]))
    lines.append("")
    lines.append("## Wilcoxon/Holm Results")
    focused = [
        row
        for row in tests
        if row["comparison"] in {"llm>rule", "llm>noise_aug"}
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
    failed = [row for row in tests if not row["passed_holm"]]
    lines.append("")
    lines.append("## Gate Decision")
    if failed:
        lines.append(f"- CWRU patch-v2 is not uniformly significant: {len(failed)} of {len(tests)} registered comparisons fail Holm q<0.05 with positive delta.")
        lines.append("- Failed rows are retained in `cwru_patch_v2_wilcoxon.csv`; do not claim uniform CWRU LOLO superiority without qualifying these folds/settings.")
    else:
        lines.append("- All registered CWRU patch-v2 comparisons pass Holm q<0.05 with positive mean delta.")
    return lines


def freeze_outputs(root: Path, freeze_dir: Path) -> None:
    if freeze_dir.exists():
        raise FileExistsError(f"freeze directory already exists: {freeze_dir}")
    freeze_dir.mkdir(parents=True)
    for path in [
        root / "cwru_patch_v2_completeness.csv",
        root / "cwru_patch_v2_summary.csv",
        root / "cwru_patch_v2_wilcoxon.csv",
        root / "cwru_patch_v2_lolo_fold_summary.csv",
        root / "cwru_patch_v2_report.md",
    ]:
        shutil.copy2(path, freeze_dir / path.name)
    downstream_dst = freeze_dir / "downstream"
    shutil.copytree(root / "downstream", downstream_dst)
    manifest = subprocess.run(
        ["find", str(freeze_dir), "-type", "f"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    digest_rows: list[str] = []
    for filename in sorted(manifest):
        if filename.endswith("manifest_sha256.txt"):
            continue
        result = subprocess.run(
            ["openssl", "dgst", "-sha256", filename],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        digest_rows.append(result)
    (freeze_dir / "manifest_sha256.txt").write_text("\n".join(digest_rows) + "\n")
    subprocess.run(["chmod", "-R", "a-w", str(freeze_dir)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="breeze/results/cwru_patch_v2_2026-07-07")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument(
        "--freeze-dir",
        default="breeze/results/cwru_patch_v2_2026-07-07_frozen",
    )
    args = parser.parse_args()

    root = Path(args.root)
    downstream = root / "downstream"
    rows = read_rows(downstream)
    completeness = validate_rows(rows)
    grouped = by_key(rows)
    summary = summarize_methods(grouped)
    tests = wilcoxon_tests(grouped)
    lolo_summary = lolo_fold_summary(summary)

    write_csv(root / "cwru_patch_v2_completeness.csv", completeness)
    write_csv(root / "cwru_patch_v2_summary.csv", summary)
    write_csv(root / "cwru_patch_v2_wilcoxon.csv", tests)
    write_csv(root / "cwru_patch_v2_lolo_fold_summary.csv", lolo_summary)
    report = report_lines(rows, completeness, summary, tests, lolo_summary)
    (root / "cwru_patch_v2_report.md").write_text("\n".join(report) + "\n")

    if args.freeze:
        freeze_outputs(root, Path(args.freeze_dir))


if __name__ == "__main__":
    main()
