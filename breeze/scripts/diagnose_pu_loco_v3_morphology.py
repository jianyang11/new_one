"""PU LOCO v3 morphology-condition map.

This is a zero-API diagnostic for option-B LOCO v3. It uses only the PU
train-bearing split within each operating condition. Held-out LOCO test windows
and test bearing IDs are not read.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import butter, find_peaks, hilbert, sosfiltfilt, welch
from scipy.stats import kurtosis, skew, spearmanr

ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "src"))

from config import CHANNELS, CLASSES, CONDITIONS, FS, PROC_DIR, SPLIT, fault_freqs  # noqa: E402
from renderer import BANDS  # noqa: E402


EXTRA_BANDS = {
    "or_resonance_600_1200": (600.0, 1200.0),
    "ir_resonance_3000_3600": (3000.0, 3600.0),
}


def tolist(x: Any) -> Any:
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, dict):
        return {k: tolist(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [tolist(v) for v in x]
    return x


def class_for_bearing(bearing: str) -> str:
    if bearing.startswith("K0"):
        return "healthy"
    if bearing.startswith("KA"):
        return "OR"
    if bearing.startswith("KI"):
        return "IR"
    raise ValueError(f"unknown bearing id: {bearing}")


def train_bearing_ids(cls: str) -> set[str]:
    return set(SPLIT["train"][cls])


def load_train_condition(cond: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    bearings: list[str] = []
    for path in sorted(PROC_DIR.glob(f"{cond}_*.npz")):
        data = np.load(path, allow_pickle=True)
        bearing = str(data["bearing"])
        cls = class_for_bearing(bearing)
        if bearing not in train_bearing_ids(cls):
            continue
        W = data["windows"].astype(np.float32)
        xs.append(W)
        ys.extend([CLASSES.index(cls)] * len(W))
        bearings.extend([bearing] * len(W))
    if not xs:
        raise FileNotFoundError(f"no train-bearing windows for {cond}")
    return np.concatenate(xs), np.asarray(ys, dtype=np.int64), np.asarray(bearings)


def psd(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return welch(x.astype(float), fs=FS, nperseg=min(2048, len(x)))


def band_fraction(x: np.ndarray, band: tuple[float, float]) -> float:
    f, p = psd(x)
    total = float(np.trapezoid(p, f)) + 1e-30
    lo, hi = band
    m = (f >= lo) & (f < hi)
    return float(np.trapezoid(p[m], f[m]) / total) if np.any(m) else 0.0


def band_fracs(x: np.ndarray) -> dict[str, float]:
    out = {}
    for i, band in enumerate(BANDS):
        out[f"band_{i}_{int(band[0])}_{int(band[1])}_frac"] = band_fraction(x, band)
    for name, band in EXTRA_BANDS.items():
        out[f"{name}_frac"] = band_fraction(x, band)
    return out


def safe_stats(x: np.ndarray) -> dict[str, float]:
    x = x.astype(float)
    rms = float(np.sqrt(np.mean(x**2)))
    peak = float(np.max(np.abs(x)))
    std = float(np.std(x))
    if std < 1e-12:
        return {"rms": rms, "std": std, "peak": peak, "kurtosis": 3.0, "skewness": 0.0, "crest": 0.0}
    return {
        "rms": rms,
        "std": std,
        "peak": peak,
        "kurtosis": float(kurtosis(x, fisher=False)),
        "skewness": float(skew(x)),
        "crest": float(peak / (rms + 1e-12)),
    }


def bandpass(x: np.ndarray, band: tuple[float, float]) -> np.ndarray:
    ny = FS / 2
    lo = max(float(band[0]), 5.0)
    hi = min(float(band[1]), ny * 0.98)
    if hi <= lo + 10:
        return x.astype(float) - np.mean(x)
    sos = butter(4, [lo / ny, hi / ny], btype="bandpass", output="sos")
    return sosfiltfilt(sos, x.astype(float))


def envelope_features(x: np.ndarray, cls: str, fr_hz: float) -> dict[str, float]:
    if cls == "healthy":
        return {
            "env_peak_prominence": 0.0,
            "env_peak_err_hz": 0.0,
            "mod_depth_fr": 0.0,
            "env_band_lo": 0.0,
            "env_band_hi": 0.0,
        }
    freqs = fault_freqs(fr_hz)
    target = float(freqs["BPFO"] if cls == "OR" else freqs["BPFI"])
    band = EXTRA_BANDS["or_resonance_600_1200"] if cls == "OR" else EXTRA_BANDS["ir_resonance_3000_3600"]
    xb = bandpass(x, band)
    env = np.abs(hilbert(xb))
    env = env - np.mean(env)
    f = np.fft.rfftfreq(len(env), 1.0 / FS)
    amp = np.abs(np.fft.rfft(env * np.hanning(len(env)))) / max(len(env), 1)
    tol = max(2.0 * (f[1] - f[0]), 0.05 * target)
    m = (f >= max(target - tol, 0.0)) & (f <= target + tol)
    if np.any(m):
        idx_local = np.argmax(amp[m])
        idx = np.where(m)[0][idx_local]
        floor = float(np.median(amp[(f >= 5.0) & (f <= min(500.0, FS / 2))])) + 1e-12
        peak_prom = float(amp[idx] / floor)
        peak_err = float(abs(f[idx] - target))
    else:
        peak_prom = 0.0
        peak_err = float(tol)
    mt = (f >= max(fr_hz - tol, 0.0)) & (f <= fr_hz + tol)
    mod = float(np.max(amp[mt]) / (np.median(amp[(f >= 5.0) & (f <= 500.0)]) + 1e-12)) if np.any(mt) else 0.0
    return {
        "env_peak_prominence": peak_prom,
        "env_peak_err_hz": peak_err,
        "mod_depth_fr": mod,
        "env_band_lo": float(band[0]),
        "env_band_hi": float(band[1]),
    }


def top_psd_components(X: np.ndarray, channel: int, max_components: int = 5) -> list[dict[str, float]]:
    if len(X) == 0:
        return []
    psds = []
    f_ref = None
    for w in X[: min(len(X), 240)]:
        f, p = psd(w[channel])
        f_ref = f
        psds.append(p)
    pmean = np.mean(np.stack(psds), axis=0)
    mask = (f_ref >= 5.0) & (f_ref <= 500.0)
    peaks, props = find_peaks(np.log10(pmean[mask] + 1e-18), prominence=0.20)
    candidate = np.where(mask)[0][peaks]
    if len(candidate) == 0:
        candidate = np.where(mask)[0][np.argsort(pmean[mask])[-max_components:]]
    order = sorted(candidate, key=lambda i: -pmean[i])[:max_components]
    df = float(f_ref[1] - f_ref[0])
    return [
        {"freq_hz": float(f_ref[i]), "amp": float(np.sqrt(max(4.0 * pmean[i] * df, 0.0)))}
        for i in sorted(order)
    ]


def group_features(
    cond: str,
    cls: str,
    W: np.ndarray,
    bearings: np.ndarray,
    sample_per_group: int,
) -> dict[str, Any]:
    rpm, torque, load = CONDITIONS[cond]
    fr_hz = rpm / 60.0
    rng = np.random.default_rng(abs(hash((cond, cls, "morphology"))) % (2**32))
    if len(W) > sample_per_group:
        idx = rng.choice(len(W), sample_per_group, replace=False)
        Ws = W[idx]
    else:
        Ws = W
    rows = []
    for w in Ws:
        vf = safe_stats(w[0])
        cur1 = safe_stats(w[1])
        cur2 = safe_stats(w[2])
        item = {f"vib_{k}": v for k, v in vf.items()}
        item.update({f"cur1_{k}": v for k, v in cur1.items()})
        item.update({f"cur2_{k}": v for k, v in cur2.items()})
        item.update(band_fracs(w[0]))
        item.update(envelope_features(w[0], cls, fr_hz))
        rows.append(item)
    keys = sorted(rows[0])
    out: dict[str, Any] = {
        "condition": cond,
        "class": cls,
        "rpm": rpm,
        "torque_nm": torque,
        "radial_load_n": load,
        "fr_hz": fr_hz,
        "n_windows_total": int(len(W)),
        "n_windows_sampled": int(len(Ws)),
        "n_bearings": int(len(set(str(b) for b in bearings))),
    }
    for key in keys:
        vals = np.asarray([r[key] for r in rows], dtype=float)
        out[f"{key}_median"] = float(np.median(vals))
        out[f"{key}_q25"] = float(np.quantile(vals, 0.25))
        out[f"{key}_q75"] = float(np.quantile(vals, 0.75))
    for ch, name in enumerate(CHANNELS):
        comps = top_psd_components(Ws, ch)
        out[f"{name}_top_components_json"] = json.dumps(tolist(comps), separators=(",", ":"))
    return out


def inverse_distance_predict(train_meta: np.ndarray, train_y: np.ndarray, target_meta: np.ndarray) -> float:
    center = np.mean(train_meta, axis=0)
    scale = np.std(train_meta, axis=0)
    scale = np.where(scale > 1e-12, scale, 1.0)
    d = np.sqrt((((train_meta - target_meta) / scale) ** 2).sum(axis=1))
    w = 1.0 / (d + 1e-6)
    w = w / w.sum()
    return float(np.sum(w * train_y))


def trend_rows(feature_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    numeric_features = sorted(
        k
        for k in feature_rows[0]
        if k.endswith("_median") and isinstance(feature_rows[0][k], (int, float, np.floating))
    )
    out = []
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in feature_rows:
        by_class[row["class"]].append(row)
    for cls, rows in by_class.items():
        rows = sorted(rows, key=lambda r: r["condition"])
        meta = np.asarray([[r["rpm"], r["torque_nm"], r["radial_load_n"]] for r in rows], dtype=float)
        for feat in numeric_features:
            y = np.asarray([float(r[feat]) for r in rows], dtype=float)
            if np.allclose(y, y[0]):
                continue
            loo_pred = []
            for i in range(len(rows)):
                mask = np.ones(len(rows), dtype=bool)
                mask[i] = False
                loo_pred.append(inverse_distance_predict(meta[mask], y[mask], meta[i]))
            loo_pred_arr = np.asarray(loo_pred, dtype=float)
            mae = float(np.mean(np.abs(loo_pred_arr - y)))
            rel_mae = float(mae / (np.median(np.abs(y)) + 1e-12))
            spearman = {}
            for j, name in enumerate(["rpm", "torque_nm", "radial_load_n"]):
                rho = spearmanr(meta[:, j], y).statistic
                spearman[name] = float(rho) if np.isfinite(rho) else 0.0
            out.append(
                {
                    "class": cls,
                    "feature": feat,
                    "range": float(np.max(y) - np.min(y)),
                    "median_abs": float(np.median(np.abs(y))),
                    "loo_idw_mae": mae,
                    "loo_idw_rel_mae": rel_mae,
                    "spearman_rpm": spearman["rpm"],
                    "spearman_torque_nm": spearman["torque_nm"],
                    "spearman_radial_load_n": spearman["radial_load_n"],
                    "values_by_condition_json": json.dumps({r["condition"]: float(r[feat]) for r in rows}, separators=(",", ":")),
                    "loo_pred_by_condition_json": json.dumps({r["condition"]: float(v) for r, v in zip(rows, loo_pred_arr)}, separators=(",", ":")),
                    "predictability": "interpolatable" if rel_mae <= 0.20 else ("weak" if rel_mae <= 0.50 else "not_predictable"),
                }
            )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="breeze/results/pu_loco_v3_2026-07-08")
    parser.add_argument("--sample-per-group", type=int, default=800)
    args = parser.parse_args()

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    feature_rows = []
    for cond in CONDITIONS:
        X, y, bearings = load_train_condition(cond)
        for ci, cls in enumerate(CLASSES):
            mask = y == ci
            feature_rows.append(group_features(cond, cls, X[mask], bearings[mask], args.sample_per_group))
    trend = trend_rows(feature_rows)
    write_csv(out_dir / "morphology_condition_features.csv", feature_rows)
    write_csv(out_dir / "morphology_condition_trends.csv", trend)

    focus_features = [
        "vib_rms_median",
        "vib_kurtosis_median",
        "vib_crest_median",
        "or_resonance_600_1200_frac_median",
        "ir_resonance_3000_3600_frac_median",
        "env_peak_prominence_median",
        "mod_depth_fr_median",
        "band_2_500_1000_frac_median",
        "band_7_3000_4000_frac_median",
    ]
    trend_by_focus = [r for r in trend if r["feature"] in focus_features]
    report = [
        "# PU LOCO v3 Morphology-Condition Map",
        "",
        "## Boundary",
        "",
        "This zero-API diagnostic uses only `config.SPLIT['train']` bearing IDs within each PU operating condition. LOCO held-out test windows and test bearing IDs are not read.",
        "",
        "## Mechanism From v1/v2",
        "",
        "- v1 failed on kinematics: recipes rendered at source training rpm produced BPFO/BPFI errors of about -40% or +66.7% when evaluated at a different held-out rpm.",
        "- v2 corrected `fr_hz`, impact rate, and current fault frequency, but still failed downstream. The remaining mismatch is morphology: resonance-band energy, impulse shape, modulation, and background spectrum depend on torque/load/transfer path and are not a linear rpm rescale.",
        "- `noise_aug` remains strong because it perturbs real windows from the training operating conditions, preserving realistic morphology diversity.",
        "",
        "## Operating Conditions",
        "",
        "| condition | rpm | torque Nm | radial load N |",
        "|---|---:|---:|---:|",
    ]
    for cond, vals in CONDITIONS.items():
        report.append(f"| {cond} | {vals[0]} | {vals[1]} | {vals[2]} |")
    report.extend(
        [
            "",
            "## Focus Feature Predictability",
            "",
            "Predictability uses leave-one-condition-out inverse-distance interpolation in `(rpm, torque, radial load)` space. With only four operating conditions, this is a development diagnostic, not a final statistical model.",
            "",
            "| class | feature | rel LOO MAE | rho rpm | rho torque | rho load | verdict | values by condition |",
            "|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for r in sorted(trend_by_focus, key=lambda x: (x["class"], x["feature"])):
        report.append(
            f"| {r['class']} | {r['feature']} | {r['loo_idw_rel_mae']:.3f} | "
            f"{r['spearman_rpm']:.3f} | {r['spearman_torque_nm']:.3f} | {r['spearman_radial_load_n']:.3f} | "
            f"{r['predictability']} | `{r['values_by_condition_json']}` |"
        )
    report.extend(
        [
            "",
            "## v3 Implication",
            "",
            "Features marked `interpolatable` are candidates for morphology interpolation/extrapolation in v3 recipes. Features marked `weak` or `not_predictable` should not be blindly extrapolated; v3 should either borrow nearest-condition morphology for them or require an explicit LLM reasoning step using the train-condition table.",
            "",
            "## Artifacts",
            "",
            "- `morphology_condition_features.csv`",
            "- `morphology_condition_trends.csv`",
        ]
    )
    (out_dir / "morphology_condition_map.md").write_text("\n".join(report) + "\n")
    print(json.dumps({"out_dir": str(out_dir), "rows": len(feature_rows), "trend_rows": len(trend)}, sort_keys=True))


if __name__ == "__main__":
    main()
