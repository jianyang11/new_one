"""PU LOCO small-batch LLM generation smoke.

This script is intentionally serial and checkpointed. It reads the provider
key only from ``DASHSCOPE_API_KEY`` and never writes it to disk.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

import sys

ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "src"))
sys.path.insert(0, str(BREEZE / "scripts"))

import llm  # noqa: E402
from build_pu_loco_pools import (  # noqa: E402
    CLASSES,
    CONDITIONS,
    calibrate_verifier,
    gate_pass,
    load_condition,
    target_rate,
    tolist,
    violations,
)
from config import LLM_BASE_URL, LLM_MODEL, LLM_MIN_INTERVAL, fault_freqs  # noqa: E402
from pipeline import exemplar_description  # noqa: E402
from renderer import render  # noqa: E402
from recipe_ablation import diversity_mask, stable_seed  # noqa: E402


def validate_recipe(recipe: dict[str, Any] | None) -> list[str]:
    if recipe is None:
        return ["parse_failed"]
    problems: list[str] = []
    for key in ("fr_hz", "target_rms", "impacts", "background", "currents"):
        if key not in recipe:
            problems.append(f"missing {key}")
    if "impacts" in recipe:
        for key in ("rate_hz", "amp", "decay_ms", "resonance_hz", "jitter_pct", "amp_var_pct", "modulation"):
            if key not in recipe["impacts"]:
                problems.append(f"missing impacts.{key}")
    if "background" in recipe:
        bg = recipe["background"]
        for key in ("noise_rms", "band_weights", "components", "random_impulses"):
            if key not in bg:
                problems.append(f"missing background.{key}")
        weights = bg.get("band_weights", [])
        if not isinstance(weights, list) or len(weights) != 8:
            problems.append("background.band_weights length must be 8")
    return problems


class ApiBudgetExceeded(RuntimeError):
    pass


def chat(messages: list[dict[str, str]], max_api_requests: int, counter: dict[str, int], temperature: float, max_tokens: int) -> tuple[str, dict[str, Any]]:
    if counter["requests"] >= max_api_requests:
        raise ApiBudgetExceeded(f"max_api_requests reached: {max_api_requests}")
    text = llm.chat(messages, temperature=temperature, max_retries=3, max_tokens=max_tokens)
    counter["requests"] += 1
    return text, {}


def conditionize(recipe: dict[str, Any], cls: str, cond: str) -> dict[str, Any]:
    freqs = fault_freqs(CONDITIONS[cond][0] / 60.0)
    out = json.loads(json.dumps(recipe))
    out["fr_hz"] = float(freqs["fr"])
    rate = target_rate(cls, freqs)
    if "impacts" in out:
        out["impacts"]["rate_hz"] = rate
    if "currents" in out:
        out["currents"]["fault_freq_hz"] = rate
    return out


def choose_bearing(bearings: np.ndarray, y: np.ndarray, cls: str, slot: int) -> str:
    ci = CLASSES.index(cls)
    vals = sorted(set(str(x) for x in bearings[y == ci]))
    if not vals:
        raise RuntimeError(f"no bearings for {cls}")
    return vals[slot % len(vals)]


def run_slot(
    out_dir: Path,
    heldout: str,
    cond: str,
    cls: str,
    slot: int,
    Xc: np.ndarray,
    yc: np.ndarray,
    bc: np.ndarray,
    verifier: Any,
    max_api_requests: int,
    counter: dict[str, int],
    k: int,
    expansions: int,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    rec_path = out_dir / f"{cond}_{cls}_{slot:04d}.json"
    if rec_path.exists():
        return json.loads(rec_path.read_text())

    freqs = fault_freqs(CONDITIONS[cond][0] / 60.0)
    bearing = choose_bearing(bc, yc, cls, slot)
    exemplar = exemplar_description(Xc, yc, bc, cls, bearing)
    history: list[dict[str, Any]] = []
    feedback: list[str] | None = None
    prev_recipe: dict[str, Any] | None = None
    accepted_paths: list[str] = []
    accepted_reports: list[dict[str, Any]] = []
    raw_response = ""
    api_errors: list[str] = []

    for rnd in range(k + 1):
        prompt = llm.user_prompt(cls, freqs, exemplar, feedback, prev_recipe, basic=False)
        messages = [{"role": "system", "content": llm.SYSTEM}, {"role": "user", "content": prompt}]
        try:
            text, payload = chat(messages, max_api_requests, counter, temperature, max_tokens)
            raw_response = text
        except ApiBudgetExceeded:
            raise
        except Exception as exc:
            api_errors.append(f"{type(exc).__name__}: {exc}")
            history.append({"round": rnd, "error": api_errors[-1]})
            time.sleep(1.0)
            continue
        recipe = llm.parse_recipe(text)
        schema_problems = validate_recipe(recipe)
        if schema_problems:
            feedback = schema_problems
            history.append({"round": rnd, "raw_response": text, "recipe": recipe, "schema_problems": schema_problems})
            prev_recipe = recipe
            continue
        assert recipe is not None
        recipe = conditionize(recipe, cls, cond)
        round_reports: list[dict[str, Any]] = []
        round_paths: list[str] = []
        round_violations: list[str] = []
        for exp in range(expansions):
            seed = stable_seed(f"pu-loco-llm:{heldout}:{cond}:{cls}:{slot}:r{rnd}:e{exp}")
            try:
                w = render(recipe, seed)
                report = verifier.verify(w, cls)
            except Exception as exc:
                round_violations.append(f"render_or_verify_error:{type(exc).__name__}:{exc}")
                continue
            round_reports.append(report)
            if report["feasible"]:
                path = out_dir / f"{cond}_{cls}_{slot:04d}_r{rnd}_e{exp}.npy"
                np.save(path, w)
                round_paths.append(str(path.relative_to(ROOT)))
        history.append(
            {
                "round": rnd,
                "recipe": recipe,
                "schema_problems": [],
                "n_candidates": expansions,
                "n_feasible_expansions": len(round_paths),
                "reports": round_reports,
            }
        )
        if round_paths:
            accepted_paths.extend(round_paths)
            accepted_reports.extend(round_reports)
            break
        if round_reports:
            msgs: list[str] = []
            for report in round_reports[:2]:
                msgs.extend(violations(report))
            feedback = msgs[:10] if msgs else ["Verifier rejected all rendered seeds; adjust statistics, spectrum, and fault-impact evidence toward the real exemplar."]
        else:
            feedback = round_violations[:10] or ["Rendered signal failed before verification; reduce extreme parameter values."]
        prev_recipe = recipe

    rec = {
        "source": "llm",
        "dataset": "PU",
        "heldout": heldout,
        "condition": cond,
        "class": cls,
        "slot": slot,
        "model": LLM_MODEL,
        "base_url": LLM_BASE_URL,
        "min_interval_seconds": LLM_MIN_INTERVAL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "api_errors": api_errors,
        "raw_response": raw_response,
        "accepted": bool(accepted_paths),
        "accepted_paths": accepted_paths,
        "history": history,
        "prompt_bearing": bearing,
    }
    rec_path.write_text(json.dumps(tolist(rec), indent=2) + "\n")
    return rec


def build_pool(out_dir: Path, Xtrain_all: np.ndarray, ytrain_all: np.ndarray) -> dict[str, Any]:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    manifest: list[dict[str, Any]] = []
    slot_rows: list[dict[str, Any]] = []
    for rec_path in sorted(out_dir.glob("*.json")):
        rec = json.loads(rec_path.read_text())
        if rec.get("source") != "llm" or "class" not in rec:
            continue
        cls = rec["class"]
        ci = CLASSES.index(cls)
        slot_rows.append(
            {
                "condition": rec["condition"],
                "class": cls,
                "slot": rec["slot"],
                "accepted": bool(rec.get("accepted")),
                "n_paths": len(rec.get("accepted_paths", [])),
            }
        )
        for rel in rec.get("accepted_paths", []):
            path = ROOT / rel
            xs.append(np.load(path))
            ys.append(ci)
            manifest.append({"condition": rec["condition"], "class": cls, "slot": rec["slot"], "path": rel})
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
        fieldnames = ["condition", "class", "slot", "path", "kept_after_diversity"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest)
    with (out_dir / "slot_summary.csv").open("w", newline="") as f:
        fieldnames = ["condition", "class", "slot", "accepted", "n_paths"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(slot_rows)
    summary = {
        "slots": len(slot_rows),
        "accepted_slots": int(sum(row["accepted"] for row in slot_rows)),
        "accepted_paths_before_diversity": len(manifest),
        "kept_after_diversity": int(len(yk)),
        "kept_counts": {CLASSES[i]: int((yk == i).sum()) for i in range(len(CLASSES))},
        "accepted_by_condition": dict(Counter(row["condition"] for row in manifest)),
    }
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2) + "\n")
    return summary


def existing_slot_index(out_dir: Path) -> dict[tuple[str, str], list[int]]:
    slots: dict[tuple[str, str], list[int]] = {}
    for rec_path in sorted(out_dir.glob("*.json")):
        try:
            rec = json.loads(rec_path.read_text())
        except json.JSONDecodeError:
            continue
        if rec.get("source") != "llm" or "condition" not in rec or "class" not in rec or "slot" not in rec:
            continue
        key = (str(rec["condition"]), str(rec["class"]))
        slots.setdefault(key, []).append(int(rec["slot"]))
    return slots


def accepted_manifest_counts(out_dir: Path) -> dict[tuple[str, str], int]:
    counts: Counter[tuple[str, str]] = Counter()
    manifest = out_dir / "manifest.csv"
    if not manifest.exists():
        return {}
    with manifest.open(newline="") as f:
        for row in csv.DictReader(f):
            if row.get("kept_after_diversity") == "True":
                counts[(row["condition"], row["class"])] += 1
    return dict(counts)


def next_balanced_condition(out_dir: Path, train_conditions: list[str], cls: str) -> str:
    counts = accepted_manifest_counts(out_dir)
    return min(train_conditions, key=lambda cond: (counts.get((cond, cls), 0), cond))


def fill_to_target(
    out_dir: Path,
    heldout: str,
    train_conditions: list[str],
    loaded: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    Xtrain_all: np.ndarray,
    ytrain_all: np.ndarray,
    counter: dict[str, int],
    max_api_requests: int,
    target_kept_per_class: int,
    max_slots_per_class: int,
    k: int,
    expansions: int,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    verifier_cache: dict[str, Any] = {}
    summary = build_pool(out_dir, Xtrain_all, ytrain_all)
    while counter["requests"] < max_api_requests:
        deficits = {
            cls: target_kept_per_class - int(summary["kept_counts"].get(cls, 0))
            for cls in CLASSES
        }
        need = [cls for cls, deficit in deficits.items() if deficit > 0]
        if not need:
            break
        slots = existing_slot_index(out_dir)
        runnable = []
        for cls in need:
            n_existing = sum(len(slots.get((cond, cls), [])) for cond in train_conditions)
            if n_existing < max_slots_per_class:
                runnable.append(cls)
        if not runnable:
            summary["status"] = "target_not_reached_max_slots_per_class"
            return summary
        cls = max(runnable, key=lambda name: (deficits[name], -CLASSES.index(name)))
        cond = next_balanced_condition(out_dir, train_conditions, cls)
        used = slots.get((cond, cls), [])
        slot = (max(used) + 1) if used else 0
        Xc, yc, bc = loaded[cond]
        if cond not in verifier_cache:
            verifier_cache[cond] = calibrate_verifier(cond, Xc, yc, bc, out_dir)
        try:
            run_slot(
                out_dir=out_dir,
                heldout=heldout,
                cond=cond,
                cls=cls,
                slot=slot,
                Xc=Xc,
                yc=yc,
                bc=bc,
                verifier=verifier_cache[cond],
                max_api_requests=max_api_requests,
                counter=counter,
                k=k,
                expansions=expansions,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ApiBudgetExceeded:
            summary = build_pool(out_dir, Xtrain_all, ytrain_all)
            summary["status"] = "target_not_reached_api_cap"
            return summary
        summary = build_pool(out_dir, Xtrain_all, ytrain_all)
    if any(int(summary["kept_counts"].get(cls, 0)) < target_kept_per_class for cls in CLASSES):
        summary["status"] = "target_not_reached_api_cap"
    else:
        summary["status"] = "target_reached"
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", default="breeze/runs/pu_loco_llm_smoke_2026-07-07")
    parser.add_argument("--heldout", default="N09_M07_F10")
    parser.add_argument("--slots-per-class", type=int, default=1)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--expansions", type=int, default=5)
    parser.add_argument("--max-api-requests", type=int, default=30)
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--target-kept-per-class", type=int, default=0)
    parser.add_argument("--max-slots-per-class", type=int, default=60)
    args = parser.parse_args()

    if args.max_api_requests > 0 and not os.environ.get("DASHSCOPE_API_KEY"):
        raise SystemExit("DASHSCOPE_API_KEY is not set")
    if args.heldout not in CONDITIONS:
        raise SystemExit(f"unknown heldout condition: {args.heldout}")

    # llm.API_KEY is initialized at import time.
    if os.environ.get("DASHSCOPE_API_KEY"):
        llm.API_KEY = os.environ["DASHSCOPE_API_KEY"]

    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = ROOT / out_root
    out_dir = (out_root / f"loco_{args.heldout}" / "llm").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    train_conditions = [cond for cond in CONDITIONS if cond != args.heldout]
    loaded = {cond: load_condition(cond) for cond in train_conditions}
    Xtrain_all = np.concatenate([loaded[cond][0] for cond in train_conditions])
    ytrain_all = np.concatenate([loaded[cond][1] for cond in train_conditions])
    counter = {"requests": 0}
    status = "completed"
    try:
        for cond in train_conditions:
            Xc, yc, bc = loaded[cond]
            verifier = calibrate_verifier(cond, Xc, yc, bc, out_dir)
            for cls in CLASSES:
                for slot in range(args.slots_per_class):
                    run_slot(
                        out_dir=out_dir,
                        heldout=args.heldout,
                        cond=cond,
                        cls=cls,
                        slot=slot,
                        Xc=Xc,
                        yc=yc,
                        bc=bc,
                        verifier=verifier,
                        max_api_requests=args.max_api_requests,
                        counter=counter,
                        k=args.k,
                        expansions=args.expansions,
                        temperature=args.temperature,
                        max_tokens=args.max_tokens,
                    )
    except ApiBudgetExceeded as exc:
        status = str(exc)
    if args.target_kept_per_class > 0 and status == "completed":
        summary = fill_to_target(
            out_dir=out_dir,
            heldout=args.heldout,
            train_conditions=train_conditions,
            loaded=loaded,
            Xtrain_all=Xtrain_all,
            ytrain_all=ytrain_all,
            counter=counter,
            max_api_requests=args.max_api_requests,
            target_kept_per_class=args.target_kept_per_class,
            max_slots_per_class=args.max_slots_per_class,
            k=args.k,
            expansions=args.expansions,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    else:
        summary = build_pool(out_dir, Xtrain_all, ytrain_all)
        summary["status"] = status
    summary["actual_api_requests_this_run"] = counter["requests"]
    summary["max_api_requests"] = args.max_api_requests
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2) + "\n")
    print(json.dumps(tolist(summary), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
