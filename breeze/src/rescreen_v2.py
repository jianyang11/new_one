"""Offline rescreen existing BREEZE generated candidates with v2 gates.

The script never edits the original run directory. It writes checkpointed
per-slot JSON records, CSV manifests, and an optional NPZ pool under --out.

Small-to-large workflow:
  python src/rescreen_v2.py --slots-per-class 10 --out runs/rescreen_v2_s10
  python src/rescreen_v2.py --slots-per-class 50 --out runs/rescreen_v2_s50
  python src/rescreen_v2.py --out runs/rescreen_v2_full
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import CLASSES, MAIN_COND, RUNS_DIR, RESULTS_DIR
from data import load_file_split
from verifier.v2 import BreezeVerifierV2, physical_embedding


def _load_slot_jsons(run_dir: Path, classes: list[str], slots_per_class: int | None) -> list[Path]:
    selected = []
    for cls in classes:
        files = sorted(run_dir.glob(f"{cls}_*.json"), key=lambda p: int(p.stem.split("_")[1]))
        if slots_per_class is not None:
            files = files[:slots_per_class]
        selected.extend(files)
    return selected


def _round_path(run_dir: Path, cls: str, slot: int, rnd: int) -> Path:
    return run_dir / f"{cls}_{slot:04d}_r{rnd}.npy"


def _expansion_paths(run_dir: Path, cls: str, slot: int) -> list[Path]:
    return sorted(run_dir.glob(f"{cls}_{slot:04d}_x*.npy"))


def _record_path(records_dir: Path, cls: str, slot: int) -> Path:
    return records_dir / f"{cls}_{slot:04d}.json"


def calibrate_or_load(path: Path, coverage: float, profile: str, force: bool) -> BreezeVerifierV2:
    if path.exists() and not force:
        return BreezeVerifierV2.load(path)
    Xtr, ytr, btr = load_file_split("train", MAIN_COND)
    verifier = BreezeVerifierV2(coverage=coverage, profile=profile)
    verifier.calibrate(Xtr.astype(np.float32), ytr, MAIN_COND, bearings=btr)
    path.parent.mkdir(parents=True, exist_ok=True)
    verifier.save(path)
    return verifier


def rescreen_slot(slot_json: Path, run_dir: Path, records_dir: Path, verifier: BreezeVerifierV2, max_k: int, force: bool) -> dict:
    data = json.loads(slot_json.read_text())
    cls = data["class"]
    slot = int(data["slot"])
    out_path = _record_path(records_dir, cls, slot)
    if out_path.exists() and not force:
        return json.loads(out_path.read_text())

    candidates = []
    selected = None
    for h in data.get("history", []):
        rnd = int(h.get("round", -1))
        if rnd < 0 or rnd > max_k or "recipe" not in h:
            continue
        npy = _round_path(run_dir, cls, slot, rnd)
        if not npy.exists():
            candidates.append({"round": rnd, "kind": "round", "path": str(npy), "missing": True})
            continue
        w = np.load(npy)
        rep = verifier.verify(w, cls)
        rec = {
            "round": rnd,
            "kind": "round",
            "path": str(npy),
            "feasible": bool(rep["feasible"]),
            "gates": {k: v["passed"] for k, v in rep["gates"].items()},
            "messages": [
                m
                for gate in rep["gates"].values()
                if not gate.get("passed", True)
                for m in gate.get("messages", [])
            ],
            "notes": [
                m
                for gate in rep["gates"].values()
                if gate.get("passed", True)
                for m in gate.get("messages", [])
            ],
            "scores": rep.get("scores", {}),
        }
        candidates.append(rec)
        if selected is None and rep["feasible"]:
            selected = rec

    expansions = []
    if selected is not None:
        for p in _expansion_paths(run_dir, cls, slot):
            w = np.load(p)
            rep = verifier.verify(w, cls)
            expansions.append({
                "kind": "expansion",
                "path": str(p),
                "feasible": bool(rep["feasible"]),
                "gates": {k: v["passed"] for k, v in rep["gates"].items()},
                "messages": [
                    m
                    for gate in rep["gates"].values()
                    if not gate.get("passed", True)
                    for m in gate.get("messages", [])
                ],
                "notes": [
                    m
                    for gate in rep["gates"].values()
                    if gate.get("passed", True)
                    for m in gate.get("messages", [])
                ],
                "scores": rep.get("scores", {}),
            })

    record = {
        "class": cls,
        "slot": slot,
        "source_json": str(slot_json),
        "selected": selected,
        "candidates": candidates,
        "expansions": expansions,
    }
    out_path.write_text(json.dumps(record, indent=2))
    return record


def _diversity_keep(records: list[dict], verifier: BreezeVerifierV2, pctl: float) -> tuple[list[dict], dict]:
    """Pool-level diversity over expanded physical embeddings."""
    Xr, yr, _ = load_file_split("train", MAIN_COND)
    accepted = []
    for rec in records:
        if rec["selected"] is None:
            continue
        accepted.append({
            "class": rec["class"],
            "slot": rec["slot"],
            "kind": "selected",
            "source": rec["selected"]["path"],
        })
        for exp in rec["expansions"]:
            if exp["feasible"]:
                accepted.append({
                    "class": rec["class"],
                    "slot": rec["slot"],
                    "kind": "expansion",
                    "source": exp["path"],
                })

    summary = {}
    kept = []
    for cls in CLASSES:
        items = [a for a in accepted if a["class"] == cls]
        if not items:
            summary[cls] = {"before": 0, "after": 0, "threshold": None}
            continue
        ci = CLASSES.index(cls)
        real_idx = np.where(yr == ci)[0]
        Fr = np.array([physical_embedding(Xr[i], cls, verifier.calib) for i in real_idx])
        mu, sd = Fr.mean(axis=0), Fr.std(axis=0) + 1e-9
        Zr = (Fr - mu) / sd
        Dr = np.sqrt(((Zr[:, None] - Zr[None]) ** 2).sum(-1))
        np.fill_diagonal(Dr, np.inf)
        threshold = float(np.percentile(Dr.min(axis=1), pctl))
        selected_idx = []
        Zi = []
        for item in items:
            w = np.load(item["source"])
            z = (physical_embedding(w, cls, verifier.calib) - mu) / sd
            if not selected_idx:
                selected_idx.append(item)
                Zi.append(z)
                continue
            dist = min(float(np.sqrt(((z - prev) ** 2).sum())) for prev in Zi)
            if dist >= threshold:
                selected_idx.append(item)
                Zi.append(z)
        kept.extend(selected_idx)
        summary[cls] = {"before": len(items), "after": len(selected_idx), "threshold": threshold}
    return kept, summary


def write_outputs(records: list[dict], kept: list[dict], diversity_summary: dict, out_dir: Path):
    manifest = out_dir / "accepted_manifest.csv"
    kept_sources = {k["source"] for k in kept}
    with manifest.open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["class", "slot", "kind", "source", "kept_after_diversity"])
        for rec in records:
            if rec["selected"] is not None:
                wr.writerow([rec["class"], rec["slot"], "selected", rec["selected"]["path"], rec["selected"]["path"] in kept_sources])
            for exp in rec["expansions"]:
                if exp["feasible"]:
                    wr.writerow([rec["class"], rec["slot"], "expansion", exp["path"], exp["path"] in kept_sources])

    rows = []
    for rec in records:
        rows.append({
            "class": rec["class"],
            "slot": rec["slot"],
            "accepted_before_diversity": rec["selected"] is not None,
            "n_candidates": len([c for c in rec["candidates"] if not c.get("missing")]),
            "n_feasible_expansions": sum(e["feasible"] for e in rec["expansions"]),
        })
    with (out_dir / "slot_summary.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["class", "slot"])
        wr.writeheader()
        wr.writerows(rows)

    X, y = [], []
    for item in kept:
        X.append(np.load(item["source"]))
        y.append(CLASSES.index(item["class"]))
    if X:
        np.savez_compressed(out_dir / "pool_v2.npz", X=np.stack(X).astype(np.float32), y=np.array(y, dtype=np.int64))
    else:
        np.savez_compressed(out_dir / "pool_v2.npz", X=np.zeros((0, 3, 2048), dtype=np.float32), y=np.zeros(0, dtype=np.int64))

    summary = {
        "slots": len(records),
        "accepted_slots_before_diversity": sum(r["selected"] is not None for r in records),
        "accepted_items_before_diversity": sum(1 for _ in csv.DictReader(manifest.open())) if manifest.exists() else 0,
        "kept_after_diversity": len(kept),
        "kept_by_class": dict(Counter(k["class"] for k in kept)),
        "diversity": diversity_summary,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(RUNS_DIR / "pool_physics_file_k3"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--coverage", type=float, default=0.90)
    ap.add_argument("--profile", default="soft_w1", choices=["soft_w1", "soft_only", "w1_only"])
    ap.add_argument("--slots-per-class", type=int, default=None)
    ap.add_argument("--classes", nargs="+", default=CLASSES)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--diversity-pctl", type=float, default=1.0)
    ap.add_argument("--calib-path", default=None,
                    help="optional shared v2 calibration JSON path; defaults to --out")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--force-calib", action="store_true")
    args = ap.parse_args()

    run_dir = Path(args.run)
    out_dir = Path(args.out)
    records_dir = out_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    calib_path = Path(args.calib_path) if args.calib_path else out_dir / f"verifier_v2_{MAIN_COND}_c{int(args.coverage * 100)}_{args.profile}.json"
    verifier = calibrate_or_load(calib_path, args.coverage, args.profile, force=args.force_calib)

    slot_jsons = _load_slot_jsons(run_dir, args.classes, args.slots_per_class)
    records = []
    for i, slot_json in enumerate(slot_jsons, 1):
        records.append(rescreen_slot(slot_json, run_dir, records_dir, verifier, args.k, args.force))
        if i % 10 == 0:
            acc = sum(r["selected"] is not None for r in records) / len(records)
            print(f"{i}/{len(slot_jsons)} slots screened, accepted before diversity={acc:.3f}", flush=True)

    kept, diversity_summary = _diversity_keep(records, verifier, args.diversity_pctl)
    summary = write_outputs(records, kept, diversity_summary, out_dir)
    print(json.dumps(summary, indent=2))
    if RESULTS_DIR.exists():
        latest = RESULTS_DIR / "rescreen_v2_latest.txt"
        latest.write_text(str(out_dir.resolve()))


if __name__ == "__main__":
    main()
