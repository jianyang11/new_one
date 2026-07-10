"""Zero-API rerendering of accepted Berkeley LLM recipes with band EQ.

The script consumes existing accepted LLM slot JSON files, re-expands their
compact recipes against the current inner-train verifier, renders new windows,
and admits only samples that pass the same train-only verifier.
"""

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
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "scripts"))

from milling_generation import (  # noqa: E402
    BERKELEY,
    MillingVerifier,
    attach_renderer_profile,
    build_pool,
    cfg_from_train_npz,
    discriminative_template_candidates,
    expand_llm_recipe,
    feature_vector,
    load_train,
    render_recipe,
    stable_seed,
    tolist,
)


def load_slot_recipe(path: Path) -> tuple[str, int, dict[str, Any] | None]:
    rec = json.loads(path.read_text())
    cls = str(rec["class"])
    slot = int(rec["slot"])
    for hist in rec.get("history", []):
        recipe = hist.get("recipe")
        if not recipe:
            continue
        compact = recipe.get("_compact_recipe")
        return cls, slot, compact if isinstance(compact, dict) else recipe
    return cls, slot, None


def parse_class_map(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"class-map item must be old:new, got {item!r}")
        old, new = item.split(":", 1)
        out[old.strip()] = new.strip()
    return out


def prepare_compact_recipe(
    recipe: dict[str, Any],
    n_ch: int,
    template_policy: str,
    high_margin_idx: int | None = None,
) -> dict[str, Any]:
    out = json.loads(json.dumps(tolist(recipe)))
    if template_policy == "keep":
        return out
    try:
        template_idx = int(out.get("template_index", 0))
    except (TypeError, ValueError):
        template_idx = 0
    if high_margin_idx is not None:
        template_idx = int(high_margin_idx)
    if template_policy in {"coherent", "full_train_margin"}:
        out["template_index"] = template_idx
        out["template_indices"] = [template_idx] * n_ch
    elif template_policy == "high_margin_coherent":
        out["template_index"] = template_idx
        out["template_indices"] = [template_idx] * n_ch
    return out


def rank_full_train_templates(
    cfg: Any,
    verifier: MillingVerifier,
    X: np.ndarray,
    y: np.ndarray,
) -> dict[str, list[tuple[int, np.ndarray]]]:
    ranked: dict[str, list[tuple[int, np.ndarray]]] = {}
    for ci, cls in enumerate(cfg.classes):
        rows = []
        for idx in np.where(y == ci)[0]:
            w = X[int(idx)]
            fv = feature_vector(w, cfg)
            dists = []
            for other in cfg.classes:
                gate = verifier.calib["classes_calib"][other]["feature_axis"]
                med = np.asarray(gate["median"], dtype=float)
                scale = np.asarray(gate["scale"], dtype=float)
                dists.append(float(np.sqrt((((fv - med) / scale) ** 2).sum())))
            own = dists[ci]
            other = min(dists[:ci] + dists[ci + 1 :])
            rows.append((other - own, -own, int(idx), w))
        rows.sort(reverse=True, key=lambda r: (r[0], r[1], -r[2]))
        ranked[cls] = [(idx, w) for _, _, idx, w in rows]
    return ranked


