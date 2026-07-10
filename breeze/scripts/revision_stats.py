"""Revision statistics for the BREEZE reviewer-response update.

This script is read-only with respect to experimental runs. It summarizes
existing v2 offline-rescreening records and applies Benjamini-Hochberg
correction to the already computed paired Wilcoxon tests.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RESULTS = BREEZE / "results"
REPORTS = ROOT / "reports"
V2_DIR = BREEZE / "runs" / "rescreen_v2_full"


def bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg FDR-adjusted q-values."""
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    q = [1.0] * n
    prev = 1.0
    for rank_from_end, idx in enumerate(reversed(order), start=1):
        rank = n - rank_from_end + 1
        val = min(prev, p_values[idx] * n / rank)
        q[idx] = min(val, 1.0)
        prev = val
    return q


def summarize_slot_window_mapping() -> pd.DataFrame:
    summary = json.loads((V2_DIR / "summary.json").read_text())
    manifest = pd.read_csv(V2_DIR / "accepted_manifest.csv")
    slot_summary = pd.read_csv(V2_DIR / "slot_summary.csv")

    rows = [
        {
            "block": "all",
            "slots": int(summary["slots"]),
            "accepted_slots_before_diversity": int(summary["accepted_slots_before_diversity"]),
            "accepted_items_before_diversity": int(summary["accepted_items_before_diversity"]),
            "kept_after_diversity": int(summary["kept_after_diversity"]),
            "kept_selected_windows": int(((manifest["kind"] == "selected") & manifest["kept_after_diversity"]).sum()),
            "kept_expansion_windows": int(((manifest["kind"] == "expansion") & manifest["kept_after_diversity"]).sum()),
            "few_shot_cap_windows": 592,
        }
    ]

    for cls, ds in slot_summary.groupby("class", sort=False):
        dm = manifest[manifest["class"] == cls]
        rows.append(
            {
                "block": cls,
                "slots": int(len(ds)),
                "accepted_slots_before_diversity": int(ds["accepted_before_diversity"].sum()),
                "accepted_items_before_diversity": int(len(dm)),
                "kept_after_diversity": int(dm["kept_after_diversity"].sum()),
                "kept_selected_windows": int(((dm["kind"] == "selected") & dm["kept_after_diversity"]).sum()),
                "kept_expansion_windows": int(((dm["kind"] == "expansion") & dm["kept_after_diversity"]).sum()),
                "few_shot_cap_windows": 192 if cls == "healthy" else 200,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "revision_v2_slot_window_mapping.csv", index=False)
    return out


def failed_gates(entry: dict) -> list[str]:
    gates = entry.get("gates", {})
    return [gate for gate, passed in gates.items() if passed is False]


def summarize_fail_reasons() -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_counts: Counter[tuple[str, str, str]] = Counter()
    rejected_slot_counts: Counter[tuple[str, str]] = Counter()
    totals = defaultdict(int)
    rejected_totals = defaultdict(int)

    for path in sorted((V2_DIR / "records").glob("*.json")):
        rec = json.loads(path.read_text())
        cls = rec["class"]
        all_entries = []
        all_entries.extend(c for c in rec.get("candidates", []) if not c.get("missing"))
        all_entries.extend(rec.get("expansions", []))
        for entry in all_entries:
            kind = entry.get("kind", "unknown")
            totals[(cls, kind)] += 1
            if entry.get("feasible"):
                continue
            failures = failed_gates(entry)
            if not failures:
                candidate_counts[(cls, kind, "unknown")] += 1
            for gate in failures:
                candidate_counts[(cls, kind, gate)] += 1

        if rec.get("selected") is None:
            rejected_totals[cls] += 1
            candidates = [c for c in rec.get("candidates", []) if not c.get("missing")]
            terminal = candidates[-1] if candidates else {}
            failures = failed_gates(terminal)
            if not failures:
                rejected_slot_counts[(cls, "unknown")] += 1
            for gate in failures:
                rejected_slot_counts[(cls, gate)] += 1

    candidate_rows = []
    for (cls, kind, gate), count in sorted(candidate_counts.items()):
        denom = totals[(cls, kind)]
        candidate_rows.append(
            {
                "scope": "candidate_or_expansion",
                "class": cls,
                "kind": kind,
                "gate": gate,
                "count": count,
                "evaluations": denom,
                "rate_per_evaluation": count / denom if denom else 0.0,
            }
        )

    rejected_rows = []
    for (cls, gate), count in sorted(rejected_slot_counts.items()):
        denom = rejected_totals[cls]
        rejected_rows.append(
            {
                "scope": "terminal_rejected_slot",
                "class": cls,
                "kind": "slot",
                "gate": gate,
                "count": count,
                "evaluations": denom,
                "rate_per_evaluation": count / denom if denom else 0.0,
            }
        )

    candidate_df = pd.DataFrame(candidate_rows)
    rejected_df = pd.DataFrame(rejected_rows)
    candidate_df.to_csv(RESULTS / "revision_v2_candidate_fail_reasons.csv", index=False)
    rejected_df.to_csv(RESULTS / "revision_v2_rejected_slot_fail_reasons.csv", index=False)
    return candidate_df, rejected_df


def summarize_bh_tests() -> pd.DataFrame:
    sig = pd.read_csv(RESULTS / "significance_v2_vs_main.csv")
    sig["q_bh_all_18"] = bh_adjust(sig["p_wilcoxon"].astype(float).tolist())
    sig["significant_at_fdr_0_05"] = sig["q_bh_all_18"] <= 0.05
    sig.to_csv(RESULTS / "revision_v2_significance_bh.csv", index=False)
    return sig


def summarize_all_baseline_tests() -> pd.DataFrame:
    from scipy.stats import wilcoxon

    main = pd.read_csv(RESULTS / "downstream_file.csv")
    custom = pd.read_csv(RESULTS / "custom_pool_eval.csv")
    v2 = custom[custom["baseline"] == "breeze_v2_full"].copy()
    rows = []
    for nr in sorted(v2["n_real"].unique()):
        v2_nr = v2[v2["n_real"] == nr].sort_values("seed")
        v2_seeds = v2_nr["seed"].to_numpy()
        for baseline in sorted(main["baseline"].unique()):
            other = main[(main["n_real"] == nr) & (main["baseline"] == baseline)].sort_values("seed")
            other = other[other["seed"].isin(v2_seeds)].sort_values("seed")
            vv = v2_nr[v2_nr["seed"].isin(other["seed"])].sort_values("seed")
            if len(other) < 5 or len(vv) != len(other):
                continue
            a = vv["acc"].to_numpy()
            b = other["acc"].to_numpy()
            try:
                _, p = wilcoxon(a, b)
            except ValueError:
                p = 1.0
            rows.append(
                {
                    "n_real": nr,
                    "baseline": baseline,
                    "v2_mean": float(a.mean()),
                    "other_mean": float(b.mean()),
                    "delta": float(a.mean() - b.mean()),
                    "p_wilcoxon": float(p),
                }
            )
    out = pd.DataFrame(rows)
    out["q_bh_all_baselines"] = bh_adjust(out["p_wilcoxon"].astype(float).tolist())
    out["significant_at_fdr_0_05"] = out["q_bh_all_baselines"] <= 0.05
    out.to_csv(RESULTS / "revision_v2_significance_all_baselines_bh.csv", index=False)
    return out


def df_to_markdown(df: pd.DataFrame) -> str:
    """Small dependency-free Markdown table writer."""
    if df.empty:
        return ""
    cols = list(df.columns)
    rows = []
    rows.append("| " + " | ".join(cols) + " |")
    rows.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        vals = []
        for col in cols:
            val = row[col]
            if isinstance(val, float):
                vals.append(f"{val:.6g}")
            else:
                vals.append(str(val))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


def write_markdown(
    mapping: pd.DataFrame,
    cand: pd.DataFrame,
    rejected: pd.DataFrame,
    sig: pd.DataFrame,
    sig_all: pd.DataFrame,
) -> None:
    lines = []
    lines.append("# BREEZE Revision Statistics")
    lines.append("")
    lines.append("Date: 2026-07-04")
    lines.append("")
    lines.append("All numbers are derived from existing frozen outputs; no new LLM generation was run.")
    lines.append("")
    lines.append("## v2 Slot/Window Mapping")
    lines.append("")
    lines.append(df_to_markdown(mapping))
    lines.append("")
    lines.append("Interpretation: a slot is one requested LLM generation unit. A feasible slot can")
    lines.append("contribute the selected round window and zero or more feasible expansion windows.")
    lines.append("The full v2 offline rescreening admits 286/450 slots, produces 761 accepted")
    lines.append("items before diversity, and keeps 757 windows after diversity. Few-shot training")
    lines.append("uses a 200-window/class cap, so the v2 training budget is 192+200+200=592.")
    lines.append("")
    lines.append("## Candidate-Level Failed Gates")
    lines.append("")
    lines.append(df_to_markdown(cand) if not cand.empty else "No candidate failures found.")
    lines.append("")
    lines.append("## Terminal Rejected-Slot Failed Gates")
    lines.append("")
    lines.append(df_to_markdown(rejected) if not rejected.empty else "No rejected-slot failures found.")
    lines.append("")
    lines.append("## Paired Wilcoxon With BH Correction")
    lines.append("")
    lines.append(df_to_markdown(sig))
    lines.append("")
    lines.append("Multiple-testing note: q-values use Benjamini-Hochberg correction across all")
    lines.append("18 v2-vs-comparator tests in `significance_v2_vs_main.csv`.")
    lines.append("")
    lines.append("## Full v2 vs All Main Baselines")
    lines.append("")
    lines.append(df_to_markdown(sig_all))
    lines.append("")
    lines.append("Multiple-testing note: q-values in this full table use Benjamini-Hochberg")
    lines.append("correction across all v2-vs-main-baseline tests in")
    lines.append("`revision_v2_significance_all_baselines_bh.csv`.")
    lines.append("")
    lines.append("## MMD2 Protocol")
    lines.append("")
    lines.append("The MMD2 tables use `breeze/src/metrics.py::pool_metrics`. For each class,")
    lines.append("the script extracts up to 150 synthetic windows and up to 150 train-real")
    lines.append("windows, computes an eight-dimensional vibration-channel feature vector")
    lines.append("(RMS, kurtosis, crest factor, skewness, and four Welch-PSD band-energy")
    lines.append("fractions over 0-500, 500-1500, 1500-2500, and 2500-4000 Hz), standardizes")
    lines.append("features by the sampled real mean and standard deviation, and computes")
    lines.append("RBF-kernel MMD2 using the median pairwise-distance bandwidth heuristic.")
    lines.append("Nearest-neighbour diversity is the mean within-pool NN distance in the same")
    lines.append("standardized feature space, reported next to the real-real reference.")
    lines.append("")
    (REPORTS / "revision_statistics_2026-07-04.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    mapping = summarize_slot_window_mapping()
    cand, rejected = summarize_fail_reasons()
    sig = summarize_bh_tests()
    sig_all = summarize_all_baseline_tests()
    write_markdown(mapping, cand, rejected, sig, sig_all)


if __name__ == "__main__":
    main()
