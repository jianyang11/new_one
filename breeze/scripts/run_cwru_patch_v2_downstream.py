"""Run the 2026-07-07 CWRU patch-v2 downstream protocol.

This is a thin checkpointed scheduler around ``breeze/src/eval_npz_downstream.py``.
Each child CSV is append-only and the evaluator skips existing
``(dataset, split, baseline, n_real, seed)`` rows.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


SPLITS = {
    "within_load0": (
        "proc/cwru_de12k_within_load0_train.npz",
        "proc/cwru_de12k_within_load0_test.npz",
    ),
    "lolo_load0": (
        "proc/cwru_de12k_lolo_load0_train.npz",
        "proc/cwru_de12k_lolo_load0_test.npz",
    ),
    "lolo_load1": (
        "proc/cwru_de12k_lolo_load1_train.npz",
        "proc/cwru_de12k_lolo_load1_test.npz",
    ),
    "lolo_load2": (
        "proc/cwru_de12k_lolo_load2_train.npz",
        "proc/cwru_de12k_lolo_load2_test.npz",
    ),
    "lolo_load3": (
        "proc/cwru_de12k_lolo_load3_train.npz",
        "proc/cwru_de12k_lolo_load3_test.npz",
    ),
}

METHODS = {
    "llm": {
        "baseline": "custom_pool",
        "pool": "breeze/runs/phaseB_cwru_within_load0_llm_full_v1_combined/pool.npz",
    },
    "rule": {
        "baseline": "custom_pool",
        "pool": "breeze/runs/phaseB_cwru_within_load0_rule_pilot_v1/pool.npz",
    },
    "noise_aug": {"baseline": "noise_aug"},
    "real_only": {"baseline": "real_only"},
}


def command_for(
    split: str,
    method: str,
    train_npz: str,
    test_npz: str,
    seeds: int,
    n_real: list[int],
    n_syn: int,
    epochs: int,
    out_dir: Path,
) -> list[str]:
    spec = METHODS[method]
    cmd = [
        sys.executable,
        "breeze/src/eval_npz_downstream.py",
        "--dataset",
        "CWRU",
        "--split",
        split,
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
        str(out_dir / f"{split}_{method}_nsyn{n_syn}.csv"),
    ]
    if spec["baseline"] != "real_only":
        cmd.extend(["--n-syn", str(n_syn)])
    if "pool" in spec:
        cmd.extend(["--pool", spec["pool"]])
    return cmd


def run_split(
    split: str,
    train_npz: str,
    test_npz: str,
    seeds: int,
    n_real: list[int],
    n_syn: int,
    epochs: int,
    out_dir: Path,
    max_parallel: int,
) -> None:
    pending = [
        (
            f"{split}_{method}_nsyn{n_syn}.csv",
            command_for(split, method, train_npz, test_npz, seeds, n_real, n_syn, epochs, out_dir),
        )
        for method in METHODS
    ]
    running: list[tuple[str, subprocess.Popen[str]]] = []
    while pending or running:
        while pending and len(running) < max_parallel:
            label, cmd = pending.pop(0)
            print(f"[launch] {label}", flush=True)
            running.append((label, subprocess.Popen(cmd, text=True)))
        still_running: list[tuple[str, subprocess.Popen[str]]] = []
        for label, proc in running:
            ret = proc.poll()
            if ret is None:
                still_running.append((label, proc))
                continue
            if ret != 0:
                raise SystemExit(f"{label} failed with exit code {ret}")
            print(f"[done] {label}", flush=True)
        running = still_running
        if running:
            time.sleep(5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="breeze/results/cwru_patch_v2_2026-07-07/downstream")
    parser.add_argument("--splits", nargs="+", default=list(SPLITS))
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--n-real", type=int, nargs="+", default=[5, 10, 25])
    parser.add_argument("--n-syn", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--max-parallel", type=int, default=4)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for split in args.splits:
        if split not in SPLITS:
            raise SystemExit(f"unknown split: {split}")
        train_npz, test_npz = SPLITS[split]
        print(f"[split] {split}", flush=True)
        run_split(
            split=split,
            train_npz=train_npz,
            test_npz=test_npz,
            seeds=args.seeds,
            n_real=args.n_real,
            n_syn=args.n_syn,
            epochs=args.epochs,
            out_dir=out_dir,
            max_parallel=args.max_parallel,
        )


if __name__ == "__main__":
    main()
