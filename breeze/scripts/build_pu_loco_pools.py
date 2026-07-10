"""Build leakage-aware PU LOCO synthetic pools.

For a held-out operating condition, synthetic windows are generated only for
the remaining training conditions. LLM recipes are reused as morphology
templates, while condition-dependent kinematic fields are supplied by the PU
bearing plugin through ``fault_freqs`` and then verified against the
corresponding training condition.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

import sys

ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "src"))
sys.path.insert(0, str(BREEZE / "scripts"))

from config import CLASSES, CONDITIONS, PROC_DIR, fault_freqs  # noqa: E402
from recipe_ablation import (  # noqa: E402
    build_profiles,
    diversity_mask,
    random_recipe,
    rule_recipe,
    stable_seed,
    tolist,
)
from renderer import render  # noqa: E402
from verifier.v2 import BreezeVerifierV2  # noqa: E402


SOURCES = ["llm", "rule", "random_open_loop"]
LLM_RECIPE_DIR = BREEZE / "runs" / "pool_physics_file_k3"


def class_for_bearing(bearing: str) -> str:
    if bearing.startswith("K0"):
        return "healthy"
    if bearing.startswith("KA"):
        return "OR"
    if bearing.startswith("KI"):
        return "IR"
    raise ValueError(f"unknown PU bearing id: {bearing}")


def load_condition(cond: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    bearings: list[str] = []
    for path in sorted(PROC_DIR.glob(f"{cond}_*.npz")):
        data = np.load(path, allow_pickle=True)
        bearing = str(data["bearing"])
        cls = class_for_bearing(bearing)
        y = CLASSES.index(cls)
        W = data["windows"].astype(np.float32)
        xs.append(W)
        ys.append(np.full(len(W), y, dtype=np.int64))
        bearings.extend([bearing] * len(W))
    if not xs:
        raise FileNotFoundError(f"no PU condition windows: {cond}")
    return np.concatenate(xs), np.concatenate(ys), np.asarray(bearings)


def load_llm_recipe(cls: str, slot: int) -> dict[str, Any]:
    path = LLM_RECIPE_DIR / f"{cls}_{slot:04d}.json"
    data = json.loads(path.read_text())
    for item in data.get("history", []):
        if "recipe" in item:
            return item["recipe"]
    raise RuntimeError(f"missing recipe in {path}")


def target_rate(cls: str, freqs: dict[str, float]) -> float:
    if cls == "OR":
        return float(freqs["BPFO"])
    if cls == "IR":
        return float(freqs["BPFI"])
    return 0.0


def conditionize_recipe(recipe: dict[str, Any], cls: str, cond: str) -> dict[str, Any]:
    freqs = fault_freqs(CONDITIONS[cond][0] / 60.0)
    out = json.loads(json.dumps(recipe))
    out["fr_hz"] = float(freqs["fr"])
    rate = target_rate(cls, freqs)
    if "impacts" in out:
        out["impacts"]["rate_hz"] = rate
    if "currents" in out:
        out["currents"]["fault_freq_hz"] = rate
    return out


def gate_pass(report: dict[str, Any]) -> dict[str, bool]:
    return {k: bool(v.get("passed", False)) for k, v in report.get("gates", {}).items()}


def violations(report: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for gate_name, gate in report.get("gates", {}).items():
        if gate.get("passed", True):
            continue
        msgs = gate.get("messages") or [gate_name]
        out.extend(str(m) for m in msgs)
    return out


def calibrate_verifier(cond: str, X: np.ndarray, y: np.ndarray, bearings: np.ndarray, out_dir: Path) -> BreezeVerifierV2:
    path = out_dir / f"verifier_{cond}_c90_soft_w1.json"
    if path.exists():
        return BreezeVerifierV2.load(path)
    verifier = BreezeVerifierV2(coverage=0.90, profile="soft_w1")
    verifier.calibrate(X, y, cond, bearings=bearings)
    verifier.save(path)
    return verifier


def recipe_for_source(
    source: str,
    cls: str,
    cond: str,
    slot: int,
    profiles: dict[str, Any],
) -> dict[str, Any]:
    freqs = fault_freqs(CONDITIONS[cond][0] / 60.0)
    if source == "llm":
        return conditionize_recipe(load_llm_recipe(cls, slot), cls, cond)
    if source == "rule":
        return rule_recipe(cls, freqs, profiles, slot)
    if source == "random_open_loop":
        return random_recipe(cls, freqs, profiles, slot)
    raise ValueError(f"unknown source: {source}")


def run_slot(
    source: str,
    heldout: str,
    cond: str,
    cls: str,
    slot: int,
    out_dir: Path,
    verifier: BreezeVerifierV2,
    profiles: dict[str, Any],
) -> None:
    rec_path = out_dir / f"{cond}_{cls}_{slot:04d}.json"
    if rec_path.exists():
        return
    recipe = recipe_for_source(source, cls, cond, slot, profiles)
    seed_text = f"pu_loco:{heldout}:{source}:{cond}:{cls}:{slot}:r0"
    try:
        w = render(recipe, stable_seed(seed_text))
        report = verifier.verify(w, cls) if source != "random_open_loop" else {"feasible": True, "gates": {}, "scores": {}}
    except Exception as exc:
        rec_path.write_text(
            json.dumps(
                tolist(
                    {
                        "source": source,
                        "heldout": heldout,
                        "condition": cond,
                        "class": cls,
                        "slot": slot,
                        "accepted": False,
                        "history": [{"round": 0, "recipe": recipe, "error": str(exc)}],
                    }
                ),
                separators=(",", ":"),
            )
        )
        return
    np.save(out_dir / f"{cond}_{cls}_{slot:04d}_r0.npy", w)
    accepted = bool(report["feasible"])
    record: dict[str, Any] = {
        "source": source,
        "heldout": heldout,
        "condition": cond,
        "class": cls,
        "slot": slot,
        "accepted": accepted,
        "history": [
            {
                "round": 0,
                "recipe": recipe,
                "feasible": accepted,
                "gate_pass": gate_pass(report),
                "violations": violations(report),
                "scores": report.get("scores", {}),
            }
        ],
    }
    if accepted:
        np.save(out_dir / f"{cond}_{cls}_{slot:04d}.npy", w)
        n_exp = 0
        for sub in range(1, 13):
            if n_exp >= 4:
                break
            wx = render(recipe, stable_seed(f"pu_loco:{heldout}:{source}:{cond}:{cls}:{slot}:x{sub}"))
            repx = verifier.verify(wx, cls) if source != "random_open_loop" else {"feasible": True}
            if repx["feasible"]:
                np.save(out_dir / f"{cond}_{cls}_{slot:04d}_x{n_exp}.npy", wx)
                n_exp += 1
        record["n_feasible_expansions"] = n_exp
    rec_path.write_text(json.dumps(tolist(record), separators=(",", ":")))


def build_pool(source: str, heldout: str, out_dir: Path, Xtrain_all: np.ndarray, ytrain_all: np.ndarray) -> dict[str, Any]:
    Xs: list[np.ndarray] = []
    ys: list[int] = []
    manifest: list[dict[str, Any]] = []
    slot_rows: list[dict[str, Any]] = []
    for rec_path in sorted(out_dir.glob("*.json")):
        rec = json.loads(rec_path.read_text())
        if "class" not in rec or "slot" not in rec or "condition" not in rec:
            continue
        cls = rec["class"]
        ci = CLASSES.index(cls)
        cond = rec["condition"]
        slot = int(rec["slot"])
        selected = out_dir / f"{cond}_{cls}_{slot:04d}.npy"
        accepted = bool(rec.get("accepted")) and selected.exists()
        n_exp = 0
        if accepted:
            Xs.append(np.load(selected))
            ys.append(ci)
            manifest.append({"source": source, "heldout": heldout, "condition": cond, "class": cls, "slot": slot, "kind": "selected", "path": str(selected)})
            for exp_path in sorted(out_dir.glob(f"{cond}_{cls}_{slot:04d}_x*.npy")):
                Xs.append(np.load(exp_path))
                ys.append(ci)
                n_exp += 1
                manifest.append({"source": source, "heldout": heldout, "condition": cond, "class": cls, "slot": slot, "kind": "expansion", "path": str(exp_path)})
        slot_rows.append(
            {
                "source": source,
                "heldout": heldout,
                "condition": cond,
                "class": cls,
                "slot": slot,
                "accepted_slot": accepted,
                "n_feasible_expansions": n_exp,
            }
        )
    if Xs:
        X = np.stack(Xs).astype(np.float32)
        y = np.asarray(ys, dtype=np.int64)
        keep = diversity_mask(X, y, Xtrain_all, ytrain_all)
        X_keep = X[keep]
        y_keep = y[keep]
    else:
        keep = np.zeros((0,), dtype=bool)
        X_keep = np.zeros((0, 3, 2048), dtype=np.float32)
        y_keep = np.zeros((0,), dtype=np.int64)
    for row, kept in zip(manifest, keep.tolist()):
        row["kept_after_diversity"] = bool(kept)
    np.savez_compressed(out_dir / "pool.npz", X=X_keep, y=y_keep, class_names=np.asarray(CLASSES))
    with (out_dir / "manifest.csv").open("w", newline="") as f:
        fieldnames = ["source", "heldout", "condition", "class", "slot", "kind", "path", "kept_after_diversity"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest)
    with (out_dir / "slot_summary.csv").open("w", newline="") as f:
        fieldnames = ["source", "heldout", "condition", "class", "slot", "accepted_slot", "n_feasible_expansions"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(slot_rows)
    summary = {
        "source": source,
        "heldout": heldout,
        "slots": len(slot_rows),
        "accepted_slots": int(sum(row["accepted_slot"] for row in slot_rows)),
        "acceptance": float(sum(row["accepted_slot"] for row in slot_rows) / len(slot_rows)) if slot_rows else 0.0,
        "accepted_items_before_diversity": len(manifest),
        "kept_after_diversity": int(len(y_keep)),
        "kept_counts": {CLASSES[i]: int((y_keep == i).sum()) for i in range(len(CLASSES))},
        "kept_by_condition": dict(Counter(row["condition"] for row in manifest if row.get("kept_after_diversity"))),
    }
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2))
    return summary


def build_for_heldout(args: argparse.Namespace, heldout: str) -> None:
    fold_dir = Path(args.out_root) / f"loco_{heldout}"
    fold_dir.mkdir(parents=True, exist_ok=True)
    train_conditions = [cond for cond in CONDITIONS if cond != heldout]
    loaded = {cond: load_condition(cond) for cond in train_conditions}
    Xtrain_all = np.concatenate([loaded[cond][0] for cond in train_conditions])
    ytrain_all = np.concatenate([loaded[cond][1] for cond in train_conditions])
    for source in args.sources:
        out_dir = fold_dir / source
        out_dir.mkdir(parents=True, exist_ok=True)
        for cond in train_conditions:
            Xc, yc, bc = loaded[cond]
            verifier = calibrate_verifier(cond, Xc, yc, bc, out_dir)
            profiles = build_profiles(Xc, yc)
            for cls in CLASSES:
                for slot in range(args.slots_per_class):
                    run_slot(source, heldout, cond, cls, slot, out_dir, verifier, profiles)
        summary = build_pool(source, heldout, out_dir, Xtrain_all, ytrain_all)
        print(
            f"heldout={heldout} source={source} slots={summary['slots']} "
            f"accepted={summary['accepted_slots']} kept={summary['kept_counts']}",
            flush=True,
        )


def freeze_outputs(out_root: Path, freeze_dir: Path) -> None:
    if freeze_dir.exists():
        raise FileExistsError(f"freeze directory exists: {freeze_dir}")
    shutil.copytree(out_root, freeze_dir)
    files = sorted(str(p) for p in freeze_dir.rglob("*") if p.is_file())
    digests = []
    import subprocess

    for filename in files:
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
    parser.add_argument("--out-root", default="breeze/runs/pu_loco_pools_2026-07-07")
    parser.add_argument("--heldout", nargs="+", default=list(CONDITIONS))
    parser.add_argument("--sources", nargs="+", default=SOURCES)
    parser.add_argument("--slots-per-class", type=int, default=50)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--freeze-dir", default="breeze/runs/pu_loco_pools_2026-07-07_frozen")
    args = parser.parse_args()
    for source in args.sources:
        if source not in SOURCES:
            raise SystemExit(f"unknown source: {source}")
    for heldout in args.heldout:
        if heldout not in CONDITIONS:
            raise SystemExit(f"unknown condition: {heldout}")
        build_for_heldout(args, heldout)
    if args.freeze:
        freeze_outputs(Path(args.out_root), Path(args.freeze_dir))


if __name__ == "__main__":
    main()
