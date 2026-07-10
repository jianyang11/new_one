"""Append known UMich process metadata as constant channels.

The added channels are not labels: they encode known machining conditions
(feedrate, clamp pressure, and stage id) so the classifier can condition on
process settings instead of mistaking them for tool wear.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def load(path: Path) -> dict[str, np.ndarray]:
    data = np.load(path, allow_pickle=True)
    return {k: data[k] for k in data.files}


def zscore(values: np.ndarray, mean: float, std: float) -> np.ndarray:
    return ((values.astype(np.float32) - mean) / (std + 1e-8)).astype(np.float32)


def build_meta_channels(
    data: dict[str, np.ndarray],
    feed_mean: float,
    feed_std: float,
    clamp_mean: float,
    clamp_std: float,
    stages: list[str],
) -> tuple[np.ndarray, list[str]]:
    n, _, win = data["X"].shape
    chans = []
    names = []
    feed = zscore(data["feedrate"], feed_mean, feed_std)[:, None, None]
    clamp = zscore(data["clamp_pressure"], clamp_mean, clamp_std)[:, None, None]
    chans.append(np.repeat(feed, win, axis=2))
    names.append("meta_feedrate_z")
    chans.append(np.repeat(clamp, win, axis=2))
    names.append("meta_clamp_pressure_z")
    stage_vals = np.asarray([str(s) for s in data["stage"]])
    for stage in stages:
        one = (stage_vals == stage).astype(np.float32)[:, None, None]
        chans.append(np.repeat(one, win, axis=2))
        names.append("stage_" + stage.lower().replace(" ", "_"))
    if chans:
        return np.concatenate(chans, axis=1).astype(np.float32), names
    return np.zeros((n, 0, win), dtype=np.float32), names


def transform(data: dict[str, np.ndarray], meta: np.ndarray, meta_names: list[str]) -> dict[str, np.ndarray]:
    out = {k: v for k, v in data.items() if k != "X"}
    out["X"] = np.concatenate([data["X"].astype(np.float32), meta], axis=1)
    old_channels = [str(c) for c in data["channels"]]
    out["channels"] = np.asarray(old_channels + meta_names)
    out["metadata_channel_definition"] = np.asarray(
        ["known process metadata appended as constant channels; z-score parameters estimated from train NPZ only"]
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-npz", required=True)
    parser.add_argument("--eval-npz", required=True)
    parser.add_argument("--out-train", required=True)
    parser.add_argument("--out-eval", required=True)
    parser.add_argument("--stats-json", default="")
    args = parser.parse_args()

    train = load(Path(args.train_npz))
    eval_data = load(Path(args.eval_npz))
    for key in ["feedrate", "clamp_pressure", "stage"]:
        if key not in train or key not in eval_data:
            raise RuntimeError(f"missing metadata key {key}; regenerate UMich v4 NPZ")
    feed_mean = float(np.mean(train["feedrate"]))
    feed_std = float(np.std(train["feedrate"]) + 1e-8)
    clamp_mean = float(np.mean(train["clamp_pressure"]))
    clamp_std = float(np.std(train["clamp_pressure"]) + 1e-8)
    stages = sorted(set(str(s) for s in train["stage"]) | set(str(s) for s in eval_data["stage"]))
    train_meta, names = build_meta_channels(train, feed_mean, feed_std, clamp_mean, clamp_std, stages)
    eval_meta, _ = build_meta_channels(eval_data, feed_mean, feed_std, clamp_mean, clamp_std, stages)
    Path(args.out_train).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out_train, **transform(train, train_meta, names))
    np.savez_compressed(args.out_eval, **transform(eval_data, eval_meta, names))
    if args.stats_json:
        Path(args.stats_json).write_text(
            json.dumps(
                {
                    "feedrate_mean": feed_mean,
                    "feedrate_std": feed_std,
                    "clamp_pressure_mean": clamp_mean,
                    "clamp_pressure_std": clamp_std,
                    "stages": stages,
                    "metadata_channels": names,
                },
                indent=2,
            )
            + "\n"
        )
    print(f"wrote {args.out_train}")
    print(f"wrote {args.out_eval}")


if __name__ == "__main__":
    main()
