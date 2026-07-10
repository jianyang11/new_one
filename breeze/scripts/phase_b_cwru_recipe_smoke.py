"""CWRU single-channel random/rule recipe smoke under a train-only verifier.

This is a Phase-B smoke script, not the final CWRU full experiment. It exists
to validate the dataset-specific renderer/verifier boundary before any costly
LLM generation. The verifier uses only the provided train split.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import find_peaks, firwin, filtfilt, hilbert, welch
from scipy.stats import kurtosis, skew


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RUNS = BREEZE / "runs"
RESULTS = BREEZE / "results"

FS = 12_000
WIN = 2048
CWRU_CLASSES = ("healthy", "IR", "B", "OR")
BANDS = tuple((float(lo), float(lo + 500)) for lo in range(0, 6000, 500))
T = np.arange(WIN) / FS
FREQ_MULT = {"IR": 5.4152, "B": 4.7135, "OR": 3.5848}
FTF_MULT = 0.39828


def stable_seed(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def time_stats(x: np.ndarray) -> dict[str, float]:
    rms = float(np.sqrt(np.mean(x * x)))
    peak = float(np.max(np.abs(x)))
    return {
        "rms": rms,
        "peak": peak,
        "std": float(np.std(x)),
        "kurtosis": float(kurtosis(x, fisher=False)),
        "skewness": float(skew(x)),
        "crest": float(peak / (rms + 1e-12)),
    }


def psd(x: np.ndarray, nperseg: int = 512) -> tuple[np.ndarray, np.ndarray]:
    return welch(x, fs=FS, nperseg=nperseg)


def band_fracs(x: np.ndarray) -> np.ndarray:
    f, p = psd(x)
    total = float(np.trapezoid(p, f)) + 1e-30
    vals = []
    for lo, hi in BANDS:
        m = (f >= lo) & (f < hi)
        vals.append(float(np.trapezoid(p[m], f[m]) / total))
    vals = np.asarray(vals, dtype=float)
    return vals / (vals.sum() + 1e-30)


def _joint_alpha(values: np.ndarray, target: float) -> float:
    best_alpha, best_gap = 0.02, np.inf
    for alpha in np.linspace(0.001, 0.12, 50):
        lo = np.quantile(values, alpha / 2, axis=0)
        hi = np.quantile(values, 1 - alpha / 2, axis=0)
        rate = float(np.mean(np.all((values >= lo) & (values <= hi), axis=1)))
        gap = abs(rate - target)
        if gap < best_gap:
            best_alpha, best_gap = float(alpha), float(gap)
    return best_alpha


def psd_cdf(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    f, p = psd(x)
    mass = np.maximum(p, 0) * np.gradient(f)
    mass = mass / (mass.sum() + 1e-30)
    cdf = np.cumsum(mass)
    return f, cdf / (cdf[-1] + 1e-30)


def psd_w1(x: np.ndarray, ref_cdf: np.ndarray) -> float:
    f, cdf = psd_cdf(x)
    return float(np.trapezoid(np.abs(cdf - ref_cdf), f))


def envelope_spectrum(x: np.ndarray, band: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    ny = FS / 2
    lo = max(5.0, band[0])
    hi = min(band[1], ny * 0.98)
    if lo >= hi:
        hi = min(ny * 0.98, lo + 500)
    taps = firwin(129, [lo / ny, hi / ny], pass_zero=False)
    xb = filtfilt(taps, [1.0], x)
    env = np.abs(hilbert(xb)) ** 2
    env = env - np.mean(env)
    spec = np.abs(np.fft.rfft(env * np.hanning(len(env)))) / len(env)
    freqs = np.fft.rfftfreq(len(env), 1 / FS)
    return freqs, spec


def env_peak(x: np.ndarray, band: tuple[float, float], target_hz: float) -> dict[str, float]:
    f, s = envelope_spectrum(x, band)
    df = f[1] - f[0]
    tol = max(2 * df, 0.03 * target_hz)
    m = (f >= target_hz - tol) & (f <= target_hz + tol)
    if not np.any(m):
        return {"prominence": 0.0, "peak_freq": np.nan, "err_hz": tol}
    j = np.argmax(s[m])
    peak_f = float(f[m][j])
    peak_a = float(s[m][j])
    nb = (f >= max(2.0, target_hz - 10 * tol)) & (f <= target_hz + 10 * tol)
    floor = float(np.median(s[nb])) + 1e-30
    return {"prominence": peak_a / floor, "peak_freq": peak_f, "err_hz": abs(peak_f - target_hz)}


def candidate_bands() -> list[tuple[float, float]]:
    bands = []
    lo = 500.0
    while lo + 1500.0 <= FS / 2:
        bands.append((lo, lo + 1500.0))
        lo += 500.0
    return bands


def target_freq(cls: str, fr_hz: float) -> float:
    if cls == "healthy":
        return 0.0
    return FREQ_MULT[cls] * fr_hz


def _band_shaped_noise(rng: np.random.Generator, rms: float, weights: np.ndarray) -> np.ndarray:
    x = rng.normal(0, 1, WIN)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(WIN, 1 / FS)
    g = np.zeros_like(f)
    weights = np.maximum(weights, 0)
    weights = weights / (weights.sum() + 1e-30)
    for (lo, hi), w in zip(BANDS, weights):
        m = (f >= lo) & (f < hi)
        g[m] = np.sqrt(w / max(hi - lo, 1.0))
    y = np.fft.irfft(X * g, WIN)
    return y / (np.std(y) + 1e-12) * rms


def _psd_template_signal(rng: np.random.Generator, rms: float, amp_template: list[float]) -> np.ndarray:
    amp = np.asarray(amp_template, dtype=float)
    phase = rng.uniform(0, 2 * np.pi, len(amp))
    phase[0] = 0.0
    if len(phase) > 1:
        phase[-1] = 0.0
    spec = amp * np.exp(1j * phase)
    x = np.fft.irfft(spec, WIN)
    return x / (np.std(x) + 1e-12) * rms


def _band_energies(x: np.ndarray) -> np.ndarray:
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / FS)
    p = np.abs(X) ** 2
    return np.asarray([p[(f >= lo) & (f < hi)].sum() for lo, hi in BANDS], dtype=float)


def _equalize_to_band_weights(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    weights = np.maximum(weights, 0)
    weights = weights / (weights.sum() + 1e-30)
    y = x.copy()
    for _ in range(4):
        current = band_fracs(y)
        gains = np.clip(np.sqrt(weights / (current + 1e-30)), 0.05, 10.0)
        X = np.fft.rfft(y)
        f = np.fft.rfftfreq(len(y), 1 / FS)
        g = np.ones_like(f)
        for (lo, hi), gain in zip(BANDS, gains):
            g[(f >= lo) & (f < hi)] = gain
        y = np.fft.irfft(X * g, len(y))
    return y


def _impulse_train(
    rng: np.random.Generator,
    rate_hz: float,
    amp: float,
    decay_ms: float,
    resonance_hz: float,
    jitter_pct: float,
    amp_var_pct: float,
    modulation: str,
    mod_depth: float,
    fr_hz: float,
) -> np.ndarray:
    x = np.zeros(WIN)
    if amp <= 0 or rate_hz <= 0:
        return x
    period = FS / rate_hz
    pos = rng.uniform(0, period)
    tau = decay_ms / 1000.0
    length = min(int(6 * tau * FS) + 1, WIN)
    tt = np.arange(length) / FS
    env = np.exp(-tt / tau)
    while pos < WIN:
        i = int(pos)
        a = amp * (1 + rng.normal(0, amp_var_pct / 100.0))
        if modulation == "shaft":
            a *= 1 + mod_depth * np.cos(2 * np.pi * fr_hz * pos / FS)
        elif modulation == "cage":
            a *= 1 + mod_depth * np.cos(2 * np.pi * FTF_MULT * fr_hz * pos / FS)
        kernel = env * np.sin(2 * np.pi * resonance_hz * tt + rng.uniform(0, 2 * np.pi))
        seg = min(length, WIN - i)
        x[i : i + seg] += a * kernel[:seg]
        pos += period * (1 + rng.normal(0, jitter_pct / 100.0))
    return x


def render(recipe: dict[str, Any], seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    bg = recipe["background"]
    x = np.zeros(WIN)
    for comp in bg.get("components", []):
        x += float(comp["amp"]) * np.sin(
            2 * np.pi * float(comp["freq_hz"]) * T + rng.uniform(0, 2 * np.pi)
        )
    imp = recipe["impacts"]
    x += _impulse_train(
        rng,
        float(imp["rate_hz"]),
        float(imp["amp"]),
        float(imp["decay_ms"]),
        float(imp["resonance_hz"]),
        float(imp["jitter_pct"]),
        float(imp["amp_var_pct"]),
        imp.get("modulation", {}).get("type", "none"),
        float(imp.get("modulation", {}).get("depth", 0.0)),
        float(recipe["fr_hz"]),
    )
    if bg.get("random_impulses", {}).get("amp", 0.0) > 0:
        ri = bg["random_impulses"]
        n_imp = rng.poisson(float(ri["rate_hz"]) * WIN / FS)
        tau = float(ri["decay_ms"]) / 1000.0
        length = min(int(6 * tau * FS) + 1, WIN)
        tt = np.arange(length) / FS
        env = np.exp(-tt / tau)
        resonance = float(ri["resonance_hz"])
        for _ in range(n_imp):
            start = int(rng.integers(0, WIN))
            amp = float(ri["amp"]) * rng.uniform(0.25, 1.25)
            kernel = env * np.sin(2 * np.pi * resonance * tt + rng.uniform(0, 2 * np.pi))
            seg = min(length, WIN - start)
            x[start : start + seg] += amp * kernel[:seg]
    weights = np.asarray(bg["band_weights"], dtype=float)
    if "psd_template_amp" in bg:
        x += _psd_template_signal(rng, float(bg["noise_rms"]), bg["psd_template_amp"])
    else:
        x += _band_shaped_noise(rng, float(bg["noise_rms"]), weights)
        x = _equalize_to_band_weights(x, weights)
    target = float(recipe["target_rms"])
    x = x / (np.sqrt(np.mean(x * x)) + 1e-12) * target
    return x[None, :].astype(np.float32)


@dataclass
class Profile:
    rms_q05: float
    rms_q50: float
    rms_q95: float
    peak_q50: float
    kurtosis_q50: float
    band_median: list[float]
    components: list[dict[str, float]]
    resonance_bands: list[tuple[float, float]]
    psd_template_amp: list[float]


def top_components(W: np.ndarray) -> list[dict[str, float]]:
    f, _ = psd(W[0, 0])
    psds = [psd(w[0])[1] for w in W[: min(len(W), 240)]]
    p = np.mean(psds, axis=0)
    mask = (f >= 5) & (f <= 1000)
    peaks, _ = find_peaks(np.log10(p[mask] + 1e-18), prominence=0.2)
    idx = np.where(mask)[0][peaks]
    if len(idx) == 0:
        idx = np.where(mask)[0][np.argsort(p[mask])[-5:]]
    idx = sorted(idx, key=lambda i: -p[i])[:5]
    df = float(f[1] - f[0])
    return [{"freq_hz": float(f[i]), "amp": float(np.sqrt(4 * p[i] * df))} for i in sorted(idx)]


def build_profiles(X: np.ndarray, y: np.ndarray, meta: list[dict[str, Any]]) -> tuple[dict[str, Profile], dict[str, Any]]:
    profiles: dict[str, Profile] = {}
    rpm = np.asarray([float(m["rpm"]) for m in meta])
    fr_hz = float(np.median(rpm) / 60.0)
    for ci, cls in enumerate(CWRU_CLASSES):
        W = X[y == ci]
        stats = [time_stats(w[0]) for w in W]
        rms = np.asarray([s["rms"] for s in stats])
        peak = np.asarray([s["peak"] for s in stats])
        kurt = np.asarray([s["kurtosis"] for s in stats])
        bands = np.asarray([band_fracs(w[0]) for w in W[: min(len(W), 600)]])
        amps = np.asarray([np.abs(np.fft.rfft(w[0] - np.mean(w[0]))) for w in W[: min(len(W), 600)]])
        resonance = []
        if cls != "healthy":
            f0 = target_freq(cls, fr_hz)
            scored = []
            for band in candidate_bands():
                vals = [env_peak(w[0], band, f0)["prominence"] for w in W[: min(len(W), 160)]]
                scored.append((float(np.median(vals)), band))
            resonance = [band for _, band in sorted(scored, reverse=True)[:3]]
        profiles[cls] = Profile(
            rms_q05=float(np.quantile(rms, 0.05)),
            rms_q50=float(np.quantile(rms, 0.50)),
            rms_q95=float(np.quantile(rms, 0.95)),
            peak_q50=float(np.quantile(peak, 0.50)),
            kurtosis_q50=float(np.quantile(kurt, 0.50)),
            band_median=(np.median(bands, axis=0) / (np.median(bands, axis=0).sum() + 1e-30)).tolist(),
            components=top_components(W),
            resonance_bands=resonance,
            psd_template_amp=np.median(amps, axis=0).astype(float).tolist(),
        )
    return profiles, {"fr_hz": fr_hz, "rpm_median": float(np.median(rpm))}


class CwruVerifier:
    def __init__(self, coverage: float = 0.90):
        self.coverage = coverage
        self.calib: dict[str, Any] = {}

    def calibrate(self, X: np.ndarray, y: np.ndarray, meta: list[dict[str, Any]]) -> None:
        rpm = np.asarray([float(m["rpm"]) for m in meta])
        fr_hz = float(np.median(rpm) / 60.0)
        self.calib = {"coverage": self.coverage, "fr_hz": fr_hz, "classes": {}}
        for ci, cls in enumerate(CWRU_CLASSES):
            W = X[y == ci]
            stats = np.asarray([[time_stats(w[0])[k] for k in ("rms", "peak", "std", "kurtosis", "skewness", "crest")] for w in W])
            alpha = _joint_alpha(stats, self.coverage)
            lo = np.quantile(stats, alpha / 2, axis=0)
            hi = np.quantile(stats, 1 - alpha / 2, axis=0)
            bands = np.asarray([band_fracs(w[0]) for w in W[: min(len(W), 600)]])
            alpha_b = _joint_alpha(bands, self.coverage)
            blo = np.quantile(bands, alpha_b / 2, axis=0)
            bhi = np.quantile(bands, 1 - alpha_b / 2, axis=0)
            bhi = np.maximum(bhi, 1e-4)
            cdfs = [psd_cdf(w[0])[1] for w in W[: min(len(W), 600)]]
            ref = np.mean(cdfs, axis=0)
            w1_vals = np.asarray([psd_w1(w[0], ref) for w in W[: min(len(W), 600)]])
            entry: dict[str, Any] = {
                "stats_lo": lo,
                "stats_hi": hi,
                "bands_lo": blo,
                "bands_hi": bhi,
                "psd_ref": ref,
                "psd_w1_max": float(np.quantile(w1_vals, self.coverage)),
            }
            if cls != "healthy":
                f0 = target_freq(cls, fr_hz)
                band_scores = []
                for band in candidate_bands():
                    vals = np.asarray([env_peak(w[0], band, f0)["prominence"] for w in W[: min(len(W), 160)]])
                    band_scores.append((float(np.median(vals)), band, float(np.quantile(vals, 1 - self.coverage))))
                chosen = sorted(band_scores, reverse=True)[:3]
                entry["target_hz"] = f0
                entry["resonance_bands"] = [band for _, band, _ in chosen]
                entry["env_min"] = min(thr for _, _, thr in chosen)
            else:
                entry["target_hz"] = 0.0
                entry["resonance_bands"] = []
                entry["env_max"] = 10.0
            self.calib["classes"][cls] = entry

    def verify(self, w: np.ndarray, cls: str) -> dict[str, Any]:
        report = {"class": cls, "feasible": True, "gate_pass": {}, "violations": []}
        if w.shape != (1, WIN) or not np.all(np.isfinite(w)):
            report["feasible"] = False
            report["gate_pass"]["sanity"] = False
            report["violations"].append("shape or finite sanity failed")
            return report
        report["gate_pass"]["sanity"] = True
        entry = self.calib["classes"][cls]
        st_vec = np.asarray([time_stats(w[0])[k] for k in ("rms", "peak", "std", "kurtosis", "skewness", "crest")])
        ok_stats = bool(np.all((st_vec >= entry["stats_lo"]) & (st_vec <= entry["stats_hi"])))
        report["gate_pass"]["stats"] = ok_stats
        if not ok_stats:
            report["violations"].append("time statistics outside train-supported interval")
        bf = band_fracs(w[0])
        ok_band = bool(np.all((bf >= entry["bands_lo"]) & (bf <= entry["bands_hi"])))
        report["gate_pass"]["soft_spectrum"] = ok_band
        if not ok_band:
            report["violations"].append("soft spectral fractions outside train-supported interval")
        w1 = psd_w1(w[0], entry["psd_ref"])
        ok_w1 = bool(w1 <= entry["psd_w1_max"])
        report["gate_pass"]["psd_w1"] = ok_w1
        if not ok_w1:
            report["violations"].append(f"PSD W1 {w1:.3f} exceeds {entry['psd_w1_max']:.3f}")
        ok_env = True
        if cls != "healthy":
            vals = [env_peak(w[0], tuple(band), entry["target_hz"])["prominence"] for band in entry["resonance_bands"]]
            ok_env = bool(max(vals or [0.0]) >= entry["env_min"])
            if not ok_env:
                report["violations"].append("fault envelope prominence below train-calibrated minimum")
            report["env_prominence_max"] = float(max(vals or [0.0]))
        report["gate_pass"]["envelope"] = ok_env
        report["feasible"] = all(report["gate_pass"].values())
        return report


def random_recipe(cls: str, profiles: dict[str, Profile], meta: dict[str, Any], slot: int) -> dict[str, Any]:
    rng = np.random.default_rng(stable_seed(f"cwru-random:{cls}:{slot}"))
    prof = profiles[cls]
    target = float(np.exp(rng.uniform(np.log(max(prof.rms_q05, 1e-8)), np.log(max(prof.rms_q95, prof.rms_q05 + 1e-8)))))
    if cls == "healthy":
        rate, amp, mod = 0.0, 0.0, {"type": "none", "depth": 0.0}
    else:
        rate = target_freq(cls, meta["fr_hz"])
        amp = float(rng.uniform(1.5, 8.0) * target)
        mod = {"type": "shaft" if cls == "IR" else ("cage" if cls == "B" else "none"), "depth": float(rng.uniform(0.1, 0.9))}
    return {
        "fr_hz": meta["fr_hz"],
        "target_rms": target,
        "impacts": {
            "rate_hz": rate,
            "amp": amp,
            "decay_ms": float(np.exp(rng.uniform(np.log(0.4), np.log(5.0)))),
            "resonance_hz": float(rng.uniform(500.0, 5500.0)),
            "jitter_pct": float(rng.uniform(0.0, 6.0)),
            "amp_var_pct": float(rng.uniform(0.0, 45.0)),
            "modulation": mod,
        },
        "background": {
            "noise_rms": float(rng.uniform(0.05, 0.35) * target),
            "band_weights": rng.dirichlet(np.ones(len(BANDS))).tolist(),
            "components": [],
            "random_impulses": {"rate_hz": float(rng.uniform(0, 80)), "amp": float(rng.uniform(0, 2.5) * target), "decay_ms": 1.0, "resonance_hz": float(rng.uniform(500, 5500))},
        },
    }


def rule_recipe(cls: str, profiles: dict[str, Profile], meta: dict[str, Any], slot: int) -> dict[str, Any]:
    prof = profiles[cls]
    wiggle = float(np.exp(0.05 * np.sin(0.61803398875 * (slot + 1))))
    target = prof.rms_q50 * wiggle
    if cls == "healthy":
        rate, amp, mod = 0.0, 0.0, {"type": "none", "depth": 0.0}
        rand_amp = 0.0
        rand_rate = 0.0
        components: list[dict[str, float]] = []
        psd_template = prof.psd_template_amp
    else:
        rate = target_freq(cls, meta["fr_hz"])
        amp = float(np.clip(np.sqrt(max(prof.kurtosis_q50, 3.0)) * 2.0, 2.5, 7.0) * target)
        mod = {"type": "shaft" if cls == "IR" else ("cage" if cls == "B" else "none"), "depth": 0.55 if cls != "OR" else 0.0}
        rand_amp = 0.15 * target
        rand_rate = 15.0
        components = prof.components
        psd_template = None
    if cls != "healthy" and prof.resonance_bands:
        band = prof.resonance_bands[slot % len(prof.resonance_bands)]
        resonance = float((band[0] + band[1]) / 2)
    else:
        resonance = 2500.0
    recipe = {
        "fr_hz": meta["fr_hz"],
        "target_rms": float(target),
        "impacts": {
            "rate_hz": rate,
            "amp": amp,
            "decay_ms": 1.4 if cls in ("IR", "B") else 2.0,
            "resonance_hz": resonance,
            "jitter_pct": 1.5,
            "amp_var_pct": 16.0,
            "modulation": mod,
        },
        "background": {
            "noise_rms": float(target if cls == "healthy" else 0.12 * target),
            "band_weights": prof.band_median,
            "components": components,
            "random_impulses": {"rate_hz": float(rand_rate), "amp": float(rand_amp), "decay_ms": 1.0, "resonance_hz": resonance},
        },
    }
    if psd_template is not None:
        recipe["background"]["psd_template_amp"] = psd_template
    return recipe


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-npz", default="proc/cwru_de12k_within_load0_train.npz")
    parser.add_argument("--split", default="within_load0")
    parser.add_argument("--source", choices=["random", "rule", "both"], default="both")
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--expansions", type=int, default=5)
    parser.add_argument("--coverage", type=float, default=0.90)
    parser.add_argument("--tag", default="smoke")
    args = parser.parse_args()

    data = np.load(ROOT / args.train_npz, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    meta_rows = [json.loads(str(item)) for item in data["metadata"]]
    profiles, meta = build_profiles(X, y, meta_rows)
    verifier = CwruVerifier(args.coverage)
    verifier.calibrate(X, y, meta_rows)

    sources = ["random", "rule"] if args.source == "both" else [args.source]
    for source in sources:
        out_dir = RUNS / f"phaseB_cwru_{args.split}_{source}_{args.tag}"
        out_dir.mkdir(parents=True, exist_ok=True)
        slot_rows: list[dict[str, Any]] = []
        manifest: list[dict[str, Any]] = []
        for cls in CWRU_CLASSES:
            for slot in range(args.n):
                rec_path = out_dir / f"{cls}_{slot:04d}.json"
                if rec_path.exists():
                    rec = json.loads(rec_path.read_text())
                    slot_rows.append(
                        {
                            "source": source,
                            "class": cls,
                            "slot": slot,
                            "accepted_slot": bool(rec["accepted"]),
                            "n_candidates": rec["n_candidates"],
                            "n_feasible_expansions": rec["n_feasible_expansions"],
                        }
                    )
                    for path in rec.get("accepted_paths", []):
                        manifest.append({"source": source, "class": cls, "slot": slot, "path": path})
                    continue
                recipe = random_recipe(cls, profiles, meta, slot) if source == "random" else rule_recipe(cls, profiles, meta, slot)
                accepted_paths = []
                reports = []
                for exp in range(args.expansions):
                    seed = stable_seed(f"{source}:{cls}:{slot}:{exp}")
                    w = render(recipe, seed)
                    report = verifier.verify(w, cls)
                    reports.append(report)
                    if report["feasible"]:
                        path = out_dir / f"{cls}_{slot:04d}_r{exp}.npy"
                        np.save(path, w)
                        accepted_paths.append(str(path.relative_to(ROOT)))
                rec = {
                    "source": source,
                    "class": cls,
                    "slot": slot,
                    "recipe": recipe,
                    "accepted": bool(accepted_paths),
                    "n_candidates": args.expansions,
                    "n_feasible_expansions": len(accepted_paths),
                    "accepted_paths": accepted_paths,
                    "reports": reports,
                }
                rec_path.write_text(json.dumps(rec, indent=2) + "\n")
                slot_rows.append(
                    {
                        "source": source,
                        "class": cls,
                        "slot": slot,
                        "accepted_slot": bool(accepted_paths),
                        "n_candidates": args.expansions,
                        "n_feasible_expansions": len(accepted_paths),
                    }
                )
                for path in accepted_paths:
                    manifest.append({"source": source, "class": cls, "slot": slot, "path": path})
        if manifest:
            xs, ys = [], []
            for item in manifest:
                xs.append(np.load(ROOT / item["path"]).astype(np.float32))
                ys.append(CWRU_CLASSES.index(item["class"]))
            np.savez_compressed(out_dir / "pool.npz", X=np.stack(xs), y=np.asarray(ys, dtype=np.int64), class_names=np.asarray(CWRU_CLASSES))
        write_csv(out_dir / "slot_summary.csv", slot_rows)
        if manifest:
            write_csv(out_dir / "manifest.csv", manifest)
        by_class = {}
        for cls in CWRU_CLASSES:
            rows = [r for r in slot_rows if r["class"] == cls]
            by_class[cls] = {
                "slots": len(rows),
                "accepted_slots": int(sum(bool(r["accepted_slot"]) for r in rows)),
                "accepted_items": int(sum(int(r["n_feasible_expansions"]) for r in rows)),
            }
        summary = {
            "dataset": "CWRU",
            "split": args.split,
            "source": source,
            "coverage": args.coverage,
            "slots": len(slot_rows),
            "accepted_slots": int(sum(bool(r["accepted_slot"]) for r in slot_rows)),
            "accepted_items": int(sum(int(r["n_feasible_expansions"]) for r in slot_rows)),
            "by_class": by_class,
            "pool": str((out_dir / "pool.npz").relative_to(ROOT)) if manifest else "",
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
