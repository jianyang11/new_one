"""Quality diagnostics for CWRU Phase-B smoke pools."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RESULTS = BREEZE / "results"
SCRIPTS = BREEZE / "scripts"
sys.path.insert(0, str(SCRIPTS))

from phase_b_cwru_recipe_smoke import (  # noqa: E402
    CWRU_CLASSES,
    CwruVerifier,
    band_fracs,
    env_peak,
    psd_cdf,
    psd_w1,
    target_freq,
    time_stats,
)


def load_npz(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(path, allow_pickle=True)
    return data["X"].astype(np.float32), data["y"].astype(np.int64)


def class_ref(train_x: np.ndarray, train_y: np.ndarray, cls_idx: int) -> dict[str, Any]:
    W = train_x[train_y == cls_idx]
    stats = [time_stats(w[0]) for w in W]
    band = np.asarray([band_fracs(w[0]) for w in W[: min(len(W), 600)]])
    cdfs = [psd_cdf(w[0])[1] for w in W[: min(len(W), 600)]]
    return {
        "rms_median": float(np.median([s["rms"] for s in stats])),
        "kurtosis_median": float(np.median([s["kurtosis"] for s in stats])),
        "crest_median": float(np.median([s["crest"] for s in stats])),
        "band_median": np.median(band, axis=0),
        "psd_ref": np.mean(cdfs, axis=0),
    }


def normalized_flatten(x: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    z = (x - mean) / std
    return z.reshape(len(z), -1)


def nearest_distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if len(a) == 0 or len(b) == 0:
        return np.asarray([], dtype=float)
    vals = []
    chunk = 128
    for start in range(0, len(a), chunk):
        aa = a[start : start + chunk]
        d2 = ((aa[:, None, :] - b[None, :, :]) ** 2).mean(axis=2)
        vals.extend(np.sqrt(d2.min(axis=1)).tolist())
    return np.asarray(vals, dtype=float)


def summarize_pool(
    method: str,
    pool_x: np.ndarray,
    pool_y: np.ndarray,
    train_x: np.ndarray,
    train_y: np.ndarray,
    verifier: CwruVerifier,
    refs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mean = train_x.mean(axis=(0, 2), keepdims=True)
    std = train_x.std(axis=(0, 2), keepdims=True) + 1e-8
    flat_train = normalized_flatten(train_x, mean, std)
    fr_hz = float(verifier.calib["fr_hz"])
    for ci, cls in enumerate(CWRU_CLASSES):
        syn = pool_x[pool_y == ci]
        real = train_x[train_y == ci]
        if len(syn) == 0:
            rows.append({"method": method, "class": cls, "n": 0})
            continue
        stats = [time_stats(w[0]) for w in syn]
        bands = np.asarray([band_fracs(w[0]) for w in syn])
        ref = refs[cls]
        psd_vals = np.asarray([psd_w1(w[0], ref["psd_ref"]) for w in syn])
        band_l1 = np.abs(bands - ref["band_median"]).sum(axis=1)
        reports = [verifier.verify(w, cls) for w in syn]
        env_vals = []
        if cls != "healthy":
            entry = verifier.calib["classes"][cls]
            target_hz = target_freq(cls, fr_hz)
            for w in syn:
                vals = [env_peak(w[0], tuple(band), target_hz)["prominence"] for band in entry["resonance_bands"]]
                env_vals.append(float(max(vals or [0.0])))
        flat_syn = normalized_flatten(syn, mean, std)
        flat_real_cls = flat_train[train_y == ci]
        nn = nearest_distances(flat_syn, flat_real_cls)
        rows.append(
            {
                "method": method,
                "class": cls,
                "n": len(syn),
                "verifier_pass_rate": float(np.mean([r["feasible"] for r in reports])),
                "rms_mean": float(np.mean([s["rms"] for s in stats])),
                "rms_ref_median": ref["rms_median"],
                "kurtosis_mean": float(np.mean([s["kurtosis"] for s in stats])),
                "kurtosis_ref_median": ref["kurtosis_median"],
                "crest_mean": float(np.mean([s["crest"] for s in stats])),
                "crest_ref_median": ref["crest_median"],
                "band_l1_mean": float(np.mean(band_l1)),
                "psd_w1_mean": float(np.mean(psd_vals)),
                "psd_w1_p90": float(np.quantile(psd_vals, 0.90)),
                "env_prominence_mean": float(np.mean(env_vals)) if env_vals else "",
                "nn_syn_real_mean": float(np.mean(nn)) if len(nn) else "",
                "nn_syn_real_p05": float(np.quantile(nn, 0.05)) if len(nn) else "",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-npz", default="proc/cwru_de12k_within_load0_train.npz")
    parser.add_argument("--rule-pool", default="breeze/runs/phaseB_cwru_within_load0_rule_smoke_v5/pool.npz")
    parser.add_argument("--llm-pool", default="breeze/runs/phaseB_cwru_within_load0_llm_smoke_combined_v3/pool.npz")
    parser.add_argument("--llm-label", default="llm_combined_v3")
    parser.add_argument("--out-csv", default="breeze/results/phaseB_cwru_pool_quality_smoke.csv")
    parser.add_argument("--out-md", default="breeze/results/phaseB_cwru_pool_quality_smoke.md")
    args = parser.parse_args()

    train_data = np.load(ROOT / args.train_npz, allow_pickle=True)
    train_x = train_data["X"].astype(np.float32)
    train_y = train_data["y"].astype(np.int64)
    meta_rows = [json.loads(str(item)) for item in train_data["metadata"]]
    verifier = CwruVerifier(0.90)
    verifier.calibrate(train_x, train_y, meta_rows)
    refs = {cls: class_ref(train_x, train_y, ci) for ci, cls in enumerate(CWRU_CLASSES)}

    rule_x, rule_y = load_npz(ROOT / args.rule_pool)
    llm_x, llm_y = load_npz(ROOT / args.llm_pool)
    rows = []
    rows.extend(summarize_pool("rule_smoke_v5", rule_x, rule_y, train_x, train_y, verifier, refs))
    rows.extend(summarize_pool(args.llm_label, llm_x, llm_y, train_x, train_y, verifier, refs))
    out_csv = ROOT / args.out_csv
    out_md = ROOT / args.out_md
    write_csv(out_csv, rows)

    lines = ["# Phase-B CWRU Pool Quality Smoke", ""]
    lines.append("| method | class | n | pass rate | band L1 | PSD W1 mean | PSD W1 p90 | env prom mean | NN syn-real mean |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        env = row["env_prominence_mean"]
        nn = row["nn_syn_real_mean"]
        lines.append(
            f"| {row['method']} | {row['class']} | {row['n']} | "
            f"{float(row['verifier_pass_rate']):.3f} | {float(row['band_l1_mean']):.4f} | "
            f"{float(row['psd_w1_mean']):.3f} | {float(row['psd_w1_p90']):.3f} | "
            f"{float(env):.3f}" if env != "" else
            f"| {row['method']} | {row['class']} | {row['n']} | "
            f"{float(row['verifier_pass_rate']):.3f} | {float(row['band_l1_mean']):.4f} | "
            f"{float(row['psd_w1_mean']):.3f} | {float(row['psd_w1_p90']):.3f} |  | "
            f"{float(nn):.3f} |"
        )
        if env != "":
            lines[-1] += f" | {float(nn):.3f} |"
    lines.append("")
    lines.append("These are diagnostics only; they do not establish downstream superiority.")
    out_md.write_text("\n".join(lines) + "\n")
    print(json.dumps({"csv": str(out_csv.relative_to(ROOT)), "md": str(out_md.relative_to(ROOT))}, indent=2), flush=True)


if __name__ == "__main__":
    main()
