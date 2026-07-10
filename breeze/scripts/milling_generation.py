"""Berkeley/NASA milling synthetic recipe smoke.

This is the milling instantiation of BREEZE's recipe -> renderer -> verifier
loop. It deliberately avoids bearing envelope features. The verifier consumes
low-frequency process features: spindle/TPF harmonic ratios, time statistics,
channel energy/correlation structure, soft PSD shape, and PSD-CDF W1 distance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import welch

ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "src"))

import llm  # noqa: E402
from kinematics import MillingKinematicsPlugin  # noqa: E402


STAT_KEYS = ["rms", "peak", "std", "kurtosis", "skewness", "crest"]
N_SOFT_BANDS = 8
EQ_BANDS_HZ = [(0.0, 8.0), (8.0, 20.0), (20.0, 40.0), (40.0, 70.0), (70.0, 100.0), (100.0, 125.0)]


def stable_seed(*parts: Any) -> int:
    payload = json.dumps(tolist(parts), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "little")


@dataclass(frozen=True)
class MillingDatasetConfig:
    name: str
    train_npz: Path
    fs_hz: float
    window: int
    channels: list[str]
    classes: list[str]
    spindle_hz: float
    n_teeth: int

    @property
    def plugin(self) -> MillingKinematicsPlugin:
        return MillingKinematicsPlugin(
            spindle_hz=self.spindle_hz,
            n_teeth=self.n_teeth,
            fs_hz=self.fs_hz,
            harmonic_count=5,
        )


BERKELEY = MillingDatasetConfig(
    name="berkeley",
    train_npz=ROOT / "proc" / "milling_berkeley_train.npz",
    fs_hz=250.0,
    window=512,
    channels=["smcAC", "smcDC", "vib_table", "vib_spindle", "AE_table", "AE_spindle"],
    classes=["sharp", "worn", "severe"],
    spindle_hz=826.0 / 60.0,
    n_teeth=6,
)

UMICH = MillingDatasetConfig(
    name="umich",
    train_npz=ROOT / "proc" / "milling_umich_train.npz",
    fs_hz=10.0,
    window=64,
    channels=[
        "X1_CurrentFeedback",
        "Y1_CurrentFeedback",
        "Z1_CurrentFeedback",
        "S1_CurrentFeedback",
        "X1_OutputCurrent",
        "Y1_OutputCurrent",
        "Z1_OutputCurrent",
        "S1_OutputCurrent",
    ],
    classes=["unworn", "worn"],
    spindle_hz=0.0,
    n_teeth=1,
)


LOW_WEAR_LABELS = {"sharp", "healthy", "unworn", "new", "normal"}
MID_WEAR_LABELS = {"worn", "degradation", "degraded", "wear", "medium", "in_service"}
HIGH_WEAR_LABELS = {"severe", "failure", "failed", "severe_wear", "end_of_life", "eol"}


def cfg_from_train_npz(base: MillingDatasetConfig, train_npz: Path) -> MillingDatasetConfig:
    data = np.load(train_npz, allow_pickle=True)
    classes = [str(x) for x in data["class_names"]]
    channels = [str(x) for x in data["channels"]] if "channels" in data.files else base.channels
    fs_hz = float(data["fs_hz"]) if "fs_hz" in data.files else base.fs_hz
    window = int(data["window"]) if "window" in data.files else base.window
    return replace(base, train_npz=train_npz, fs_hz=fs_hz, window=window, channels=channels, classes=classes)


def wear_role(cls: str, cfg: MillingDatasetConfig) -> str:
    key = cls.lower()
    if key in LOW_WEAR_LABELS:
        return "low"
    if key in MID_WEAR_LABELS:
        return "mid"
    if key in HIGH_WEAR_LABELS:
        return "high"
    if len(cfg.classes) == 2:
        return "low" if cfg.classes.index(cls) == 0 else "high"
    if len(cfg.classes) >= 3:
        idx = cfg.classes.index(cls)
        if idx == 0:
            return "low"
        if idx == len(cfg.classes) - 1:
            return "high"
    return "mid"


def wear_rank(cls: str, cfg: MillingDatasetConfig) -> float:
    role = wear_role(cls, cfg)
    if role == "low":
        return 0.0
    if role == "high":
        return 1.0
    return 0.5


def class_for_role(cfg: MillingDatasetConfig, role: str) -> str:
    for cls in cfg.classes:
        if wear_role(cls, cfg) == role:
            return cls
    if role == "low":
        return cfg.classes[0]
    if role == "high":
        return cfg.classes[-1]
    return cfg.classes[min(1, len(cfg.classes) - 1)]


SYSTEM = (
    "You are an expert in CNC milling condition monitoring. Design physically "
    "plausible parameter recipes for low-sampling-rate milling process signals. "
    "Respond only with one JSON object, no markdown."
)


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


def load_train(cfg: MillingDatasetConfig) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(cfg.train_npz, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    classes = [str(x) for x in data["class_names"]]
    if classes != cfg.classes:
        raise RuntimeError(f"class mismatch: {classes} != {cfg.classes}")
    return X, y


def soft_band_fracs(x: np.ndarray, n_bands: int = N_SOFT_BANDS) -> np.ndarray:
    f, p = welch(x, fs=1.0, nperseg=min(256, len(x)))
    centers = (np.arange(n_bands, dtype=float) + 0.5) * (0.5 / n_bands)
    vals = []
    for i, center in enumerate(centers):
        left = 0.0 if i == 0 else centers[i - 1]
        right = 0.5 if i == n_bands - 1 else centers[i + 1]
        weights = np.zeros_like(f)
        ml = (f >= left) & (f <= center)
        mr = (f > center) & (f <= right)
        weights[ml] = (f[ml] - left) / max(center - left, 1e-12)
        weights[mr] = (right - f[mr]) / max(right - center, 1e-12)
        vals.append(np.trapezoid(p * np.clip(weights, 0.0, 1.0), f))
    vals = np.asarray(vals, dtype=float)
    return vals / (vals.sum() + 1e-30)


def eq_band_fracs_hz(x: np.ndarray, fs_hz: float, bands: list[tuple[float, float]] = EQ_BANDS_HZ) -> np.ndarray:
    X = np.fft.rfft(np.asarray(x, dtype=float))
    f = np.fft.rfftfreq(len(x), 1.0 / fs_hz)
    p = np.abs(X) ** 2
    vals = []
    for lo, hi in bands:
        m = (f >= lo) & (f < hi)
        vals.append(float(p[m].sum()) if np.any(m) else 0.0)
    arr = np.asarray(vals, dtype=float)
    return arr / (arr.sum() + 1e-30)


def band_equalize_hz(
    x: np.ndarray,
    fs_hz: float,
    target_frac: np.ndarray,
    strength: float,
    bands: list[tuple[float, float]] = EQ_BANDS_HZ,
) -> np.ndarray:
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength <= 0.0:
        return np.asarray(x, dtype=float)
    x0 = np.asarray(x, dtype=float)
    mean = float(np.mean(x0))
    dyn = x0 - mean
    rms = float(np.sqrt(np.mean(dyn**2)))
    if rms <= 1e-12:
        return x0
    cur = eq_band_fracs_hz(dyn, fs_hz, bands)
    tgt = np.asarray(target_frac, dtype=float)
    if tgt.size != len(bands) or not np.all(np.isfinite(tgt)):
        return x0
    tgt = np.clip(tgt, 0.0, None)
    tgt = tgt / (tgt.sum() + 1e-30)
    raw_gain = np.sqrt((tgt + 1e-8) / (cur + 1e-8))
    gains = np.exp(strength * np.log(np.clip(raw_gain, 0.25, 4.0)))
    X = np.fft.rfft(dyn)
    f = np.fft.rfftfreq(len(dyn), 1.0 / fs_hz)
    g = np.ones_like(f)
    for (lo, hi), gain in zip(bands, gains):
        g[(f >= lo) & (f < hi)] = gain
    out = np.fft.irfft(X * g, n=len(dyn))
    out = out / (np.sqrt(np.mean(out**2)) + 1e-12) * rms
    return out + mean


def psd_cdf(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    f, p = welch(x, fs=1.0, nperseg=min(256, len(x)))
    p = np.maximum(p, 0.0)
    mass = p * np.gradient(f)
    mass = mass / (mass.sum() + 1e-30)
    cdf = np.cumsum(mass)
    return f, cdf / (cdf[-1] + 1e-30)


def psd_w1(x: np.ndarray, ref_cdf: np.ndarray) -> float:
    f, cdf = psd_cdf(x)
    return float(np.trapezoid(np.abs(cdf - ref_cdf), f))


def fft_amp_ratio(x: np.ndarray, fs: float, freq: float) -> float:
    if freq <= 0 or freq >= 0.48 * fs:
        return 0.0
    x0 = x - np.mean(x)
    n = len(x0)
    F = np.fft.rfftfreq(n, 1.0 / fs)
    A = np.abs(np.fft.rfft(x0 * np.hanning(n))) / max(n, 1)
    df = F[1] - F[0]
    tol = max(2.0 * df, 0.03 * freq)
    m = (F >= freq - tol) & (F <= freq + tol)
    if not np.any(m):
        return 0.0
    return float(np.max(A[m]) / (np.sqrt(np.mean(x0**2)) + 1e-12))


def harmonic_freqs(cfg: MillingDatasetConfig) -> list[float]:
    freqs = cfg.plugin.char_freqs()
    out = []
    for f in freqs["spindle_harmonics"] + freqs["TPF_harmonics"]:
        if 0 < float(f) < 0.48 * cfg.fs_hz:
            out.append(float(f))
    return sorted(set(round(f, 6) for f in out))


def harmonic_vector(w: np.ndarray, cfg: MillingDatasetConfig) -> np.ndarray:
    freqs = harmonic_freqs(cfg)
    return np.asarray(
        [fft_amp_ratio(w[ch], cfg.fs_hz, freq) for ch in range(w.shape[0]) for freq in freqs],
        dtype=float,
    )


def stat_vector(w: np.ndarray) -> np.ndarray:
    def safe_stats(x: np.ndarray) -> dict[str, float]:
        rms = float(np.sqrt(np.mean(x**2)))
        peak = float(np.max(np.abs(x)))
        std = float(np.std(x))
        if std < 1e-12 or rms < 1e-12:
            return {"rms": rms, "peak": peak, "std": std, "kurtosis": 3.0, "skewness": 0.0, "crest": 0.0}
        from scipy.stats import kurtosis, skew

        return {
            "rms": rms,
            "peak": peak,
            "std": std,
            "kurtosis": float(kurtosis(x, fisher=False)),
            "skewness": float(skew(x)),
            "crest": float(peak / rms),
        }

    return np.asarray(
        [safe_stats(w[ch])[key] for ch in range(w.shape[0]) for key in STAT_KEYS],
        dtype=float,
    )


def channel_energy_ratios(w: np.ndarray) -> np.ndarray:
    e = np.mean(w.astype(float) ** 2, axis=1)
    return e / (e.sum() + 1e-30)


def corr_upper(w: np.ndarray) -> np.ndarray:
    c = np.corrcoef(w)
    c = np.nan_to_num(c, nan=0.0, posinf=0.0, neginf=0.0)
    return c[np.triu_indices(w.shape[0], k=1)]


def soft_vector(w: np.ndarray) -> np.ndarray:
    return np.concatenate([soft_band_fracs(w[ch]) for ch in range(w.shape[0])])


def feature_vector(w: np.ndarray, cfg: MillingDatasetConfig) -> np.ndarray:
    return np.concatenate(
        [stat_vector(w), channel_energy_ratios(w), corr_upper(w), soft_vector(w), harmonic_vector(w, cfg)]
    ).astype(float)


def robust_center_scale(vals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
    med = np.median(vals, axis=0)
    q25 = np.quantile(vals, 0.25, axis=0)
    q75 = np.quantile(vals, 0.75, axis=0)
    scale = (q75 - q25) / 1.349
    scale = np.where(scale > 1e-12, scale, np.std(vals, axis=0) + 1e-9)
    return med, scale


def joint_alpha(vals: np.ndarray, target: float) -> float:
    best_alpha, best_gap = 0.01, np.inf
    for alpha in np.linspace(0.001, 0.10, 50):
        lo = np.quantile(vals, alpha / 2, axis=0)
        hi = np.quantile(vals, 1.0 - alpha / 2, axis=0)
        rate = float(np.mean(np.all((vals >= lo) & (vals <= hi), axis=1)))
        gap = abs(rate - target)
        if gap < best_gap:
            best_alpha, best_gap = float(alpha), gap
    return best_alpha


class MillingVerifier:
    def __init__(self, cfg: MillingDatasetConfig, coverage: float = 0.90):
        self.cfg = cfg
        self.coverage = coverage
        self.calib: dict[str, Any] = {}

    def calibrate(self, X: np.ndarray, y: np.ndarray) -> None:
        gate_cov = self.coverage ** 0.25
        self.calib = {
            "dataset": self.cfg.name,
            "coverage": self.coverage,
            "gate_coverage": gate_cov,
            "fs_hz": self.cfg.fs_hz,
            "window": self.cfg.window,
            "channels": self.cfg.channels,
            "classes": self.cfg.classes,
            "char_freqs": self.cfg.plugin.char_freqs(),
            "band_priors": self.cfg.plugin.band_priors(),
            "classes_calib": {},
        }
        for ci, cls in enumerate(self.cfg.classes):
            W = X[y == ci]
            fv = np.asarray([feature_vector(w, self.cfg) for w in W])
            stats = np.asarray([stat_vector(w) for w in W])
            soft = np.asarray([soft_vector(w) for w in W])
            harm = np.asarray([harmonic_vector(w, self.cfg) for w in W])
            med, scale = robust_center_scale(fv)
            z = (fv - med) / scale
            axis = np.sqrt((z**2).sum(axis=1))
            cdfs = [np.asarray([psd_cdf(w[ch])[1] for w in W]) for ch in range(len(self.cfg.channels))]
            ref = [np.median(c, axis=0) for c in cdfs]
            w1 = np.stack(
                [np.asarray([psd_w1(w[ch], ref[ch]) for w in W]) for ch in range(len(self.cfg.channels))],
                axis=1,
            )
            self.calib["classes_calib"][cls] = {
                "n_train": int(len(W)),
            "stats": self._axis_coord_gate(stats, gate_cov),
                "soft": self._axis_coord_gate(soft, gate_cov),
                "harmonic": self._axis_coord_gate(harm, gate_cov),
                "feature_axis": {
                    "median": med,
                    "scale": scale,
                    "threshold": float(np.quantile(axis, gate_cov)),
                },
                "psd_w1": {
                    "ref_cdf": ref,
                    "threshold": np.quantile(w1, gate_cov, axis=0),
                },
                "recipe_profile": self.recipe_profile(W),
            }

    def _coord_gate(self, vals: np.ndarray, target: float) -> dict[str, Any]:
        alpha = joint_alpha(vals, target)
        return {
            "alpha": alpha,
            "lo": np.quantile(vals, alpha / 2, axis=0),
            "hi": np.quantile(vals, 1.0 - alpha / 2, axis=0),
        }

    def _axis_coord_gate(self, vals: np.ndarray, target: float) -> dict[str, Any]:
        coord = self._coord_gate(vals, target)
        med, scale = robust_center_scale(vals)
        z = (vals - med) / scale
        axis = np.sqrt((z**2).sum(axis=1))
        coord.update({"median": med, "scale": scale, "axis_threshold": float(np.quantile(axis, target))})
        return coord

    def recipe_profile(self, W: np.ndarray) -> dict[str, Any]:
        mean = np.asarray([np.mean(w, axis=1) for w in W])
        std = np.asarray([np.std(w, axis=1) for w in W])
        rms = np.asarray([np.sqrt(np.mean(w**2, axis=1)) for w in W])
        harm = np.asarray([harmonic_vector(w, self.cfg).reshape(len(self.cfg.channels), -1) for w in W])
        corr = np.asarray([np.corrcoef(w) for w in W])
        corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
        rfft_amp = []
        band_frac = []
        for w in W:
            chans = []
            ch_bands = []
            for ch in range(w.shape[0]):
                x = w[ch] - np.mean(w[ch])
                amp = np.abs(np.fft.rfft(x * np.hanning(len(x)))) / max(len(x), 1)
                chans.append(amp / (np.sqrt(np.mean(x**2)) + 1e-12))
                ch_bands.append(eq_band_fracs_hz(x, self.cfg.fs_hz))
            rfft_amp.append(chans)
            band_frac.append(ch_bands)
        rfft_amp = np.asarray(rfft_amp)
        band_frac = np.asarray(band_frac)
        valid = np.all(np.std(W, axis=2) > 1e-10, axis=1)
        valid_idx = np.where(valid)[0]
        if len(valid_idx) > 96:
            fv_local = np.asarray([feature_vector(w, self.cfg) for w in W])
            med, scale = robust_center_scale(fv_local)
            axis = np.sqrt((((fv_local - med) / scale) ** 2).sum(axis=1))
            valid_idx = valid_idx[np.argsort(axis[valid_idx])[:96]]
        bank = rfft_amp[valid_idx]
        if len(bank) == 0:
            bank = rfft_amp[:1]
            template_bank = W[:1]
        else:
            template_bank = W[valid_idx]
        return {
            "mean_median": np.median(mean, axis=0),
            "mean_q10": np.quantile(mean, 0.10, axis=0),
            "mean_q90": np.quantile(mean, 0.90, axis=0),
            "std_median": np.median(std, axis=0),
            "std_q10": np.quantile(std, 0.10, axis=0),
            "std_q90": np.quantile(std, 0.90, axis=0),
            "rms_median": np.median(rms, axis=0),
            "rms_q10": np.quantile(rms, 0.10, axis=0),
            "rms_q90": np.quantile(rms, 0.90, axis=0),
            "harmonic_amp_median": np.median(harm, axis=0),
            "harmonic_amp_q90": np.quantile(harm, 0.90, axis=0),
            "corr_median": np.median(corr, axis=0),
            "rfft_amp_median": np.median(rfft_amp, axis=0),
            "rfft_amp_q10": np.quantile(rfft_amp, 0.10, axis=0),
            "rfft_amp_q90": np.quantile(rfft_amp, 0.90, axis=0),
            "band_frac_median": np.median(band_frac, axis=0),
            "band_frac_q10": np.quantile(band_frac, 0.10, axis=0),
            "band_frac_q90": np.quantile(band_frac, 0.90, axis=0),
            "rfft_amp_bank": bank,
            "iaaft_template_bank": template_bank,
            "rfft_amp_bank_n_valid": int(valid.sum()),
        }

    def verify(self, w: np.ndarray, cls: str) -> dict[str, Any]:
        rep: dict[str, Any] = {"class": cls, "feasible": True, "gates": {}, "scores": {}}

        def gate(name: str, passed: bool, messages: list[str]) -> None:
            rep["gates"][name] = {"passed": bool(passed), "messages": messages}
            rep["feasible"] = bool(rep["feasible"] and passed)

        sanity = []
        if w.shape != (len(self.cfg.channels), self.cfg.window):
            sanity.append(f"shape {w.shape} != {(len(self.cfg.channels), self.cfg.window)}")
        if not np.all(np.isfinite(w)):
            sanity.append("non-finite values")
        if np.any(np.std(w, axis=1) < 1e-10):
            sanity.append("constant channel")
        gate("sanity", not sanity, sanity)
        if sanity:
            return tolist(rep)
        cal = self.calib["classes_calib"][cls]

        st = stat_vector(w)
        sg = cal["stats"]
        lo, hi = np.asarray(sg["lo"]), np.asarray(sg["hi"])
        med, scale = np.asarray(sg["median"]), np.asarray(sg["scale"])
        bad = np.where((st < lo) | (st > hi))[0]
        coord_passed = len(bad) == 0
        axis = float(np.sqrt((((st - med) / scale) ** 2).sum()))
        axis_passed = axis <= float(sg["axis_threshold"])
        gate(
            "stats",
            bool(coord_passed or axis_passed),
            [] if coord_passed or axis_passed else [f"stat_{i} outside train interval" for i in bad[:8]] + [f"axis={axis:.3f} > {float(sg['axis_threshold']):.3f}"],
        )
        rep["scores"]["stats"] = {"coord_passed": coord_passed, "axis": axis, "axis_threshold": float(sg["axis_threshold"])}

        for name, vals in [("soft_spectrum", soft_vector(w)), ("tpf_harmonics", harmonic_vector(w, self.cfg))]:
            cg = cal["soft"] if name == "soft_spectrum" else cal["harmonic"]
            lo, hi = np.asarray(cg["lo"]), np.asarray(cg["hi"])
            med, scale = np.asarray(cg["median"]), np.asarray(cg["scale"])
            coord = np.all((vals >= lo) & (vals <= hi))
            axis = float(np.sqrt((((vals - med) / scale) ** 2).sum()))
            passed = bool(coord or axis <= float(cg["axis_threshold"]))
            gate(name, passed, [] if passed else [f"axis={axis:.3f} > {float(cg['axis_threshold']):.3f}"])
            rep["scores"][name] = {"axis": axis, "axis_threshold": float(cg["axis_threshold"]), "coord_passed": bool(coord)}

        fv = feature_vector(w, self.cfg)
        fg = cal["feature_axis"]
        axis = float(np.sqrt((((fv - np.asarray(fg["median"])) / np.asarray(fg["scale"])) ** 2).sum()))
        gate("structure_axis", axis <= float(fg["threshold"]), [] if axis <= float(fg["threshold"]) else [f"axis={axis:.3f} > {float(fg['threshold']):.3f}"])

        w1 = np.asarray([psd_w1(w[ch], np.asarray(cal["psd_w1"]["ref_cdf"][ch])) for ch in range(len(self.cfg.channels))])
        thr = np.asarray(cal["psd_w1"]["threshold"])
        bad = np.where(w1 > thr)[0]
        gate("psd_w1", len(bad) == 0, [f"{self.cfg.channels[i]} PSD W1 {w1[i]:.4f}>{thr[i]:.4f}" for i in bad[:8]])
        rep["scores"]["psd_w1"] = {"values": w1, "thresholds": thr}
        return tolist(rep)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(tolist(self.calib), indent=2) + "\n")

    @classmethod
    def load(cls, cfg: MillingDatasetConfig, path: Path) -> "MillingVerifier":
        obj = cls(cfg)
        obj.calib = json.loads(path.read_text())
        return obj


def recipe_from_profile(cfg: MillingDatasetConfig, verifier: MillingVerifier, cls: str, source: str, slot: int) -> dict[str, Any]:
    prof = verifier.calib["classes_calib"][cls]["recipe_profile"]
    rng = np.random.default_rng(stable_seed(cfg.name, source, cls, slot))
    freqs = harmonic_freqs(cfg)
    rms_med = np.asarray(prof["rms_median"], dtype=float)
    rms_lo = np.asarray(prof["rms_q10"], dtype=float)
    rms_hi = np.asarray(prof["rms_q90"], dtype=float)
    mean_med = np.asarray(prof.get("mean_median", np.zeros_like(rms_med)), dtype=float)
    std_med = np.asarray(prof.get("std_median", rms_med), dtype=float)
    std_lo = np.asarray(prof.get("std_q10", np.maximum(std_med * 0.75, 1e-9)), dtype=float)
    std_hi = np.asarray(prof.get("std_q90", np.maximum(std_med * 1.25, std_lo + 1e-9)), dtype=float)
    if source == "rule":
        h_med = np.asarray(prof["harmonic_amp_median"], dtype=float)
        h_hi = np.asarray(prof["harmonic_amp_q90"], dtype=float)
        harm = rng.uniform(np.minimum(h_med, h_hi), np.maximum(h_med, h_hi) + 1e-9)
        bank = np.asarray(prof.get("rfft_amp_bank", [prof["rfft_amp_median"]]), dtype=float)
        bank_idx = int(rng.integers(0, len(bank)))
        profile_amp = bank[bank_idx]
        template_bank = np.asarray(prof.get("iaaft_template_bank", []), dtype=float)
        template = template_bank[min(bank_idx, len(template_bank) - 1)] if len(template_bank) else None
        rms = np.clip(
            rms_med * rng.uniform(0.97, 1.03, size=len(cfg.channels)),
            np.maximum(rms_lo, 1e-9),
            np.maximum(rms_hi, rms_lo + 1e-9),
        )
        mean = mean_med * rng.uniform(0.98, 1.02, size=len(cfg.channels))
        std = np.clip(
            std_med * rng.uniform(0.97, 1.03, size=len(cfg.channels)),
            np.maximum(std_lo, 1e-9),
            np.maximum(std_hi, std_lo + 1e-9),
        )
    elif source == "random_open_loop":
        rms = rng.uniform(np.maximum(rms_lo * 0.5, 1e-6), rms_hi * 1.5)
        mean = rng.uniform(mean_med - np.maximum(np.abs(mean_med), 1.0), mean_med + np.maximum(np.abs(mean_med), 1.0))
        std = rng.uniform(np.maximum(std_lo * 0.5, 1e-6), std_hi * 1.5)
        harm = rng.uniform(0.0, np.asarray(prof["harmonic_amp_q90"], dtype=float) * 1.8 + 1e-4)
        profile_amp = np.asarray(prof["rfft_amp_median"], dtype=float)
        template = None
    else:
        raise ValueError(source)
    rank = wear_rank(cls, cfg)
    return {
        "class": cls,
        "fs_hz": cfg.fs_hz,
        "window": cfg.window,
        "rms": rms,
        "mean": mean,
        "std": std,
        "harmonic_freqs_hz": freqs,
        "harmonic_amp_ratio": harm,
        "noise_color": float(0.15 if source == "rule" else rng.uniform(0.0, 0.6)),
        "background_weight": float(1.0 if source == "rule" else 0.80),
        "background_mode": "real_exemplar" if source == "rule" else "spectral_surrogate",
        "harmonic_gain": float(0.05 if source == "rule" else 1.0),
        "noise_gain": float(0.0 if source == "rule" else 0.10),
        "shared_gain": float(0.0 if source == "rule" else 0.20),
        "trend_strength": float((0.02 * rank) if source == "rule" else (0.03 + 0.07 * rank)),
        "corr": np.asarray(prof["corr_median"], dtype=float),
        "_profile_rfft_amp_median": profile_amp,
        "_iaaft_template": template,
    }


def render_recipe(recipe: dict[str, Any], cfg: MillingDatasetConfig, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n_ch, n = len(cfg.channels), cfg.window
    t = np.arange(n, dtype=float) / cfg.fs_hz
    rms = np.asarray(recipe["rms"], dtype=float)
    mean = np.asarray(recipe.get("mean", np.zeros(n_ch)), dtype=float)
    if mean.size != n_ch:
        mean = np.resize(mean, n_ch)
    dyn_std = np.asarray(recipe.get("std", np.sqrt(np.maximum(rms**2 - mean**2, 1e-12))), dtype=float)
    if dyn_std.size != n_ch:
        dyn_std = np.resize(dyn_std, n_ch)
    dyn_std = np.maximum(dyn_std, 1e-9)
    freqs = [float(x) for x in recipe["harmonic_freqs_hz"]]
    harm = np.asarray(recipe["harmonic_amp_ratio"], dtype=float)
    if harm.shape != (n_ch, len(freqs)):
        harm = np.resize(harm, (n_ch, len(freqs)))
    x = np.zeros((n_ch, n), dtype=float)
    profile_amp = np.asarray(recipe.get("_profile_rfft_amp_median", []), dtype=float)
    iaaft_template = np.asarray(recipe.get("_iaaft_template", []), dtype=float)
    background_mode = str(recipe.get("background_mode", "spectral_surrogate"))
    shared_shift = int(rng.integers(0, n)) if background_mode == "real_exemplar" else 0
    for ch in range(n_ch):
        if background_mode == "real_exemplar" and iaaft_template.shape == (n_ch, n):
            bg = np.roll(iaaft_template[ch] - np.mean(iaaft_template[ch]), shared_shift)
            bg = bg / (np.sqrt(np.mean(bg**2)) + 1e-12)
            x[ch] += float(recipe.get("background_weight", 1.0)) * dyn_std[ch] * bg
        elif iaaft_template.shape == (n_ch, n):
            bg = iaaft_surrogate(iaaft_template[ch], rng)
            x[ch] += float(recipe.get("background_weight", 0.80)) * dyn_std[ch] * bg
        elif profile_amp.shape == (n_ch, n // 2 + 1):
            phase = rng.uniform(0, 2 * np.pi, size=n // 2 + 1)
            phase[0] = 0.0
            if n % 2 == 0:
                phase[-1] = 0.0
            spec = profile_amp[ch] * np.exp(1j * phase)
            bg = np.fft.irfft(spec, n=n)
            bg -= np.mean(bg)
            bg_rms = np.sqrt(np.mean(bg**2)) + 1e-12
            x[ch] += float(recipe.get("background_weight", 0.80)) * dyn_std[ch] * bg / bg_rms
        for j, freq in enumerate(freqs):
            phase = rng.uniform(0, 2 * np.pi)
            x[ch] += float(recipe.get("harmonic_gain", 1.0)) * harm[ch, j] * dyn_std[ch] * np.sin(2 * np.pi * freq * t + phase)
        noise = rng.normal(size=n)
        color = float(recipe.get("noise_color", 0.2))
        if color > 0:
            for i in range(1, n):
                noise[i] = color * noise[i - 1] + np.sqrt(max(1.0 - color**2, 1e-6)) * noise[i]
        trend = float(recipe.get("trend_strength", 0.0)) * dyn_std[ch] * np.linspace(-1, 1, n)
        x[ch] += noise * dyn_std[ch] * float(recipe.get("noise_gain", 0.10)) + trend
    corr = np.asarray(recipe.get("corr", np.eye(n_ch)), dtype=float)
    if corr.shape == (n_ch, n_ch):
        shared = rng.normal(size=(n_ch, n))
        try:
            vals, vecs = np.linalg.eigh((corr + corr.T) / 2)
            mix = vecs @ np.diag(np.sqrt(np.clip(vals, 0.0, None))) @ vecs.T
            x += float(recipe.get("shared_gain", 0.20)) * (mix @ shared) * dyn_std[:, None]
        except np.linalg.LinAlgError:
            pass
    band_eq = np.asarray(recipe.get("_band_eq_frac_median", []), dtype=float)
    band_eq_strength = float(recipe.get("band_eq_strength", 0.0))
    for ch in range(n_ch):
        if band_eq_strength > 0.0 and band_eq.shape == (n_ch, len(EQ_BANDS_HZ)):
            x[ch] = band_equalize_hz(x[ch], cfg.fs_hz, band_eq[ch], band_eq_strength)
        x[ch] -= np.mean(x[ch])
        cur = np.std(x[ch]) + 1e-12
        x[ch] *= dyn_std[ch] / cur
        x[ch] += mean[ch]
    return x.astype(np.float32)


def validate_llm_recipe(recipe: dict[str, Any] | None, cfg: MillingDatasetConfig) -> list[str]:
    if recipe is None:
        return ["parse_failed"]
    needed = ["class", "rms", "harmonic_freqs_hz", "harmonic_amp_ratio", "noise_color", "trend_strength"]
    bad = [f"missing {k}" for k in needed if k not in recipe]
    if "rms" in recipe and len(recipe["rms"]) != len(cfg.channels):
        bad.append("rms length mismatch")
    if harmonic_freqs(cfg) and "harmonic_freqs_hz" in recipe and len(recipe["harmonic_freqs_hz"]) == 0:
        bad.append("no harmonic frequencies")
    return bad


def _as_vector(value: Any, length: int, default: float, lo: float, hi: float) -> np.ndarray:
    try:
        arr = np.asarray(value if isinstance(value, list) else [default] * length, dtype=float)
    except (TypeError, ValueError):
        arr = np.asarray([default] * length, dtype=float)
    if arr.size != length:
        arr = np.resize(arr, length)
    return np.clip(arr, lo, hi)


def _as_int_vector(value: Any, length: int, default: int, lo: int, hi: int) -> np.ndarray:
    try:
        arr = np.asarray(value if isinstance(value, list) else [default] * length, dtype=int)
    except (TypeError, ValueError):
        arr = np.asarray([default] * length, dtype=int)
    if arr.size != length:
        arr = np.resize(arr, length)
    return np.clip(arr, lo, hi)


def _as_harmonic_matrix(
    value: Any,
    n_ch: int,
    n_freq: int,
    default: float,
    lo: float,
    hi: float,
) -> np.ndarray:
    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        arr = np.asarray([default] * n_ch, dtype=float)
    if arr.shape == (n_ch, n_freq):
        out = arr
    elif arr.shape == (n_ch,):
        out = arr[:, None] * np.ones((n_ch, n_freq), dtype=float)
    else:
        out = np.resize(arr, (n_ch, n_freq))
    return np.clip(out, lo, hi)


def _safe_float(value: Any, default: float, lo: float, hi: float) -> float:
    try:
        val = float(value)
    except (TypeError, ValueError):
        val = default
    return float(np.clip(val, lo, hi))


def expand_llm_recipe(
    recipe: dict[str, Any] | None,
    cfg: MillingDatasetConfig,
    verifier: MillingVerifier,
    cls: str,
    slot: int,
    mode: str = "standard",
) -> dict[str, Any] | None:
    if recipe is None:
        return None
    if "rms" in recipe and "harmonic_amp_ratio" in recipe:
        return recipe
    prof = verifier.calib["classes_calib"][cls]["recipe_profile"]
    freqs = harmonic_freqs(cfg)
    has_harmonics = bool(freqs)
    n_ch = len(cfg.channels)
    bank = np.asarray(prof.get("rfft_amp_bank", [prof["rfft_amp_median"]]), dtype=float)
    template_bank = np.asarray(prof.get("iaaft_template_bank", []), dtype=float)
    default_template_idx = stable_seed(cfg.name, "llm", cls, slot) % max(len(bank), 1)
    try:
        template_idx = int(recipe.get("template_index", default_template_idx))
    except (TypeError, ValueError):
        template_idx = default_template_idx
    template_idx = int(np.clip(template_idx, 0, max(len(bank) - 1, 0)))
    template_indices = np.asarray([template_idx] * n_ch, dtype=int)
    if mode == "contrastive" and len(template_bank):
        template_indices = _as_int_vector(recipe.get("template_indices"), n_ch, template_idx, 0, len(template_bank) - 1)
    if len(template_bank):
        template_rows = [template_bank[int(template_indices[ch]), ch] for ch in range(n_ch)]
        template = np.stack(template_rows).astype(float)
    else:
        template = None
    # Templates are used only for PSD/phase background. Channel RMS must come
    # from the robust class profile; otherwise an atypical template can move
    # most energy into the wrong sensor channel and still pass loose gates.
    base_rms = np.asarray(prof["rms_median"], dtype=float)
    base_mean = np.asarray(prof.get("mean_median", np.zeros(n_ch)), dtype=float)
    base_std = np.asarray(prof.get("std_median", base_rms), dtype=float)
    role = wear_role(cls, cfg)
    if mode in {"contrastive", "repair"}:
        if role == "low":
            rms_bounds = (0.90, 1.12)
            harm_bounds = (0.35, 1.60)
            trend_bounds = (0.0, 0.010)
            gain_bounds = (0.0, 0.10)
            noise_bounds = (0.0, 0.02)
            shared_bounds = (0.0, 0.05)
        elif role == "mid":
            rms_bounds = (0.90, 1.18)
            harm_bounds = (0.35, 2.10)
            trend_bounds = (0.0, 0.018)
            gain_bounds = (0.0, 0.12)
            noise_bounds = (0.0, 0.01)
            shared_bounds = (0.0, 0.04)
        else:
            rms_bounds = (0.92, 1.25)
            harm_bounds = (0.40, 2.40)
            trend_bounds = (0.0, 0.030)
            gain_bounds = (0.0, 0.14)
            noise_bounds = (0.0, 0.01)
            shared_bounds = (0.0, 0.04)
        if not has_harmonics:
            harm_bounds = (1.0, 1.0)
            gain_bounds = (0.0, 0.0)
            noise_bounds = (0.0, 0.08 if role == "low" else 0.12)
            shared_bounds = (0.0, 0.12)
    elif role == "low":
        rms_bounds = (0.95, 1.05)
        harm_bounds = (0.60, 1.20)
        trend_bounds = (0.0, 0.005)
        gain_bounds = (0.0, 0.06)
        noise_bounds = (0.0, 0.01)
        shared_bounds = (0.0, 0.02)
    elif role == "mid":
        rms_bounds = (0.95, 1.08)
        harm_bounds = (0.60, 1.50)
        trend_bounds = (0.0, 0.005)
        gain_bounds = (0.0, 0.05)
        noise_bounds = (0.0, 0.0)
        shared_bounds = (0.0, 0.0)
    else:
        rms_bounds = (0.95, 1.10)
        harm_bounds = (0.70, 1.80)
        trend_bounds = (0.0, 0.01)
        gain_bounds = (0.0, 0.08)
        noise_bounds = (0.0, 0.0)
        shared_bounds = (0.0, 0.0)
    if not has_harmonics and mode not in {"contrastive", "repair"}:
        harm_bounds = (1.0, 1.0)
        gain_bounds = (0.0, 0.0)
        noise_bounds = (0.0, 0.08 if role == "low" else 0.12)
        shared_bounds = (0.0, 0.10)
    rms_mult = _as_vector(recipe.get("rms_mult"), n_ch, 1.0, rms_bounds[0], rms_bounds[1])
    mean_mult = _as_vector(recipe.get("mean_mult"), n_ch, 1.0, 0.95, 1.05)
    std_mult = _as_vector(recipe.get("std_mult"), n_ch, 1.0, rms_bounds[0], rms_bounds[1])
    n_freq = len(freqs)
    harm_mult = _as_harmonic_matrix(recipe.get("harmonic_mult"), n_ch, n_freq, 1.0, harm_bounds[0], harm_bounds[1])
    harm = np.asarray(prof["harmonic_amp_median"], dtype=float) * harm_mult
    corr = np.asarray(prof["corr_median"], dtype=float)
    corr_blend = _safe_float(recipe.get("corr_blend"), 1.0, 0.5, 1.2)
    corr = np.eye(n_ch) + (corr - np.eye(n_ch)) * corr_blend
    default_trend = 0.04 * wear_rank(cls, cfg)
    requested_background = str(recipe.get("background_mode", "")).strip()
    if requested_background not in {"real_exemplar", "spectral_surrogate"}:
        requested_background = "spectral_surrogate" if not has_harmonics else "real_exemplar"
    return {
        "class": cls,
        "fs_hz": cfg.fs_hz,
        "window": cfg.window,
        "rms": base_rms * rms_mult,
        "mean": base_mean * mean_mult,
        "std": base_std * std_mult,
        "harmonic_freqs_hz": freqs,
        "harmonic_amp_ratio": harm,
        "noise_color": _safe_float(recipe.get("noise_color"), 0.10, 0.0, 0.60),
        "background_weight": _safe_float(recipe.get("background_weight"), 1.0, 0.70, 1.10),
        "background_mode": requested_background,
        "harmonic_gain": _safe_float(recipe.get("harmonic_gain"), 0.10, gain_bounds[0], gain_bounds[1]),
        "noise_gain": _safe_float(recipe.get("noise_gain"), 0.0, noise_bounds[0], noise_bounds[1]),
        "shared_gain": _safe_float(recipe.get("shared_gain"), 0.0, shared_bounds[0], shared_bounds[1]),
        "trend_strength": _safe_float(recipe.get("trend_strength"), default_trend, trend_bounds[0], trend_bounds[1]),
        "corr": corr,
        "_profile_rfft_amp_median": bank[template_idx],
        "_iaaft_template": template,
        "_template_indices": template_indices,
        "_llm_mode": mode,
        "_compact_recipe": recipe,
    }


def attach_renderer_profile(recipe: dict[str, Any], verifier: MillingVerifier, cls: str) -> dict[str, Any]:
    out = json.loads(json.dumps(tolist(recipe)))
    prof = verifier.calib["classes_calib"][cls]["recipe_profile"]
    if "_profile_rfft_amp_median" not in out:
        out["_profile_rfft_amp_median"] = prof["rfft_amp_median"]
    if float(out.get("band_eq_strength", 0.0)) > 0.0 and "_band_eq_frac_median" not in out:
        out["_band_eq_frac_median"] = prof.get("band_frac_median")
    return out


def rank_map_to_sorted(x: np.ndarray, target_sorted: np.ndarray) -> np.ndarray:
    order = np.argsort(x)
    out = np.empty_like(x, dtype=float)
    out[order] = target_sorted
    return out


def iaaft_surrogate(template: np.ndarray, rng: np.random.Generator, n_iter: int = 20) -> np.ndarray:
    x = np.asarray(template, dtype=float)
    x = x - np.mean(x)
    if np.std(x) < 1e-12:
        return rng.normal(size=len(x))
    target_sorted = np.sort(x)
    target_amp = np.abs(np.fft.rfft(x))
    y = rng.permutation(x)
    for _ in range(n_iter):
        phase = np.angle(np.fft.rfft(y))
        y = np.fft.irfft(target_amp * np.exp(1j * phase), n=len(x))
        y = rank_map_to_sorted(y, target_sorted)
    y = y - np.mean(y)
    return y / (np.sqrt(np.mean(y**2)) + 1e-12)


def discriminative_template_candidates(
    cfg: MillingDatasetConfig,
    verifier: MillingVerifier,
    cls: str,
    max_items: int = 10,
) -> list[dict[str, Any]]:
    prof = verifier.calib["classes_calib"][cls]["recipe_profile"]
    bank = np.asarray(prof.get("iaaft_template_bank", []), dtype=float)
    if bank.ndim != 3 or len(bank) == 0:
        return []
    own_cal = verifier.calib["classes_calib"][cls]["feature_axis"]
    own_med = np.asarray(own_cal["median"], dtype=float)
    own_scale = np.asarray(own_cal["scale"], dtype=float)
    rows = []
    for idx, w in enumerate(bank):
        fv = feature_vector(w, cfg)
        own_dist = float(np.sqrt((((fv - own_med) / own_scale) ** 2).sum()))
        other_dists = []
        for other in cfg.classes:
            if other == cls:
                continue
            cal = verifier.calib["classes_calib"][other]["feature_axis"]
            med = np.asarray(cal["median"], dtype=float)
            scale = np.asarray(cal["scale"], dtype=float)
            other_dists.append(float(np.sqrt((((fv - med) / scale) ** 2).sum())))
        margin = float(min(other_dists) - own_dist) if other_dists else 0.0
        harm = harmonic_vector(w, cfg).reshape(len(cfg.channels), -1)
        rows.append(
            {
                "idx": idx,
                "margin": margin,
                "own_axis": own_dist,
                "total_rms": float(np.sqrt(np.mean(np.mean(w**2, axis=1)))),
                "AE_table_TPF_ratio": float(harm[4, -1]) if harm.shape[0] > 4 and harm.shape[1] else 0.0,
                "AE_spindle_TPF_ratio": float(harm[5, -1]) if harm.shape[0] > 5 and harm.shape[1] else 0.0,
            }
        )
    rows.sort(key=lambda r: (-r["margin"], r["own_axis"], r["idx"]))
    out = []
    for row in rows[:max_items]:
        out.append(
            {
                "idx": int(row["idx"]),
                "margin": round(float(row["margin"]), 3),
                "own_axis": round(float(row["own_axis"]), 3),
                "total_rms": round(float(row["total_rms"]), 5),
                "AE_table_TPF_ratio": round(float(row["AE_table_TPF_ratio"]), 5),
                "AE_spindle_TPF_ratio": round(float(row["AE_spindle_TPF_ratio"]), 5),
            }
        )
    return out


def llm_prompt(
    cfg: MillingDatasetConfig,
    verifier: MillingVerifier,
    cls: str,
    feedback: list[str] | None,
    prev: dict[str, Any] | None,
    mode: str = "standard",
) -> str:
    prof = verifier.calib["classes_calib"][cls]["recipe_profile"]
    freqs = cfg.plugin.char_freqs()
    available_harmonics = harmonic_freqs(cfg)
    has_harmonics = bool(available_harmonics)
    low_cls = class_for_role(cfg, "low")
    mid_cls = class_for_role(cfg, "mid")
    high_cls = class_for_role(cfg, "high")
    schema = {
        "class": cls,
        "template_index": 0,
        "template_indices": [0] * len(cfg.channels),
        "rms_mult": [1.0] * len(cfg.channels),
        "mean_mult": [1.0] * len(cfg.channels),
        "std_mult": [1.0] * len(cfg.channels),
        "harmonic_mult": [[1.0] * len(available_harmonics) for _ in cfg.channels],
        "background_weight": 1.0,
        "background_mode": "spectral_surrogate" if not has_harmonics else "real_exemplar",
        "harmonic_gain": 0.10,
        "noise_gain": 0.02,
        "noise_color": 0.10,
        "shared_gain": 0.02,
        "trend_strength": 0.02,
        "corr_blend": 1.0,
    }
    rms_mid = [round(float(v), 5) for v in prof["rms_median"]]
    rms_lo = [round(float(v), 5) for v in prof["rms_q10"]]
    rms_hi = [round(float(v), 5) for v in prof["rms_q90"]]
    mean_mid = [round(float(v), 5) for v in prof.get("mean_median", [0.0] * len(cfg.channels))]
    std_mid = [round(float(v), 5) for v in prof.get("std_median", prof["rms_median"])]
    class_order = {}
    tpf_idx = len(available_harmonics) - 1
    for other in cfg.classes:
        p = verifier.calib["classes_calib"][other]["recipe_profile"]
        rms_vec = np.asarray(p["rms_median"], dtype=float)
        harm = np.asarray(p["harmonic_amp_median"], dtype=float)
        order_row = {
            "total_rms": round(float(np.sqrt(np.mean(rms_vec**2))), 5),
        }
        if tpf_idx >= 0 and harm.ndim == 2 and harm.shape[1] > tpf_idx:
            for ch_idx, ch_name in enumerate(cfg.channels):
                if harm.shape[0] > ch_idx:
                    order_row[f"{ch_name}_last_harmonic_ratio"] = round(float(harm[ch_idx, tpf_idx]), 5)
        class_order[other] = order_row
    if len(cfg.classes) == 2:
        ranges = (
            f"{low_cls} ranges: rms_mult/std_mult 0.95-1.05, trend 0-0.005; "
            f"{high_cls} ranges: rms_mult/std_mult 0.95-1.10, trend 0-0.012."
        )
    else:
        ranges = (
            f"{low_cls} ranges: rms_mult/std_mult 0.95-1.05, harmonic_gain 0-0.06, trend 0-0.005; "
            f"{mid_cls} ranges: rms_mult/std_mult 0.95-1.08, harmonic_gain 0-0.05, trend 0-0.005; "
            f"{high_cls} ranges: rms_mult/std_mult 0.95-1.10, harmonic_gain 0-0.08, trend 0-0.01."
        )
    if mode in {"contrastive", "repair"}:
        if len(cfg.classes) == 2:
            ranges = (
                f"contrastive ranges: {low_cls} rms/std 0.90-1.12, trend 0-0.010; "
                f"{high_cls} rms/std 0.92-1.22, trend 0-0.025. "
                "background_weight 0.75-1.20, corr_blend 0.40-1.30. "
                "Use these ranges to create class-separating process recipes, not neutral all-ones recipes."
            )
        else:
            ranges = (
                f"contrastive ranges: {low_cls} rms/std 0.90-1.12, harmonic_mult 0.35-1.60, harmonic_gain 0-0.10, trend 0-0.010; "
                f"{mid_cls} rms/std 0.90-1.18, harmonic_mult 0.35-2.10, harmonic_gain 0-0.12, trend 0-0.018; "
                f"{high_cls} rms/std 0.92-1.25, harmonic_mult 0.40-2.40, harmonic_gain 0-0.14, trend 0-0.030. "
                "background_weight 0.75-1.20, corr_blend 0.40-1.30. "
                "Use these ranges to create class-separating recipes, not neutral all-ones recipes."
            )
    dataset_label = "UMich CNC milling" if cfg.name == "umich" else "Berkeley/NASA milling"
    if has_harmonics:
        harmonic_sentence = (
            f"Spindle frequency is {freqs['spindle_hz']:.4f} Hz and tooth passing frequency TPF is {freqs['TPF']:.4f} Hz. "
            "Use spindle and TPF harmonics below Nyquist only when verified and nonzero; otherwise rely on process statistics, PSD shape, trends, and channel correlations. "
            "Wear severity should mainly change RMS multipliers, TPF harmonic multipliers, trend, and correlation. "
        )
        background_sentence = (
            "Use real_exemplar background mode so channel correlations and process PSD come from train-fold exemplars; "
            "the recipe should control wear-specific multipliers rather than inventing a full waveform. "
        )
    else:
        harmonic_sentence = (
            "No verified rotational or tooth-passing harmonics are available below Nyquist for this dataset configuration. "
            "Keep harmonic_mult empty and rely on process RMS/std, operating offsets, PSD shape, trends, and channel correlations. "
        )
        background_sentence = (
            "Use spectral_surrogate background mode so the PSD amplitude comes from train-fold exemplars while phase is randomized; "
            "the recipe should control condition-specific multipliers without copying exact experiment segments. "
        )
    class_relation_sentence = (
        f"Keep the requested class in the correct relative condition position; {high_cls} should be separable from {low_cls}."
        if len(cfg.classes) == 2
        else f"Keep the requested class in the correct relative wear position; {mid_cls} should be intermediate rather than collapsing into {low_cls} or {high_cls}."
    )
    text = (
        f"Design one compact {dataset_label} recipe for class {cls}. "
        f"Sampling rate is {cfg.fs_hz} Hz, window length {cfg.window}, channels are {cfg.channels}. "
        f"{harmonic_sentence}"
        "Do not use bearing envelope assumptions. "
        "For low-rate process channels, preserve DC operating offsets with mean_mult and control fluctuations with std_mult; do not turn DC current channels into zero-mean vibration. "
        f"Use these physical bounds: {ranges} "
        f"Train-only RMS q10/median/q90 are {rms_lo}/{rms_mid}/{rms_hi}. "
        f"Train-only channel mean medians are {mean_mid}; dynamic std medians are {std_mid}. "
        f"Train-only class ordering hints are {json.dumps(class_order, separators=(',', ':'))}. "
        f"{class_relation_sentence} "
        f"Choose template_index from 0 to {max(len(prof.get('rfft_amp_bank', [])) - 1, 0)}. "
        f"{background_sentence}"
        "Return compact multipliers only; do not output full harmonic matrices, profiles, markdown, or commentary. "
        f"Output JSON exactly matching this schema: {json.dumps(schema, separators=(',', ':'))}"
    )
    if mode in {"contrastive", "repair"}:
        proto = discriminative_template_candidates(cfg, verifier, cls, max_items=10)
        if len(cfg.classes) == 2:
            diagnosis = (
                f"previous LLM pools were too close to the rule recipe and weak at separating {low_cls} from {high_cls}."
            )
            template_sentence = (
                "Use per-channel template_indices so process-channel backgrounds can come from different train exemplars when helpful."
            )
            contrastive_goal = (
                f"Preserve the train-only ordering when supported by data: process RMS/std and correlation structure should distinguish {low_cls} from {high_cls}; "
                "do not invent unverified TPF cues when harmonic_freqs_hz is empty. "
                f"For {high_cls}, emphasize feasible worn-tool signatures through process fluctuations, offsets, PSD texture, and trend. "
                f"For {low_cls}, keep a cleaner stable-process background without high-wear-like broadband/crest inflation."
            )
        else:
            diagnosis = (
                "previous LLM pools were too close to the rule recipe and weak on the intermediate wear class."
            )
            template_sentence = (
                "Use per-channel template_indices so force/current/vibration/AE backgrounds can come from different train exemplars when helpful."
            )
            contrastive_goal = (
                f"Preserve the train-only ordering when supported by data: total_rms {low_cls} < {mid_cls} < {high_cls}; verified channel harmonic ratios should generally follow the train ordering. "
                f"For {mid_cls}, emphasize intermediate-but-distinct features: stronger verified harmonics or process energy than {low_cls}, lower than or near {high_cls}, with stable force/current offsets. "
                f"For {high_cls}, emphasize high wear signatures through verified harmonic multipliers and trend, without moving the DC current background out of train range. "
                f"For {low_cls}, keep low wear energy and avoid adding false high-wear signatures."
            )
        text += (
            f"\nContrastive inner-validation diagnosis to fix: {diagnosis} "
            f"{template_sentence} "
            f"{contrastive_goal} "
            f"Train-only high-margin template candidates for this class are {json.dumps(proto, separators=(',', ':'))}. "
            "Choose template_index and template_indices primarily from these candidates, and vary choices across slots instead of repeatedly using one template. "
        )
    if mode == "repair":
        if len(cfg.classes) == 2:
            text += (
                "\nRepair objective from the zero-API attack log: exemplar backgrounds should preserve process PSD and channel structure, while LLM controls class-specific multipliers. "
                "Do not output a neutral rule-like all-ones recipe. The recipe must create an LLM-only class boundary advantage while staying inside the train verifier. "
                f"{high_cls} must be separable from {low_cls} through feasible process fluctuations, operating offsets, PSD texture, correlation, and trend; do not use fabricated tooth-count or spindle cues. "
                f"{low_cls} must stay clean and stable without high-wear-like broadband/crest inflation. "
                f"Latest inner-validation diagnosis: accepted LLM pools overpredicted {high_cls} and collapsed {low_cls} F1. For {low_cls}, create stronger low-wear support with lower fluctuation multipliers, stable offsets, low trend, and coherent low-wear PSD texture; for {high_cls}, keep contrast but avoid making every synthetic boundary point look like {high_cls}. "
                "Use different template choices across slots, but pick coherent backgrounds when class separation would be damaged by mixing channels from unrelated operating segments. "
            )
        else:
            text += (
                "\nRepair objective from the zero-API attack log: per-band EQ and exemplar backgrounds already improved PSD, but LLM still trails the rule recipe by a small margin. "
                "Do not output a neutral rule-like all-ones recipe. The recipe must create an LLM-only class boundary advantage while staying inside the train verifier. "
                f"{mid_cls} must be intermediate but separable: keep total RMS and verified harmonic cues below {high_cls} and above {low_cls}. "
                f"{high_cls} must not collapse into {mid_cls} after dynamic overlays: use stronger but still feasible harmonic/process multipliers and trend than {mid_cls}, while preserving real current-channel DC offsets. "
                f"{low_cls} must stay clean: low trend and no high-wear-like broadband/crest inflation. "
                "Use different template choices across slots, but pick coherent backgrounds when class separation would be damaged by mixing channels from unrelated operating segments. "
                "Avoid manipulating current-channel high-frequency content as the main wear cue unless train-only ordering supports it. "
            )
    if feedback:
        text += "\nPrevious recipe was rejected."
        if prev is not None:
            text += "\nPrevious recipe: " + json.dumps(prev, separators=(",", ":"))
        text += "\nFix these verifier messages with minimal changes:\n- " + "\n- ".join(feedback[:12])
    return text


def run_slot(
    cfg: MillingDatasetConfig,
    verifier: MillingVerifier,
    cls: str,
    source: str,
    slot: int,
    out_dir: Path,
    counter: dict[str, int],
    max_api_requests: int,
    k: int,
    expansions: int,
    llm_mode: str,
) -> dict[str, Any]:
    rec_path = out_dir / f"{source}_{cls}_{slot:04d}.json"
    if rec_path.exists():
        return json.loads(rec_path.read_text())
    feedback = None
    prev = None
    history = []
    accepted_paths = []
    if source in {"rule", "random_open_loop"}:
        recipe = recipe_from_profile(cfg, verifier, cls, source, slot)
        rounds = [recipe]
    else:
        rounds = []
    for rnd in range(k + 1):
        if source == "llm":
            if counter["requests"] >= max_api_requests:
                break
            messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": llm_prompt(cfg, verifier, cls, feedback, prev, llm_mode)}]
            text = llm.chat(messages, temperature=0.8, max_retries=3, max_tokens=900)
            counter["requests"] += 1
            compact_recipe = llm.parse_recipe(text)
            recipe = expand_llm_recipe(compact_recipe, cfg, verifier, cls, slot, llm_mode)
            schema_bad = validate_llm_recipe(recipe, cfg)
            if schema_bad:
                history.append({"round": rnd, "schema_bad": schema_bad, "raw_response": text})
                feedback = schema_bad
                prev = compact_recipe
                continue
        else:
            if rnd > 0:
                break
            recipe = rounds[0]
            schema_bad = []
        assert recipe is not None
        recipe = attach_renderer_profile(recipe, verifier, cls)
        reports = []
        paths = []
        for exp in range(expansions):
            w = render_recipe(recipe, cfg, stable_seed(cfg.name, source, cls, slot, rnd, exp))
            report = {"feasible": True, "gates": {}, "scores": {}} if source == "random_open_loop" else verifier.verify(w, cls)
            reports.append(report)
            if report["feasible"]:
                path = out_dir / f"{source}_{cls}_{slot:04d}_r{rnd}_e{exp}.npy"
                np.save(path, w)
                paths.append(str(path.relative_to(ROOT)))
        history.append({"round": rnd, "recipe": recipe, "n_feasible": len(paths), "reports": reports})
        if paths:
            accepted_paths.extend(paths)
            break
        feedback = []
        for rep in reports[:3]:
            for gate in rep.get("gates", {}).values():
                if not gate.get("passed", True):
                    feedback.extend(gate.get("messages", []))
        feedback = feedback or ["Verifier rejected all rendered candidates; adjust RMS, harmonic ratios, PSD shape, and correlations toward train profile."]
        prev = recipe
    rec = {"source": source, "class": cls, "slot": slot, "accepted": bool(accepted_paths), "accepted_paths": accepted_paths, "history": history}
    rec_path.write_text(json.dumps(tolist(rec), indent=2) + "\n")
    return rec


def build_pool(cfg: MillingDatasetConfig, out_dir: Path) -> dict[str, Any]:
    xs, ys, manifest = [], [], []
    for p in sorted(out_dir.glob("*.json")):
        rec = json.loads(p.read_text())
        if "class" not in rec:
            continue
        ci = cfg.classes.index(rec["class"])
        for rel in rec.get("accepted_paths", []):
            xs.append(np.load(ROOT / rel))
            ys.append(ci)
            manifest.append({"source": rec["source"], "class": rec["class"], "slot": rec["slot"], "path": rel})
    if xs:
        X = np.stack(xs).astype(np.float32)
        y = np.asarray(ys, dtype=np.int64)
    else:
        X = np.zeros((0, len(cfg.channels), cfg.window), dtype=np.float32)
        y = np.zeros((0,), dtype=np.int64)
    np.savez_compressed(out_dir / "pool.npz", X=X, y=y, class_names=np.asarray(cfg.classes))
    with (out_dir / "manifest.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "class", "slot", "path"])
        writer.writeheader()
        writer.writerows(manifest)
    rec_paths = []
    for p in out_dir.glob("*.json"):
        try:
            r = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if "class" in r and "source" in r:
            rec_paths.append(p)
    summary = {
        "n": int(len(y)),
        "counts": {cfg.classes[i]: int((y == i).sum()) for i in range(len(cfg.classes))},
        "slots": len(rec_paths),
        "accepted_slots": int(sum(json.loads(p.read_text()).get("accepted", False) for p in rec_paths)),
    }
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["berkeley", "umich"], default="berkeley")
    parser.add_argument("--train-npz", default="", help="Override calibration/training NPZ; relative paths are resolved from the project root.")
    parser.add_argument("--source", choices=["rule", "random_open_loop", "llm"], required=True)
    parser.add_argument("--slots-per-class", type=int, default=3)
    parser.add_argument("--classes", default="", help="Comma-separated subset of classes to generate; default uses all classes.")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--expansions", type=int, default=5)
    parser.add_argument("--max-api-requests", type=int, default=30)
    parser.add_argument("--out-root", default="breeze/runs/milling_generation_2026-07-07")
    parser.add_argument("--llm-mode", choices=["standard", "contrastive", "repair"], default="standard")
    args = parser.parse_args()
    cfg = BERKELEY if args.dataset == "berkeley" else UMICH
    if args.train_npz.strip():
        train_npz = Path(args.train_npz)
        if not train_npz.is_absolute():
            train_npz = ROOT / train_npz
        cfg = cfg_from_train_npz(cfg, train_npz)
    X, y = load_train(cfg)
    out_dir = ROOT / args.out_root / cfg.name / args.source
    out_dir.mkdir(parents=True, exist_ok=True)
    cal_path = out_dir / "verifier_c90.json"
    if cal_path.exists():
        verifier = MillingVerifier.load(cfg, cal_path)
    else:
        verifier = MillingVerifier(cfg, coverage=0.90)
        verifier.calibrate(X, y)
        verifier.save(cal_path)
    if args.source == "llm":
        if not os.environ.get("DASHSCOPE_API_KEY"):
            raise SystemExit("DASHSCOPE_API_KEY is not set")
        llm.API_KEY = os.environ["DASHSCOPE_API_KEY"]
    counter = {"requests": 0}
    selected_classes = cfg.classes
    if args.classes.strip():
        selected_classes = [c.strip() for c in args.classes.split(",") if c.strip()]
        unknown = sorted(set(selected_classes) - set(cfg.classes))
        if unknown:
            raise SystemExit(f"unknown classes: {unknown}; valid={cfg.classes}")
    for cls in selected_classes:
        for slot in range(args.slots_per_class):
            run_slot(cfg, verifier, cls, args.source, slot, out_dir, counter, args.max_api_requests, args.k, args.expansions, args.llm_mode)
    summary = build_pool(cfg, out_dir)
    summary["api_requests"] = counter["requests"]
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2) + "\n")
    print(json.dumps(tolist(summary), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
