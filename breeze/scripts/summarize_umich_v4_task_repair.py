"""Summarize UMich v4 learnability repair results."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd


def read_downstream(path: Path, variant: str, method: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["variant"] = variant
    df["method"] = method
    return df


def parse_f1(row: pd.Series, cls: str) -> float:
    try:
        return float(json.loads(row["per_class_f1_json"]).get(cls, 0.0))
    except Exception:
        return 0.0


def summarize_downstream(frames: list[pd.DataFrame]) -> pd.DataFrame:
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    if df.empty:
        return pd.DataFrame()
    df["f1_unworn"] = df.apply(lambda r: parse_f1(r, "unworn"), axis=1)
    df["f1_worn"] = df.apply(lambda r: parse_f1(r, "worn"), axis=1)
    rows = []
    for (variant, method, n_real), g in df.groupby(["variant", "method", "n_real"], sort=True):
        rows.append(
            {
                "variant": variant,
                "method": method,
                "n_real": int(n_real),
                "rows": int(len(g)),
                "mean_acc": float(g["acc"].mean()),
                "std_acc": float(g["acc"].std(ddof=1)) if len(g) > 1 else 0.0,
                "mean_macro_f1": float(g["macro_f1"].mean()),
                "std_macro_f1": float(g["macro_f1"].std(ddof=1)) if len(g) > 1 else 0.0,
                "mean_f1_unworn": float(g["f1_unworn"].mean()),
                "mean_f1_worn": float(g["f1_worn"].mean()),
            }
        )
    return pd.DataFrame(rows)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", default="breeze/results/milling_umich_v4_task_repair_2026-07-09")
    args = parser.parse_args()
    root = Path(args.result_dir)
    frames = [
        read_downstream(
            root / "downstream_real_only_multi_raw_10seed/umich_v4_multi_raw_real_only_nsyn0.csv",
            "all_label_multi_raw",
            "real_only",
        ),
        read_downstream(
            root / "downstream_real_only_multi_stagez_10seed/umich_v4_multi_stagez_real_only_nsyn0.csv",
            "all_label_multi_stagez",
            "real_only",
        ),
        read_downstream(
            root / "downstream_real_only_layer1up_10seed/umich_v4_layer1up_real_only_nsyn0.csv",
            "all_label_layer1up",
            "real_only",
        ),
        read_downstream(
            root / "downstream_real_only_clean_multi_raw_10seed/umich_v4_clean_multi_raw_real_only_nsyn0.csv",
            "clean_multi_raw",
            "real_only",
        ),
        read_downstream(
            root / "downstream_real_only_clean_multi_stagez_10seed/umich_v4_clean_multi_stagez_real_only_nsyn0.csv",
            "clean_multi_stagez",
            "real_only",
        ),
        read_downstream(
            root / "downstream_real_only_clean_multi_meta_10seed/umich_v4_clean_multi_meta_real_only_nsyn0.csv",
            "clean_multi_meta",
            "real_only",
        ),
        read_downstream(
            root / "downstream_real_only_clean_multi_stagez_meta_10seed/umich_v4_clean_multi_stagez_meta_real_only_nsyn0.csv",
            "clean_multi_stagez_meta",
            "real_only",
        ),
        read_downstream(
            root
            / "downstream_noise_aug_clean_multi_stagez_meta_10seed/umich_v4_clean_multi_stagez_meta_noise_aug_nsyn20.csv",
            "clean_multi_stagez_meta",
            "noise_aug",
        ),
    ]
    summary = summarize_downstream(frames)
    summary_path = root / "umich_v4_task_repair_downstream_summary.csv"
    summary.to_csv(summary_path, index=False)

    audit_path = root / "learnability_audit/umich_v4_diagnostic_baselines.csv"
    audit = pd.read_csv(audit_path) if audit_path.exists() else pd.DataFrame()
    condition_path = root / "learnability_audit/umich_v4_condition_quadrant_counts.csv"
    condition = pd.read_csv(condition_path) if condition_path.exists() else pd.DataFrame()
    clean_split_report = root / "clean_inner/umich_v4_clean_inner_split_report.md"
    split_text = clean_split_report.read_text() if clean_split_report.exists() else ""

    def row_for(variant: str, method: str, n_real: int) -> pd.Series | None:
        m = summary[(summary["variant"] == variant) & (summary["method"] == method) & (summary["n_real"] == n_real)]
        return None if m.empty else m.iloc[0]

    selected_full = row_for("clean_multi_stagez_meta", "real_only", 9999)
    selected_n10 = row_for("clean_multi_stagez_meta", "real_only", 10)
    raw_full = row_for("clean_multi_raw", "real_only", 9999)
    raw_n10 = row_for("clean_multi_raw", "real_only", 10)
    noise_n10 = row_for("clean_multi_stagez_meta", "noise_aug", 10)
    learnability_numeric_pass = bool(
        selected_full is not None
        and selected_n10 is not None
        and float(selected_full["mean_acc"]) >= 0.75
        and float(selected_full["mean_macro_f1"]) >= 0.65
        and float(selected_n10["mean_acc"]) > 0.55
        and float(selected_n10["mean_macro_f1"]) > 0.55
        and float(selected_n10["mean_f1_unworn"]) > 0.05
        and float(selected_n10["mean_f1_worn"]) > 0.05
    )
    metadata_only = audit[audit["baseline"] == "metadata_only"].iloc[0] if not audit.empty else None
    signal_only = audit[audit["baseline"] == "signal_feature_only"].iloc[0] if not audit.empty else None
    stage_only = audit[audit["baseline"] == "stage_only"].iloc[0] if not audit.empty else None
    confounded = bool(
        metadata_only is not None
        and signal_only is not None
        and float(metadata_only["acc"]) >= float(signal_only["acc"]) - 0.02
        and float(metadata_only["macro_f1"]) >= float(signal_only["macro_f1"]) - 0.02
    )
    clean_conditions = {}
    if not condition.empty:
        for q in ["clean_unworn", "clean_worn"]:
            rows = condition[condition["quadrant"] == q]
            clean_conditions[q] = sorted((float(r.feedrate), float(r.clamp_pressure), int(r.windows)) for r in rows.itertuples())

    lines = [
        "# UMich v4 Task-Repair Report",
        "",
        "Date: 2026-07-09 Asia/Shanghai",
        "",
        "Status: stop before LLM generation. No formal held-out test was run.",
        "",
        "## Protocol Boundary",
        "",
        "- Berkeley v2 binary formal remains frozen as partial/no-go and is not tuned here.",
        "- UMich v4 uses only outer-train derived inner-train/inner-val artifacts for task repair.",
        "- LLM/API calls in this v4 repair stage: 0; cumulative API remains 1020/3000.",
        "- Clean supervised labels are restricted to `unworn+passed_visual_inspection=yes` and `worn+passed_visual_inspection=no`.",
        "",
        "## Clean Split",
        "",
        split_text.strip(),
        "",
        "## Real-Only Learnability",
        "",
        "| variant | method | n_real | Acc | Macro-F1 | F1 unworn | F1 worn |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in summary.sort_values(["variant", "method", "n_real"]).iterrows():
        lines.append(
            f"| {r['variant']} | {r['method']} | {int(r['n_real'])} | {float(r['mean_acc']):.4f} | "
            f"{float(r['mean_macro_f1']):.4f} | {float(r['mean_f1_unworn']):.4f} | {float(r['mean_f1_worn']):.4f} |"
        )
    lines.extend(["", "## Confound Audit", ""])
    if metadata_only is not None and stage_only is not None and signal_only is not None:
        lines.extend(
            [
                "| baseline | Acc | Macro-F1 | F1 unworn | F1 worn |",
                "|---|---:|---:|---:|---:|",
                f"| metadata_only | {float(metadata_only['acc']):.4f} | {float(metadata_only['macro_f1']):.4f} | {float(metadata_only['f1_unworn']):.4f} | {float(metadata_only['f1_worn']):.4f} |",
                f"| stage_only | {float(stage_only['acc']):.4f} | {float(stage_only['macro_f1']):.4f} | {float(stage_only['f1_unworn']):.4f} | {float(stage_only['f1_worn']):.4f} |",
                f"| signal_feature_only | {float(signal_only['acc']):.4f} | {float(signal_only['macro_f1']):.4f} | {float(signal_only['f1_unworn']):.4f} | {float(signal_only['f1_worn']):.4f} |",
            ]
        )
    lines.extend(
        [
            "",
            "Clean feedrate/clamp support:",
            f"- clean_unworn: `{clean_conditions.get('clean_unworn', [])}`",
            f"- clean_worn: `{clean_conditions.get('clean_worn', [])}`",
            "",
            "There is no feedrate x clamp_pressure condition containing both clean classes. Metadata-only classification is perfect, so the clean task cannot distinguish tool wear from process-condition confounding under a condition-balanced protocol.",
            "",
            "## Gate Decision",
            "",
            f"- Numeric learnability gate on the best clean CNN representation: `{learnability_numeric_pass}`.",
            f"- Confound gate failed: `{confounded}`.",
            "- Single-stage clean diagnosis is also under-supported: each active single stage has only 3-4 clean worn windows total, so n_real=10 cannot be evaluated without violating class support.",
            "- Therefore UMich v4 must stop before LLM synthetic generation. Running LLM now would optimize a condition-confounded label boundary, not a defensible worn/unworn wear signal.",
            "",
            "## Artifacts",
            "",
            f"- Downstream summary: `{summary_path}`",
            "- Audit report: `learnability_audit/umich_v4_learnability_audit.md`",
            "- Clean split report: `clean_inner/umich_v4_clean_inner_split_report.md`",
            "- Diagnostic baseline CSVs: `learnability_audit/umich_v4_diagnostic_baselines.csv`, `learnability_audit/umich_v4_diagnostic_baseline_confusions.csv`, `learnability_audit/umich_v4_diagnostic_baseline_per_condition.csv`",
        ]
    )
    report_path = root / "umich_v4_task_repair_report.md"
    report_path.write_text("\n".join(lines) + "\n")
    print(f"wrote {summary_path}")
    print(f"wrote {report_path}")
    if raw_full is not None and raw_n10 is not None:
        print(
            "clean raw: full Acc/Macro-F1="
            f"{float(raw_full['mean_acc']):.4f}/{float(raw_full['mean_macro_f1']):.4f}; "
            f"n10={float(raw_n10['mean_acc']):.4f}/{float(raw_n10['mean_macro_f1']):.4f}"
        )
    if selected_full is not None and selected_n10 is not None:
        print(
            "clean stagez_meta: full Acc/Macro-F1="
            f"{float(selected_full['mean_acc']):.4f}/{float(selected_full['mean_macro_f1']):.4f}; "
            f"n10={float(selected_n10['mean_acc']):.4f}/{float(selected_n10['mean_macro_f1']):.4f}"
        )
    if noise_n10 is not None:
        print(f"noise_aug stagez_meta n10={float(noise_n10['mean_acc']):.4f}/{float(noise_n10['mean_macro_f1']):.4f}")
    print(f"numeric_gate={learnability_numeric_pass} confounded={confounded}")


if __name__ == "__main__":
    main()