def run_rerender(
    source_dirs: list[Path],
    out_dir: Path,
    train_npz: Path,
    eq_strength: float,
    template_policy: str,
    llm_mode: str,
    expansions: int,
    class_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    cfg = cfg_from_train_npz(BERKELEY, train_npz)
    X, y = load_train(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    verifier = MillingVerifier(cfg, coverage=0.90)
    verifier.calibrate(X, y)
    verifier.save(out_dir / "verifier_c90.json")
    full_train_templates = rank_full_train_templates(cfg, verifier, X, y) if template_policy == "full_train_margin" else {}

    slot_rows = []
    for src_i, source_dir in enumerate(source_dirs):
        tag = f"s{src_i}_{source_dir.parent.parent.name}_{source_dir.parent.name}_{source_dir.name}"
        for path in sorted(source_dir.glob("llm_*.json")):
            src_cls, slot, compact = load_slot_recipe(path)
            cls = (class_map or {}).get(src_cls, src_cls)
            if cls not in cfg.classes:
                continue
            rec_name = f"{tag}_{cls}_{slot:04d}"
            rec_path = out_dir / f"{rec_name}.json"
            if rec_path.exists():
                slot_rows.append(json.loads(rec_path.read_text()))
                continue
            accepted_paths = []
            reports = []
            if compact is None:
                recipe = None
            else:
                high_margin_idx = None
                if template_policy == "high_margin_coherent":
                    candidates = discriminative_template_candidates(cfg, verifier, cls, max_items=24)
                    if candidates:
                        high_margin_idx = int(candidates[(slot + src_i * 7) % len(candidates)]["idx"])
                prepared = prepare_compact_recipe(compact, len(cfg.channels), template_policy, high_margin_idx)
                recipe = expand_llm_recipe(prepared, cfg, verifier, cls, slot + 1000 * src_i, llm_mode)
            if recipe is not None:
                recipe["band_eq_strength"] = float(eq_strength)
                recipe["_rerender_source_json"] = str(path.relative_to(ROOT))
                recipe["_template_policy"] = template_policy
                recipe = attach_renderer_profile(recipe, verifier, cls)
                for exp in range(expansions):
                    recipe_exp = recipe
                    template_ref = None
                    if template_policy == "full_train_margin":
                        bank = full_train_templates[cls]
                        template_idx, template = bank[(slot * expansions + exp + src_i * 101) % len(bank)]
                        recipe_exp = json.loads(json.dumps(tolist(recipe)))
                        recipe_exp["_iaaft_template"] = template
                        template_ref = int(template_idx)
                    seed = stable_seed(cfg.name, "llm_eq_rerender", tag, cls, slot, exp, eq_strength, template_policy)
                    w = render_recipe(recipe_exp, cfg, seed)
                    report = verifier.verify(w, cls)
                    if template_ref is not None:
                        report["template_idx"] = template_ref
                    reports.append(report)
                    if report["feasible"]:
                        rel = out_dir / f"{rec_name}_e{exp}.npy"
                        np.save(rel, w)
                        accepted_paths.append(str(rel.relative_to(ROOT)))
            row = {
                "source": "llm",
                "class": cls,
                "source_class": src_cls,
                "slot": int(slot + 1000 * src_i),
                "accepted": bool(accepted_paths),
                "accepted_paths": accepted_paths,
                "history": [
                    {
                        "round": 0,
                        "recipe": recipe,
                        "n_feasible": len(accepted_paths),
                        "reports": reports,
                    }
                ],
                "rerender_source_json": str(path.relative_to(ROOT)),
            }
            rec_path.write_text(json.dumps(tolist(row), indent=2) + "\n")
            slot_rows.append(row)

    summary = build_pool(cfg, out_dir)
    summary.update(
        {
            "api_requests": 0,
            "eq_strength": float(eq_strength),
            "template_policy": template_policy,
            "llm_mode": llm_mode,
            "expansions": int(expansions),
            "source_dirs": [str(p.relative_to(ROOT)) for p in source_dirs],
        }
    )
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2) + "\n")
    with (out_dir / "slot_summary.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["source_json", "source_class", "class", "slot", "accepted", "n_feasible"],
        )
        writer.writeheader()
        for row in slot_rows:
            writer.writerow(
                {
                    "source_json": row.get("rerender_source_json", ""),
                    "class": row["class"],
                    "source_class": row.get("source_class", row["class"]),
                    "slot": row["slot"],
                    "accepted": bool(row["accepted"]),
                    "n_feasible": len(row.get("accepted_paths", [])),
                }
            )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dirs", nargs="+", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--train-npz", default="proc/milling_berkeley_inner_train.npz")
    parser.add_argument("--eq-strength", type=float, default=0.75)
    parser.add_argument("--template-policy", choices=["keep", "coherent", "high_margin_coherent", "full_train_margin"], default="coherent")
    parser.add_argument("--llm-mode", choices=["standard", "contrastive", "repair"], default="contrastive")
    parser.add_argument("--expansions", type=int, default=5)
    parser.add_argument("--class-map", default="", help="Comma-separated source:target labels, e.g. sharp:healthy,worn:degradation,severe:failure")
    args = parser.parse_args()

    source_dirs = []
    for raw in args.source_dirs:
        p = Path(raw)
        if not p.is_absolute():
            p = ROOT / p
        source_dirs.append(p)
    train_npz = Path(args.train_npz)
    if not train_npz.is_absolute():
        train_npz = ROOT / train_npz
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    summary = run_rerender(
        source_dirs=source_dirs,
        out_dir=out_dir,
        train_npz=train_npz,
        eq_strength=args.eq_strength,
        template_policy=args.template_policy,
        llm_mode=args.llm_mode,
        expansions=args.expansions,
        class_map=parse_class_map(args.class_map) if args.class_map.strip() else None,
    )
    print(json.dumps(tolist(summary), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
