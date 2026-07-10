"""Training-fold diagnostics for the Berkeley/NASA milling synthetic pools.

This script deliberately uses only the Berkeley inner-train split for feature
targets. It may inspect the current held-out-smoke synthetic pools to diagnose
why they underperform, but those pools are not treated as valid formal
inner-validation artifacts because they were built before the inner split was
created.
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
from scipy.signal import welch
from scipy.stats import kurtosis, skew, spearmanr

ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "scripts"))
sys.path.insert(0, str(BREEZE / "src"))

from eval_npz_downstream import noise_aug as make_noise_aug  # noqa: E402
from milling_generation import BERKELEY, MillingDatasetConfig, harmonic_freqs  # noqa: E402


CLASS_ORDER = ["sharp", "worn", "severe"]
BANDS_HZ = [(0.0, 8.0), (8.0, 20.0), (20.0, 40.0), (40.0, 70.0), (70.0, 100.0), (100.0, 125.0)]


def load_npz(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    data = np.load(path, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    class_names = [str(v) for v in data["class_names"]]
    return X, y, class_names


def sample_balanced(
    X: np.ndarray, y: np.ndarray, class_names: list[str], n_per_class: int, seed: int
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    rng = np.random.default_rng(seed)
    keep: list[int] = []
    counts = {}
    for ci, cls in enumerate(class_names):
        idx = np.where(y == ci)[0]
        take = min(n_per_class, len(idx))
        if take:
            keep.extend(rng.choice(idx, take, replace=False).tolist())
        counts[cls] = int(take)
    keep_arr = np.asarray(keep, dtype=int)
    return X[keep_arr], y[keep_arr], counts


def build_noise_pool(
    X: np.ndarray, y: np.ndarray, n_per_class: int, class_names: list[str], seed: int
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    # Match the downstream implementation: few-shot real subset first, then
    # Gaussian jitter and light scaling around those real traces.
    Xr, yr, _ = sample_balanced(X, y, class_names, n_per_class, seed)
    Xs, ys = make_noise_aug(Xr, yr, n_per_class, len(class_names), rng)
    return Xs.astype(np.float32), ys.astype(np.int64)


def psd(x: np.ndarray, fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    f, p = welch(x, fs=fs_hz, nperseg=min(256, len(x)))
    p = np.maximum(p.astype(float), 0.0)
    return f.astype(float), p


def psd_cdf_from_power(f: np.ndarray, p: np.ndarray) -> np.ndarray:
    mass = p * np.gradient(f)
    mass = mass / (mass.sum() + 1e-30)
    cdf = np.cumsum(mass)
    return cdf / (cdf[-1] + 1e-30)


def class_channel_mean_psd(X: np.ndarray, y: np.ndarray, n_classes: int, fs_hz: float) -> dict[tuple[int, int], tuple[np.ndarray, np.ndarray]]:
    out: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
    for ci in range(n_classes):
        W = X[y == ci]
        if len(W) == 0:
            continue
        for ch in range(X.shape[1]):
            powers = []
            f_ref = None
            for w in W:
                f, p = psd(w[ch], fs_hz)
                f_ref = f
                powers.append(p)
            out[(ci, ch)] = (f_ref, np.mean(np.stack(powers), axis=0))
    return out


def band_fracs_from_power(f: np.ndarray, p: np.ndarray) -> np.ndarray:
    vals = []
    for lo, hi in BANDS_HZ:
        m = (f >= lo) & (f < hi)
        vals.append(float(np.trapezoid(p[m], f[m])) if np.any(m) else 0.0)
    arr = np.asarray(vals, dtype=float)
    return arr / (arr.sum() + 1e-30)


def scalar_features(w: np.ndarray, fs_hz: float, tpf_hz: float) -> dict[str, float]:
    feats: dict[str, float] = {}
    total_power = 0.0
    high_power = 0.0
    for ch in range(w.shape[0]):
        x = w[ch].astype(float)
        rms = float(np.sqrt(np.mean(x**2)))
        std = float(np.std(x))
        peak = float(np.max(np.abs(x)))
        feats[f"ch{ch}_rms"] = rms
        feats[f"ch{ch}_crest"] = float(peak / (rms + 1e-12))
        feats[f"ch{ch}_kurtosis"] = float(kurtosis(x, fisher=False)) if std > 1e-12 else 3.0
        feats[f"ch{ch}_skewness"] = float(skew(x)) if std > 1e-12 else 0.0
        f, p = psd(x, fs_hz)
        bands = band_fracs_from_power(f, p)
        for bi, frac in enumerate(bands):
            feats[f"ch{ch}_band{bi}_frac"] = float(frac)
        total_power += float(np.trapezoid(p, f))
        high = f >= 70.0
        high_power += float(np.trapezoid(p[high], f[high])) if np.any(high) else 0.0
        feats[f"ch{ch}_tpf_amp_ratio"] = harmonic_amp_ratio(x, fs_hz, tpf_hz)
        feats[f"ch{ch}_tooth_rms_cv"] = tooth_rms_cv(x, fs_hz, tpf_hz)
    feats["total_rms"] = float(np.sqrt(np.mean(w.astype(float) ** 2)))
    feats["high_band_frac"] = float(high_power / (total_power + 1e-30))
    energy = np.mean(w.astype(float) ** 2, axis=1)
    energy_frac = energy / (energy.sum() + 1e-30)
    for ch, val in enumerate(energy_frac):
        feats[f"energy_frac_ch{ch}"] = float(val)
    return feats


def harmonic_amp_ratio(x: np.ndarray, fs_hz: float, freq_hz: float) -> float:
    if freq_hz <= 0 or freq_hz >= fs_hz * 0.48:
        return 0.0
    x0 = x - np.mean(x)
    n = len(x0)
    freqs = np.fft.rfftfreq(n, 1.0 / fs_hz)
    amp = np.abs(np.fft.rfft(x0 * np.hanning(n))) / max(n, 1)
    df = freqs[1] - freqs[0]
    tol = max(2.0 * df, 0.03 * freq_hz)
    m = (freqs >= freq_hz - tol) & (freqs <= freq_hz + tol)
    if not np.any(m):
        return 0.0
    return float(np.max(amp[m]) / (np.sqrt(np.mean(x0**2)) + 1e-12))


def tooth_rms_cv(x: np.ndarray, fs_hz: float, tpf_hz: float) -> float:
    period = max(int(round(fs_hz / max(tpf_hz, 1e-9))), 2)
    n_seg = len(x) // period
    if n_seg < 4:
        return 0.0
    seg = x[: n_seg * period].reshape(n_seg, period)
    vals = np.sqrt(np.mean(seg.astype(float) ** 2, axis=1))
    return float(np.std(vals) / (np.mean(vals) + 1e-12))


def feature_matrix(X: np.ndarray, cfg: MillingDatasetConfig) -> list[dict[str, float]]:
    tpf = cfg.plugin.char_freqs()["TPF"]
    return [scalar_features(w, cfg.fs_hz, float(tpf)) for w in X]


def hist_overlap(a: np.ndarray, b: np.ndarray, bins: int = 40) -> float:
    lo = float(min(np.min(a), np.min(b)))
    hi = float(max(np.max(a), np.max(b)))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return 1.0
    ha, edges = np.histogram(a, bins=bins, range=(lo, hi), density=True)
    hb, _ = np.histogram(b, bins=edges, density=True)
    widths = np.diff(edges)
    return float(np.sum(np.minimum(ha, hb) * widths))


def robust_scale(a: np.ndarray) -> float:
    q25, q75 = np.quantile(a, [0.25, 0.75])
    scale = float((q75 - q25) / 1.349)
    if scale <= 1e-12:
        scale = float(np.std(a))
    return max(scale, 1e-12)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        keys = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def class_corr_and_energy(X: np.ndarray, y: np.ndarray, n_classes: int) -> dict[int, dict[str, np.ndarray]]:
    out: dict[int, dict[str, np.ndarray]] = {}
    for ci in range(n_classes):
        W = X[y == ci]
        if len(W) == 0:
            continue
        corrs = []
        energy = []
        for w in W:
            c = np.corrcoef(w)
            corrs.append(np.nan_to_num(c, nan=0.0, posinf=0.0, neginf=0.0))
            e = np.mean(w.astype(float) ** 2, axis=1)
            energy.append(e / (e.sum() + 1e-30))
        out[ci] = {"corr": np.median(np.stack(corrs), axis=0), "energy": np.median(np.stack(energy), axis=0)}
    return out


def summarize_downstream(csv_dir: Path, out_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not csv_dir.exists():
        return [], [f"downstream directory not found: {csv_dir}"]
    rows = []
    notes = []
    for path in sorted(csv_dir.glob("*.csv")):
        method = path.stem.replace("berkeley_", "").replace("_nsyn20", "")
        with path.open(newline="") as fh:
            for rec in csv.DictReader(fh):
                try:
                    per = json.loads(rec["per_class_f1_json"])
                    cm = np.asarray(json.loads(rec["confusion_json"]), dtype=int)
                    rows.append(
                        {
                            "method": method,
                            "n_real": int(rec["n_real"]),
                            "seed": int(rec["seed"]),
                            "acc": float(rec["acc"]),
                            "macro_f1": float(rec["macro_f1"]),
                            "f1_sharp": float(per.get("sharp", 0.0)),
                            "f1_worn": float(per.get("worn", 0.0)),
                            "f1_severe": float(per.get("severe", 0.0)),
                            "confusion_json": json.dumps(cm.tolist(), separators=(",", ":")),
                        }
                    )
                except (KeyError, ValueError, json.JSONDecodeError):
                    notes.append(f"could not parse downstream row in {path}")
    if rows:
        grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(str(row["method"]), int(row["n_real"]))].append(row)
        summary = []
        for (method, n_real), vals in sorted(grouped.items()):
            out = {"method": method, "n_real": n_real, "rows": len(vals)}
            for key in ["acc", "macro_f1", "f1_sharp", "f1_worn", "f1_severe"]:
                arr = np.asarray([float(v[key]) for v in vals], dtype=float)
                out[f"{key}_mean"] = f"{arr.mean():.4f}"
                out[f"{key}_std"] = f"{arr.std(ddof=1) if len(arr) > 1 else 0.0:.4f}"
            summary.append(out)
        write_csv(out_dir / "berkeley_inner_downstream_summary.csv", summary)
    return rows, notes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inner-train", default="proc/milling_berkeley_inner_train.npz")
    parser.add_argument("--inner-val", default="proc/milling_berkeley_inner_val.npz")
    parser.add_argument(
        "--llm-pool",
        default="breeze/runs/milling_generation_2026-07-08_llm_rescreen_v4/berkeley/llm_rescreen/pool.npz",
    )
    parser.add_argument("--rule-pool", default="breeze/runs/milling_generation_2026-07-08_smoke_v7/berkeley/rule/pool.npz")
    parser.add_argument(
        "--random-pool",
        default="breeze/runs/milling_generation_2026-07-08_smoke_v7/berkeley/random_open_loop/pool.npz",
    )
    parser.add_argument("--out-dir", default="breeze/results/milling_berkeley_inner_attack_2026-07-08")
    parser.add_argument("--downstream-dir", default="")
    parser.add_argument("--n-per-class", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260708)
    args = parser.parse_args()

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    X_real, y_real, class_names = load_npz(ROOT / args.inner_train)
    X_val, y_val, val_names = load_npz(ROOT / args.inner_val)
    if class_names != val_names:
        raise RuntimeError(f"class mismatch: train={class_names}, val={val_names}")
    if class_names != CLASS_ORDER:
        raise RuntimeError(f"unexpected class names: {class_names}")
    cfg = MillingDatasetConfig(
        name=BERKELEY.name,
        train_npz=ROOT / args.inner_train,
        fs_hz=BERKELEY.fs_hz,
        window=BERKELEY.window,
        channels=BERKELEY.channels,
        classes=BERKELEY.classes,
        spindle_hz=BERKELEY.spindle_hz,
        n_teeth=BERKELEY.n_teeth,
    )
    n_classes = len(class_names)

    methods: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for name, rel in [("llm", args.llm_pool), ("rule", args.rule_pool), ("random_open_loop", args.random_pool)]:
        Xp, yp, names = load_npz(ROOT / rel)
        if names != class_names:
            raise RuntimeError(f"{name} classes {names} != {class_names}")
        methods[name] = sample_balanced(Xp, yp, names, args.n_per_class, args.seed)[:2]
    Xn, yn = build_noise_pool(X_real, y_real, args.n_per_class, class_names, args.seed)
    methods["noise_aug"] = (Xn, yn)
    np.savez_compressed(out_dir / "berkeley_noise_aug_diagnostic_pool.npz", X=Xn, y=yn, class_names=np.asarray(class_names))

    real_psd = class_channel_mean_psd(X_real, y_real, n_classes, cfg.fs_hz)
    psd_rows = []
    band_rows = []
    for method, (Xm, ym) in methods.items():
        method_psd = class_channel_mean_psd(Xm, ym, n_classes, cfg.fs_hz)
        for ci, cls in enumerate(class_names):
            for ch, ch_name in enumerate(cfg.channels):
                if (ci, ch) not in method_psd or (ci, ch) not in real_psd:
                    continue
                f_real, p_real = real_psd[(ci, ch)]
                f_syn, p_syn = method_psd[(ci, ch)]
                cdf_real = psd_cdf_from_power(f_real, p_real)
                cdf_syn = psd_cdf_from_power(f_syn, p_syn)
                w1 = float(np.trapezoid(np.abs(cdf_syn - cdf_real), f_real))
                real_bands = band_fracs_from_power(f_real, p_real)
                syn_bands = band_fracs_from_power(f_syn, p_syn)
                psd_rows.append(
                    {
                        "method": method,
                        "class": cls,
                        "channel": ch_name,
                        "psd_w1": f"{w1:.6f}",
                        "band_l1": f"{np.abs(syn_bands - real_bands).sum():.6f}",
                    }
                )
                for bi, (lo, hi) in enumerate(BANDS_HZ):
                    band_rows.append(
                        {
                            "method": method,
                            "class": cls,
                            "channel": ch_name,
                            "band": f"{lo:g}-{hi:g}",
                            "real_frac": f"{real_bands[bi]:.6f}",
                            "method_frac": f"{syn_bands[bi]:.6f}",
                            "delta": f"{syn_bands[bi] - real_bands[bi]:.6f}",
                        }
                    )
    write_csv(out_dir / "berkeley_inner_psd_w1.csv", psd_rows)
    write_csv(out_dir / "berkeley_inner_band_energy.csv", band_rows)

    real_features = feature_matrix(X_real, cfg)
    real_by_class: dict[int, list[dict[str, float]]] = {ci: [] for ci in range(n_classes)}
    for feat, yi in zip(real_features, y_real):
        real_by_class[int(yi)].append(feat)
    stat_rows = []
    ordering_rows = []
    method_feature_cache: dict[str, tuple[list[dict[str, float]], np.ndarray]] = {}
    for method, (Xm, ym) in methods.items():
        feats = feature_matrix(Xm, cfg)
        method_feature_cache[method] = (feats, ym)
        for ci, cls in enumerate(class_names):
            rf = real_by_class[ci]
            mf = [feat for feat, yi in zip(feats, ym) if int(yi) == ci]
            if not mf:
                continue
            keys = sorted(rf[0])
            for key in keys:
                rv = np.asarray([v[key] for v in rf], dtype=float)
                mv = np.asarray([v[key] for v in mf], dtype=float)
                med_r = float(np.median(rv))
                med_m = float(np.median(mv))
                rel = (med_m - med_r) / (abs(med_r) + 1e-12)
                rz = (med_m - med_r) / robust_scale(rv)
                stat_rows.append(
                    {
                        "method": method,
                        "class": cls,
                        "feature": key,
                        "real_median": f"{med_r:.8g}",
                        "method_median": f"{med_m:.8g}",
                        "median_delta": f"{med_m - med_r:.8g}",
                        "robust_z_delta": f"{rz:.6f}",
                        "relative_delta": f"{rel:.6f}",
                        "hist_overlap": f"{hist_overlap(rv, mv):.6f}",
                    }
                )
    write_csv(out_dir / "berkeley_inner_stats_overlap.csv", stat_rows)

    key_order_features = [
        "total_rms",
        "high_band_frac",
        "ch0_tpf_amp_ratio",
        "ch1_tpf_amp_ratio",
        "ch2_tpf_amp_ratio",
        "ch3_tpf_amp_ratio",
        "ch4_tpf_amp_ratio",
        "ch5_tpf_amp_ratio",
        "energy_frac_ch4",
        "energy_frac_ch5",
    ]
    real_order = []
    for key in key_order_features:
        real_vals = []
        for ci in range(n_classes):
            rv = np.asarray([v[key] for v in real_by_class[ci]], dtype=float)
            real_vals.append(float(np.median(rv)))
        real_order.append((key, real_vals))
    for method, (feats, ym) in method_feature_cache.items():
        for key, real_vals in real_order:
            method_vals = []
            for ci in range(n_classes):
                vals = np.asarray([feat[key] for feat, yi in zip(feats, ym) if int(yi) == ci], dtype=float)
                method_vals.append(float(np.median(vals)) if len(vals) else np.nan)
            rho = spearmanr(real_vals, method_vals, nan_policy="omit").statistic
            ordering_rows.append(
                {
                    "method": method,
                    "feature": key,
                    "real_sharp": f"{real_vals[0]:.8g}",
                    "real_worn": f"{real_vals[1]:.8g}",
                    "real_severe": f"{real_vals[2]:.8g}",
                    "method_sharp": f"{method_vals[0]:.8g}",
                    "method_worn": f"{method_vals[1]:.8g}",
                    "method_severe": f"{method_vals[2]:.8g}",
                    "spearman_to_real_order": f"{float(rho) if np.isfinite(rho) else np.nan:.6f}",
                }
            )
    write_csv(out_dir / "berkeley_inner_class_ordering.csv", ordering_rows)

    real_struct = class_corr_and_energy(X_real, y_real, n_classes)
    struct_rows = []
    for method, (Xm, ym) in methods.items():
        m_struct = class_corr_and_energy(Xm, ym, n_classes)
        for ci, cls in enumerate(class_names):
            if ci not in real_struct or ci not in m_struct:
                continue
            corr_delta = float(np.linalg.norm(m_struct[ci]["corr"] - real_struct[ci]["corr"], ord="fro"))
            energy_l1 = float(np.abs(m_struct[ci]["energy"] - real_struct[ci]["energy"]).sum())
            struct_rows.append(
                {
                    "method": method,
                    "class": cls,
                    "corr_fro_delta": f"{corr_delta:.6f}",
                    "energy_frac_l1": f"{energy_l1:.6f}",
                    "real_energy_json": json.dumps(real_struct[ci]["energy"].tolist(), separators=(",", ":")),
                    "method_energy_json": json.dumps(m_struct[ci]["energy"].tolist(), separators=(",", ":")),
                }
            )
    write_csv(out_dir / "berkeley_inner_channel_structure.csv", struct_rows)

    downstream_rows, downstream_notes = summarize_downstream(Path(ROOT / args.downstream_dir) if args.downstream_dir else Path(""), out_dir)

    def top_rows(rows: list[dict[str, Any]], key: str, n: int = 8) -> list[dict[str, Any]]:
        return sorted(rows, key=lambda r: abs(float(r[key])), reverse=True)[:n]

    mean_psd = []
    for method in sorted(methods):
        vals = [float(r["psd_w1"]) for r in psd_rows if r["method"] == method]
        bands = [float(r["band_l1"]) for r in psd_rows if r["method"] == method]
        mean_psd.append((method, float(np.mean(vals)), float(np.mean(bands))))
    mean_struct = []
    for method in sorted(methods):
        corr_vals = [float(r["corr_fro_delta"]) for r in struct_rows if r["method"] == method]
        energy_vals = [float(r["energy_frac_l1"]) for r in struct_rows if r["method"] == method]
        mean_struct.append((method, float(np.mean(corr_vals)), float(np.mean(energy_vals))))

    report = [
        "# Berkeley Inner-Train Diagnostics",
        "",
        "This is a zero-API diagnostic pass. All reference distributions come from `milling_berkeley_inner_train.npz`; no held-out Berkeley test signal is used.",
        "",
        "## Inputs",
        "",
        f"- inner_train windows: {len(X_real)}; counts: "
        + json.dumps({class_names[i]: int((y_real == i).sum()) for i in range(n_classes)}, ensure_ascii=False),
        f"- inner_val windows: {len(X_val)}; counts: "
        + json.dumps({class_names[i]: int((y_val == i).sum()) for i in range(n_classes)}, ensure_ascii=False),
        f"- diagnostic synthetic budget: {args.n_per_class}/class for LLM, rule, random_open_loop, and noise_aug.",
        f"- spindle harmonics/TPF used for diagnostics: {json.dumps(harmonic_freqs(cfg))}",
        "",
        "Important caveat: the inspected current LLM/rule/random pools were built before the inner split existed. They are valid for failure diagnosis, but not valid as final inner-validation artifacts for choosing a formal protocol.",
        "",
        "## PSD And Band-Energy Distance",
        "",
        "| method | mean PSD-W1 | mean band L1 |",
        "|---|---:|---:|",
    ]
    for method, w1, band_l1 in mean_psd:
        report.append(f"| {method} | {w1:.4f} | {band_l1:.4f} |")
    report.extend(["", "Largest single PSD/band mismatches:"])
    for row in sorted(psd_rows, key=lambda r: float(r["psd_w1"]), reverse=True)[:10]:
        report.append(
            f"- {row['method']} / {row['class']} / {row['channel']}: PSD-W1={row['psd_w1']}, bandL1={row['band_l1']}"
        )

    report.extend(
        [
            "",
            "## Statistics And Channel Structure",
            "",
            "| method | mean corr Frobenius delta | mean channel-energy L1 |",
            "|---|---:|---:|",
        ]
    )
    for method, corr_delta, energy_l1 in mean_struct:
        report.append(f"| {method} | {corr_delta:.4f} | {energy_l1:.4f} |")
    report.extend(["", "Largest median feature deltas by absolute relative shift:"])
    for row in top_rows(stat_rows, "robust_z_delta", n=12):
        report.append(
            f"- {row['method']} / {row['class']} / {row['feature']}: real={row['real_median']}, method={row['method_median']}, robust_z={row['robust_z_delta']}, overlap={row['hist_overlap']}"
        )

    report.extend(["", "## Class-Ordering Check", ""])
    weak_order = [r for r in ordering_rows if r["method"] == "llm" and float(r["spearman_to_real_order"]) < 0.5]
    if weak_order:
        report.append("LLM features whose class ordering does not follow inner-train real data:")
        for row in weak_order:
            report.append(
                f"- {row['feature']}: real=({row['real_sharp']},{row['real_worn']},{row['real_severe']}), "
                f"LLM=({row['method_sharp']},{row['method_worn']},{row['method_severe']}), rho={row['spearman_to_real_order']}"
            )
    else:
        report.append("No LLM key ordering feature has Spearman rho < 0.5 against the real class medians.")

    if downstream_rows:
        report.extend(["", "## Inner-Val Downstream Confusion Summary", ""])
        report.append("Parsed downstream rows are summarized in `berkeley_inner_downstream_summary.csv`.")
        by_method = defaultdict(list)
        for row in downstream_rows:
            by_method[(row["method"], row["n_real"])].append(row)
        for (method, n_real), vals in sorted(by_method.items()):
            acc = np.mean([float(v["acc"]) for v in vals])
            f1 = np.mean([float(v["macro_f1"]) for v in vals])
            per = {k: np.mean([float(v[k]) for v in vals]) for k in ["f1_sharp", "f1_worn", "f1_severe"]}
            report.append(
                f"- {method} n={n_real}: acc={acc:.4f}, macro_f1={f1:.4f}, "
                f"F1 sharp/worn/severe={per['f1_sharp']:.4f}/{per['f1_worn']:.4f}/{per['f1_severe']:.4f}"
            )
    elif downstream_notes:
        report.extend(["", "## Inner-Val Downstream Confusion Summary", ""])
        report.extend([f"- {note}" for note in downstream_notes])

    report.extend(
        [
            "",
            "## Files",
            "",
            "- `berkeley_inner_psd_w1.csv`",
            "- `berkeley_inner_band_energy.csv`",
            "- `berkeley_inner_stats_overlap.csv`",
            "- `berkeley_inner_channel_structure.csv`",
            "- `berkeley_inner_class_ordering.csv`",
            "- `berkeley_noise_aug_diagnostic_pool.npz`",
        ]
    )
    (out_dir / "berkeley_inner_diagnostics_report.md").write_text("\n".join(report) + "\n")
    print(json.dumps({"out_dir": str(out_dir), "methods": sorted(methods), "n_per_class": args.n_per_class}, sort_keys=True))


if __name__ == "__main__":
    main()
