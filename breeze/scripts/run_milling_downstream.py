"""Run Berkeley/NASA milling downstream evaluations with checkpointed CSVs."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


METHODS = {
    "llm": {
        "baseline": "custom_pool",
        "pool": "breeze/runs/milling_generation_2026-07-08_llm_rescreen_v4/berkeley/llm_rescreen/pool.npz",
    },
    "rule": {
        "baseline": "custom_pool",
        "pool": "breeze/runs/milling_generation_2026-07-08_smoke_v7/berkeley/rule/pool.npz",
    },
    "random_open_loop": {
        "baseline": "custom_pool",
        "pool": "breeze/runs/milling_generation_2026-07-08_smoke_v7/berkeley/random_open_loop/pool.npz",
    },
    "noise_aug": {"baseline": "noise_aug"},
    "real_only": {"baseline": "real_only"},
}


def command_for(
    method: str,
    dataset_name: str,
    split_name: str,
    out_prefix: str,
    train_npz: str,
    test_npz: str,
    seeds: int,
    n_real: list[int],
    n_syn: int,
    epochs: int,
    out_dir: Path,
    pool_overrides: dict[str, str],
) -> list[str]:
    spec = METHODS[method]
    cmd = [
        sys.executable,
        "breeze/src/eval_npz_downstream.py",
        "--dataset",
        dataset_name,
        "--split",
        split_name,
        "--train-npz",
        train_npz,
        "--test-npz",
        test_npz,
        "--baseline",
        spec["baseline"],
        "--seeds",
        str(seeds),
        "--n-real",
        *[str(x) for x in n_real],
        "--epochs",
        str(epochs),
        "--out",
        str(out_dir / f"{out_prefix}_{method}_nsyn{n_syn}.csv"),
    ]
    if spec["baseline"] != "real_only":
        cmd.extend(["--n-syn", str(n_syn)])
    pool_path = pool_overrides.get(method, spec.get("pool", ""))
    if pool_path:
        cmd.extend(["--pool", pool_path])
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="breeze/results/milling_berkeley_2026-07-08/downstream")
    parser.add_argument("--dataset-name", default="Berkeley_milling")
    parser.add_argument("--split-name", default="case_split")
    parser.add_argument("--out-prefix", default="berkeley")
    parser.add_argument("--train-npz", default="proc/milling_berkeley_train.npz")
    parser.add_argument("--test-npz", default="proc/milling_berkeley_test.npz")
    parser.add_argument("--methods", nargs="+", default=list(METHODS))
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--n-real", type=int, nargs="+", default=[5, 10])
    parser.add_argument("--n-syn", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--max-parallel", type=int, default=3)
    parser.add_argument("--llm-pool", default="")
    parser.add_argument("--rule-pool", default="")
    parser.add_argument("--random-pool", default="")
    args = parser.parse_args()

    for method in args.methods:
        if method not in METHODS:
            raise SystemExit(f"unknown method: {method}; valid={list(METHODS)}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pool_overrides = {
        key: value
        for key, value in {
            "llm": args.llm_pool,
            "rule": args.rule_pool,
            "random_open_loop": args.random_pool,
        }.items()
        if value
    }
    pending = [
        (
            method,
            command_for(
                method,
                args.dataset_name,
                args.split_name,
                args.out_prefix,
                args.train_npz,
                args.test_npz,
                args.seeds,
                args.n_real,
                args.n_syn,
                args.epochs,
                out_dir,
                pool_overrides,
            ),
        )
        for method in args.methods
    ]
    running: list[tuple[str, subprocess.Popen[str]]] = []
    while pending or running:
        while pending and len(running) < args.max_parallel:
            label, cmd = pending.pop(0)
            print(f"[launch] {label}", flush=True)
            running.append((label, subprocess.Popen(cmd, text=True)))
        still: list[tuple[str, subprocess.Popen[str]]] = []
        for label, proc in running:
            ret = proc.poll()
            if ret is None:
                still.append((label, proc))
                continue
            if ret != 0:
                raise SystemExit(f"{label} failed with exit code {ret}")
            print(f"[done] {label}", flush=True)
        running = still
        if running:
            time.sleep(5)


if __name__ == "__main__":
    main()
