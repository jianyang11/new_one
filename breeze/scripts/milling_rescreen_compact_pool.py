"""Re-expand saved compact milling LLM recipes without new API calls."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "scripts"))

import milling_generation as mg  # noqa: E402


def tolist(x: Any) -> Any:
    return mg.tolist(x)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-roots", nargs="+", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--train-npz", default="", help="Override calibration/training NPZ; relative paths are resolved from the project root.")
    parser.add_argument("--expansions", type=int, default=5)
    parser.add_argument("--max-slots-per-class", type=int, default=9999)
    parser.add_argument("--llm-mode", choices=["standard", "contrastive"], default="standard")
    args = parser.parse_args()

    cfg = mg.BERKELEY
    if args.train_npz.strip():
        train_npz = Path(args.train_npz)
        if not train_npz.is_absolute():
            train_npz = ROOT / train_npz
        cfg = replace(mg.BERKELEY, train_npz=train_npz)
    X, y = mg.load_train(cfg)
    verifier = mg.MillingVerifier(cfg, coverage=0.90)
    verifier.calibrate(X, y)

    out_dir = ROOT / args.out_root / cfg.name / "llm_rescreen"
    out_dir.mkdir(parents=True, exist_ok=True)
    verifier.save(out_dir / "verifier_c90.json")

    used_by_class = {cls: 0 for cls in cfg.classes}
    records = []
    xs, ys, manifest = [], [], []

    for root_s in args.source_roots:
        root = ROOT / root_s
        for p in sorted(root.glob("llm_*.json")):
            saved = json.loads(p.read_text())
            cls = saved.get("class")
            if cls not in cfg.classes or used_by_class[cls] >= args.max_slots_per_class:
                continue
            slot = int(saved.get("slot", used_by_class[cls]))
            accepted_paths = []
            history = []
            for h in saved.get("history", []):
                compact = h.get("recipe", {}).get("_compact_recipe")
                if compact is None:
                    continue
                recipe = mg.expand_llm_recipe(compact, cfg, verifier, cls, slot, args.llm_mode)
                if recipe is None:
                    continue
                reports = []
                paths = []
                round_id = int(h.get("round", 0))
                for exp in range(args.expansions):
                    seed = mg.stable_seed("milling_rescreen", str(p), round_id, exp)
                    w = mg.render_recipe(recipe, cfg, seed)
                    report = verifier.verify(w, cls)
                    reports.append(report)
                    if report["feasible"]:
                        name = f"rescreen_{cls}_{used_by_class[cls]:04d}_r{round_id}_e{exp}.npy"
                        path = out_dir / name
                        np.save(path, w)
                        rel = str(path.relative_to(ROOT))
                        paths.append(rel)
                        xs.append(w)
                        ys.append(cfg.classes.index(cls))
                        manifest.append(
                            {
                                "source": "llm_rescreen",
                                "class": cls,
                                "slot": used_by_class[cls],
                                "path": rel,
                                "source_json": str(p.relative_to(ROOT)),
                            }
                        )
                history.append({"round": round_id, "compact_recipe": compact, "recipe": recipe, "n_feasible": len(paths), "reports": reports})
                if paths:
                    accepted_paths.extend(paths)
                    break
            rec = {
                "source": "llm_rescreen",
                "class": cls,
                "slot": used_by_class[cls],
                "source_json": str(p.relative_to(ROOT)),
                "accepted": bool(accepted_paths),
                "accepted_paths": accepted_paths,
                "history": history,
            }
            rec_path = out_dir / f"rescreen_{cls}_{used_by_class[cls]:04d}.json"
            rec_path.write_text(json.dumps(tolist(rec), indent=2) + "\n")
            records.append(rec)
            used_by_class[cls] += 1

    if xs:
        Xsyn = np.stack(xs).astype(np.float32)
        ysyn = np.asarray(ys, dtype=np.int64)
    else:
        Xsyn = np.zeros((0, len(cfg.channels), cfg.window), dtype=np.float32)
        ysyn = np.zeros((0,), dtype=np.int64)
    np.savez_compressed(out_dir / "pool.npz", X=Xsyn, y=ysyn, class_names=np.asarray(cfg.classes))
    with (out_dir / "manifest.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "class", "slot", "path", "source_json"])
        writer.writeheader()
        writer.writerows(manifest)
    summary = {
        "api_requests": 0,
        "slots": len(records),
        "accepted_slots": int(sum(r["accepted"] for r in records)),
        "n": int(len(ysyn)),
        "counts": {cfg.classes[i]: int((ysyn == i).sum()) for i in range(len(cfg.classes))},
        "source_roots": args.source_roots,
        "out_dir": str(out_dir.relative_to(ROOT)),
    }
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2) + "\n")
    print(json.dumps(tolist(summary), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
