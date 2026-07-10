"""UMich CNC task-repair preprocessing.

This script fixes the UMich representation before any generation attack:

- windows are cut inside one contiguous Machining_Process segment;
- source_units remain experiment-level to avoid inner split leakage;
- optional single-stage restriction is supported for learnability diagnosis.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


CHANNELS_DYNAMIC = [
    "X1_CurrentFeedback",
    "Y1_CurrentFeedback",
    "S1_CurrentFeedback",
    "X1_OutputCurrent",
    "Y1_OutputCurrent",
    "S1_OutputCurrent",
]
CLASSES = ["unworn", "worn"]
TEST_EXPERIMENTS = {1, 2, 6, 7, 8}
ACTIVE_STAGES = [
    "Layer 1 Up",
    "Layer 1 Down",
    "Layer 2 Up",
    "Layer 2 Down",
    "Layer 3 Up",
    "Layer 3 Down",
]
FS_HZ = 10.0
WIN = 64


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def is_pure(tool_condition: str, passed_visual: str) -> bool:
    return (tool_condition == "unworn" and passed_visual == "yes") or (
        tool_condition == "worn" and passed_visual == "no"
    )


def contiguous_stage_segments(df: pd.DataFrame, stage: str) -> list[np.ndarray]:
    mask = (df["Machining_Process"] == stage).to_numpy()
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return []
    breaks = np.where(np.diff(idx) > 1)[0] + 1
    return [seg for seg in np.split(idx, breaks) if len(seg) >= WIN]


def window_segment(sig: np.ndarray, win: int = WIN) -> np.ndarray:
    n = sig.shape[1] // win
    if n < 1:
        return np.zeros((0, sig.shape[0], win), dtype=np.float32)
    return np.stack([sig[:, i * win : (i + 1) * win] for i in range(n)]).astype(np.float32)


def append_windows(
    split_data: dict[str, dict[str, list]],
    split: str,
    W: np.ndarray,
    exp_no: int,
    label: str,
    stage: str,
    segment_index: int,
    rec: pd.Series,
) -> None:
    yi = CLASSES.index(label)
    n = len(W)
    split_data[split]["X"].append(W)
    split_data[split]["y"].append(np.full(n, yi, dtype=np.int64))
    split_data[split]["source_units"].extend([f"experiment_{exp_no:02d}"] * n)
    split_data[split]["segment_units"].extend([f"experiment_{exp_no:02d}:{stage}:seg{segment_index:02d}"] * n)
    split_data[split]["experiment"].extend([exp_no] * n)
    split_data[split]["stage"].extend([stage] * n)
    split_data[split]["tool_condition"].extend([label] * n)
    passed_visual = clean(rec.get("passed_visual_inspection", ""))
    machining_finalized = clean(rec.get("machining_finalized", ""))
    split_data[split]["passed_visual_inspection"].extend([passed_visual] * n)
    split_data[split]["machining_finalized"].extend([machining_finalized] * n)
    split_data[split]["pure_exemplar"].extend([is_pure(label, passed_visual)] * n)
    split_data[split]["feedrate"].extend([float(rec["feedrate"])] * n)
    split_data[split]["clamp_pressure"].extend([float(rec["clamp_pressure"])] * n)


def empty_split() -> dict[str, list]:
    return {
        "X": [],
        "y": [],
        "source_units": [],
        "segment_units": [],
        "experiment": [],
        "stage": [],
        "tool_condition": [],
        "passed_visual_inspection": [],
        "machining_finalized": [],
        "pure_exemplar": [],
        "feedrate": [],
        "clamp_pressure": [],
    }


def save_npz(proc_dir: Path, prefix: str, split: str, data: dict[str, list]) -> None:
    if data["X"]:
        X = np.concatenate(data["X"]).astype(np.float32)
        y = np.concatenate(data["y"]).astype(np.int64)
    else:
        X = np.zeros((0, len(CHANNELS_DYNAMIC), WIN), dtype=np.float32)
        y = np.zeros((0,), dtype=np.int64)
    np.savez_compressed(
        proc_dir / f"{prefix}_{split}.npz",
        X=X,
        y=y,
        class_names=np.asarray(CLASSES),
        source_units=np.asarray(data["source_units"]),
        segment_units=np.asarray(data["segment_units"]),
        fs_hz=FS_HZ,
        window=WIN,
        channels=np.asarray(CHANNELS_DYNAMIC),
        experiment=np.asarray(data["experiment"], dtype=np.int64),
        stage=np.asarray(data["stage"]),
        tool_condition=np.asarray(data["tool_condition"]),
        passed_visual_inspection=np.asarray(data["passed_visual_inspection"]),
        machining_finalized=np.asarray(data["machining_finalized"]),
        pure_exemplar=np.asarray(data["pure_exemplar"], dtype=bool),
        feedrate=np.asarray(data["feedrate"], dtype=np.float32),
        clamp_pressure=np.asarray(data["clamp_pressure"], dtype=np.float32),
        windowing_definition=np.asarray(
            [
                "stage_contiguous; windows are cut within a single contiguous Machining_Process segment; "
                "source_units are experiment-level"
            ]
        ),
    )


def counts_for_npz(path: Path) -> dict[str, int]:
    data = np.load(path, allow_pickle=True)
    classes = [str(x) for x in data["class_names"]]
    return {classes[i]: int((data["y"] == i).sum()) for i in range(len(classes))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/archive")
    parser.add_argument("--proc-dir", default="proc")
    parser.add_argument("--out-dir", default="breeze/results/milling_umich_v4_task_repair_2026-07-09")
    parser.add_argument("--prefix", default="milling_umich_v4_stage_multi")
    parser.add_argument("--stage", default="", help="Optional exact Machining_Process stage. Empty means all active stages.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    proc_dir = Path(args.proc_dir)
    out_dir = Path(args.out_dir)
    proc_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected_stages = [args.stage] if args.stage else ACTIVE_STAGES
    unknown = sorted(set(selected_stages) - set(ACTIVE_STAGES))
    if unknown:
        raise SystemExit(f"unknown active stage(s): {unknown}; valid={ACTIVE_STAGES}")

    meta = pd.read_csv(data_dir / "train.csv")
    split_data = {"train": empty_split(), "test": empty_split()}
    rows = []
    stage_rows = []
    for _, rec in meta.iterrows():
        exp_no = int(rec["No"])
        label = clean(rec["tool_condition"])
        split = "test" if exp_no in TEST_EXPERIMENTS else "train"
        df = pd.read_csv(data_dir / f"experiment_{exp_no:02d}.csv")
        raw_rows = len(df)
        non_cutting = int((~df["Machining_Process"].isin(ACTIVE_STAGES)).sum())
        kept_windows = 0
        stage_counts: Counter[str] = Counter()
        stage_raw: Counter[str] = Counter(df["Machining_Process"])
        for stage in selected_stages:
            for seg_i, idx in enumerate(contiguous_stage_segments(df, stage)):
                sig = (
                    df.iloc[idx][CHANNELS_DYNAMIC]
                    .apply(pd.to_numeric, errors="coerce")
                    .interpolate(limit_direction="both")
                    .fillna(0.0)
                    .to_numpy(dtype=np.float32)
                    .T
                )
                W = window_segment(sig)
                if len(W) == 0:
                    continue
                append_windows(split_data, split, W, exp_no, label, stage, seg_i, rec)
                kept_windows += len(W)
                stage_counts[stage] += len(W)
        rows.append(
            {
                "experiment": exp_no,
                "split": split,
                "tool_condition": label,
                "feedrate": rec["feedrate"],
                "clamp_pressure": rec["clamp_pressure"],
                "passed_visual_inspection": clean(rec.get("passed_visual_inspection", "")),
                "machining_finalized": clean(rec.get("machining_finalized", "")),
                "raw_rows": raw_rows,
                "non_cutting_rows": non_cutting,
                "selected_stages": ";".join(selected_stages),
                "kept_windows": kept_windows,
            }
        )
        for stage in ACTIVE_STAGES:
            stage_rows.append(
                {
                    "experiment": exp_no,
                    "split": split,
                    "tool_condition": label,
                    "stage": stage,
                    "raw_rows": int(stage_raw.get(stage, 0)),
                    "windows": int(stage_counts.get(stage, 0)),
                }
            )

    for split in ["train", "test"]:
        save_npz(proc_dir, args.prefix, split, split_data[split])

    with (out_dir / f"{args.prefix}_units.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (out_dir / f"{args.prefix}_stage_counts.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(stage_rows[0]))
        writer.writeheader()
        writer.writerows(stage_rows)

    lines = [f"# UMich v4 Stage-Contiguous Preprocessing: {args.prefix}", ""]
    lines.append(f"- Selected stages: `{selected_stages}`")
    lines.append(f"- Window length: `{WIN}` samples ({WIN / FS_HZ:.3f} s)")
    lines.append("- Windowing: contiguous within one Machining_Process stage; no cross-stage windows.")
    lines.append("- Split unit: experiment-level; source_units remain experiment ids.")
    lines.append(f"- Train counts: {counts_for_npz(proc_dir / f'{args.prefix}_train.npz')}")
    lines.append(f"- Test counts: {counts_for_npz(proc_dir / f'{args.prefix}_test.npz')}")
    lines.append(f"- Unit audit CSV: `{args.prefix}_units.csv`")
    lines.append(f"- Stage count CSV: `{args.prefix}_stage_counts.csv`")
    (out_dir / f"{args.prefix}_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
