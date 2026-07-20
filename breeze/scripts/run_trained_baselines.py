"""Run checkpointed TimeGAN and DDPM baselines on the frozen PU file split.

The runner enforces the following boundary:

* only ``load_file_split('train', 'N09_M07_F10')`` can reach a generator;
* downstream few-shot subsets use the same deterministic draw as the legacy
  file-split runner;
* the outer-test file split is used only for final downstream evaluation; and
* generator checkpoints, generated pools, downstream rows, and wall-clock
  costs are written under a fresh results root and can be resumed safely.

``--smoke`` validates wiring with deliberately tiny training budgets and must
not be reported as a scientific result.  Formal runs omit ``--smoke`` and use
the declared 40 seeds and registered few-shot budgets.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import signal
import socket
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "breeze" / "src"
sys.path.insert(0, str(SRC))

from data import load_file_split  # noqa: E402
from eval_npz_downstream import evaluate, fit  # noqa: E402
from trained_baselines import DDPMConfig, TimeGANConfig, linear_beta_schedule, make_trainer  # noqa: E402


class StopRequested(RuntimeError):
    """Raised only after the current epoch has been checkpointed durably."""


class ProgressWriter:
    def __init__(self, root: Path, device_name: str):
        self.jsonl = root / "heartbeat.jsonl"
        self.log = root / "runner.log"
        self.device_name = device_name

    def write(self, event: dict) -> None:
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "device": self.device_name,
            **event,
        }
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        for path, text in (
            (self.jsonl, line),
            (
                self.log,
                f"{payload['timestamp_utc']} {payload.get('event', 'progress')} "
                f"{payload.get('cell', '-')} {payload.get('stage', '-')} "
                f"{payload.get('completed', '-')}/{payload.get('total', '-')} "
                f"elapsed={payload.get('elapsed_seconds', '-')}s",
            ),
        ):
            with path.open("a", encoding="utf-8") as handle:
                handle.write(text + "\n")
                handle.flush()
                os.fsync(handle.fileno())


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_path = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(raw_path)
    try:
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(json.dumps(list(contiguous.shape), separators=(",", ":")).encode("ascii"))
    digest.update(memoryview(contiguous).cast("B"))
    return digest.hexdigest()


def few_shot_subset(x: np.ndarray, y: np.ndarray, n_real: int, seed: int, n_classes: int):
    rng = np.random.default_rng(1000 * n_real + seed)
    chosen = []
    actual: dict[str, int] = {}
    for class_id in range(n_classes):
        indexes = np.where(y == class_id)[0]
        if len(indexes) < n_real:
            raise RuntimeError(f"class {class_id} has {len(indexes)} train windows, need {n_real}")
        picks = rng.choice(indexes, n_real, replace=False)
        chosen.extend(picks.tolist())
        actual[str(class_id)] = int(n_real)
    index_array = np.asarray(chosen, dtype=int)
    return x[index_array], y[index_array], actual


def cap_examples(x: np.ndarray, cap: int | None, seed: int):
    if cap is None:
        return x
    rng = np.random.default_rng(seed)
    indexes = rng.choice(len(x), min(cap, len(x)), replace=False)
    return x[np.sort(indexes)]


def completed_keys(path: Path) -> set[tuple[str, str, int, int]]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            (row["method"], row["train_mode"], int(row["n_real"]), int(row["seed"]))
            for row in reader
        }


def completed_history_keys(path: Path) -> set[tuple[str, str, int, int, int, str, int]]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            (
                row["method"],
                row["train_mode"],
                int(row["n_real"]),
                int(row["seed"]),
                int(row["class_id"]),
                row["stage"],
                int(row["epoch"]),
            )
            for row in reader
        }


def completed_cost_keys(path: Path) -> set[tuple[str, str, int, int, int]]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            (
                row["method"],
                row["train_mode"],
                int(row["n_real"]),
                int(row["seed"]),
                int(row["class_id"]),
            )
            for row in reader
        }


def append_row(path: Path, fieldnames: list[str], row: dict) -> None:
    new_file = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        if new_file:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()
        os.fsync(handle.fileno())


def save_pool(path: Path, x: np.ndarray, y: np.ndarray) -> None:
    if path.exists():
        existing = np.load(path, allow_pickle=True)
        if np.array_equal(existing["X"], x) and np.array_equal(existing["y"], y):
            return
        raise RuntimeError(f"refusing to overwrite mismatched generated pool: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, X=x.astype(np.float32), y=y.astype(np.int64), class_names=np.array(["healthy", "OR", "IR"]))


def write_smoke_report(root: Path, downstream: Path, status: str, detail: str) -> None:
    rows = []
    if downstream.exists():
        with downstream.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
    report = [
        "# Trained-baseline PU smoke report",
        "",
        "Status: " + status,
        "",
        "This is a pipeline smoke test only. It uses a capped training subset, one seed, and one epoch per generator stage. It is not a registered result and must not be used in the manuscript or in any comparison.",
        "",
        "## Detail",
        "",
        detail,
        "",
        "## Produced rows",
        "",
        "| method | train mode | n_real | seed | n_syn | Acc | Macro-F1 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        report.append(
            f"| {row['method']} | {row['train_mode']} | {row['n_real']} | {row['seed']} | {row['n_syn']} | {row['acc']} | {row['macro_f1']} |"
        )
    (root / "trained_baselines_smoke_report.md").write_text("\n".join(report) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", default="breeze/results/trained_baselines_2026-07-14")
    parser.add_argument("--methods", nargs="+", choices=["timegan", "ddpm"], default=["timegan", "ddpm"])
    parser.add_argument("--train-modes", nargs="+", choices=["full_train", "few_shot"], default=["full_train", "few_shot"])
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--n-real", type=int, nargs="+", default=[5, 10, 25])
    parser.add_argument("--n-syn", type=int, default=20)
    parser.add_argument("--downstream-epochs", type=int, default=60)
    parser.add_argument("--timegan-iterations", type=int, default=50_000)
    parser.add_argument("--ddpm-epochs", type=int, default=200)
    parser.add_argument("--ddpm-steps", type=int, default=1000)
    parser.add_argument("--device", choices=["auto", "cpu", "mps"], default="auto")
    parser.add_argument("--max-train-per-class", type=int)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed-stop", type=int)
    parser.add_argument("--execute-methods", nargs="+", choices=["timegan", "ddpm"])
    parser.add_argument("--execute-train-modes", nargs="+", choices=["full_train", "few_shot"])
    args = parser.parse_args()

    if args.seeds <= 0 or args.n_syn <= 0 or any(value <= 0 for value in args.n_real):
        raise SystemExit("seeds, n_syn, and n_real must all be positive")
    seed_stop = args.seeds if args.seed_stop is None else args.seed_stop
    if not 0 <= args.seed_start < seed_stop <= args.seeds:
        raise SystemExit("execution seed interval must satisfy 0 <= seed-start < seed-stop <= seeds")
    execute_methods = args.methods if args.execute_methods is None else args.execute_methods
    execute_train_modes = args.train_modes if args.execute_train_modes is None else args.execute_train_modes
    if not set(execute_methods).issubset(args.methods):
        raise SystemExit("execute-methods must be a subset of the formal methods")
    if not set(execute_train_modes).issubset(args.train_modes):
        raise SystemExit("execute-train-modes must be a subset of the formal train modes")
    if args.device == "auto":
        device_name = "mps" if torch.backends.mps.is_available() else "cpu"
    else:
        device_name = args.device
    if device_name == "mps" and not torch.backends.mps.is_available():
        raise SystemExit("--device mps was requested but torch.backends.mps.is_available() is false")
    if not args.smoke and "ddpm" in args.methods and args.ddpm_steps != 1000:
        raise SystemExit(
            "formal DDPM requires the registered 1000-step linear schedule; "
            "short schedules are permitted only for wiring smoke tests"
        )
    if args.smoke:
        if (
            args.seeds != 1
            or not args.n_real
            or any(value not in {5, 10, 25} for value in args.n_real)
            or args.max_train_per_class != 8
        ):
            raise SystemExit(
                "--smoke requires --seeds 1, n-real values drawn from 5/10/25, "
                "and --max-train-per-class 8"
            )
        if args.downstream_epochs != 1:
            raise SystemExit("--smoke requires --downstream-epochs 1")
        if (
            args.timegan_iterations != 1
            or args.ddpm_epochs != 1
            or args.ddpm_steps != 1000
        ):
            raise SystemExit(
                "--smoke requires one iteration per TimeGAN stage, one DDPM epoch, "
                "and the registered 1000-step DDPM schedule"
            )

    out_root = Path(args.out_root).resolve()
    expected_downstream_cells = len(args.methods) * len(args.train_modes) * len(args.n_real) * args.seeds
    if args.dry_run:
        full_units = len(args.methods) * args.seeds * 3 if "full_train" in args.train_modes else 0
        few_units = (
            len(args.methods) * args.seeds * len(args.n_real) * 3
            if "few_shot" in args.train_modes
            else 0
        )
        print(
            json.dumps(
                {
                    "out_root": str(out_root),
                    "expected_downstream_cells": expected_downstream_cells,
                    "expected_class_training_units": full_units + few_units,
                    "full_train_class_units": full_units,
                    "few_shot_class_units": few_units,
                    "full_train_policy": "one generator pool per method and seed, reused across shot levels",
                    "execution_methods": execute_methods,
                    "execution_train_modes": execute_train_modes,
                    "execution_seed_interval": [args.seed_start, seed_stop],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    out_root.mkdir(parents=True, exist_ok=True)
    lock_path = out_root / ".runner.lock"
    lock_handle = lock_path.open("w")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        lock_handle.close()
        raise RuntimeError(
            f"another trained-baseline runner already owns {out_root}; "
            "wait for it to finish instead of starting a competing resume"
        ) from exc
    lock_handle.write(f"pid={os.getpid()}\n")
    lock_handle.flush()
    manifest_path = out_root / "run_manifest.json"
    downstream_path = out_root / "pu_file_trained_baselines.csv"
    cost_path = out_root / "training_cost.csv"
    dynamics_path = out_root / "training_dynamics.csv"
    failures_path = out_root / "training_failures.csv"
    progress = ProgressWriter(out_root, device_name)
    stop_requested = False

    def request_stop(_signum, _frame) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    x_train, y_train, _ = load_file_split("train", "N09_M07_F10")
    x_test, y_test, _ = load_file_split("test", "N09_M07_F10")
    x_train = x_train.astype(np.float32)
    x_test = x_test.astype(np.float32)
    n_classes = len(np.unique(y_train))
    if n_classes != 3 or set(np.unique(y_test)) != {0, 1, 2}:
        raise RuntimeError("unexpected PU class support in frozen file split")

    timegan_config = TimeGANConfig(iterations=args.timegan_iterations)
    ddpm_config = DDPMConfig(epochs=args.ddpm_epochs, diffusion_steps=args.ddpm_steps)
    ddpm_beta = linear_beta_schedule(ddpm_config.diffusion_steps, torch.device("cpu"))
    ddpm_terminal_alpha_bar = float(torch.cumprod(1.0 - ddpm_beta, dim=0)[-1])
    parameter_counts = {}
    for method in args.methods:
        probe = make_trainer(
            method,
            channels=x_train.shape[1],
            length=x_train.shape[2],
            seed=0,
            timegan_config=timegan_config,
            ddpm_config=ddpm_config,
            device_name=device_name,
        )
        parameter_counts[method] = int(sum(parameter.numel() for parameter in probe.model.parameters()))

    manifest = {
        "dataset": "PU",
        "condition": "N09_M07_F10",
        "split": "file_chronological_80_20",
        "generator_data_boundary": "outer_train_only",
        "test_access": "downstream_evaluation_only",
        "methods": args.methods,
        "train_modes": args.train_modes,
        "seeds": args.seeds,
        "n_real": args.n_real,
        "n_syn_per_class": args.n_syn,
        "downstream_epochs": args.downstream_epochs,
        "max_train_per_class": args.max_train_per_class,
        "smoke": args.smoke,
        "x_train_shape": list(x_train.shape),
        "x_test_shape": list(x_test.shape),
        "data_sha256": {
            "x_train": array_sha256(x_train),
            "y_train": array_sha256(y_train),
            "x_test": array_sha256(x_test),
            "y_test": array_sha256(y_test),
        },
        "runtime": {
            "python_executable": sys.executable,
            "numpy": np.__version__,
            "torch": torch.__version__,
            "torch_threads": torch.get_num_threads(),
            "torch_interop_threads": torch.get_num_interop_threads(),
            "mps_available": torch.backends.mps.is_available(),
            "generator_device": device_name,
        },
        "model_parameter_counts": parameter_counts,
        "source_scripts": {
            "runner_sha256": file_sha256(Path(__file__)),
            "models_sha256": file_sha256(SRC / "trained_baselines.py"),
        },
        "timegan_config": asdict(timegan_config),
        "ddpm_config": asdict(ddpm_config),
        "ddpm_schedule": {
            "family": "linear",
            "beta_start": float(ddpm_beta[0]),
            "beta_end": float(ddpm_beta[-1]),
            "terminal_alpha_bar": ddpm_terminal_alpha_bar,
            "reverse_variance": ddpm_config.reverse_variance,
            "sample_start": "standard_normal",
            "sampling_weights": "ema",
            "ema_decay": ddpm_config.ema_decay,
            "optimizer": "adam",
            "warmup_steps": ddpm_config.warmup_steps,
            "gradient_clip_norm": ddpm_config.gradient_clip_norm,
        },
        "training_dynamics": "raw per-epoch optimization losses, checkpointed and exported without stability thresholds",
        "full_train_pool_policy": "one trained generator and one sampled pool per method/seed, reused across n_real downstream levels",
        "heartbeat": "append-only heartbeat.jsonl and runner.log after every atomically checkpointed epoch",
    }
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
        if existing != manifest:
            raise RuntimeError(f"run manifest differs at {manifest_path}; use a new output root")
    else:
        atomic_write_json(manifest_path, manifest)

    downstream_fields = [
        "method", "train_mode", "n_real", "seed", "actual_real_per_class", "n_syn", "acc", "macro_f1", "pool_path", "pool_sha256", "generator_train_seconds", "generator_train_examples_per_class", "smoke",
    ]
    cost_fields = ["method", "train_mode", "n_real", "seed", "class_id", "train_examples", "wall_seconds", "checkpoint", "smoke"]
    dynamics_fields = [
        "method", "train_mode", "n_real", "seed", "class_id", "train_examples", "checkpoint", "stage", "epoch",
        "reconstruction_loss", "supervisor_loss", "discriminator_loss", "generator_loss", "noise_prediction_mse", "smoke",
    ]
    failure_fields = ["method", "train_mode", "n_real", "seed", "class_id", "train_examples", "checkpoint", "phase", "exception_type", "exception_message", "smoke"]
    done = completed_keys(downstream_path)
    recorded_history = completed_history_keys(dynamics_path)
    recorded_cost = completed_cost_keys(cost_path)
    progress.write(
        {
            "event": "run_started",
            "cell": "coordinator",
            "completed": len(done),
            "total": expected_downstream_cells,
        }
    )

    try:
        for method in args.methods:
            if method not in execute_methods:
                continue
            for train_mode in args.train_modes:
                if train_mode not in execute_train_modes:
                    continue
                for n_real in args.n_real:
                    for seed in range(args.seed_start, seed_stop):
                        key = (method, train_mode, n_real, seed)
                        if key in done:
                            continue
                        if stop_requested:
                            raise StopRequested("stop requested before starting the next downstream cell")
                        x_few, y_few, actual = few_shot_subset(x_train, y_train, n_real, seed, n_classes)
                        generated_x, generated_y = [], []
                        train_seconds: list[float] = []
                        train_counts: list[int] = []
                        training_n_real = 0 if train_mode == "full_train" else n_real
                        cell_name = f"{method}/{train_mode}/train_n={training_n_real}/seed={seed}"
                        for class_id in range(n_classes):
                            if train_mode == "full_train":
                                source_x = x_train[y_train == class_id]
                            else:
                                source_x = x_few[y_few == class_id]
                            source_x = cap_examples(source_x, args.max_train_per_class, seed + class_id)
                            if len(source_x) == 0:
                                raise RuntimeError(f"no train examples for class {class_id}")
                            checkpoint = out_root / "checkpoints" / method / train_mode / f"train_nreal_{training_n_real}" / f"seed_{seed}" / f"class_{class_id}.pt"
                            trainer = make_trainer(
                                method,
                                channels=source_x.shape[1],
                                length=source_x.shape[2],
                                seed=10_000_000 * seed + 100_000 * training_n_real + 1_000 * class_id,
                                timegan_config=timegan_config,
                                ddpm_config=ddpm_config,
                                device_name=device_name,
                            )
                            tic = perf_counter()
                            try:
                                def report_epoch(event: dict, class_id: int = class_id) -> None:
                                    progress.write(
                                        {
                                            "event": "epoch_checkpointed",
                                            "cell": cell_name,
                                            "class_id": class_id,
                                            **event,
                                        }
                                    )
                                    if stop_requested:
                                        raise StopRequested("stop requested; current epoch checkpoint is durable")

                                cumulative_seconds = trainer.fit(
                                    source_x,
                                    checkpoint,
                                    progress_callback=report_epoch,
                                )
                                wall_seconds = perf_counter() - tic
                                synthetic = trainer.sample(
                                    args.n_syn,
                                    sample_seed=20_000_000 * seed + 100_000 * training_n_real + 1_000 * class_id,
                                )
                                if not np.isfinite(synthetic).all():
                                    raise FloatingPointError("non-finite generated samples")
                            except StopRequested:
                                raise
                            except Exception as exc:
                                append_row(
                                    failures_path,
                                    failure_fields,
                                    {
                                        "method": method,
                                        "train_mode": train_mode,
                                        "n_real": training_n_real,
                                        "seed": seed,
                                        "class_id": class_id,
                                        "train_examples": len(source_x),
                                        "checkpoint": str(checkpoint.relative_to(ROOT)),
                                        "phase": "fit_or_sample",
                                        "exception_type": type(exc).__name__,
                                        "exception_message": str(exc),
                                        "smoke": args.smoke,
                                    },
                                )
                                raise
                            for history_row in trainer.training_history():
                                history_key = (
                                    method,
                                    train_mode,
                                    training_n_real,
                                    seed,
                                    class_id,
                                    str(history_row["stage"]),
                                    int(history_row["epoch"]),
                                )
                                if history_key in recorded_history:
                                    continue
                                append_row(
                                    dynamics_path,
                                    dynamics_fields,
                                    {
                                        "method": method,
                                        "train_mode": train_mode,
                                        "n_real": training_n_real,
                                        "seed": seed,
                                        "class_id": class_id,
                                        "train_examples": len(source_x),
                                        "checkpoint": str(checkpoint.relative_to(ROOT)),
                                        "stage": history_row["stage"],
                                        "epoch": history_row["epoch"],
                                        "reconstruction_loss": history_row.get("reconstruction_loss", ""),
                                        "supervisor_loss": history_row.get("supervisor_loss", ""),
                                        "discriminator_loss": history_row.get("discriminator_loss", ""),
                                        "generator_loss": history_row.get("generator_loss", ""),
                                        "noise_prediction_mse": history_row.get("noise_prediction_mse", ""),
                                        "smoke": args.smoke,
                                    },
                                )
                                recorded_history.add(history_key)
                            generated_x.append(synthetic)
                            generated_y.append(np.full(args.n_syn, class_id, dtype=np.int64))
                            train_seconds.append(cumulative_seconds)
                            train_counts.append(len(source_x))
                            cost_key = (method, train_mode, training_n_real, seed, class_id)
                            if cost_key not in recorded_cost:
                                append_row(
                                    cost_path,
                                    cost_fields,
                                    {
                                        "method": method,
                                        "train_mode": train_mode,
                                        "n_real": training_n_real,
                                        "seed": seed,
                                        "class_id": class_id,
                                        "train_examples": len(source_x),
                                        "wall_seconds": f"{wall_seconds:.6f}",
                                        "checkpoint": str(checkpoint.relative_to(ROOT)),
                                        "smoke": args.smoke,
                                    },
                                )
                                recorded_cost.add(cost_key)
                        x_syn = np.concatenate(generated_x).astype(np.float32)
                        y_syn = np.concatenate(generated_y).astype(np.int64)
                        pool_path = out_root / "pools" / method / train_mode / f"train_nreal_{training_n_real}" / f"seed_{seed}.npz"
                        save_pool(pool_path, x_syn, y_syn)
                        x_aug = np.concatenate([x_few, x_syn])
                        y_aug = np.concatenate([y_few, y_syn])
                        model, mean, std = fit(x_aug, y_aug, seed=seed, epochs=args.downstream_epochs, n_classes=n_classes)
                        acc, macro_f1, _ = evaluate(model, mean, std, x_test, y_test)
                        append_row(
                            downstream_path,
                            downstream_fields,
                            {
                                "method": method,
                                "train_mode": train_mode,
                                "n_real": n_real,
                                "seed": seed,
                                "actual_real_per_class": json.dumps(actual, sort_keys=True, separators=(",", ":")),
                                "n_syn": len(y_syn),
                                "acc": f"{acc:.6f}",
                                "macro_f1": f"{macro_f1:.6f}",
                                "pool_path": str(pool_path.relative_to(ROOT)),
                                "pool_sha256": file_sha256(pool_path),
                                "generator_train_seconds": f"{sum(train_seconds):.6f}",
                                "generator_train_examples_per_class": json.dumps(train_counts),
                                "smoke": args.smoke,
                            },
                        )
                        print(
                            f"{method} {train_mode} n_real={n_real} seed={seed} n_syn={len(y_syn)} "
                            f"acc={acc:.4f} macro_f1={macro_f1:.4f}",
                            flush=True,
                        )
                        done.add(key)
                        progress.write(
                            {
                                "event": "downstream_cell_completed",
                                "cell": f"{method}/{train_mode}/n_real={n_real}/seed={seed}",
                                "completed": len(done),
                                "total": expected_downstream_cells,
                            }
                        )
    except Exception as exc:
        progress.write(
            {
                "event": "run_interrupted" if isinstance(exc, StopRequested) else "run_failed",
                "cell": "coordinator",
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "completed": len(done),
                "total": expected_downstream_cells,
            }
        )
        if args.smoke:
            write_smoke_report(out_root, downstream_path, "FAILED", f"{type(exc).__name__}: {exc}")
        raise

    if args.smoke:
        write_smoke_report(out_root, downstream_path, "PASSED", "Both selected trained-baseline pipelines completed their checkpoint, sampling, pool persistence, and downstream-evaluation paths.")
    progress.write(
        {
            "event": "formal_run_completed" if len(done) == expected_downstream_cells else "invocation_completed",
            "cell": "coordinator",
            "completed": len(done),
            "total": expected_downstream_cells,
        }
    )


if __name__ == "__main__":
    main()
