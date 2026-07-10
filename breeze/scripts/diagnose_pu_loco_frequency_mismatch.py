"""Diagnose PU LOCO v1 kinematic frequency mismatch.

This audit uses only synthetic recipe metadata and public/known operating
condition metadata. It does not read held-out vibration/current windows.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "src"))

from config import CLASSES, CONDITIONS, fault_freqs  # noqa: E402


FAULT_KEY = {"OR": "BPFO", "IR": "BPFI"}


def load_recipe_from_record(path: Path) -> dict[str, Any] | None:
    rec = json.loads(path.read_text())
    history = rec.get("history") or []
    for item in reversed(history):
        if item.get("recipe") is not None:
            return item["recipe"]
    return None


def iter_records(root: Path, source: str) -> list[Path]:
    if source == "llm":
        return sorted(root.glob(f"loco_*/llm/*_*.json"))
    return sorted(root.glob(f"loco_*/{source}/*_*.json"))


def parse_record_path(path: Path, source: str) -> tuple[str, str, str] | None:
    # Expected:
    #   <root>/loco_<heldout>/<source>/<cond>_<cls>_<slot>.json
    heldout_dir = path.parents[1].name
    if not heldout_dir.startswith("loco_"):
        return None
    heldout = heldout_dir.replace("loco_", "", 1)
    stem = path.stem
    if stem in {"summary", "verifier_c90", "gate_report"} or stem.startswith("verifier_"):
        return None
    for cls in CLASSES:
        marker = f"_{cls}_"
        if marker in stem:
            cond = stem.split(marker)[0]
            return heldout, cond, cls
    return None


def recipe_fault_rate(recipe: dict[str, Any], cls: str) -> float:
    if cls == "healthy":
        return 0.0
    impacts = recipe.get("impacts") or {}
    currents = recipe.get("currents") or {}
    if impacts.get("rate_hz") not in (None, ""):
        return float(impacts.get("rate_hz"))
    if currents.get("fault_freq_hz") not in (None, ""):
        return float(currents.get("fault_freq_hz"))
    return math.nan


def row_for(path: Path, source: str) -> dict[str, Any] | None:
    parsed = parse_record_path(path, source)
    if parsed is None:
        return None
    heldout, render_cond, cls = parsed
    if heldout not in CONDITIONS or render_cond not in CONDITIONS or cls == "healthy":
        return None
    rec = json.loads(path.read_text())
    if rec.get("accepted") is False:
        return None
    recipe = load_recipe_from_record(path)
    if recipe is None:
        return None
    key = FAULT_KEY[cls]
    recipe_rate = recipe_fault_rate(recipe, cls)
    recipe_fr = float(recipe.get("fr_hz", math.nan))
    render_freqs = fault_freqs(CONDITIONS[render_cond][0] / 60.0)
    target_freqs = fault_freqs(CONDITIONS[heldout][0] / 60.0)
    render_target = float(render_freqs[key])
    heldout_target = float(target_freqs[key])
    err_hz = recipe_rate - heldout_target
    err_pct = 100.0 * err_hz / heldout_target
    render_err_hz = recipe_rate - render_target
    render_err_pct = 100.0 * render_err_hz / render_target
    return {
        "source": source,
        "heldout": heldout,
        "render_condition": render_cond,
        "class": cls,
        "fault_key": key,
        "recipe_fr_hz": recipe_fr,
        "recipe_fault_rate_hz": recipe_rate,
        "render_condition_target_hz": render_target,
        "heldout_condition_target_hz": heldout_target,
        "error_vs_render_condition_hz": render_err_hz,
        "error_vs_render_condition_pct": render_err_pct,
        "error_vs_heldout_hz": err_hz,
        "error_vs_heldout_pct": err_pct,
        "abs_error_vs_heldout_pct": abs(err_pct),
        "path": str(path.relative_to(ROOT)),
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["source"], row["heldout"], row["render_condition"], row["class"])].append(row)
    out = []
    for key, vals in sorted(groups.items()):
        source, heldout, render_cond, cls = key
        abs_pct = np.asarray([float(v["abs_error_vs_heldout_pct"]) for v in vals], dtype=float)
        pct = np.asarray([float(v["error_vs_heldout_pct"]) for v in vals], dtype=float)
        render_abs_pct = np.asarray([abs(float(v["error_vs_render_condition_pct"])) for v in vals], dtype=float)
        out.append(
            {
                "source": source,
                "heldout": heldout,
                "render_condition": render_cond,
                "class": cls,
                "n_records": len(vals),
                "mean_error_vs_heldout_pct": float(np.mean(pct)),
                "mean_abs_error_vs_heldout_pct": float(np.mean(abs_pct)),
                "median_abs_error_vs_heldout_pct": float(np.median(abs_pct)),
                "max_abs_error_vs_heldout_pct": float(np.max(abs_pct)),
                "mean_abs_error_vs_render_condition_pct": float(np.mean(render_abs_pct)),
            }
        )
    return out


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for row in rows:
        vals = []
        for col in cols:
            val = row.get(col, "")
            if isinstance(val, float):
                vals.append(f"{val:.2f}")
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def report(rows: list[dict[str, Any]], summary: list[dict[str, Any]]) -> str:
    total = len(rows)
    by_source = Counter(row["source"] for row in rows)
    big = [row for row in rows if float(row["abs_error_vs_heldout_pct"]) > 10.0]
    lines: list[str] = []
    lines.append("# PU LOCO v1 Frequency-Mismatch Diagnostic")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Purpose: test whether v1 synthetic recipes were rendered at training-condition kinematics instead of held-out deployment-condition kinematics.")
    lines.append("- Inputs: synthetic recipe JSON files and known operating-condition metadata only.")
    lines.append("- Held-out vibration/current windows and labels are not read.")
    lines.append("- Fault frequencies are computed from PU 6203 geometry and condition rpm.")
    lines.append("")
    lines.append("## Result")
    lines.append(f"- Audited accepted OR/IR recipe records: {total}.")
    lines.append("- Records by source: " + ", ".join(f"{k}={v}" for k, v in sorted(by_source.items())) + ".")
    lines.append(f"- Records with absolute fault-rate error >10% relative to held-out target: {len(big)}/{total}.")
    lines.append("- Error relative to the render condition is near zero for rule/conditionized LLM recipes; error relative to the held-out condition is large whenever the render condition rpm differs from the held-out rpm.")
    lines.append("")
    lines.append("## Summary By Source / Fold / Render Condition / Class")
    lines.extend(
        md_table(
            summary,
            [
                "source",
                "heldout",
                "render_condition",
                "class",
                "n_records",
                "mean_error_vs_heldout_pct",
                "mean_abs_error_vs_heldout_pct",
                "mean_abs_error_vs_render_condition_pct",
            ],
        )
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- v1 is physically mismatched for cross-speed LOCO: recipes rendered at 1500 rpm are about +66.7% high when deployed against N09 900 rpm, while recipes rendered at 900 rpm are about -40.0% low when deployed against N15 1500 rpm.")
    lines.append("- This supports the v2 protocol change: use held-out condition metadata to set `fr_hz`, BPFO/BPFI impact rate, and current fault frequency while still using zero held-out signal or label data.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm-root", default="breeze/runs/pu_loco_llm_smoke_2026-07-07_v3")
    parser.add_argument("--nonllm-root", default="breeze/runs/pu_loco_nonllm_pools_2026-07-07")
    parser.add_argument("--out-dir", default="breeze/results/pu_loco_v2_2026-07-08")
    args = parser.parse_args()
    rows: list[dict[str, Any]] = []
    for source, root in [
        ("llm", ROOT / args.llm_root),
        ("rule", ROOT / args.nonllm_root),
        ("random_open_loop", ROOT / args.nonllm_root),
    ]:
        for path in iter_records(root, source):
            row = row_for(path, source)
            if row is not None:
                rows.append(row)
    summary = summarize(rows)
    out_dir = ROOT / args.out_dir
    write_csv(out_dir / "pu_loco_v1_frequency_mismatch_records.csv", rows)
    write_csv(out_dir / "pu_loco_v1_frequency_mismatch_summary.csv", summary)
    (out_dir / "pu_loco_v1_frequency_mismatch_report.md").write_text(report(rows, summary))
    print(json.dumps({"records": len(rows), "summary_rows": len(summary), "out_dir": str(out_dir.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
