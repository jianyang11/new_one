"""Summarize the Phase-A LLM contribution gate.

Inputs are the checkpointed downstream CSV and existing pool summary JSON files.
The script writes reproducible CSV/Markdown artifacts and does not change any
data, model, or test split.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RESULTS = BREEZE / "results"
REPORTS = ROOT / "reports"

DOWNSTREAM = RESULTS / "phaseA_downstream_cnn.csv"
SUMMARY_CSV = RESULTS / "phaseA_downstream_summary.csv"
TEST_CSV = RESULTS / "phaseA_wilcoxon_holm_bh.csv"
POOL_CSV = RESULTS / "phaseA_pool_summary.csv"
REPORT = REPORTS / "phaseA_gate_report_2026-07-05.md"


BASELINES = ("real_only", "phaseA_random_v2", "phaseA_rule_v2", "phaseA_llm_k3_v2")
SHOTS = (10, 25, 50)
METRICS = ("acc", "macro_f1")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


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


def load_pool_summaries() -> list[dict[str, object]]:
    specs = [
        ("phaseA_random_v2", BREEZE / "runs" / "recipe_ablation_random_v2_full" / "summary.json"),
        ("phaseA_rule_v2", BREEZE / "runs" / "recipe_ablation_rule_v2_full" / "summary.json"),
        ("phaseA_llm_k3_v2", BREEZE / "runs" / "rescreen_v2_full" / "summary.json"),
    ]
    rows: list[dict[str, object]] = []
    for baseline, path in specs:
        data = json.loads(path.read_text())
        if baseline == "phaseA_llm_k3_v2":
            slots = int(data["slots"])
            accepted = int(data["accepted_slots_before_diversity"])
            items = int(data["accepted_items_before_diversity"])
            kept = int(data["kept_after_diversity"])
            counts = data["kept_by_class"]
        else:
            slots = int(data["slots"])
            accepted = int(data["accepted_slots"])
            items = int(data["accepted_items_before_diversity"])
            kept = int(data["kept_after_diversity"])
            counts = data["kept_counts"]
        rows.append(
            {
                "baseline": baseline,
                "recipe_slots": slots,
                "accepted_slots": accepted,
                "slot_acceptance": accepted / slots if slots else 0.0,
                "accepted_items_before_diversity": items,
                "kept_after_diversity": kept,
                "kept_healthy": int(counts.get("healthy", 0)),
                "kept_OR": int(counts.get("OR", 0)),
                "kept_IR": int(counts.get("IR", 0)),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def md_table(rows: list[dict[str, object]], cols: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for row in rows:
        vals = []
        for col in cols:
            val = row.get(col, "")
            if isinstance(val, float):
                vals.append(f"{val:.6g}")
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def main() -> None:
    rows = read_rows(DOWNSTREAM)
    by: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by[(row["baseline"], int(row["n_real"]))].append(row)

    summary_rows: list[dict[str, object]] = []
    for baseline in BASELINES:
        for n_real in SHOTS:
            group = sorted(by[(baseline, n_real)], key=lambda r: int(r["seed"]))
            for metric in METRICS:
                vals = np.asarray([float(r[metric]) for r in group], dtype=float)
                summary_rows.append(
                    {
                        "baseline": baseline,
                        "n_real": n_real,
                        "metric": metric,
                        "n": len(vals),
                        "mean": float(np.mean(vals)),
                        "std": float(np.std(vals, ddof=1)),
                        "median": float(np.median(vals)),
                        "n_syn_values": ";".join(str(v) for v in sorted({int(r["n_syn"]) for r in group})),
                    }
                )

    test_rows: list[dict[str, object]] = []
    for metric in METRICS:
        for n_real in SHOTS:
            llm = np.asarray(
                [float(r[metric]) for r in sorted(by[("phaseA_llm_k3_v2", n_real)], key=lambda r: int(r["seed"]))],
                dtype=float,
            )
            for comp in ("phaseA_random_v2", "phaseA_rule_v2"):
                other = np.asarray(
                    [float(r[metric]) for r in sorted(by[(comp, n_real)], key=lambda r: int(r["seed"]))],
                    dtype=float,
                )
                diff = llm - other
                try:
                    stat, pval = wilcoxon(diff, alternative="greater", zero_method="wilcox")
                except ValueError:
                    stat, pval = math.nan, math.nan
                test_rows.append(
                    {
                        "metric": metric,
                        "n_real": n_real,
                        "comparison": f"phaseA_llm_k3_v2>{comp}",
                        "mean_delta": float(np.mean(diff)),
                        "median_delta": float(np.median(diff)),
                        "wins": int(np.sum(diff > 0)),
                        "ties": int(np.sum(diff == 0)),
                        "losses": int(np.sum(diff < 0)),
                        "wilcoxon_p_one_sided": float(pval),
                    }
                )
    hvals = holm([float(r["wilcoxon_p_one_sided"]) for r in test_rows])
    bvals = bh([float(r["wilcoxon_p_one_sided"]) for r in test_rows])
    for row, hval, bval in zip(test_rows, hvals, bvals):
        row["holm_q"] = hval
        row["bh_q"] = bval

    pool_rows = load_pool_summaries()
    write_csv(SUMMARY_CSV, summary_rows)
    write_csv(TEST_CSV, test_rows)
    write_csv(POOL_CSV, pool_rows)

    llm_rule_50 = [
        r
        for r in test_rows
        if r["comparison"] == "phaseA_llm_k3_v2>phaseA_rule_v2" and int(r["n_real"]) == 50
    ]
    failed = any(float(r["mean_delta"]) <= 0 or float(r["holm_q"]) >= 0.05 for r in llm_rule_50)

    lines = [
        "# Phase-A LLM Contribution Gate",
        "",
        "Date: 2026-07-05",
        "",
        "Inputs:",
        "",
        f"- Downstream CSV: `{DOWNSTREAM.relative_to(ROOT)}`",
        "- Random pool: `breeze/runs/recipe_ablation_random_v2_full/pool_v2.npz`",
        "- Rule pool: `breeze/runs/recipe_ablation_rule_v2_full/pool_v2.npz`",
        "- LLM K=3 + v2 rescreen pool: `breeze/runs/rescreen_v2_full/pool_v2.npz`",
        "",
        "All three recipe sources use 150 recipe slots per class and the same renderer/v2 verifier for admission in this Phase-A comparison. Random accepted no slots, so its downstream augmentation contains no synthetic samples and equals real-only for the same seeds.",
        "",
        "## Pool Admission",
        "",
        *md_table(
            pool_rows,
            [
                "baseline",
                "recipe_slots",
                "accepted_slots",
                "slot_acceptance",
                "accepted_items_before_diversity",
                "kept_after_diversity",
                "kept_healthy",
                "kept_OR",
                "kept_IR",
            ],
        ),
        "",
        "## Downstream Means",
        "",
        *md_table(
            summary_rows,
            ["baseline", "n_real", "metric", "n", "mean", "std", "median", "n_syn_values"],
        ),
        "",
        "## One-Sided Paired Wilcoxon Tests",
        "",
        *md_table(
            test_rows,
            [
                "metric",
                "n_real",
                "comparison",
                "mean_delta",
                "median_delta",
                "wins",
                "losses",
                "wilcoxon_p_one_sided",
                "holm_q",
                "bh_q",
            ],
        ),
        "",
        "## Gate Decision",
        "",
    ]
    if failed:
        lines.extend(
            [
                "Phase A does not pass.",
                "",
                "Reason: LLM K=3 + v2 is significantly better than the random recipe source, but it is not significantly better than the rule recipe source after Holm correction, and at n_real=50 it is slightly worse than rule on both Accuracy and Macro-F1. This violates the required gate that LLM recipe downstream Accuracy/Macro-F1 must be significantly higher than both random and rule.",
                "",
                "Per the latest user instruction, do not proceed to Stage B/C/D/E/F/G expansion until the LLM contribution mechanism is improved and this Phase-A gate is re-run.",
            ]
        )
    else:
        lines.append("Phase A passes under the configured gate.")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")
    print(f"wrote {SUMMARY_CSV}")
    print(f"wrote {TEST_CSV}")
    print(f"wrote {POOL_CSV}")
    print(f"wrote {REPORT}")
    print(f"phase_a_failed={failed}")


if __name__ == "__main__":
    main()
