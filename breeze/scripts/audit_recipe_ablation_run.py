"""Reproduce and audit a non-LLM recipe-ablation run from recipes and seeds."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RUNS = BREEZE / "runs"
sys.path.insert(0, str(BREEZE / "src"))
sys.path.insert(0, str(BREEZE / "scripts"))

from config import CLASSES, MAIN_COND
from data import load_file_split
from recipe_ablation import diversity_mask, stable_seed
from renderer import render
from verifier.v2 import BreezeVerifierV2


RECORD_RE = re.compile(r"(healthy|OR|IR)_(\d{4})\.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_hash(root: Path) -> tuple[str, int, int]:
    digest = hashlib.sha256()
    paths = sorted(path for path in root.rglob("*") if path.is_file())
    total_bytes = 0
    for path in paths:
        total_bytes += path.stat().st_size
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), len(paths), total_bytes


def audit(root: Path, source: str, cond: str) -> dict[str, Any]:
    record_paths = sorted(path for path in root.glob("*.json") if RECORD_RE.fullmatch(path.name))
    if not record_paths:
        raise AssertionError(f"no slot records in {root}")
    verifier_path = RUNS / f"verifier_v2_{cond}_c90_soft_w1.json"
    verifier = BreezeVerifierV2.load(verifier_path)
    Xtr, ytr, _ = load_file_split("train", cond)
    Xtr = Xtr.astype(np.float32)

    all_windows: list[np.ndarray] = []
    all_labels: list[int] = []
    slot_keys: set[tuple[str, int]] = set()
    admitted = 0
    expansion_count = 0
    for record_path in record_paths:
        record = json.loads(record_path.read_text())
        cls = str(record["class"])
        slot = int(record["slot"])
        key = (cls, slot)
        if key in slot_keys:
            raise AssertionError(f"duplicate slot {key}")
        slot_keys.add(key)
        if record.get("source") != source:
            raise AssertionError(f"source mismatch in {record_path}")
        history = record.get("history", [])
        if len(history) != 1 or "recipe" not in history[0]:
            raise AssertionError(f"expected one saved recipe in {record_path}")
        recipe = history[0]["recipe"]
        expected = render(recipe, stable_seed(f"{source}:{cls}:{slot}:0"))
        r0_path = root / f"{cls}_{slot:04d}_r0.npy"
        observed = np.load(r0_path)
        if not np.array_equal(expected, observed):
            raise AssertionError(f"primary waveform is not reproducible: {r0_path}")
        report = verifier.verify(observed, cls)
        accepted = bool(record.get("accepted"))
        if accepted != bool(report["feasible"]):
            raise AssertionError(f"feasibility mismatch in {record_path}")
        archived_gates = history[0].get("gate_pass", {})
        replayed_gates = {name: bool(entry["passed"]) for name, entry in report["gates"].items()}
        if archived_gates != replayed_gates:
            raise AssertionError(f"gate replay mismatch in {record_path}")

        if accepted:
            admitted += 1
            selected_path = root / f"{cls}_{slot:04d}.npy"
            if not np.array_equal(np.load(selected_path), observed):
                raise AssertionError(f"selected waveform differs from r0: {selected_path}")
            all_windows.append(observed)
            all_labels.append(CLASSES.index(cls))
            feasible_expansions: list[np.ndarray] = []
            for sub in range(1, 13):
                candidate = render(recipe, stable_seed(f"{source}:{cls}:{slot}:x:{sub}"))
                if verifier.verify(candidate, cls)["feasible"]:
                    feasible_expansions.append(candidate)
                if len(feasible_expansions) == 4:
                    break
            archived_expansions = sorted(root.glob(f"{cls}_{slot:04d}_x*.npy"))
            if len(archived_expansions) != len(feasible_expansions):
                raise AssertionError(f"expansion count mismatch for {key}")
            for index, (path, candidate) in enumerate(zip(archived_expansions, feasible_expansions)):
                if path.name != f"{cls}_{slot:04d}_x{index}.npy" or not np.array_equal(np.load(path), candidate):
                    raise AssertionError(f"expansion replay mismatch: {path}")
                all_windows.append(candidate)
                all_labels.append(CLASSES.index(cls))
                expansion_count += 1
        elif (root / f"{cls}_{slot:04d}.npy").exists():
            raise AssertionError(f"rejected slot has a selected waveform: {key}")

    X = np.stack(all_windows).astype(np.float32) if all_windows else np.zeros((0, 3, 2048), dtype=np.float32)
    y = np.asarray(all_labels, dtype=np.int64)
    keep = diversity_mask(X, y, Xtr, ytr) if len(X) else np.zeros(0, dtype=bool)
    expected_X, expected_y = X[keep], y[keep]
    pool = np.load(root / "pool_v2.npz")
    if not np.array_equal(pool["X"], expected_X) or not np.array_equal(pool["y"], expected_y):
        raise AssertionError("pool_v2.npz does not match deterministic replay plus diversity admission")

    digest, file_count, total_bytes = manifest_hash(root)
    return {
        "schema_version": 1,
        "run_root": str(root.relative_to(ROOT)),
        "source": source,
        "condition": cond,
        "data_access": "load_file_split('train') only",
        "verifier": str(verifier_path.relative_to(ROOT)),
        "verifier_sha256": sha256(verifier_path),
        "slots": len(record_paths),
        "saved_recipe_proposals": len(record_paths),
        "admitted_slots": admitted,
        "feasible_expansions": expansion_count,
        "items_before_diversity": len(X),
        "items_after_diversity": len(expected_X),
        "class_counts_after_diversity": {
            cls: int(np.sum(expected_y == index)) for index, cls in enumerate(CLASSES)
        },
        "all_primary_waveforms_exactly_reproduced": True,
        "all_gate_decisions_replayed": True,
        "all_expansions_exactly_reproduced": True,
        "pool_exactly_rebuilt": True,
        "run_manifest_sha256": digest,
        "run_file_count": file_count,
        "run_bytes": total_bytes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--source", choices=["random", "rule", "empirical"], required=True)
    parser.add_argument("--cond", default=MAIN_COND)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = audit(args.run_root.resolve(), args.source, args.cond)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
