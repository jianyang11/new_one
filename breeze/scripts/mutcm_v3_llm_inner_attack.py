"""MU-TCM v3 LLM inner-validation attack.

This is an inner-val-only attack.  It never reads a formal held-out test and
does not run preregistration/formal evaluation unless the inner gate is met.
The LLM key is read only from the process environment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from scipy.stats import kurtosis, skew, spearmanr, wilcoxon
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "src"))

from config import LLM_BASE_URL, LLM_MIN_INTERVAL, LLM_MODEL  # noqa: E402


CLASSES = ["healthy", "worn"]
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}
BANDS_HZ = np.asarray(
    [
        [0.0, 20.0],
        [20.0, 50.0],
        [50.0, 100.0],
        [100.0, 200.0],
        [200.0, 400.0],
        [400.0, 650.0],
        [650.0, 850.0],
        [850.0, 1000.0],
    ],
    dtype=float,
)
GROUPS = {
    "force": ["Fx", "Fy", "Fz"],
    "vibration": ["Ax", "Ay", "Az"],
    "ae": ["AE_RMS"],
    "cnc": [
        "SREAL",
        "CV3_S",
        "CV3_X",
        "CV3_Y",
        "CV3_Z",
        "TV2_S",
        "TV2_X",
        "TV2_Y",
        "TV2_Z",
        "TV50",
        "TV51",
        "FREAL",
    ],
}
RECIPE_TYPES = ["prototype", "boundary", "condition_balanced"]


def stable_seed(*parts: Any) -> int:
    payload = json.dumps(tolist(parts), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "little")


def tolist(x: Any) -> Any:
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, dict):
        return {str(k): tolist(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [tolist(v) for v in x]
    return x


def safe_json(text: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def rms(x: np.ndarray, axis: int | tuple[int, ...] | None = None) -> np.ndarray:
    return np.sqrt(np.mean(np.asarray(x, dtype=float) ** 2, axis=axis))


def class_label(y: int) -> str:
    return CLASSES[int(y)]


def channel_group_indices(channels: list[str]) -> dict[str, list[int]]:
    out = {}
    for group, names in GROUPS.items():
        out[group] = [i for i, ch in enumerate(channels) if ch in names]
    return out


def window_stats(w: np.ndarray) -> np.ndarray:
    vals = []
    for ch in range(w.shape[0]):
        x = np.asarray(w[ch], dtype=float)
        sd = float(np.std(x))
        rr = float(rms(x))
        vals.extend(
            [
                float(np.mean(x)),
                sd,
                rr,
                float(np.ptp(x)),
                float(kurtosis(x, fisher=False)) if sd > 1e-12 else 3.0,
                float(skew(x)) if sd > 1e-12 else 0.0,
                float(np.max(np.abs(x)) / (rr + 1e-12)),
            ]
        )
    return np.asarray(vals, dtype=np.float32)


def band_fracs(w: np.ndarray, fs_hz: float) -> np.ndarray:
    n = w.shape[1]
    freqs = np.fft.rfftfreq(n, 1.0 / fs_hz)
    feats = []
    for ch in range(w.shape[0]):
        x = np.asarray(w[ch], dtype=float)
        x = x - np.mean(x)
        p = np.abs(np.fft.rfft(x * np.hanning(n))) ** 2
        total = float(np.sum(p) + 1e-30)
        fracs = []
        for lo, hi in BANDS_HZ:
            m = (freqs >= lo) & (freqs < hi)
            fracs.append(float(np.sum(p[m]) / total) if np.any(m) else 0.0)
        p_norm = p / total
        centroid = float(np.sum(freqs * p_norm))
        peak = float(freqs[int(np.argmax(p[1:]) + 1)]) if p.size > 1 else 0.0
        entropy = float(-(p_norm * np.log(p_norm + 1e-30)).sum() / np.log(len(p_norm) + 1e-30))
        feats.extend(fracs + [centroid / max(fs_hz / 2, 1e-12), peak / max(fs_hz / 2, 1e-12), entropy])
    return np.asarray(feats, dtype=np.float32)


def corr_upper(w: np.ndarray) -> np.ndarray:
    c = np.corrcoef(w)
    c = np.nan_to_num(c, nan=0.0, posinf=0.0, neginf=0.0)
    return c[np.triu_indices(w.shape[0], k=1)].astype(np.float32)


def feature_one(w: np.ndarray, fs_hz: float) -> np.ndarray:
    e = np.mean(w.astype(float) ** 2, axis=1)
    er = e / (e.sum() + 1e-30)
    return np.concatenate([window_stats(w), band_fracs(w, fs_hz), er.astype(np.float32), corr_upper(w)]).astype(np.float32)


def feature_matrix(X: np.ndarray, fs_hz: float) -> np.ndarray:
    return np.asarray([feature_one(w, fs_hz) for w in X], dtype=np.float32)


def robust_center_scale(vals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    vals = np.nan_to_num(vals.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    med = np.median(vals, axis=0)
    q25 = np.quantile(vals, 0.25, axis=0)
    q75 = np.quantile(vals, 0.75, axis=0)
    scale = (q75 - q25) / 1.349
    scale = np.where(scale > 1e-9, scale, np.std(vals, axis=0) + 1e-9)
    return med, scale


@dataclass
class DataBundle:
    X: np.ndarray
    y: np.ndarray
    fs_hz: float
    channels: list[str]
    file_name: np.ndarray
    sample_id: np.ndarray
    condition_id: np.ndarray
    insert_edge_id: np.ndarray
    split: np.ndarray
    rounded_vb: np.ndarray
    feature: np.ndarray

    @property
    def train_mask(self) -> np.ndarray:
        return self.split == "inner_train"

    @property
    def val_mask(self) -> np.ndarray:
        return self.split == "inner_val"


@dataclass
class AdmissionCalib:
    class_median: dict[str, np.ndarray]
    class_scale: dict[str, np.ndarray]
    class_axis_hi: dict[str, float]
    class_stat_lo: dict[str, np.ndarray]
    class_stat_hi: dict[str, np.ndarray]
    class_band_med: dict[str, np.ndarray]
    class_channel_mean: dict[str, np.ndarray]
    class_channel_std: dict[str, np.ndarray]
    class_identity_ratio_hi: dict[str, float]
    global_median: np.ndarray
    global_scale: np.ndarray
    min_nn_distance: float


def load_bundle(window_npz: Path, split_csv: Path, metadata_csv: Path, out_dir: Path) -> DataBundle:
    data = np.load(window_npz, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    channels = [str(x) for x in data["channels"]]
    fs_hz = float(data["fs_hz"])
    file_name = np.asarray([str(x) for x in data["file_name"]])
    sample_id = np.asarray([str(x) for x in data["sample_id"]])
    condition_id = np.asarray([str(x) for x in data["condition_id"]])
    insert_edge_id = np.asarray([str(x) for x in data["insert_edge_id"]])
    split_df = pd.read_csv(split_csv)
    meta_df = pd.read_csv(metadata_csv)
    split_map = dict(zip(split_df["file_name"], split_df["split"]))
    vb_map = dict(zip(meta_df["file_name"], meta_df["rounded_VB"]))
    split = np.asarray([split_map[str(f)] for f in file_name])
    rounded_vb = np.asarray([float(vb_map[str(f)]) for f in file_name], dtype=float)
    feature_path = out_dir / "mutcm_v3_window_features.npy"
    if feature_path.exists():
        F = np.load(feature_path)
    else:
        F = feature_matrix(X, fs_hz)
        np.save(feature_path, F)
    return DataBundle(X, y, fs_hz, channels, file_name, sample_id, condition_id, insert_edge_id, split, rounded_vb, F)


def write_split(bundle: DataBundle, out_dir: Path) -> None:
    rows = []
    for i in range(len(bundle.y)):
        rows.append(
            {
                "window_id": i,
                "sample_id": bundle.sample_id[i],
                "file_name": bundle.file_name[i],
                "split": bundle.split[i],
                "label": class_label(bundle.y[i]),
                "condition_id": bundle.condition_id[i],
                "insert_edge_id": bundle.insert_edge_id[i],
                "rounded_VB": bundle.rounded_vb[i],
            }
        )
    pd.DataFrame(rows).to_csv(out_dir / "mutcm_v3_inner_split_index.csv", index=False)
    exp_rows = []
    for fn in sorted(set(bundle.file_name)):
        m = bundle.file_name == fn
        exp_rows.append(
            {
                "file_name": fn,
                "split": sorted(set(bundle.split[m]))[0],
                "label": class_label(int(bundle.y[m][0])),
                "n_windows": int(m.sum()),
                "condition_id": str(bundle.condition_id[m][0]),
                "insert_edge_id": str(bundle.insert_edge_id[m][0]),
                "rounded_VB": float(bundle.rounded_vb[m][0]),
            }
        )
    exp = pd.DataFrame(exp_rows)
    leakage = exp.groupby("file_name")["split"].nunique().max()
    lines = [
        "# MU-TCM v3 Inner Split Report",
        "",
        "- Source: v2 fixed `mutcm_v2_inner_split_assignments.csv`; no split was selected from LLM results.",
        "- Group unit: MAT experiment/file; all windows from one MAT stay in one split.",
        f"- Window count: `{len(bundle.y)}`",
        f"- Experiment count: `{len(exp)}`",
        f"- Max split count per file: `{int(leakage)}`",
        "",
        "## Window Counts",
        "",
    ]
    for split_name in ["inner_train", "inner_val"]:
        m = bundle.split == split_name
        lines.append(f"- {split_name} labels: `{dict(Counter(class_label(v) for v in bundle.y[m]))}`")
        lines.append(f"- {split_name} conditions: `{dict(Counter(str(v) for v in bundle.condition_id[m]))}`")
        lines.append(f"- {split_name} insert_edge: `{dict(Counter(str(v) for v in bundle.insert_edge_id[m]))}`")
    lines.extend(["", "## Experiment Counts", ""])
    for split_name in ["inner_train", "inner_val"]:
        frame = exp[exp["split"] == split_name]
        lines.append(f"- {split_name} labels: `{dict(Counter(frame['label']))}`")
        lines.append(f"- {split_name} conditions: `{dict(Counter(frame['condition_id']))}`")
        lines.append(f"- {split_name} supports n_real=2/5/10 in train: `{split_name == 'inner_train' and min(Counter(frame['label']).values()) >= 10}`")
    (out_dir / "mutcm_v3_inner_split_report.md").write_text("\n".join(lines) + "\n")


def class_channel_stats(X: np.ndarray, channels: list[str], fs_hz: float) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    freqs = np.fft.rfftfreq(X.shape[2], 1.0 / fs_hz)
    for ci, ch in enumerate(channels):
        x = X[:, ci, :].astype(float)
        row = {
            "mean_median": float(np.median(np.mean(x, axis=1))),
            "std_median": float(np.median(np.std(x, axis=1))),
            "rms_median": float(np.median(rms(x, axis=1))),
            "ptp_median": float(np.median(np.ptp(x, axis=1))),
            "kurtosis_median": float(np.median([kurtosis(v, fisher=False) for v in x])),
            "skew_median": float(np.median([skew(v) for v in x])),
        }
        psd = []
        for v in x:
            vv = v - np.mean(v)
            psd.append(np.abs(np.fft.rfft(vv * np.hanning(len(vv)))) ** 2)
        med_psd = np.median(np.asarray(psd), axis=0)
        peaks = np.argsort(med_psd[1:])[-3:][::-1] + 1 if med_psd.size > 1 else []
        row["top_peaks_hz"] = [float(freqs[p]) for p in peaks]
        band_vals = []
        total = float(np.sum(med_psd) + 1e-30)
        for lo, hi in BANDS_HZ:
            m = (freqs >= lo) & (freqs < hi)
            band_vals.append(float(np.sum(med_psd[m]) / total) if np.any(m) else 0.0)
        row["band_energy_frac"] = band_vals
        rows[ch] = row
    return rows


def write_exemplar(bundle: DataBundle, out_dir: Path) -> dict[str, Any]:
    train = bundle.train_mask
    stats: dict[str, Any] = {
        "dataset": "MU-TCM full_dataset",
        "split": "inner_train only",
        "fs_hz": bundle.fs_hz,
        "window_length": int(bundle.X.shape[2]),
        "channels": bundle.channels,
        "classes": {},
        "class_difference": {},
        "monotonic_with_rounded_vb": [],
    }
    group_idx = channel_group_indices(bundle.channels)
    class_group_rms: dict[str, dict[str, float]] = {}
    for ci, cls in enumerate(CLASSES):
        m = train & (bundle.y == ci)
        Xc = bundle.X[m]
        stats["classes"][cls] = {
            "n_windows": int(len(Xc)),
            "n_experiments": int(len(set(bundle.file_name[m]))),
            "condition_distribution": dict(Counter(bundle.condition_id[m])),
            "channel_stats": class_channel_stats(Xc, bundle.channels, bundle.fs_hz),
        }
        class_group_rms[cls] = {}
        for group, idx in group_idx.items():
            if idx:
                class_group_rms[cls][group] = float(np.median(rms(Xc[:, idx, :], axis=(1, 2))))
    diff_rows = []
    for group in GROUPS:
        hv = class_group_rms["healthy"].get(group, np.nan)
        wv = class_group_rms["worn"].get(group, np.nan)
        diff_rows.append({"group": group, "healthy_rms": hv, "worn_rms": wv, "worn_over_healthy": float(wv / (hv + 1e-12))})
    stats["class_difference"]["group_rms"] = diff_rows
    exp_rows = []
    for fn in sorted(set(bundle.file_name[train])):
        m = train & (bundle.file_name == fn)
        exp_rows.append({"file_name": fn, "rounded_vb": float(bundle.rounded_vb[m][0]), "feature": np.mean(bundle.feature[m], axis=0)})
    if len(exp_rows) >= 8:
        vb = np.asarray([r["rounded_vb"] for r in exp_rows], dtype=float)
        F = np.stack([r["feature"] for r in exp_rows])
        cors = []
        for j in range(F.shape[1]):
            rho, p = spearmanr(vb, F[:, j])
            if np.isfinite(rho):
                cors.append((abs(float(rho)), float(rho), float(p), j))
        cors.sort(reverse=True)
        for _, rho, p, j in cors[:20]:
            stats["monotonic_with_rounded_vb"].append({"feature_index": int(j), "spearman_rho": rho, "p_value": p})
    (out_dir / "mutcm_v3_inner_train_exemplar_stats.json").write_text(json.dumps(tolist(stats), indent=2) + "\n")
    lines = [
        "# MU-TCM v3 Class Difference Report",
        "",
        "Stats use inner-train windows only. No formal held-out data is read.",
        "",
        "## Group RMS",
        "",
    ]
    for row in diff_rows:
        lines.append(
            f"- {row['group']}: healthy `{row['healthy_rms']:.6g}`, worn `{row['worn_rms']:.6g}`, ratio `{row['worn_over_healthy']:.3f}`"
        )
    lines.extend(["", "## Strongest Rounded-VB Monotonic Feature Indices", ""])
    for row in stats["monotonic_with_rounded_vb"][:10]:
        lines.append(f"- feature {row['feature_index']}: rho `{row['spearman_rho']:.3f}`, p `{row['p_value']:.4g}`")
    (out_dir / "mutcm_v3_class_difference_report.md").write_text("\n".join(lines) + "\n")
    return stats


def calibrate_admission(bundle: DataBundle) -> AdmissionCalib:
    train = bundle.train_mask
    F = bundle.feature[train]
    gmed, gscale = robust_center_scale(F)
    class_median, class_scale, class_axis_hi = {}, {}, {}
    class_stat_lo, class_stat_hi = {}, {}
    class_band_med, class_channel_mean, class_channel_std = {}, {}, {}
    class_identity_ratio_hi = {}
    for ci, cls in enumerate(CLASSES):
        m = train & (bundle.y == ci)
        Fc = bundle.feature[m]
        med, scale = robust_center_scale(Fc)
        dist = np.sqrt((((Fc - med) / scale) ** 2).sum(axis=1))
        class_median[cls] = med
        class_scale[cls] = scale
        class_axis_hi[cls] = float(np.quantile(dist, 0.995) * 1.15 + 1e-9)
        S = np.asarray([window_stats(w) for w in bundle.X[m]])
        class_stat_lo[cls] = np.quantile(S, 0.002, axis=0)
        class_stat_hi[cls] = np.quantile(S, 0.998, axis=0)
        bands = np.asarray([band_fracs(w, bundle.fs_hz).reshape(len(bundle.channels), -1)[:, : len(BANDS_HZ)] for w in bundle.X[m]])
        class_band_med[cls] = np.median(bands, axis=0)
        class_channel_mean[cls] = np.median(np.mean(bundle.X[m], axis=2), axis=0)
        class_channel_std[cls] = np.median(np.std(bundle.X[m], axis=2), axis=0)
    for ci, cls in enumerate(CLASSES):
        m = train & (bundle.y == ci)
        other_cls = "worn" if cls == "healthy" else "healthy"
        ratios = []
        for f in bundle.feature[m]:
            own = float(np.sqrt((((f - class_median[cls]) / class_scale[cls]) ** 2).sum()))
            other = float(np.sqrt((((f - class_median[other_cls]) / class_scale[other_cls]) ** 2).sum()))
            ratios.append(own / (other + 1e-12))
        class_identity_ratio_hi[cls] = float(np.quantile(ratios, 0.995) * 1.05 + 1e-9)
    Z = (F - gmed) / gscale
    nn_vals = []
    for i in range(len(Z)):
        d = np.sqrt(((Z - Z[i]) ** 2).sum(axis=1))
        d[i] = np.inf
        nn_vals.append(float(np.min(d)))
    min_nn_distance = float(np.quantile(nn_vals, 0.01) * 0.35) if nn_vals else 0.0
    return AdmissionCalib(
        class_median,
        class_scale,
        class_axis_hi,
        class_stat_lo,
        class_stat_hi,
        class_band_med,
        class_channel_mean,
        class_channel_std,
        class_identity_ratio_hi,
        gmed,
        gscale,
        min_nn_distance,
    )


def iaaft_surrogate(template: np.ndarray, rng: np.random.Generator, n_iter: int = 16) -> np.ndarray:
    x = np.asarray(template, dtype=float)
    x = x - np.mean(x)
    if np.std(x) < 1e-12:
        y = rng.normal(size=len(x))
        return y / (np.std(y) + 1e-12)
    target_sorted = np.sort(x)
    target_amp = np.abs(np.fft.rfft(x))
    y = rng.permutation(x)
    for _ in range(n_iter):
        phase = np.angle(np.fft.rfft(y))
        y = np.fft.irfft(target_amp * np.exp(1j * phase), n=len(x))
        order = np.argsort(y)
        yy = np.empty_like(y)
        yy[order] = target_sorted
        y = yy
    y = y - np.mean(y)
    return y / (np.std(y) + 1e-12)


def band_equalize(x: np.ndarray, fs_hz: float, target_frac: np.ndarray, strength: float) -> np.ndarray:
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength <= 0:
        return x
    dyn = np.asarray(x, dtype=float) - float(np.mean(x))
    n = len(dyn)
    F = np.fft.rfft(dyn)
    freqs = np.fft.rfftfreq(n, 1.0 / fs_hz)
    p = np.abs(F) ** 2
    cur = []
    for lo, hi in BANDS_HZ:
        m = (freqs >= lo) & (freqs < hi)
        cur.append(float(np.sum(p[m])) if np.any(m) else 0.0)
    cur = np.asarray(cur, dtype=float)
    cur = cur / (cur.sum() + 1e-30)
    tgt = np.asarray(target_frac, dtype=float)
    tgt = np.clip(tgt, 0, None)
    tgt = tgt / (tgt.sum() + 1e-30)
    gains = np.sqrt((tgt + 1e-8) / (cur + 1e-8))
    gains = np.exp(strength * np.log(np.clip(gains, 0.35, 2.85)))
    g = np.ones_like(freqs)
    for (lo, hi), gain in zip(BANDS_HZ, gains):
        g[(freqs >= lo) & (freqs < hi)] = gain
    out = np.fft.irfft(F * g, n=n)
    out -= np.mean(out)
    return out / (np.std(out) + 1e-12) * (np.std(dyn) + 1e-12)


def normalize_recipe(raw: dict[str, Any] | None, target_class: str, recipe_type: str, condition_id: str) -> dict[str, Any] | None:
    if raw is None:
        return None
    def f(name: str, default: float, lo: float, hi: float) -> float:
        try:
            val = float(raw.get(name, default))
        except (TypeError, ValueError):
            val = default
        return float(np.clip(val, lo, hi))

    def group_dict(name: str, default: float, lo: float, hi: float) -> dict[str, float]:
        src = raw.get(name, {})
        if not isinstance(src, dict):
            src = {}
        return {g: float(np.clip(float(src.get(g, default)), lo, hi)) for g in GROUPS}

    try:
        template_rank = int(raw.get("template_rank", 0))
    except (TypeError, ValueError):
        template_rank = 0
    out = {
        "class": target_class,
        "recipe_type": recipe_type,
        "condition_id": str(raw.get("condition_id", condition_id) or condition_id),
        "template_rank": int(np.clip(template_rank, 0, 200)),
        "group_std_mult": group_dict("group_std_mult", 1.0, 0.82, 1.24),
        "group_mean_mult": group_dict("group_mean_mult", 1.0, 0.92, 1.08),
        "high_freq_gain": group_dict("high_freq_gain", 1.0, 0.75, 1.32),
        "low_freq_gain": group_dict("low_freq_gain", 1.0, 0.75, 1.32),
        "band_eq_strength": f("band_eq_strength", 0.35, 0.0, 0.85),
        "noise_gain": f("noise_gain", 0.015, 0.0, 0.09),
        "impulse_rate_hz": f("impulse_rate_hz", 0.0, 0.0, 18.0),
        "impulse_amp_std": f("impulse_amp_std", 0.0, 0.0, 0.65),
        "trend_strength": f("trend_strength", 0.0, -0.055, 0.055),
        "shared_gain": f("shared_gain", 0.0, 0.0, 0.12),
        "spectral_mix": f("spectral_mix", 0.20, 0.0, 0.75),
        "rationale": str(raw.get("rationale", ""))[:300],
    }
    return out


def recipe_prompt(
    target_class: str,
    recipe_type: str,
    condition_id: str,
    exemplar: dict[str, Any],
    slot: int,
    prototype_rows: list[dict[str, Any]],
) -> str:
    groups = exemplar["class_difference"]["group_rms"]
    class_counts = {
        cls: {
            "n_windows": exemplar["classes"][cls]["n_windows"],
            "conditions": exemplar["classes"][cls]["condition_distribution"],
        }
        for cls in CLASSES
    }
    schema = {
        "class": target_class,
        "recipe_type": recipe_type,
        "condition_id": condition_id,
        "template_rank": 0,
        "group_std_mult": {"force": 1.0, "vibration": 1.0, "ae": 1.0, "cnc": 1.0},
        "group_mean_mult": {"force": 1.0, "vibration": 1.0, "ae": 1.0, "cnc": 1.0},
        "high_freq_gain": {"force": 1.0, "vibration": 1.0, "ae": 1.0, "cnc": 1.0},
        "low_freq_gain": {"force": 1.0, "vibration": 1.0, "ae": 1.0, "cnc": 1.0},
        "band_eq_strength": 0.35,
        "noise_gain": 0.02,
        "impulse_rate_hz": 0.0,
        "impulse_amp_std": 0.0,
        "trend_strength": 0.0,
        "shared_gain": 0.02,
        "spectral_mix": 0.20,
        "rationale": "short train-statistics rationale",
    }
    if target_class == "healthy":
        bounds = (
            "healthy should remain stable: group_std_mult usually 0.88-1.08, "
            "noise_gain <=0.04, impulse_amp_std <=0.10, trend close to zero. "
            "For boundary recipes near VB 0.1, mild fluctuation is allowed but do not make it worn-like."
        )
    else:
        bounds = (
            "worn should be separable but still feasible: group_std_mult usually 0.96-1.18, "
            "allow stronger force/vibration/AE texture when train differences support it, "
            "noise_gain <=0.07, impulse_amp_std <=0.45, trend may be nonzero but small."
        )
    if recipe_type == "condition_balanced":
        objective = "Preserve the named condition and make a class-balanced synthetic support point for that condition."
    elif recipe_type == "boundary":
        objective = "Create a hard but correctly labeled boundary support point around rounded VB 0.1/0.2 without crossing class identity."
    else:
        objective = "Create a local prototype-conditioned support point around train exemplars without copying a window."
    return (
        "You are designing compact synthetic recipes for MU-TCM CNC face-milling condition monitoring. "
        "Return exactly one JSON object and no markdown. The renderer uses inner-train exemplar PSDs and channel statistics; "
        "you only choose multipliers and texture controls, not a waveform. "
        f"Target class: {target_class}. Recipe type: {recipe_type}. Target condition_id: {condition_id}. Slot: {slot}. "
        f"Objective: {objective} "
        "Allowed channel groups are force=(Fx,Fy,Fz), vibration=(Ax,Ay,Az), ae=(AE_RMS), cnc=(spindle/current/torque/power channels). "
        f"Train-only class counts and conditions: {json.dumps(class_counts, separators=(',', ':'))}. "
        f"Train-only worn/healthy group RMS comparison: {json.dumps(groups, separators=(',', ':'))}. "
        f"Prototype candidates for this target class/condition: {json.dumps(prototype_rows[:8], separators=(',', ':'))}. "
        f"Physical bounds: {bounds} "
        "Do not use filename, VB, insert, edge, repetition, material, Vc, fz, ap, or ae as model features. "
        "The recipe must stay inside train-supported ranges and be class-specific; avoid neutral all-ones recipes. "
        f"Output JSON exactly matching this schema: {json.dumps(schema, separators=(',', ':'))}"
    )


def chat_api(
    messages: list[dict[str, str]],
    api_key: str,
    counter: dict[str, Any],
    max_api_requests: int,
    api_rows: list[dict[str, Any]],
    meta: dict[str, Any],
    temperature: float = 0.75,
    max_tokens: int = 1000,
) -> str:
    last_error = ""
    for attempt in range(3):
        if counter["requests"] >= max_api_requests:
            raise RuntimeError("API request budget exhausted")
        dt = LLM_MIN_INTERVAL - (time.time() - counter.get("last_call", 0.0))
        if dt > 0:
            time.sleep(dt)
        counter["last_call"] = time.time()
        counter["requests"] += 1
        rec = dict(meta)
        rec.update({"attempt": attempt + 1, "request_index": counter["requests"], "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
        try:
            r = requests.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "enable_thinking": False,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
                timeout=300,
            )
            status = int(r.status_code)
            d = r.json()
            if status >= 400 or "choices" not in d:
                raise RuntimeError(str(d)[:500])
            rec.update({"status": "ok", "http_status": status})
            api_rows.append(rec)
            return str(d["choices"][0]["message"]["content"])
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)[:500]
            rec.update({"status": "error", "error": last_error})
            api_rows.append(rec)
            time.sleep(2**attempt)
    raise RuntimeError(last_error)


def select_template(bundle: DataBundle, label: int, condition_id: str, rank: int, seed: int) -> np.ndarray:
    train = bundle.train_mask
    cand = np.where(train & (bundle.y == label) & (bundle.condition_id == condition_id))[0]
    if len(cand) == 0:
        cand = np.where(train & (bundle.y == label))[0]
    if len(cand) == 0:
        raise RuntimeError("no train template candidates")
    rng = np.random.default_rng(seed)
    ordered = cand[np.argsort(np.linalg.norm(bundle.feature[cand] - np.median(bundle.feature[cand], axis=0), axis=1))]
    idx = int(ordered[int(rank) % len(ordered)]) if len(ordered) else int(rng.choice(cand))
    return bundle.X[idx]


def render_recipe(
    recipe: dict[str, Any],
    bundle: DataBundle,
    calib: AdmissionCalib,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    channels = bundle.channels
    group_idx = channel_group_indices(channels)
    cls = str(recipe["class"])
    label = CLASS_TO_ID[cls]
    template = select_template(bundle, label, str(recipe["condition_id"]), int(recipe["template_rank"]), seed)
    n_ch, n = template.shape
    out = np.zeros_like(template, dtype=float)
    std_target = np.asarray(calib.class_channel_std[cls], dtype=float).copy()
    mean_target = np.asarray(calib.class_channel_mean[cls], dtype=float).copy()
    for group, idx in group_idx.items():
        std_target[idx] *= float(recipe["group_std_mult"][group])
        mean_target[idx] *= float(recipe["group_mean_mult"][group])
    for ch in range(n_ch):
        group = next(g for g, idx in group_idx.items() if ch in idx)
        x = iaaft_surrogate(template[ch], rng)
        target_band = np.asarray(calib.class_band_med[cls][ch], dtype=float).copy()
        lo = float(recipe["low_freq_gain"][group])
        hi = float(recipe["high_freq_gain"][group])
        target_band[:3] *= lo
        target_band[5:] *= hi
        target_band = target_band / (target_band.sum() + 1e-30)
        x = band_equalize(x, bundle.fs_hz, target_band, float(recipe["band_eq_strength"]))
        if recipe["spectral_mix"] > 0:
            x2 = iaaft_surrogate(template[ch], rng)
            x = (1.0 - float(recipe["spectral_mix"])) * x + float(recipe["spectral_mix"]) * x2
        noise = rng.normal(size=n)
        if recipe["noise_gain"] > 0:
            x += float(recipe["noise_gain"]) * noise
        trend = np.linspace(-1, 1, n)
        x += float(recipe["trend_strength"]) * trend
        if recipe["impulse_rate_hz"] > 0 and group in {"force", "vibration", "ae"}:
            expected = float(recipe["impulse_rate_hz"]) * n / bundle.fs_hz
            k = int(rng.poisson(expected))
            for _ in range(k):
                pos = int(rng.integers(0, n))
                width = int(rng.integers(3, 25))
                end = min(n, pos + width)
                if end > pos:
                    decay = np.exp(-np.linspace(0, 4, end - pos))
                    x[pos:end] += float(recipe["impulse_amp_std"]) * rng.choice([-1.0, 1.0]) * decay
        x -= np.mean(x)
        x = x / (np.std(x) + 1e-12) * max(std_target[ch], 1e-9)
        x += mean_target[ch]
        out[ch] = x
    shared_gain = float(recipe["shared_gain"])
    if shared_gain > 0:
        shared = rng.normal(size=n)
        shared = (shared - shared.mean()) / (shared.std() + 1e-12)
        out += shared_gain * std_target[:, None] * shared[None, :]
    return out.astype(np.float32)


def admit_window(w: np.ndarray, cls: str, bundle: DataBundle, calib: AdmissionCalib) -> tuple[bool, list[str], dict[str, Any]]:
    reasons = []
    if w.shape != (len(bundle.channels), int(bundle.fs_hz)):
        reasons.append(f"shape {w.shape} mismatch")
    if not np.all(np.isfinite(w)):
        reasons.append("nonfinite")
    if reasons:
        return False, reasons, {}
    st = window_stats(w)
    lo = calib.class_stat_lo[cls]
    hi = calib.class_stat_hi[cls]
    stat_ok = bool(np.mean((st >= lo) & (st <= hi)) >= 0.94)
    if not stat_ok:
        reasons.append("too many channel stats outside train-supported quantiles")
    f = feature_one(w, bundle.fs_hz)
    own = float(np.sqrt((((f - calib.class_median[cls]) / calib.class_scale[cls]) ** 2).sum()))
    other_cls = "worn" if cls == "healthy" else "healthy"
    other = float(np.sqrt((((f - calib.class_median[other_cls]) / calib.class_scale[other_cls]) ** 2).sum()))
    if own > calib.class_axis_hi[cls]:
        reasons.append(f"own_axis {own:.3f}>{calib.class_axis_hi[cls]:.3f}")
    ratio = own / (other + 1e-12)
    if ratio > calib.class_identity_ratio_hi[cls]:
        reasons.append(f"class_identity ratio={ratio:.3f}>{calib.class_identity_ratio_hi[cls]:.3f} own={own:.3f} other={other:.3f}")
    train_z = (bundle.feature[bundle.train_mask] - calib.global_median) / calib.global_scale
    z = (f - calib.global_median) / calib.global_scale
    nn = float(np.min(np.sqrt(((train_z - z) ** 2).sum(axis=1)))) if len(train_z) else np.inf
    if nn < calib.min_nn_distance:
        reasons.append(f"too_close_to_train nn={nn:.4f}<min={calib.min_nn_distance:.4f}")
    info = {
        "own_axis": own,
        "other_axis": other,
        "identity_ratio": ratio,
        "identity_ratio_hi": calib.class_identity_ratio_hi[cls],
        "nn_feature_dist": nn,
        "stat_pass_fraction": float(np.mean((st >= lo) & (st <= hi))),
    }
    return len(reasons) == 0, reasons, info


def prototype_candidates(bundle: DataBundle, target_class: str, condition_id: str, limit: int = 10) -> list[dict[str, Any]]:
    label = CLASS_TO_ID[target_class]
    train = bundle.train_mask
    cand = np.where(train & (bundle.y == label) & (bundle.condition_id == condition_id))[0]
    if len(cand) == 0:
        cand = np.where(train & (bundle.y == label))[0]
    F = bundle.feature[cand]
    med = np.median(F, axis=0)
    order = np.argsort(np.linalg.norm(F - med, axis=1))
    rows = []
    for rank, local in enumerate(order[:limit]):
        idx = int(cand[int(local)])
        rows.append(
            {
                "template_rank": int(rank),
                "sample_id": str(bundle.sample_id[idx]),
                "condition_id": str(bundle.condition_id[idx]),
                "group_rms": {
                    group: float(rms(bundle.X[idx, channel_group_indices(bundle.channels)[group], :]))
                    for group in GROUPS
                    if channel_group_indices(bundle.channels)[group]
                },
            }
        )
    return rows


def build_pool_from_saved(pool_dir: Path, out_path: Path) -> dict[str, Any]:
    rows = []
    Xs, ys = [], []
    manifest = pool_dir / "manifest.csv"
    if manifest.exists():
        rows = list(csv.DictReader(manifest.open(newline="")))
    for row in rows:
        path = ROOT / row["path"]
        if path.exists():
            Xs.append(np.load(path).astype(np.float32))
            ys.append(CLASS_TO_ID[row["class"]])
    X = np.stack(Xs).astype(np.float32) if Xs else np.zeros((0, 19, 2000), dtype=np.float32)
    y = np.asarray(ys, dtype=np.int64)
    np.savez_compressed(out_path, X=X, y=y, class_names=np.asarray(CLASSES))
    return {"n": int(len(y)), "counts": {cls: int((y == i).sum()) for i, cls in enumerate(CLASSES)}}


def generate_llm_pool(
    bundle: DataBundle,
    exemplar: dict[str, Any],
    calib: AdmissionCalib,
    out_dir: Path,
    max_api_requests: int,
    target_per_class: int,
    expansions: int,
    prepare_only: bool,
    readmit_existing: bool,
) -> dict[str, Any]:
    pool_dir = out_dir / "synthetic_llm"
    pool_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = pool_dir / "manifest.csv"
    manifest_rows = list(csv.DictReader(manifest_path.open(newline=""))) if manifest_path.exists() else []
    accepted_counts = Counter(row["class"] for row in manifest_rows)
    api_rows: list[dict[str, Any]] = []
    counter = {"requests": 0, "last_call": 0.0}
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("MIMO_API_KEY")
    prompt_log = out_dir / "mutcm_v3_prompt_log.md"
    if not prompt_log.exists():
        prompt_log.write_text("# MU-TCM v3 Prompt Log\n\n")
    with prompt_log.open("a") as f:
        f.write(f"\n## Run {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    conditions = sorted(set(bundle.condition_id[bundle.train_mask]))
    if not manifest_path.exists():
        with manifest_path.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=["path", "class", "slot", "recipe_type", "condition_id", "recipe_path"]).writeheader()

    def readmit_recipe_file(rec_path: Path) -> None:
        nonlocal accepted_counts
        parts = rec_path.stem.split("_")
        if len(parts) < 4:
            return
        slot_id = int(parts[1])
        cls_name = parts[2]
        recipe_type_name = "_".join(parts[3:])
        rec_obj = json.loads(rec_path.read_text())
        recipe = rec_obj.get("recipe")
        already = rec_obj.get("accepted", [])
        if recipe is None or already:
            return
        condition_name = str(recipe.get("condition_id", ""))
        rec_obj["readmission_rejected"] = []
        rec_obj["accepted"] = []
        for exp in range(expansions):
            seed = stable_seed("mutcm_v3_readmit", cls_name, recipe_type_name, condition_name, slot_id, exp)
            w = render_recipe(recipe, bundle, calib, seed)
            ok, reasons, info = admit_window(w, cls_name, bundle, calib)
            row = {"expansion": exp, "ok": ok, "reasons": reasons, "scores": info, "readmit": True}
            if ok:
                rel = Path("breeze") / "results" / out_dir.name / "synthetic_llm" / f"llm_{cls_name}_{slot_id:04d}_readmit_e{exp}.npy"
                np.save(ROOT / rel, w)
                with manifest_path.open("a", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["path", "class", "slot", "recipe_type", "condition_id", "recipe_path"])
                    writer.writerow(
                        {
                            "path": str(rel),
                            "class": cls_name,
                            "slot": slot_id,
                            "recipe_type": recipe_type_name,
                            "condition_id": condition_name,
                            "recipe_path": str(rec_path.relative_to(ROOT)),
                        }
                    )
                accepted_counts[cls_name] += 1
                row["path"] = str(rel)
                rec_obj["accepted"].append(row)
            else:
                rec_obj["readmission_rejected"].append(row)
        rec_obj["accepted_count"] = len(rec_obj.get("accepted", []))
        rec_path.write_text(json.dumps(tolist(rec_obj), indent=2) + "\n")

    if readmit_existing:
        for existing_recipe in sorted(pool_dir.glob("recipe_*.json")):
            readmit_recipe_file(existing_recipe)

    if prepare_only or max_api_requests <= 0:
        log_path = out_dir / "mutcm_v3_api_log.md"
        new_log = not log_path.exists()
        with log_path.open("a") as f:
            if new_log:
                f.write("# MU-TCM v3 API Log\n\n")
            f.write(f"\n## Run {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("- prepare-only/readmit-only or zero max_api_requests; no new API calls were made.\n")
        summary = build_pool_from_saved(pool_dir, out_dir / "mutcm_v3_llm_synthetic_pool.npz")
        summary["api_requests"] = 0
        return summary
    if not api_key:
        raise SystemExit("Set DASHSCOPE_API_KEY or MIMO_API_KEY in the environment; the key is not read from files.")
    slot = 0
    max_slots = max_api_requests
    while min(accepted_counts.get(c, 0) for c in CLASSES) < target_per_class and counter["requests"] < max_api_requests and slot < max_slots:
        cls = min(CLASSES, key=lambda c: (accepted_counts.get(c, 0), c))
        recipe_type = RECIPE_TYPES[slot % len(RECIPE_TYPES)]
        condition = conditions[slot % len(conditions)]
        proto = prototype_candidates(bundle, cls, condition)
        rec_path = pool_dir / f"recipe_{slot:04d}_{cls}_{recipe_type}.json"
        if rec_path.exists():
            if readmit_existing:
                rec_obj = json.loads(rec_path.read_text())
                recipe = rec_obj.get("recipe")
                already = rec_obj.get("accepted", [])
                if recipe is not None and not already:
                    rec_obj["readmission_rejected"] = []
                    rec_obj["accepted"] = []
                    for exp in range(expansions):
                        seed = stable_seed("mutcm_v3_readmit", cls, recipe_type, condition, slot, exp)
                        w = render_recipe(recipe, bundle, calib, seed)
                        ok, reasons, info = admit_window(w, cls, bundle, calib)
                        row = {"expansion": exp, "ok": ok, "reasons": reasons, "scores": info, "readmit": True}
                        if ok:
                            rel = Path("breeze") / "results" / out_dir.name / "synthetic_llm" / f"llm_{cls}_{slot:04d}_readmit_e{exp}.npy"
                            np.save(ROOT / rel, w)
                            with manifest_path.open("a", newline="") as f:
                                writer = csv.DictWriter(f, fieldnames=["path", "class", "slot", "recipe_type", "condition_id", "recipe_path"])
                                writer.writerow(
                                    {
                                        "path": str(rel),
                                        "class": cls,
                                        "slot": slot,
                                        "recipe_type": recipe_type,
                                        "condition_id": condition,
                                        "recipe_path": str(rec_path.relative_to(ROOT)),
                                    }
                                )
                            accepted_counts[cls] += 1
                            row["path"] = str(rel)
                            rec_obj["accepted"].append(row)
                        else:
                            rec_obj["readmission_rejected"].append(row)
                    rec_obj["accepted_count"] = len(rec_obj.get("accepted", []))
                    rec_path.write_text(json.dumps(tolist(rec_obj), indent=2) + "\n")
            slot += 1
            continue
        user = recipe_prompt(cls, recipe_type, condition, exemplar, slot, proto)
        with prompt_log.open("a") as f:
            f.write(f"## slot {slot} class={cls} type={recipe_type}\n\n```text\n{user}\n```\n\n")
        messages = [
            {"role": "system", "content": "You are an expert CNC milling condition-monitoring signal designer. Respond only with valid JSON."},
            {"role": "user", "content": user},
        ]
        text = chat_api(messages, api_key, counter, max_api_requests, api_rows, {"slot": slot, "class": cls, "recipe_type": recipe_type})
        raw = safe_json(text)
        recipe = normalize_recipe(raw, cls, recipe_type, condition)
        history = {"raw_response": text, "recipe": recipe, "accepted": [], "rejected": []}
        if recipe is not None:
            for exp in range(expansions):
                seed = stable_seed("mutcm_v3", cls, recipe_type, condition, slot, exp)
                w = render_recipe(recipe, bundle, calib, seed)
                ok, reasons, info = admit_window(w, cls, bundle, calib)
                row = {"expansion": exp, "ok": ok, "reasons": reasons, "scores": info}
                if ok:
                    rel = Path("breeze") / "results" / out_dir.name / "synthetic_llm" / f"llm_{cls}_{slot:04d}_e{exp}.npy"
                    np.save(ROOT / rel, w)
                    with manifest_path.open("a", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=["path", "class", "slot", "recipe_type", "condition_id", "recipe_path"])
                        writer.writerow(
                            {
                                "path": str(rel),
                                "class": cls,
                                "slot": slot,
                                "recipe_type": recipe_type,
                                "condition_id": condition,
                                "recipe_path": str((rec_path.relative_to(ROOT))),
                            }
                        )
                    accepted_counts[cls] += 1
                    row["path"] = str(rel)
                    history["accepted"].append(row)
                else:
                    history["rejected"].append(row)
        history["accepted_count"] = len(history["accepted"])
        rec_path.write_text(json.dumps(tolist(history), indent=2) + "\n")
        slot += 1
    log_path = out_dir / "mutcm_v3_api_log.md"
    new_log = not log_path.exists()
    with log_path.open("a") as f:
        if new_log:
            f.write("# MU-TCM v3 API Log\n\n")
        f.write(f"\n## Run {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"- Base URL: `{LLM_BASE_URL}`\n")
        f.write(f"- Model: `{LLM_MODEL}`\n")
        f.write(f"- Min interval seconds: `{LLM_MIN_INTERVAL}`\n")
        f.write(f"- Requests counted this run: `{counter['requests']}`\n")
        f.write(f"- Max API requests: `{max_api_requests}`\n")
        f.write("- API key is read from environment and never written.\n\n")
        for row in api_rows:
            f.write("- " + json.dumps(tolist(row), ensure_ascii=False, sort_keys=True) + "\n")
    summary = build_pool_from_saved(pool_dir, out_dir / "mutcm_v3_llm_synthetic_pool.npz")
    summary["api_requests"] = int(counter["requests"])
    return summary


def generate_noapi_pool(bundle: DataBundle, calib: AdmissionCalib, out_dir: Path, source: str, per_class: int = 80) -> dict[str, Any]:
    rng = np.random.default_rng(stable_seed("mutcm_v3", source))
    Xs, ys = [], []
    for cls in CLASSES:
        label = CLASS_TO_ID[cls]
        conditions = sorted(set(bundle.condition_id[bundle.train_mask & (bundle.y == label)]))
        attempts = 0
        while sum(int(v == label) for v in ys) < per_class and attempts < per_class * 20:
            condition = conditions[attempts % len(conditions)] if conditions else sorted(set(bundle.condition_id[bundle.train_mask]))[0]
            if source == "rule":
                recipe = {
                    "class": cls,
                    "condition_id": condition,
                    "template_rank": attempts,
                    "group_std_mult": {g: 1.0 for g in GROUPS},
                    "group_mean_mult": {g: 1.0 for g in GROUPS},
                    "high_freq_gain": {g: 1.0 for g in GROUPS},
                    "low_freq_gain": {g: 1.0 for g in GROUPS},
                    "band_eq_strength": 0.55,
                    "noise_gain": 0.005,
                    "impulse_rate_hz": 0.0,
                    "impulse_amp_std": 0.0,
                    "trend_strength": 0.0,
                    "shared_gain": 0.02,
                    "spectral_mix": 0.10,
                }
            else:
                recipe = {
                    "class": cls,
                    "condition_id": condition,
                    "template_rank": int(rng.integers(0, 100)),
                    "group_std_mult": {g: float(rng.uniform(0.80, 1.25)) for g in GROUPS},
                    "group_mean_mult": {g: float(rng.uniform(0.90, 1.10)) for g in GROUPS},
                    "high_freq_gain": {g: float(rng.uniform(0.70, 1.35)) for g in GROUPS},
                    "low_freq_gain": {g: float(rng.uniform(0.70, 1.35)) for g in GROUPS},
                    "band_eq_strength": float(rng.uniform(0.0, 0.65)),
                    "noise_gain": float(rng.uniform(0.0, 0.09)),
                    "impulse_rate_hz": float(rng.uniform(0.0, 16.0)),
                    "impulse_amp_std": float(rng.uniform(0.0, 0.55)),
                    "trend_strength": float(rng.uniform(-0.04, 0.04)),
                    "shared_gain": float(rng.uniform(0.0, 0.12)),
                    "spectral_mix": float(rng.uniform(0.0, 0.75)),
            }
            w = render_recipe(recipe, bundle, calib, stable_seed(source, cls, attempts))
            ok = bool(w.shape == (len(bundle.channels), int(bundle.fs_hz)) and np.all(np.isfinite(w)))
            if source == "LLM_synthetic":
                ok, _, _ = admit_window(w, cls, bundle, calib)
            if ok or source == "random_open_loop":
                Xs.append(w)
                ys.append(label)
            attempts += 1
    X = np.stack(Xs).astype(np.float32) if Xs else np.zeros((0, len(bundle.channels), int(bundle.fs_hz)), dtype=np.float32)
    y = np.asarray(ys, dtype=np.int64)
    path = out_dir / f"mutcm_v3_{source}_pool.npz"
    np.savez_compressed(path, X=X, y=y, class_names=np.asarray(CLASSES))
    return {"path": str(path), "n": int(len(y)), "counts": {cls: int((y == i).sum()) for i, cls in enumerate(CLASSES)}}


def summarize_synthetic(bundle: DataBundle, out_dir: Path, pools: dict[str, dict[str, Any]]) -> None:
    rows = []
    for source, info in pools.items():
        path = Path(info["path"]) if "path" in info else out_dir / "mutcm_v3_llm_synthetic_pool.npz"
        if not path.exists():
            continue
        data = np.load(path, allow_pickle=True)
        X = data["X"].astype(np.float32)
        y = data["y"].astype(np.int64)
        for ci, cls in enumerate(CLASSES):
            m = y == ci
            if not np.any(m):
                continue
            rows.append(
                {
                    "source": source,
                    "class": cls,
                    "n": int(m.sum()),
                    "median_total_rms": float(np.median(rms(X[m], axis=(1, 2)))),
                    "median_abs_mean": float(np.median(np.abs(np.mean(X[m], axis=(1, 2))))),
                    "nan_inf": int((~np.isfinite(X[m])).sum()),
                }
            )
    pd.DataFrame(rows).to_csv(out_dir / "mutcm_v3_synthetic_pool_stats.csv", index=False)
    lines = ["# MU-TCM v3 Synthetic Admission Report", ""]
    for source, info in pools.items():
        lines.append(f"- {source}: `{info}`")
    lines.append("")
    lines.append("LLM_synthetic admission uses inner-train class statistics, feature-axis distance, class-identity distance, and nearest-neighbor anti-copy distance.")
    lines.append("No-API rule/random pools are baseline generators; they are checked for shape/finite values and are not used as admission-tuning feedback.")
    (out_dir / "mutcm_v3_synthetic_admission_report.md").write_text("\n".join(lines) + "\n")


def augment_noise(X: np.ndarray, n_per_class: int, rng: np.random.Generator) -> np.ndarray:
    if len(X) == 0:
        return X
    std = X.std(axis=(0, 2), keepdims=True) + 1e-8
    idx = rng.choice(np.arange(len(X)), n_per_class, replace=True)
    base = X[idx]
    scale = rng.normal(1.0, 0.04, size=(len(base), 1, 1)).astype(np.float32)
    jitter = rng.normal(0.0, 0.03, size=base.shape).astype(np.float32) * std
    return (base * scale + jitter).astype(np.float32)


def sample_pool_features(pool: dict[str, Any], fs_hz: float, n_per_class: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    X = pool["X"]
    y = pool["y"]
    keep = []
    for ci in range(len(CLASSES)):
        idx = np.where(y == ci)[0]
        if len(idx):
            keep.extend(rng.choice(idx, min(n_per_class, len(idx)), replace=False))
    keep = np.asarray(keep, dtype=int)
    if len(keep) == 0:
        return np.zeros((0, pool["F"].shape[1]), dtype=np.float32), np.zeros((0,), dtype=np.int64)
    return pool["F"][keep], y[keep]


def load_pool_features(path: Path, fs_hz: float) -> dict[str, Any]:
    data = np.load(path, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    F = feature_matrix(X, fs_hz) if len(X) else np.zeros((0, 1), dtype=np.float32)
    return {"X": X, "y": y, "F": F}


def experiment_choices(bundle: DataBundle, n_real: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(1000 * n_real + seed)
    files = []
    for ci in range(len(CLASSES)):
        train_files = sorted(set(bundle.file_name[bundle.train_mask & (bundle.y == ci)]))
        take = min(n_real, len(train_files))
        files.extend(rng.choice(train_files, take, replace=False).tolist())
    files = np.asarray(files)
    return np.isin(bundle.file_name, files) & bundle.train_mask


def evaluate_inner(
    bundle: DataBundle,
    pools: dict[str, dict[str, Any]],
    out_dir: Path,
    seeds: int,
    n_real_values: list[int],
    n_syn_values: list[int],
) -> pd.DataFrame:
    rows = []
    per_rows = []
    cond_rows = []
    val = bundle.val_mask
    Xv = bundle.feature[val]
    yv = bundle.y[val]
    for n_real in n_real_values:
        for seed in range(seeds):
            real_mask = experiment_choices(bundle, n_real, seed)
            Fr = bundle.feature[real_mask]
            yr = bundle.y[real_mask]
            rng = np.random.default_rng(9000 + 100 * n_real + seed)
            noise_feats_by_n = {}
            for n_syn in n_syn_values:
                X_noise, y_noise = [], []
                for ci in range(len(CLASSES)):
                    Xc = bundle.X[real_mask & (bundle.y == ci)]
                    Xa = augment_noise(Xc, n_syn, rng)
                    X_noise.append(Xa)
                    y_noise.append(np.full(len(Xa), ci, dtype=np.int64))
                Xn = np.concatenate(X_noise).astype(np.float32) if X_noise else np.zeros((0,) + bundle.X.shape[1:], dtype=np.float32)
                yn = np.concatenate(y_noise).astype(np.int64) if y_noise else np.zeros((0,), dtype=np.int64)
                noise_feats_by_n[n_syn] = (feature_matrix(Xn, bundle.fs_hz), yn)
            for n_syn in n_syn_values:
                methods = {"real_only": (Fr, yr, 0)}
                Fn, yn = noise_feats_by_n[n_syn]
                methods["noise_aug"] = (np.concatenate([Fr, Fn]), np.concatenate([yr, yn]), len(yn))
                for method in ["rule", "random_open_loop", "LLM_synthetic"]:
                    Fp, yp = sample_pool_features(pools[method], bundle.fs_hz, n_syn, rng)
                    methods[method] = (np.concatenate([Fr, Fp]), np.concatenate([yr, yp]), len(yp))
                for method, (Ft, yt, actual_syn) in methods.items():
                    clf = ExtraTreesClassifier(
                        n_estimators=400,
                        random_state=stable_seed("clf", method, n_real, n_syn, seed),
                        max_features="sqrt",
                        class_weight="balanced",
                        min_samples_leaf=1,
                    )
                    clf.fit(Ft, yt)
                    pred = clf.predict(Xv)
                    acc = float(accuracy_score(yv, pred))
                    macro = float(f1_score(yv, pred, average="macro", zero_division=0))
                    per = f1_score(yv, pred, average=None, labels=list(range(len(CLASSES))), zero_division=0)
                    cm = confusion_matrix(yv, pred, labels=list(range(len(CLASSES))))
                    rows.append(
                        {
                            "method": method,
                            "n_real": n_real,
                            "n_syn": n_syn,
                            "seed": seed,
                            "actual_syn": int(actual_syn),
                            "acc": acc,
                            "macro_f1": macro,
                            "confusion_json": json.dumps(cm.tolist(), separators=(",", ":")),
                        }
                    )
                    for ci, cls in enumerate(CLASSES):
                        per_rows.append({"method": method, "n_real": n_real, "n_syn": n_syn, "seed": seed, "class": cls, "f1": float(per[ci])})
                    for cond in sorted(set(bundle.condition_id[val])):
                        m = val & (bundle.condition_id == cond)
                        local_pred = pred[bundle.condition_id[val] == cond]
                        local_y = bundle.y[m]
                        cond_rows.append(
                            {
                                "method": method,
                                "n_real": n_real,
                                "n_syn": n_syn,
                                "seed": seed,
                                "condition_id": cond,
                                "n": int(len(local_y)),
                                "acc": float(accuracy_score(local_y, local_pred)) if len(local_y) else np.nan,
                                "macro_f1": float(f1_score(local_y, local_pred, average="macro", zero_division=0)) if len(local_y) else np.nan,
                            }
                        )
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "mutcm_v3_inner_summary.csv", index=False)
    pd.DataFrame(per_rows).to_csv(out_dir / "mutcm_v3_inner_per_class_f1.csv", index=False)
    pd.DataFrame(cond_rows).to_csv(out_dir / "mutcm_v3_inner_condition_report.csv", index=False)
    return df


def holm_adjust(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.zeros(m, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * pvals[idx]
        running = max(running, val)
        adj[idx] = min(running, 1.0)
    return adj.tolist()


def wilcoxon_holm(summary: pd.DataFrame, selected_n_syn: int, out_dir: Path) -> pd.DataFrame:
    rows = []
    baselines = ["noise_aug", "rule", "random_open_loop", "real_only"]
    for n_syn in sorted(summary["n_syn"].unique()):
        for n_real in sorted(summary["n_real"].unique()):
            for metric in ["acc", "macro_f1"]:
                fam_rows = []
                llm = summary[(summary["method"] == "LLM_synthetic") & (summary["n_real"] == n_real) & (summary["n_syn"] == n_syn)].sort_values("seed")
                for baseline in baselines:
                    base = summary[(summary["method"] == baseline) & (summary["n_real"] == n_real) & (summary["n_syn"] == n_syn)].sort_values("seed")
                    merged = llm[["seed", metric]].merge(base[["seed", metric]], on="seed", suffixes=("_llm", "_base"))
                    delta = merged[f"{metric}_llm"].to_numpy() - merged[f"{metric}_base"].to_numpy()
                    if len(delta) == 0 or np.allclose(delta, 0):
                        p = 1.0
                    else:
                        try:
                            p = float(wilcoxon(delta, alternative="greater", zero_method="zsplit").pvalue)
                        except ValueError:
                            p = 1.0
                    fam_rows.append(
                        {
                            "n_syn": int(n_syn),
                            "selected_n_syn": bool(n_syn == selected_n_syn),
                            "n_real": int(n_real),
                            "metric": metric,
                            "comparison": f"LLM_synthetic>{baseline}",
                            "p_raw": p,
                            "mean_delta": float(np.mean(delta)) if len(delta) else np.nan,
                            "median_delta": float(np.median(delta)) if len(delta) else np.nan,
                            "win_rate": float(np.mean(delta > 0)) if len(delta) else np.nan,
                            "effect_size_mean_over_sd": float(np.mean(delta) / (np.std(delta, ddof=1) + 1e-12)) if len(delta) > 1 else np.nan,
                        }
                    )
                core = [r for r in fam_rows if not r["comparison"].endswith(">real_only")]
                q = holm_adjust([r["p_raw"] for r in core])
                for r, qv in zip(core, q):
                    r["holm_q"] = qv
                for r in fam_rows:
                    if "holm_q" not in r:
                        r["holm_q"] = np.nan
                    rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(out_dir / "mutcm_v3_inner_wilcoxon_holm.csv", index=False)
    return out


def select_n_syn(summary: pd.DataFrame) -> tuple[int, dict[str, Any]]:
    candidates = []
    for n_syn in sorted(summary["n_syn"].unique()):
        pass_count = 0
        deltas = []
        for n_real in sorted(summary["n_real"].unique()):
            for metric in ["acc", "macro_f1"]:
                means = summary[summary["n_syn"] == n_syn].groupby(["method", "n_real"])[metric].mean()
                llm = float(means[("LLM_synthetic", n_real)])
                base_vals = [float(means[(b, n_real)]) for b in ["noise_aug", "rule", "random_open_loop"]]
                ok = all(llm > b for b in base_vals)
                pass_count += int(ok)
                deltas.append(llm - max(base_vals))
        candidates.append((pass_count, float(np.mean(deltas)), -int(n_syn), int(n_syn)))
    candidates.sort(reverse=True)
    return candidates[0][3], {"candidates": [{"n_syn": c[3], "core_pass_count": c[0], "mean_delta_vs_best_core": c[1]} for c in candidates]}


def write_gate(summary: pd.DataFrame, per_class_path: Path, condition_path: Path, holm: pd.DataFrame, selected_n_syn: int, pools: dict[str, Any], out_dir: Path) -> bool:
    means = summary[summary["n_syn"] == selected_n_syn].groupby(["method", "n_real"])[["acc", "macro_f1"]].mean()
    core_rows = []
    pass_count = 0
    for n_real in sorted(summary["n_real"].unique()):
        for metric in ["acc", "macro_f1"]:
            llm = float(means.loc[("LLM_synthetic", n_real), metric])
            base = {b: float(means.loc[(b, n_real), metric]) for b in ["noise_aug", "rule", "random_open_loop"]}
            ok = all(llm > v for v in base.values())
            pass_count += int(ok)
            core_rows.append({"n_real": int(n_real), "metric": metric, "llm": llm, **base, "passed": ok})
    per = pd.read_csv(per_class_path)
    per_sel = per[per["n_syn"] == selected_n_syn].groupby(["method", "n_real", "class"])["f1"].mean().reset_index()
    hard = {}
    for cls in CLASSES:
        vals = []
        for n_real in sorted(summary["n_real"].unique()):
            llm = float(per_sel[(per_sel["method"] == "LLM_synthetic") & (per_sel["n_real"] == n_real) & (per_sel["class"] == cls)]["f1"].iloc[0])
            real = float(per_sel[(per_sel["method"] == "real_only") & (per_sel["n_real"] == n_real) & (per_sel["class"] == cls)]["f1"].iloc[0])
            vals.append(llm - real)
        hard[f"{cls}_not_collapsed"] = bool(min(vals) >= -0.10 and per_sel[(per_sel["method"] == "LLM_synthetic") & (per_sel["class"] == cls)]["f1"].mean() >= 0.45)
    cond = pd.read_csv(condition_path)
    cond_sel = cond[(cond["method"] == "LLM_synthetic") & (cond["n_syn"] == selected_n_syn)]
    cond_perf = cond_sel.groupby("condition_id")["macro_f1"].mean()
    hard["condition_not_single_condition"] = bool(len(cond_perf) >= 2 and float((cond_perf > 0.45).mean()) >= 0.5)
    mean_rule_delta = np.mean([r["llm"] - r["rule"] for r in core_rows])
    hard["berkeley_like_weak_gain_risk"] = bool(mean_rule_delta < 0.005)
    gate_passed = bool(pass_count >= 5 and all(v for k, v in hard.items() if k != "berkeley_like_weak_gain_risk"))
    lines = [
        "# MU-TCM v3 Inner-Val Gate Report",
        "",
        "Status: inner-val only. No preregistration/formal test was run by this script.",
        f"- Selected n_syn from inner-val scan: `{selected_n_syn}`",
        f"- Core pass count: `{pass_count}/6`",
        f"- Gate passed: `{gate_passed}`",
        "",
        "## Synthetic Pool Support",
        "",
    ]
    for name, info in pools.items():
        lines.append(f"- {name}: `{info}`")
    lines.extend(["", "## Core Comparisons", ""])
    for row in core_rows:
        lines.append(
            f"- n_real={row['n_real']} {row['metric']}: LLM `{row['llm']:.4f}`, "
            f"noise `{row['noise_aug']:.4f}`, rule `{row['rule']:.4f}`, random `{row['random_open_loop']:.4f}` -> `{row['passed']}`"
        )
    lines.extend(["", "## Hard Constraints", ""])
    for key, val in hard.items():
        lines.append(f"- {key}: `{val}`")
    sig = holm[(holm["selected_n_syn"] == True) & (holm["comparison"].isin(["LLM_synthetic>noise_aug", "LLM_synthetic>rule", "LLM_synthetic>random_open_loop"]))]
    lines.extend(["", "## Holm Diagnostics", ""])
    for _, row in sig.iterrows():
        lines.append(
            f"- n_real={int(row['n_real'])} {row['metric']} {row['comparison']}: "
            f"delta `{row['mean_delta']:.4f}`, win_rate `{row['win_rate']:.3f}`, q `{row['holm_q']:.4g}`"
        )
    if gate_passed:
        lines.append("")
        lines.append("Decision: inner-val gate passed. Stop tuning and write preregistration before any formal held-out test.")
    else:
        lines.append("")
        lines.append("Decision: inner-val gate failed. Do not preregister and do not run formal held-out test.")
    (out_dir / "mutcm_v3_inner_gate_report.md").write_text("\n".join(lines) + "\n")
    if gate_passed:
        prereg = [
            "# MU-TCM v3 Preregistration Draft",
            "",
            "This draft is written only after the inner-val gate passed. It does not run a formal test.",
            "",
            "- Dataset: MU-TCM full_dataset",
            "- Label scheme: Scheme A, healthy=rounded VB in {0.0,0.1}, worn=rounded VB in {0.2,0.3}",
            "- Split protocol: experiment/MAT grouped split; formal held-out test must be frozen before execution.",
            "- Window: 1.0 s synced MAT windows, 19 channels, fs=2000 Hz",
            "- Features/classifier: signal-only handcrafted time/frequency/correlation features with ExtraTrees",
            "- Baselines: real_only, noise_aug, rule, random_open_loop, LLM_synthetic",
            "- n_real: {2,5,10}",
            f"- n_syn: {selected_n_syn}",
            "- Metrics: Acc, Macro-F1, healthy F1, worn F1",
            "- Core success: LLM_synthetic must exceed noise_aug/rule/random_open_loop for at least 5/6 n_real x {Acc,Macro-F1} combinations.",
            "- Statistical test: paired one-sided Wilcoxon per comparison; Holm correction within each n_real x metric family.",
            "- API budget: v3 inner attack <=180 calls; formal run must not change prompts/admission/rules.",
        ]
        (out_dir / "mutcm_v3_preregistration.md").write_text("\n".join(prereg) + "\n")
    else:
        fail = ["# MU-TCM v3 Inner-Val Gate Fail Analysis", "", f"- Core pass count: {pass_count}/6", f"- Selected n_syn: {selected_n_syn}", f"- Mean LLM-rule delta: {mean_rule_delta:.6f}"]
        (out_dir / "mutcm_v3_inner_gate_fail.md").write_text("\n".join(fail) + "\n")
    return gate_passed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-npz", default="proc/mutcm_v2_schemeA_window_signal.npz")
    parser.add_argument("--split-csv", default="breeze/results/mutcm_v2_synced_2026-07-09/mutcm_v2_inner_split_assignments.csv")
    parser.add_argument("--metadata-csv", default="breeze/results/mutcm_v2_synced_2026-07-09/mutcm_v2_metadata_index.csv")
    parser.add_argument("--out-dir", default="breeze/results/mutcm_v3_llm_inner_2026-07-09")
    parser.add_argument("--max-api-requests", type=int, default=90)
    parser.add_argument("--target-per-class", type=int, default=60)
    parser.add_argument("--expansions", type=int, default=3)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--n-real", type=int, nargs="+", default=[2, 5, 10])
    parser.add_argument("--n-syn", type=int, nargs="+", default=[10, 20, 40])
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--readmit-existing", action="store_true")
    args = parser.parse_args()

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = load_bundle(ROOT / args.window_npz, ROOT / args.split_csv, ROOT / args.metadata_csv, out_dir)
    write_split(bundle, out_dir)
    exemplar = write_exemplar(bundle, out_dir)
    calib = calibrate_admission(bundle)
    rule_info = generate_noapi_pool(bundle, calib, out_dir, "rule", per_class=max(args.n_syn) * 2)
    random_info = generate_noapi_pool(bundle, calib, out_dir, "random_open_loop", per_class=max(args.n_syn) * 2)
    llm_info = generate_llm_pool(
        bundle,
        exemplar,
        calib,
        out_dir,
        args.max_api_requests,
        args.target_per_class,
        args.expansions,
        args.prepare_only,
        args.readmit_existing,
    )
    pools_info = {
        "rule": rule_info,
        "random_open_loop": random_info,
        "LLM_synthetic": {"path": str(out_dir / "mutcm_v3_llm_synthetic_pool.npz"), **llm_info},
    }
    summarize_synthetic(bundle, out_dir, pools_info)
    if args.prepare_only or args.generate_only:
        print(json.dumps({"prepare_only": bool(args.prepare_only), "generate_only": bool(args.generate_only), "llm_pool": llm_info}, sort_keys=True))
        return
    pools = {
        "rule": load_pool_features(Path(rule_info["path"]), bundle.fs_hz),
        "random_open_loop": load_pool_features(Path(random_info["path"]), bundle.fs_hz),
        "LLM_synthetic": load_pool_features(out_dir / "mutcm_v3_llm_synthetic_pool.npz", bundle.fs_hz),
    }
    summary = evaluate_inner(bundle, pools, out_dir, args.seeds, args.n_real, args.n_syn)
    selected_n_syn, scan_info = select_n_syn(summary)
    (out_dir / "mutcm_v3_nsyn_selection.json").write_text(json.dumps(tolist(scan_info), indent=2) + "\n")
    holm = wilcoxon_holm(summary, selected_n_syn, out_dir)
    passed = write_gate(
        summary,
        out_dir / "mutcm_v3_inner_per_class_f1.csv",
        out_dir / "mutcm_v3_inner_condition_report.csv",
        holm,
        selected_n_syn,
        pools_info,
        out_dir,
    )
    print(json.dumps({"gate_passed": passed, "selected_n_syn": selected_n_syn, "llm_pool": llm_info}, sort_keys=True))


if __name__ == "__main__":
    main()
