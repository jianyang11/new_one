"""Build PU LOCO v2 condition-aware LLM pools without new API calls.

This implements the preregistered v2 protocol:

* reuse accepted v1 LLM recipe morphology;
* replace only condition-dependent kinematics with the held-out rpm;
* calibrate verifier statistics/PSD boundaries from training-condition real
  windows, then extrapolate the kinematic target frequencies to the held-out
  condition metadata;
* never read held-out windows or labels during pool construction.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import sys

ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "src"))
sys.path.insert(0, str(BREEZE / "scripts"))

from build_pu_loco_pools import CLASSES, CONDITIONS, load_condition, target_rate, tolist, violations, gate_pass  # noqa: E402
from config import fault_freqs  # noqa: E402
from recipe_ablation import diversity_mask, stable_seed  # noqa: E402
from renderer import render  # noqa: E402
from verifier.v2 import BreezeVerifierV2  # noqa: E402


V1_ROOT = BREEZE / "runs" / "pu_loco_llm_smoke_2026-07-07_v3"


def abs_path(path_s: str | Path) -> Path:
    p = Path(path_s)
    return p if p.is_absolute() else ROOT / p


def conditionize_to_heldout(recipe: dict[str, Any], cls: str, heldout: str) -> dict[str, Any]:
    freqs = fault_freqs(CONDITIONS[heldout][0] / 60.0)
    out = json.loads(json.dumps(recipe))
    out["fr_hz"] = float(freqs["fr"])
    rate = target_rate(cls, freqs)
    if "impacts" in out:
        out["impacts"]["rate_hz"] = rate
    if "currents" in out:
        out["currents"]["fault_freq_hz"] = rate
    return out


def accepted_recipe(record: dict[str, Any]) -> dict[str, Any] | None:
    if not record.get("accepted"):
        return None
    for hist in record.get("history", []):
        if hist.get("n_feasible_expansions", 0) > 0 and isinstance(hist.get("recipe"), dict):
            return hist["recipe"]
    for hist in record.get("history", []):
        if isinstance(hist.get("recipe"), dict):
            return hist["recipe"]
    return None


def extrapolated_verifier(heldout: str, cond: str, Xc: np.ndarray, yc: np.ndarray, bc: np.ndarray, out_dir: Path) -> BreezeVerifierV2:
    path = out_dir / f"verifier_{cond}_to_{heldout}_c90_soft_w1.json"
    if path.exists():
        return BreezeVerifierV2.load(path)
    verifier = BreezeVerifierV2(coverage=0.90, profile="soft_w1")
    verifier.calibrate(Xc, yc, cond, bearings=bc)
    freqs = fault_freqs(CONDITIONS[heldout][0] / 60.0)
    verifier.calib["heldout_condition"] = heldout
    verifier.calib["source_train_condition"] = cond
    verifier.calib["freqs"] = freqs
    verifier.calib["boundary"]["freqs"] = freqs
    if verifier.boundary is not None:
        verifier.boundary.freqs = freqs
    verifier.save(path)
    return verifier


def source_records(heldout: str) -> list[Path]:
    root = V1_ROOT / f"loco_{heldout}" / "llm"
    if not root.exists():
        raise FileNotFoundError(root)
    return sorted(p for p in root.glob("*.json") if p.name != "summary.json")


def run_record(
    rec_path: Path,
    heldout: str,
    out_dir: Path,
    verifier_by_cond: dict[str, BreezeVerifierV2],
    expansions: int,
) -> dict[str, Any] | None:
    src = json.loads(rec_path.read_text())
    cls = src.get("class")
    cond = src.get("condition")
    slot = int(src.get("slot", -1))
    if cls not in CLASSES or cond not in CONDITIONS:
        return None
    out_rec_path = out_dir / f"{cond}_{cls}_{slot:04d}_from_{rec_path.stem}.json"
    if out_rec_path.exists():
        return json.loads(out_rec_path.read_text())
    recipe0 = accepted_recipe(src)
    if recipe0 is None:
        rec = {
            "source": "llm_condition_aware_v2",
            "heldout": heldout,
            "source_condition": cond,
            "class": cls,
            "slot": slot,
            "source_json": str(rec_path.relative_to(ROOT)),
            "accepted": False,
            "reason": "source v1 record has no accepted recipe",
            "accepted_paths": [],
            "history": [],
        }
        out_rec_path.write_text(json.dumps(tolist(rec), indent=2) + "\n")
        return rec
    recipe = conditionize_to_heldout(recipe0, cls, heldout)
    verifier = verifier_by_cond[cond]
    reports = []
    accepted_paths = []
    for exp in range(expansions):
        seed = stable_seed(f"pu-loco-v2:{heldout}:{cond}:{cls}:{slot}:{rec_path.stem}:e{exp}")
        try:
            w = render(recipe, seed)
            report = verifier.verify(w, cls)
        except Exception as exc:
            reports.append({"feasible": False, "error": f"{type(exc).__name__}: {exc}", "gates": {}})
            continue
        reports.append(report)
        if report.get("feasible"):
            path = out_dir / f"{cond}_{cls}_{slot:04d}_{rec_path.stem}_e{exp}.npy"
            np.save(path, w)
            accepted_paths.append(str(path.relative_to(ROOT)))
    rec = {
        "source": "llm_condition_aware_v2",
        "heldout": heldout,
        "source_condition": cond,
        "class": cls,
        "slot": slot,
        "source_json": str(rec_path.relative_to(ROOT)),
        "accepted": bool(accepted_paths),
        "accepted_paths": accepted_paths,
        "history": [
            {
                "round": 0,
                "recipe": recipe,
                "source_recipe": recipe0,
                "n_candidates": expansions,
                "n_feasible_expansions": len(accepted_paths),
                "reports": reports,
                "gate_pass": gate_pass(reports[0]) if reports else {},
                "violations": violations(reports[0]) if reports else [],
            }
        ],
    }
    out_rec_path.write_text(json.dumps(tolist(rec), indent=2) + "\n")
    return rec


def build_pool(heldout: str, out_dir: Path, Xtrain_all: np.ndarray, ytrain_all: np.ndarray) -> dict[str, Any]:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    manifest: list[dict[str, Any]] = []
    slot_rows: list[dict[str, Any]] = []
    failure = Counter()
    for rec_path in sorted(out_dir.glob("*.json")):
        rec = json.loads(rec_path.read_text())
        if rec.get("source") != "llm_condition_aware_v2":
            continue
        cls = rec["class"]
        ci = CLASSES.index(cls)
        paths = rec.get("accepted_paths", [])
        slot_rows.append(
            {
                "heldout": heldout,
                "source_condition": rec.get("source_condition", ""),
                "class": cls,
                "slot": rec.get("slot", ""),
                "accepted": bool(paths),
                "n_paths": len(paths),
                "source_json": rec.get("source_json", ""),
            }
        )
        if not paths:
            for hist in rec.get("history", []):
                reports = hist.get("reports", [])
                for rep in reports[:1]:
                    for msg in violations(rep):
                        failure[f"{cls}: {msg}"] += 1
        for rel in paths:
            xs.append(np.load(ROOT / rel))
            ys.append(ci)
            manifest.append(
                {
                    "heldout": heldout,
                    "source_condition": rec.get("source_condition", ""),
                    "class": cls,
                    "slot": rec.get("slot", ""),
                    "path": rel,
                    "source_json": rec.get("source_json", ""),
                }
            )
    if xs:
        X = np.stack(xs).astype(np.float32)
        y = np.asarray(ys, dtype=np.int64)
        keep = diversity_mask(X, y, Xtrain_all, ytrain_all)
        Xk, yk = X[keep], y[keep]
    else:
        keep = np.zeros((0,), dtype=bool)
        Xk = np.zeros((0, 3, 2048), dtype=np.float32)
        yk = np.zeros((0,), dtype=np.int64)
    for row, kept in zip(manifest, keep.tolist()):
        row["kept_after_diversity"] = bool(kept)
    np.savez_compressed(out_dir / "pool.npz", X=Xk, y=yk, class_names=np.asarray(CLASSES))
    with (out_dir / "manifest.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["heldout", "source_condition", "class", "slot", "path", "source_json", "kept_after_diversity"],
        )
        writer.writeheader()
        writer.writerows(manifest)
    with (out_dir / "slot_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["heldout", "source_condition", "class", "slot", "accepted", "n_paths", "source_json"])
        writer.writeheader()
        writer.writerows(slot_rows)
    summary = {
        "heldout": heldout,
        "slots": len(slot_rows),
        "accepted_slots": int(sum(1 for r in slot_rows if r["accepted"])),
        "accepted_paths_before_diversity": len(manifest),
        "kept_after_diversity": int(len(yk)),
        "kept_counts": {CLASSES[i]: int((yk == i).sum()) for i in range(len(CLASSES))},
        "kept_by_source_condition": dict(Counter(row["source_condition"] for row in manifest if row.get("kept_after_diversity"))),
        "top_failures": dict(failure.most_common(20)),
    }
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2) + "\n")
    return summary


def build_heldout(args: argparse.Namespace, heldout: str) -> dict[str, Any]:
    fold_dir = abs_path(args.out_root) / f"loco_{heldout}" / "llm"
    fold_dir.mkdir(parents=True, exist_ok=True)
    train_conditions = [cond for cond in CONDITIONS if cond != heldout]
    loaded = {cond: load_condition(cond) for cond in train_conditions}
    Xtrain_all = np.concatenate([loaded[cond][0] for cond in train_conditions])
    ytrain_all = np.concatenate([loaded[cond][1] for cond in train_conditions])
    verifier_by_cond = {
        cond: extrapolated_verifier(heldout, cond, loaded[cond][0], loaded[cond][1], loaded[cond][2], fold_dir)
        for cond in train_conditions
    }
    records = [p for p in source_records(heldout) if json.loads(p.read_text()).get("accepted")]
    if args.max_records_per_class > 0:
        kept = []
        counts = Counter()
        for p in records:
            cls = json.loads(p.read_text()).get("class")
            if counts[cls] < args.max_records_per_class:
                kept.append(p)
                counts[cls] += 1
        records = kept
    for rec_path in records:
        run_record(rec_path, heldout, fold_dir, verifier_by_cond, args.expansions)
    summary = build_pool(heldout, fold_dir, Xtrain_all, ytrain_all)
    print(
        f"heldout={heldout} accepted_slots={summary['accepted_slots']}/{summary['slots']} "
        f"kept={summary['kept_counts']}",
        flush=True,
    )
    return summary


def write_report(out_root: Path, summaries: list[dict[str, Any]]) -> None:
    results_dir = ROOT / "breeze" / "results" / "pu_loco_v2_2026-07-08"
    results_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in summaries:
        row = {
            "heldout": s["heldout"],
            "slots": s["slots"],
            "accepted_slots": s["accepted_slots"],
            "accepted_paths_before_diversity": s["accepted_paths_before_diversity"],
            "kept_after_diversity": s["kept_after_diversity"],
        }
        row.update({f"kept_{cls}": s["kept_counts"].get(cls, 0) for cls in CLASSES})
        rows.append(row)
    with (results_dir / "pu_loco_v2_pool_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["heldout"])
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# PU LOCO v2 Condition-Aware Pool Report", ""]
    lines.append("- Protocol: `pu_loco_v2_preregistration.md`; no held-out signals or labels used.")
    lines.append("- API usage: 0 calls for this condition-aware rerender block.")
    lines.append(f"- Output root: `{out_root}`")
    lines.append("- Kinematic metadata used: held-out condition rpm/torque/load from `config.CONDITIONS`.")
    lines.append("- Verifier: stats/PSD boundaries calibrated on each source training condition; kinematic frequencies extrapolated to held-out rpm.")
    lines.append("")
    lines.append("| heldout | accepted slots | kept healthy | kept OR | kept IR | status |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for s in summaries:
        counts = s["kept_counts"]
        ok = all(counts.get(cls, 0) >= 20 for cls in CLASSES)
        lines.append(
            f"| {s['heldout']} | {s['accepted_slots']}/{s['slots']} | "
            f"{counts.get('healthy', 0)} | {counts.get('OR', 0)} | {counts.get('IR', 0)} | "
            f"{'target_reached' if ok else 'target_not_reached'} |"
        )
    lines.append("")
    for s in summaries:
        if all(s["kept_counts"].get(cls, 0) >= 20 for cls in CLASSES):
            continue
        lines.append(f"## Bottleneck: {s['heldout']}")
        for msg, n in s.get("top_failures", {}).items():
            lines.append(f"- {n}: {msg}")
        lines.append("")
    (results_dir / "pu_loco_v2_pool_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", default="breeze/runs/pu_loco_v2_condition_aware_2026-07-08")
    parser.add_argument("--heldout", nargs="+", default=list(CONDITIONS))
    parser.add_argument("--expansions", type=int, default=10)
    parser.add_argument("--max-records-per-class", type=int, default=0)
    args = parser.parse_args()
    summaries = []
    for heldout in args.heldout:
        if heldout not in CONDITIONS:
            raise SystemExit(f"unknown heldout condition: {heldout}")
        summaries.append(build_heldout(args, heldout))
    write_report(abs_path(args.out_root), summaries)


if __name__ == "__main__":
    main()
