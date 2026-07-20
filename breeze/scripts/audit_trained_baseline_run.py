"""Strict completeness and integrity audit for a trained-baseline result root."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
MODEL_SOURCE = ROOT / "breeze" / "src" / "trained_baselines.py"
RUNNER_SOURCE = ROOT / "breeze" / "scripts" / "run_trained_baselines.py"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def require_unique(rows: list[dict[str, str]], fields: tuple[str, ...], label: str) -> None:
    keys = [tuple(row[field] for field in fields) for row in rows]
    if len(keys) != len(set(keys)):
        duplicates = [key for key, count in Counter(keys).items() if count > 1]
        raise AssertionError(f"duplicate {label} keys: {duplicates[:5]}")


def resolve_recorded_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def write_atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def audit(root: Path) -> dict[str, object]:
    root = root.resolve()
    manifest = json.loads((root / "run_manifest.json").read_text())
    methods = [str(value) for value in manifest["methods"]]
    train_modes = [str(value) for value in manifest["train_modes"]]
    shot_levels = [int(value) for value in manifest["n_real"]]
    seeds = int(manifest["seeds"])
    n_classes = 3
    n_syn_per_class = int(manifest["n_syn_per_class"])

    expected_downstream = len(methods) * len(train_modes) * len(shot_levels) * seeds
    expected_cost = 0
    if "full_train" in train_modes:
        expected_cost += len(methods) * seeds * n_classes
    if "few_shot" in train_modes:
        expected_cost += len(methods) * seeds * len(shot_levels) * n_classes

    downstream = read_csv(root / "pu_file_trained_baselines.csv")
    costs = read_csv(root / "training_cost.csv")
    dynamics = read_csv(root / "training_dynamics.csv")
    require_unique(downstream, ("method", "train_mode", "n_real", "seed"), "downstream")
    require_unique(costs, ("method", "train_mode", "n_real", "seed", "class_id"), "cost")
    require_unique(
        dynamics,
        ("method", "train_mode", "n_real", "seed", "class_id", "stage", "epoch"),
        "dynamics",
    )
    if len(downstream) != expected_downstream:
        raise AssertionError(f"downstream rows {len(downstream)} != expected {expected_downstream}")
    if len(costs) != expected_cost:
        raise AssertionError(f"cost rows {len(costs)} != expected {expected_cost}")

    failure_path = root / "training_failures.csv"
    failures = read_csv(failure_path) if failure_path.exists() else []
    if failures:
        raise AssertionError(f"run contains {len(failures)} recorded training failures")

    for row in downstream:
        for metric in ("acc", "macro_f1", "generator_train_seconds"):
            if not math.isfinite(float(row[metric])):
                raise AssertionError(f"non-finite downstream {metric}: {row}")
        pool_path = resolve_recorded_path(row["pool_path"])
        if file_sha256(pool_path) != row["pool_sha256"]:
            raise AssertionError(f"pool hash mismatch: {pool_path}")
        with np.load(pool_path, allow_pickle=False) as pool:
            x = pool["X"]
            y = pool["y"]
            if x.shape != (n_syn_per_class * n_classes, 3, 2048):
                raise AssertionError(f"unexpected pool shape {x.shape}: {pool_path}")
            if not np.isfinite(x).all():
                raise AssertionError(f"non-finite pool: {pool_path}")
            counts = np.bincount(y.astype(np.int64), minlength=n_classes)
            if counts.tolist() != [n_syn_per_class] * n_classes:
                raise AssertionError(f"class support mismatch {counts.tolist()}: {pool_path}")
        if int(row["n_syn"]) != n_syn_per_class * n_classes:
            raise AssertionError(f"downstream n_syn mismatch: {row}")

    for row in costs:
        wall_seconds = float(row["wall_seconds"])
        if not math.isfinite(wall_seconds) or wall_seconds < 0:
            raise AssertionError(f"invalid wall time: {row}")
        checkpoint = resolve_recorded_path(row["checkpoint"])
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        if row["method"] == "timegan":
            complete = state.get("stage") == "complete"
        elif row["method"] == "ddpm":
            complete = int(state.get("completed_epoch", -1)) == int(state["config"]["epochs"])
        else:
            raise AssertionError(f"unknown method in cost row: {row['method']}")
        if not complete:
            raise AssertionError(f"incomplete checkpoint: {checkpoint}")

    metric_fields = (
        "reconstruction_loss",
        "supervisor_loss",
        "discriminator_loss",
        "generator_loss",
        "noise_prediction_mse",
    )
    for row in dynamics:
        values = [float(row[field]) for field in metric_fields if row.get(field) not in (None, "")]
        if not values or not all(math.isfinite(value) for value in values):
            raise AssertionError(f"empty or non-finite dynamics row: {row}")

    pool_keys: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
    for row in downstream:
        training_n = "0" if row["train_mode"] == "full_train" else row["n_real"]
        key = (row["method"], row["train_mode"], row["seed"])
        pool_keys.setdefault(key, set()).add((training_n, row["pool_sha256"]))
    for (method, mode, seed), values in pool_keys.items():
        expected = 1 if mode == "full_train" else len(shot_levels)
        if len(values) != expected:
            raise AssertionError(
                f"pool reuse mismatch for {(method, mode, seed)}: {len(values)} != {expected}"
            )

    expected_sources = {
        "runner_sha256": file_sha256(RUNNER_SOURCE),
        "models_sha256": file_sha256(MODEL_SOURCE),
    }
    if manifest["source_scripts"] != expected_sources:
        raise AssertionError(
            f"source hash mismatch: recorded={manifest['source_scripts']} current={expected_sources}"
        )

    heartbeat = [json.loads(line) for line in (root / "heartbeat.jsonl").read_text().splitlines() if line]
    if not heartbeat or heartbeat[-1].get("event") != "formal_run_completed":
        raise AssertionError("heartbeat does not end with formal_run_completed")

    unique_pools = {(row["pool_path"], row["pool_sha256"]) for row in downstream}
    return {
        "status": "PASS",
        "root": str(root),
        "smoke": bool(manifest["smoke"]),
        "downstream_rows": len(downstream),
        "cost_rows": len(costs),
        "dynamics_rows": len(dynamics),
        "failure_rows": len(failures),
        "unique_pools": len(unique_pools),
        "source_scripts": expected_sources,
        "ddpm_schedule": manifest.get("ddpm_schedule"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root)
    output = args.output or args.root / "completeness_audit.json"
    write_atomic_json(output, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
