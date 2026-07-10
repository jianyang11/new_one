"""Summarize revised Phase-A v2 downstream and gate decision.

Pre-registered statistical family definition for Phase-A v2:

* For each n_real in {5, 10, 25, 50} and each metric in {acc, macro_f1},
  one family contains exactly two one-sided paired Wilcoxon comparisons:
  LLM K=3 > random open-loop and LLM K=3 > rule.
* Holm correction is applied within each family. A global Benjamini-Hochberg
  q value across all pre-registered one-sided superiority tests is reported
  only as a reference.
* The n_real=50 gate additionally checks whether LLM is not worse than rule.
  If the paired mean delta is negative, the two-sided LLM-vs-rule Wilcoxon
  p value must be >= 0.05; if the paired mean delta is non-negative, the
  direction is already not worse. LLM > real_only at n_real=50 is checked by
  a positive paired mean delta and one-sided Wilcoxon p < 0.05.

The script only reads local checkpointed experiment artifacts and writes
summary CSV/Markdown files. It does not alter pools, splits, or trained results.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import wilcoxon


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RESULTS = BREEZE / "results"
RUNS = BREEZE / "runs"

DOWNSTREAM = RESULTS / "phaseA_v2_downstream_cnn.csv"
SUMMARY_CSV = RESULTS / "phaseA_v2_downstream_summary.csv"
PER_CLASS_CSV = RESULTS / "phaseA_v2_per_class_summary.csv"
WILCOXON_CSV = RESULTS / "phaseA_v2_wilcoxon.csv"
CRITERIA_CSV = RESULTS / "phaseA_v2_gate_criteria.csv"
FAILURE_CSV = RESULTS / "phaseA_v2_failure_gate_summary.csv"
REPORT = RESULTS / "phaseA_v2_gate_report.md"

BASELINES = (
    "real_only",
    "phaseA_v2_random_open_loop",
    "phaseA_v2_rule",
    "phaseA_v2_llm_k3",
)
SHOTS = (5, 10, 25, 50)
SEEDS = tuple(range(20))
PRIMARY_METRICS = ("acc", "macro_f1")
CLASS_METRICS = ("f1_healthy", "f1_OR", "f1_IR")
ALL_METRICS = PRIMARY_METRICS + CLASS_METRICS


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"no rows to write for {path}")
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: Any) -> float:
    if value in ("", None):
        return math.nan
    return float(value)


def fmt(value: Any) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        if abs(value) < 0.001 and value != 0:
            return f"{value:.3e}"
        return f"{value:.4f}"
    return str(value)


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


def validate_downstream(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int, int]] = set()
    completeness: list[dict[str, Any]] = []
    for row in rows:
        key = (row["baseline"], int(row["n_real"]), int(row["seed"]))
        if key in seen:
            raise RuntimeError(f"duplicate downstream row: {key}")
        seen.add(key)
    for baseline in BASELINES:
        for n_real in SHOTS:
            missing = [seed for seed in SEEDS if (baseline, n_real, seed) not in seen]
            if missing:
                raise RuntimeError(f"missing rows for {baseline} n={n_real}: {missing}")
            group = [
                row
                for row in rows
                if row["baseline"] == baseline and int(row["n_real"]) == n_real
            ]
            completeness.append(
                {
                    "baseline": baseline,
                    "n_real": n_real,
                    "rows": len(group),
                    "seed_min": min(int(row["seed"]) for row in group),
                    "seed_max": max(int(row["seed"]) for row in group),
                    "n_syn_values": ";".join(sorted({row["n_syn"] for row in group}, key=int)),
                }
            )
    return completeness


def grouped(rows: list[dict[str, str]]) -> dict[tuple[str, int], list[dict[str, str]]]:
    out: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        out[(row["baseline"], int(row["n_real"]))].append(row)
    for key in list(out):
        out[key] = sorted(out[key], key=lambda r: int(r["seed"]))
    return out


def summarize_downstream(by: dict[tuple[str, int], list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for baseline in BASELINES:
        for n_real in SHOTS:
            group = by[(baseline, n_real)]
            for metric in ALL_METRICS:
                vals = np.asarray([float(row[metric]) for row in group], dtype=float)
                rows.append(
                    {
                        "baseline": baseline,
                        "n_real": n_real,
                        "metric": metric,
                        "n": len(vals),
                        "mean": float(np.mean(vals)),
                        "std": float(np.std(vals, ddof=1)),
                        "median": float(np.median(vals)),
                        "min": float(np.min(vals)),
                        "max": float(np.max(vals)),
                        "n_syn_values": ";".join(sorted({row["n_syn"] for row in group}, key=int)),
                    }
                )
    return rows


def per_class_gap(by: dict[tuple[str, int], list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n_real in SHOTS:
        for metric in CLASS_METRICS:
            llm = np.asarray([float(row[metric]) for row in by[("phaseA_v2_llm_k3", n_real)]])
            rule = np.asarray([float(row[metric]) for row in by[("phaseA_v2_rule", n_real)]])
            real = np.asarray([float(row[metric]) for row in by[("real_only", n_real)]])
            random_ol = np.asarray(
                [float(row[metric]) for row in by[("phaseA_v2_random_open_loop", n_real)]]
            )
            rows.append(
                {
                    "n_real": n_real,
                    "class_metric": metric,
                    "llm_mean": float(np.mean(llm)),
                    "rule_mean": float(np.mean(rule)),
                    "random_open_loop_mean": float(np.mean(random_ol)),
                    "real_only_mean": float(np.mean(real)),
                    "llm_minus_rule": float(np.mean(llm - rule)),
                    "llm_minus_random_open_loop": float(np.mean(llm - random_ol)),
                    "llm_minus_real_only": float(np.mean(llm - real)),
                }
            )
    return rows


def add_wilcoxon_row(
    rows: list[dict[str, Any]],
    family_id: str,
    metric: str,
    n_real: int,
    comparison: str,
    test_type: str,
    alternative: str,
    llm: np.ndarray,
    other: np.ndarray,
) -> None:
    diff = llm - other
    stat, pval = safe_wilcoxon(diff, alternative=alternative)
    rows.append(
        {
            "family_id": family_id,
            "metric": metric,
            "n_real": n_real,
            "comparison": comparison,
            "test_type": test_type,
            "alternative": alternative,
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
        }
    )


def wilcoxon_tests(by: dict[tuple[str, int], list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n_real in SHOTS:
        for metric in PRIMARY_METRICS:
            family_id = f"n{n_real}_{metric}_superiority"
            llm = np.asarray([float(row[metric]) for row in by[("phaseA_v2_llm_k3", n_real)]])
            for other_name in ("phaseA_v2_random_open_loop", "phaseA_v2_rule"):
                other = np.asarray([float(row[metric]) for row in by[(other_name, n_real)]])
                add_wilcoxon_row(
                    rows,
                    family_id,
                    metric,
                    n_real,
                    f"phaseA_v2_llm_k3>{other_name}",
                    "pre_registered_superiority",
                    "greater",
                    llm,
                    other,
                )

    families: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        if row["test_type"] == "pre_registered_superiority":
            families[str(row["family_id"])].append(idx)
    for idxs in families.values():
        qvals = holm([float(rows[idx]["p_value"]) for idx in idxs])
        for idx, qval in zip(idxs, qvals):
            rows[idx]["holm_q_in_family"] = qval
    pre_idxs = [idx for idx, row in enumerate(rows) if row["test_type"] == "pre_registered_superiority"]
    bvals = bh([float(rows[idx]["p_value"]) for idx in pre_idxs])
    for idx, qval in zip(pre_idxs, bvals):
        rows[idx]["bh_q_global"] = qval

    for metric in PRIMARY_METRICS:
        n_real = 50
        llm = np.asarray([float(row[metric]) for row in by[("phaseA_v2_llm_k3", n_real)]])
        rule = np.asarray([float(row[metric]) for row in by[("phaseA_v2_rule", n_real)]])
        real = np.asarray([float(row[metric]) for row in by[("real_only", n_real)]])
        add_wilcoxon_row(
            rows,
            f"n50_{metric}_aux",
            metric,
            n_real,
            "phaseA_v2_llm_k3_vs_phaseA_v2_rule",
            "n50_rule_two_sided_aux",
            "two-sided",
            llm,
            rule,
        )
        add_wilcoxon_row(
            rows,
            f"n50_{metric}_aux",
            metric,
            n_real,
            "phaseA_v2_llm_k3>real_only",
            "n50_real_only_superiority_aux",
            "greater",
            llm,
            real,
        )
    return rows


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def slot_admission_from_csv(
    source: str,
    path: Path,
    accepted_col: str,
    kept_by_class: dict[str, int],
) -> list[dict[str, Any]]:
    rows = read_csv(path)
    out: list[dict[str, Any]] = []
    for cls in ("healthy", "OR", "IR"):
        group = [row for row in rows if row["class"] == cls]
        accepted = sum(1 for row in group if boolish(row[accepted_col]))
        feasible = sum(int(row.get("n_feasible_expansions", 0)) for row in group)
        out.append(
            {
                "source": source,
                "class": cls,
                "slots": len(group),
                "accepted_slots": accepted,
                "slot_acceptance": accepted / len(group) if group else 0.0,
                "slot_summary_feasible_expansions": feasible,
                "kept_after_diversity": int(kept_by_class.get(cls, 0)),
            }
        )
    return out


def pool_admission_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    random_summary = json.loads((RUNS / "recipe_ablation_random_v2_full" / "summary.json").read_text())
    rule_summary = json.loads((RUNS / "recipe_ablation_rule_v2_full" / "summary.json").read_text())
    llm_summary = json.loads((RUNS / "rescreen_v2_full" / "summary.json").read_text())
    rows.extend(
        slot_admission_from_csv(
            "random_plus_verifier",
            RUNS / "recipe_ablation_random_v2_full" / "slot_summary.csv",
            "accepted_slot",
            random_summary["kept_counts"],
        )
    )
    rows.extend(
        slot_admission_from_csv(
            "rule_verified",
            RUNS / "recipe_ablation_rule_v2_full" / "slot_summary.csv",
            "accepted_slot",
            rule_summary["kept_counts"],
        )
    )
    rows.extend(
        slot_admission_from_csv(
            "llm_k3_rescreen_v2",
            RUNS / "rescreen_v2_full" / "slot_summary.csv",
            "accepted_before_diversity",
            llm_summary["kept_by_class"],
        )
    )
    return rows


def failed_gates_for_record(data: dict[str, Any], source_kind: str) -> tuple[bool, set[str]]:
    if source_kind == "rescreen":
        selected = data.get("selected")
        if selected:
            return True, set()
        gates: set[str] = set()
        for cand in data.get("candidates", []):
            for gate, passed in cand.get("gates", {}).items():
                if not passed:
                    gates.add(gate)
        return False, gates or {"unknown"}

    accepted = boolish(data.get("accepted", False))
    if accepted:
        return True, set()
    gates = set()
    history = data.get("history") or []
    if history:
        for gate, passed in history[-1].get("gate_pass", {}).items():
            if not passed:
                gates.add(gate)
    return False, gates or {"unknown"}


def failure_gate_summary() -> list[dict[str, Any]]:
    specs = [
        ("random_plus_verifier", RUNS / "recipe_ablation_random_v2_full", "*.json", "recipe"),
        ("rule_verified", RUNS / "recipe_ablation_rule_v2_full", "*.json", "recipe"),
        ("llm_k3_rescreen_v2", RUNS / "rescreen_v2_full" / "records", "*.json", "rescreen"),
    ]
    counters: Counter[tuple[str, str, str]] = Counter()
    totals: Counter[tuple[str, str]] = Counter()
    failed_totals: Counter[tuple[str, str]] = Counter()
    for source, directory, pattern, source_kind in specs:
        for path in sorted(directory.glob(pattern)):
            if path.name == "summary.json":
                continue
            data = json.loads(path.read_text())
            cls = str(data.get("class", "unknown"))
            totals[(source, cls)] += 1
            accepted, gates = failed_gates_for_record(data, source_kind)
            if accepted:
                continue
            failed_totals[(source, cls)] += 1
            for gate in gates:
                counters[(source, cls, gate)] += 1
    rows: list[dict[str, Any]] = []
    for (source, cls, gate), count in sorted(counters.items()):
        total_failed = failed_totals[(source, cls)]
        total_slots = totals[(source, cls)]
        rows.append(
            {
                "source": source,
                "class": cls,
                "gate": gate,
                "failed_slots_with_gate": count,
                "failed_slots_total": total_failed,
                "slots_total": total_slots,
                "share_of_failed_slots": count / total_failed if total_failed else 0.0,
                "share_of_all_slots": count / total_slots if total_slots else 0.0,
            }
        )
    return rows


def criteria_rows(test_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {
        (row["test_type"], row["metric"], int(row["n_real"]), row["comparison"]): row for row in test_rows
    }
    rows: list[dict[str, Any]] = []
    for n_real in (5, 10, 25):
        for metric in PRIMARY_METRICS:
            for other in ("phaseA_v2_random_open_loop", "phaseA_v2_rule"):
                row = lookup[
                    (
                        "pre_registered_superiority",
                        metric,
                        n_real,
                        f"phaseA_v2_llm_k3>{other}",
                    )
                ]
                passed = float(row["mean_delta"]) > 0 and float(row["holm_q_in_family"]) < 0.05
                rows.append(
                    {
                        "criterion": f"n{n_real}_{metric}_llm_gt_{other}",
                        "metric": metric,
                        "n_real": n_real,
                        "comparison": row["comparison"],
                        "mean_delta": row["mean_delta"],
                        "p_value": row["p_value"],
                        "holm_q_in_family": row["holm_q_in_family"],
                        "passed": passed,
                    }
                )

    for metric in PRIMARY_METRICS:
        rule_super = lookup[
            (
                "pre_registered_superiority",
                metric,
                50,
                "phaseA_v2_llm_k3>phaseA_v2_rule",
            )
        ]
        rule_two = lookup[
            (
                "n50_rule_two_sided_aux",
                metric,
                50,
                "phaseA_v2_llm_k3_vs_phaseA_v2_rule",
            )
        ]
        mean_delta = float(rule_super["mean_delta"])
        rule_ok = mean_delta >= 0 or float(rule_two["p_value"]) >= 0.05
        rows.append(
            {
                "criterion": f"n50_{metric}_llm_not_worse_than_rule",
                "metric": metric,
                "n_real": 50,
                "comparison": "phaseA_v2_llm_k3_vs_phaseA_v2_rule",
                "mean_delta": mean_delta,
                "p_value": rule_two["p_value"],
                "holm_q_in_family": "",
                "passed": rule_ok,
            }
        )

        real_aux = lookup[
            (
                "n50_real_only_superiority_aux",
                metric,
                50,
                "phaseA_v2_llm_k3>real_only",
            )
        ]
        real_ok = float(real_aux["mean_delta"]) > 0 and float(real_aux["p_value"]) < 0.05
        rows.append(
            {
                "criterion": f"n50_{metric}_llm_gt_real_only",
                "metric": metric,
                "n_real": 50,
                "comparison": "phaseA_v2_llm_k3>real_only",
                "mean_delta": real_aux["mean_delta"],
                "p_value": real_aux["p_value"],
                "holm_q_in_family": "",
                "passed": real_ok,
            }
        )
    return rows


def compact_primary_summary(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "baseline": row["baseline"],
            "n_real": row["n_real"],
            "metric": row["metric"],
            "mean": row["mean"],
            "std": row["std"],
        }
        for row in summary_rows
        if row["metric"] in PRIMARY_METRICS
    ]


def report_lines(
    completeness: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    per_class_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
    passed: bool,
) -> list[str]:
    budget = read_csv(RESULTS / "phaseA_v2_budget_summary.csv")
    balanced = read_csv(RESULTS / "phaseA_v2_balanced_pool_summary.csv")
    admissions = pool_admission_rows()
    failed_criteria = [row for row in criteria if not boolish(row["passed"])]
    top_failures = sorted(
        failure_rows,
        key=lambda r: (r["source"], r["class"], -float(r["share_of_all_slots"]), r["gate"]),
    )

    lines = [
        "# Phase-A v2 Gate Report",
        "",
        "Date: 2026-07-05",
        "",
        "## Protocol Lock",
        "",
        "- Dataset/protocol: PU N09_M07_F10 file split, CNN downstream classifier.",
        "- Synthetic budget: B=150 per class for LLM K=3, rule, and random open-loop; each downstream augmentation uses n_syn=450.",
        "- Random+verifier accepted 0/450 slots and is reported as verifier robustness evidence only; downstream random comparison uses random open-loop without verifier.",
        "- Seeds: 0-19; n_real in {5, 10, 25, 50}; each result row is checkpointed in `breeze/results/phaseA_v2_downstream_cnn.csv`.",
        "- API usage in this Phase-A v2 rerun: 0 new LLM API calls. The LLM pool is the cached K=3 accepted/rescreened pool.",
        "",
        "## Test Family Registration",
        "",
        "For each n_real and each metric, the pre-registered family contains exactly two one-sided paired Wilcoxon tests: LLM K=3 > random open-loop and LLM K=3 > rule. Holm correction is applied within that family. Global BH q values across all pre-registered superiority tests are reported as a reference only. At n=50, LLM is accepted as not worse than rule if its paired mean delta is non-negative, or if a two-sided LLM-vs-rule Wilcoxon test has p>=0.05 when the mean delta is negative. LLM > real_only at n=50 is checked by positive paired mean delta and one-sided p<0.05.",
        "",
        "## Completeness Check",
        "",
        *md_table(completeness, ["baseline", "n_real", "rows", "seed_min", "seed_max", "n_syn_values"]),
        "",
        "## Budget Equality",
        "",
        *md_table(
            budget,
            [
                "source",
                "available_healthy",
                "available_OR",
                "available_IR",
                "selected_B_per_class",
                "selection_seed",
            ],
        ),
        "",
        *md_table(balanced, ["pool", "n", "healthy", "OR", "IR"]),
        "",
        "## Verifier Admission",
        "",
        *md_table(
            admissions,
            ["source", "class", "slots", "accepted_slots", "slot_acceptance", "kept_after_diversity"],
        ),
        "",
        "## Downstream Means",
        "",
        *md_table(compact_primary_summary(summary_rows), ["baseline", "n_real", "metric", "mean", "std"]),
        "",
        "## Pre-Registered Wilcoxon Tests",
        "",
        *md_table(
            [row for row in test_rows if row["test_type"] == "pre_registered_superiority"],
            [
                "family_id",
                "comparison",
                "mean_delta",
                "wins",
                "losses",
                "p_value",
                "holm_q_in_family",
                "bh_q_global",
            ],
        ),
        "",
        "## n=50 Auxiliary Checks",
        "",
        *md_table(
            [row for row in test_rows if row["test_type"] != "pre_registered_superiority"],
            ["comparison", "metric", "mean_delta", "wins", "losses", "p_value"],
        ),
        "",
        "## Per-Class F1 Gap",
        "",
        *md_table(
            per_class_rows,
            [
                "n_real",
                "class_metric",
                "llm_mean",
                "rule_mean",
                "random_open_loop_mean",
                "real_only_mean",
                "llm_minus_rule",
            ],
        ),
        "",
        "## Gate Failure Distribution",
        "",
        *md_table(
            top_failures[:36],
            [
                "source",
                "class",
                "gate",
                "failed_slots_with_gate",
                "failed_slots_total",
                "slots_total",
                "share_of_all_slots",
            ],
        ),
        "",
        "## Gate Criteria",
        "",
        *md_table(criteria, ["criterion", "mean_delta", "p_value", "holm_q_in_family", "passed"]),
        "",
        "## Decision",
        "",
    ]
    if passed:
        lines.extend(
            [
                "Phase-A v2 passes the revised gate.",
                "",
                "Supported claim scope: in PU few-shot settings n<=25, LLM recipes significantly outperform random open-loop and rule recipes for both Accuracy and Macro-F1 under the pre-registered Holm-corrected families. At n=50, LLM is not worse than rule under the registered auxiliary check and is superior to real-only.",
            ]
        )
    else:
        lines.extend(
            [
                "Phase-A v2 does not pass the revised gate.",
                "",
                "Failed criteria:",
                "",
                *md_table(failed_criteria, ["criterion", "mean_delta", "p_value", "holm_q_in_family", "passed"]),
                "",
                "Per the task instruction, Phase B and later large-scale expansion remain blocked until this gate is revised by discussion or the method is improved and rerun.",
            ]
        )
    return lines


def main() -> None:
    rows = read_csv(DOWNSTREAM)
    completeness = validate_downstream(rows)
    by = grouped(rows)
    summary_rows = summarize_downstream(by)
    per_class_rows = per_class_gap(by)
    test_rows = wilcoxon_tests(by)
    criteria = criteria_rows(test_rows)
    failure_rows = failure_gate_summary()
    passed = all(boolish(row["passed"]) for row in criteria)

    write_csv(SUMMARY_CSV, summary_rows)
    write_csv(PER_CLASS_CSV, per_class_rows)
    write_csv(WILCOXON_CSV, test_rows)
    write_csv(CRITERIA_CSV, criteria)
    write_csv(FAILURE_CSV, failure_rows)
    REPORT.write_text(
        "\n".join(
            report_lines(
                completeness,
                summary_rows,
                per_class_rows,
                test_rows,
                criteria,
                failure_rows,
                passed,
            )
        )
        + "\n"
    )
    print(f"wrote {SUMMARY_CSV}")
    print(f"wrote {PER_CLASS_CSV}")
    print(f"wrote {WILCOXON_CSV}")
    print(f"wrote {CRITERIA_CSV}")
    print(f"wrote {FAILURE_CSV}")
    print(f"wrote {REPORT}")
    print(f"phase_a_v2_passed={passed}")


if __name__ == "__main__":
    main()
