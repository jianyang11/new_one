"""Generate random/rule recipe ablation pools under the v2 verifier.

This script tests whether the LLM recipe source contributes beyond the
deterministic renderer and verifier. It creates three non-LLM recipe sources:

- random recipe + renderer + v2 verifier;
- rule recipe + renderer + v2 verifier.
- empirical recipe + renderer + v2 verifier.

All use the same slot budget, renderer equations, train-only v2 verifier, and
diversity gate as the LLM v2 pool. Results are checkpoint-resumable because each
slot writes its own JSON and candidate windows before the pool is assembled.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import find_peaks


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RUNS = BREEZE / "runs"
RESULTS = BREEZE / "results"
REPORTS = ROOT / "reports"

sys.path.insert(0, str(BREEZE / "src"))
from config import CLASSES, CONDITIONS, FS, MAIN_COND, fault_freqs
from data import load_file_split
from renderer import BANDS, render
from verifier.features import psd, time_stats
from verifier.v2 import BreezeVerifierV2


STAT_KEYS = ("rms", "peak", "std", "kurtosis", "skewness", "crest")


def stable_seed(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


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


def band_fracs(x: np.ndarray) -> np.ndarray:
    f, p = psd(x, FS, nperseg=2048)
    total = float(np.trapezoid(p, f)) + 1e-30
    vals = []
    for lo, hi in BANDS:
        m = (f >= lo) & (f < hi)
        vals.append(float(np.trapezoid(p[m], f[m]) / total))
    vals = np.asarray(vals, dtype=float)
    return vals / (vals.sum() + 1e-30)


def top_components(windows: np.ndarray, max_components: int = 5) -> list[dict[str, float]]:
    psds = []
    for w in windows[: min(len(windows), 240)]:
        psds.append(psd(w[0], FS, nperseg=2048)[1])
    fgrid = psd(windows[0][0], FS, nperseg=2048)[0]
    pmean = np.mean(psds, axis=0)
    mask = (fgrid >= 5.0) & (fgrid <= 500.0)
    peak_idx, props = find_peaks(np.log10(pmean[mask] + 1e-18), prominence=0.25)
    candidates = np.where(mask)[0][peak_idx]
    if len(candidates) == 0:
        candidates = np.argsort(pmean[mask])[-max_components:]
        candidates = np.where(mask)[0][candidates]
    order = sorted(candidates, key=lambda i: -pmean[i])[:max_components]
    df = float(fgrid[1] - fgrid[0])
    return [
        {"freq_hz": float(fgrid[i]), "amp": float(np.sqrt(4.0 * pmean[i] * df))}
        for i in sorted(order)
    ]


@dataclass
class ClassProfile:
    rms_q05: float
    rms_q50: float
    rms_q95: float
    kurtosis_q50: float
    band_median: list[float]
    components: list[dict[str, float]]
    current_rms_q05: float
    current_rms_q50: float
    current_rms_q95: float
    current_kurtosis_q50: float
    current_crest_q50: float
    peak_q50: float
    rms_values: list[float]
    peak_values: list[float]
    kurtosis_values: list[float]
    band_pool: list[list[float]]
    current_rms_values: list[float]
    current_kurtosis_values: list[float]
    current_crest_values: list[float]


def build_profiles(Xtr: np.ndarray, ytr: np.ndarray) -> dict[str, ClassProfile]:
    profiles: dict[str, ClassProfile] = {}
    for ci, cls in enumerate(CLASSES):
        W = Xtr[ytr == ci]
        vib_stats = [time_stats(w[0]) for w in W]
        cur_stats = [time_stats(w[1]) for w in W]
        rms = np.asarray([s["rms"] for s in vib_stats], dtype=float)
        peak = np.asarray([s["peak"] for s in vib_stats], dtype=float)
        kurt = np.asarray([s["kurtosis"] for s in vib_stats], dtype=float)
        crms = np.asarray([s["rms"] for s in cur_stats], dtype=float)
        ckur = np.asarray([s["kurtosis"] for s in cur_stats], dtype=float)
        ccrest = np.asarray([s["crest"] for s in cur_stats], dtype=float)
        bands = np.asarray([band_fracs(w[0]) for w in W[: min(len(W), 600)]])
        profiles[cls] = ClassProfile(
            rms_q05=float(np.quantile(rms, 0.05)),
            rms_q50=float(np.quantile(rms, 0.50)),
            rms_q95=float(np.quantile(rms, 0.95)),
            kurtosis_q50=float(np.quantile(kurt, 0.50)),
            band_median=(np.median(bands, axis=0) / (np.median(bands, axis=0).sum() + 1e-30)).tolist(),
            components=top_components(W),
            current_rms_q05=float(np.quantile(crms, 0.05)),
            current_rms_q50=float(np.quantile(crms, 0.50)),
            current_rms_q95=float(np.quantile(crms, 0.95)),
            current_kurtosis_q50=float(np.quantile(ckur, 0.50)),
            current_crest_q50=float(np.quantile(ccrest, 0.50)),
            peak_q50=float(np.quantile(peak, 0.50)),
            rms_values=rms.astype(float).tolist(),
            peak_values=peak.astype(float).tolist(),
            kurtosis_values=kurt.astype(float).tolist(),
            band_pool=bands.astype(float).tolist(),
            current_rms_values=crms.astype(float).tolist(),
            current_kurtosis_values=ckur.astype(float).tolist(),
            current_crest_values=ccrest.astype(float).tolist(),
        )
    return profiles


def global_bounds(profiles: dict[str, ClassProfile]) -> dict[str, tuple[float, float]]:
    return {
        "rms": (
            min(p.rms_q05 for p in profiles.values()),
            max(p.rms_q95 for p in profiles.values()),
        ),
        "current_rms": (
            min(p.current_rms_q05 for p in profiles.values()),
            max(p.current_rms_q95 for p in profiles.values()),
        ),
    }


def _impact_rate(cls: str, freqs: dict[str, float]) -> float:
    if cls == "OR":
        return float(freqs["BPFO"])
    if cls == "IR":
        return float(freqs["BPFI"])
    return 0.0


def random_recipe(cls: str, freqs: dict[str, float], profiles: dict[str, ClassProfile], slot: int) -> dict[str, Any]:
    rng = np.random.default_rng(stable_seed(f"random:{cls}:{slot}"))
    bounds = global_bounds(profiles)
    lo, hi = bounds["rms"]
    target_rms = float(np.exp(rng.uniform(np.log(max(lo, 1e-6)), np.log(max(hi, lo + 1e-6)))))
    cur_lo, cur_hi = bounds["current_rms"]
    current_rms = float(rng.uniform(cur_lo, cur_hi))
    n_components = int(rng.integers(0, 5))
    components = [
        {
            "freq_hz": float(rng.uniform(5.0, 500.0)),
            "amp": float(rng.uniform(0.02, 0.20) * target_rms),
        }
        for _ in range(n_components)
    ]
    if cls == "healthy":
        impact_amp = 0.0
        modulation = {"type": "none", "depth": 0.0}
    else:
        impact_amp = float(rng.uniform(2.0, 8.0) * target_rms)
        modulation = {
            "type": "shaft" if cls == "IR" else "none",
            "depth": float(rng.uniform(0.2, 1.0) if cls == "IR" else 0.0),
        }
    return {
        "fr_hz": float(freqs["fr"]),
        "target_rms": target_rms,
        "impacts": {
            "rate_hz": _impact_rate(cls, freqs),
            "amp": impact_amp,
            "decay_ms": float(np.exp(rng.uniform(np.log(0.5), np.log(6.0)))),
            "resonance_hz": float(rng.uniform(250.0, 3800.0)),
            "jitter_pct": float(rng.uniform(0.0, 5.0)),
            "amp_var_pct": float(rng.uniform(0.0, 45.0)),
            "modulation": modulation,
        },
        "background": {
            "noise_rms": float(rng.uniform(0.05, 0.40) * target_rms),
            "band_weights": rng.dirichlet(np.ones(len(BANDS))).tolist(),
            "components": components,
            "random_impulses": {
                "rate_hz": float(rng.uniform(0.0, 70.0)),
                "amp": float(rng.uniform(0.0, 4.0) * target_rms),
                "decay_ms": float(rng.uniform(0.5, 3.0)),
                "resonance_hz": float(rng.uniform(250.0, 3800.0)),
            },
        },
        "currents": {
            "fe_hz": 60.0,
            "rms": current_rms,
            "kurtosis": float(rng.uniform(1.49, 1.56)),
            "crest": float(rng.uniform(1.40, 1.62)),
            "thd": float(rng.uniform(0.0, 0.10)),
            "sideband_depth": float(rng.uniform(0.0, 0.20) if cls != "healthy" else 0.0),
            "fault_freq_hz": _impact_rate(cls, freqs),
            "noise_rms": float(rng.uniform(0.008, 0.030)),
        },
    }


def _rule_variation(slot: int, scale: float) -> float:
    return float(np.exp(scale * np.sin(0.61803398875 * (slot + 1))))


def rule_recipe(cls: str, freqs: dict[str, float], profiles: dict[str, ClassProfile], slot: int) -> dict[str, Any]:
    profile = profiles[cls]
    target_rms = profile.rms_q50 * _rule_variation(slot, 0.08)
    current_rms = profile.current_rms_q50 * _rule_variation(slot + 11, 0.03)
    resonance = 850.0 if cls == "OR" else 3200.0
    if cls == "healthy":
        impact_amp = 0.0
        modulation = {"type": "none", "depth": 0.0}
        random_impulse_amp = max(profile.peak_q50, 2.5 * target_rms) * 0.35
        sideband = 0.0
    else:
        impact_factor = float(np.clip(np.sqrt(max(profile.kurtosis_q50, 3.0)) * 2.2, 3.0, 8.0))
        impact_amp = impact_factor * target_rms
        modulation = {"type": "shaft" if cls == "IR" else "none", "depth": 0.65 if cls == "IR" else 0.0}
        random_impulse_amp = 0.25 * target_rms
        sideband = 0.04
    components = []
    for i, comp in enumerate(profile.components):
        components.append(
            {
                "freq_hz": float(comp["freq_hz"]),
                "amp": float(comp["amp"] * _rule_variation(slot + i, 0.05)),
            }
        )
    return {
        "fr_hz": float(freqs["fr"]),
        "target_rms": float(target_rms),
        "impacts": {
            "rate_hz": _impact_rate(cls, freqs),
            "amp": float(impact_amp),
            "decay_ms": 1.6 if cls == "IR" else 2.2,
            "resonance_hz": resonance,
            "jitter_pct": 2.0,
            "amp_var_pct": 18.0 if cls != "healthy" else 0.0,
            "modulation": modulation,
        },
        "background": {
            "noise_rms": float(0.12 * target_rms),
            "band_weights": profile.band_median,
            "components": components,
            "random_impulses": {
                "rate_hz": 45.0 if cls == "healthy" else 20.0,
                "amp": float(random_impulse_amp),
                "decay_ms": 1.4,
                "resonance_hz": 2600.0 if cls != "OR" else 900.0,
            },
        },
        "currents": {
            "fe_hz": 60.0,
            "rms": float(current_rms),
            "kurtosis": float(profile.current_kurtosis_q50),
            "crest": float(profile.current_crest_q50),
            "thd": 0.045,
            "sideband_depth": sideband,
            "fault_freq_hz": _impact_rate(cls, freqs),
            "noise_rms": 0.012,
        },
    }


def _sample(values: list[float], rng: np.random.Generator) -> float:
    return float(values[int(rng.integers(0, len(values)))])


def empirical_recipe(cls: str, freqs: dict[str, float], profiles: dict[str, ClassProfile], slot: int) -> dict[str, Any]:
    """Train-calibrated stochastic recipe baseline.

    The sampler draws target statistics from class-conditional real training
    windows and maps them once into renderer parameters. It does not inspect
    verifier outcomes or retry failed slots, so it remains a recipe-source
    baseline rather than a gate-search procedure.
    """
    rng = np.random.default_rng(stable_seed(f"empirical:{cls}:{slot}"))
    profile = profiles[cls]
    target_rms = max(_sample(profile.rms_values, rng), 1e-8)
    target_peak = max(_sample(profile.peak_values, rng), target_rms)
    target_kurtosis = max(_sample(profile.kurtosis_values, rng), 1.5)
    current_rms = max(_sample(profile.current_rms_values, rng), 1e-8)
    current_kurtosis = max(_sample(profile.current_kurtosis_values, rng), 1.45)
    current_crest = max(_sample(profile.current_crest_values, rng), 1.35)
    band_weights = np.asarray(profile.band_pool[int(rng.integers(0, len(profile.band_pool)))], dtype=float)
    band_weights = np.clip(band_weights, 1e-12, None)
    band_weights = (band_weights / band_weights.sum()).tolist()

    components = []
    if profile.components:
        n_components = int(rng.integers(1, min(len(profile.components), 5) + 1))
        chosen = rng.choice(len(profile.components), size=n_components, replace=False)
        scale = target_rms / max(profile.rms_q50, 1e-8)
        for idx in chosen:
            comp = profile.components[int(idx)]
            components.append(
                {
                    "freq_hz": float(comp["freq_hz"]),
                    "amp": float(comp["amp"] * scale),
                }
            )

    peak_ratio = float(np.clip(target_peak / target_rms, 1.5, 12.0))
    excess_kurtosis = float(max(target_kurtosis - 3.0, 0.0))
    random_impulse_amp = float(0.20 * peak_ratio * target_rms)
    if cls == "healthy":
        impact_amp = 0.0
        modulation = {"type": "none", "depth": 0.0}
        random_impulse_rate = 20.0 + 5.0 * excess_kurtosis
        sideband_depth = 0.0
    else:
        impact_amp = float(np.clip(0.55 * peak_ratio + 0.35 * np.sqrt(excess_kurtosis + 1.0), 2.0, 9.0) * target_rms)
        modulation = {
            "type": "shaft" if cls == "IR" else "none",
            "depth": float(np.clip(0.15 + 0.08 * np.sqrt(excess_kurtosis + 1.0), 0.15, 0.85)) if cls == "IR" else 0.0,
        }
        random_impulse_rate = 8.0 + 2.0 * excess_kurtosis
        sideband_depth = float(np.clip(0.015 * np.sqrt(excess_kurtosis + 1.0), 0.01, 0.08))

    band_idx = int(rng.choice(len(BANDS), p=np.asarray(band_weights) / np.sum(band_weights)))
    lo, hi = BANDS[band_idx]
    if hi <= 250:
        lo, hi = 250, 1500
    resonance_hz = float(rng.uniform(lo, min(hi, FS / 2 - 50)))

    return {
        "fr_hz": float(freqs["fr"]),
        "target_rms": float(target_rms),
        "impacts": {
            "rate_hz": _impact_rate(cls, freqs),
            "amp": impact_amp,
            "decay_ms": float(np.clip(1000.0 / max(resonance_hz, 1.0), 0.6, 4.0)),
            "resonance_hz": resonance_hz,
            "jitter_pct": float(np.clip(1.0 + 0.4 * np.sqrt(excess_kurtosis + 1.0), 1.0, 5.0)),
            "amp_var_pct": float(np.clip(8.0 + 3.0 * excess_kurtosis, 8.0, 35.0)),
            "modulation": modulation,
        },
        "background": {
            "noise_rms": float(0.10 * target_rms),
            "band_weights": band_weights,
            "components": components,
            "random_impulses": {
                "rate_hz": float(random_impulse_rate),
                "amp": random_impulse_amp,
                "decay_ms": float(np.clip(1000.0 / max(resonance_hz, 1.0), 0.6, 3.0)),
                "resonance_hz": resonance_hz,
            },
        },
        "currents": {
            "fe_hz": 60.0,
            "rms": float(current_rms),
            "kurtosis": float(current_kurtosis),
            "crest": float(current_crest),
            "thd": 0.045,
            "sideband_depth": sideband_depth,
            "fault_freq_hz": _impact_rate(cls, freqs),
            "noise_rms": 0.012,
        },
    }


def recipe_for(source: str, cls: str, freqs: dict[str, float], profiles: dict[str, ClassProfile], slot: int) -> dict[str, Any]:
    if source == "random":
        return random_recipe(cls, freqs, profiles, slot)
    if source == "rule":
        return rule_recipe(cls, freqs, profiles, slot)
    if source == "empirical":
        return empirical_recipe(cls, freqs, profiles, slot)
    raise ValueError(source)


def gate_pass(report: dict[str, Any]) -> dict[str, bool]:
    return {name: bool(entry["passed"]) for name, entry in report.get("gates", {}).items()}


def violations(report: dict[str, Any]) -> list[str]:
    out = []
    for entry in report.get("gates", {}).values():
        out.extend(entry.get("messages", []))
    return out


def run_slot(
    source: str,
    cls: str,
    slot: int,
    out_dir: Path,
    verifier: BreezeVerifierV2,
    freqs: dict[str, float],
    profiles: dict[str, ClassProfile],
) -> tuple[str, int, bool] | None:
    rec_path = out_dir / f"{cls}_{slot:04d}.json"
    if rec_path.exists():
        return None
    recipe = recipe_for(source, cls, freqs, profiles, slot)
    seed = stable_seed(f"{source}:{cls}:{slot}:0")
    try:
        w = render(recipe, seed)
        report = verifier.verify(w, cls)
    except Exception as exc:
        record = {
            "source": source,
            "class": cls,
            "slot": slot,
            "accepted": False,
            "history": [{"round": 0, "recipe": recipe, "error": str(exc)}],
        }
        rec_path.write_text(json.dumps(tolist(record), separators=(",", ":")))
        return cls, slot, False
    np.save(out_dir / f"{cls}_{slot:04d}_r0.npy", w)
    accepted = bool(report["feasible"])
    record = {
        "source": source,
        "class": cls,
        "slot": slot,
        "accepted": accepted,
        "rounds_used": 1,
        "history": [
            {
                "round": 0,
                "recipe": recipe,
                "feasible": accepted,
                "gate_pass": gate_pass(report),
                "violations": violations(report),
                "scores": report.get("scores", {}),
            }
        ],
    }
    if accepted:
        np.save(out_dir / f"{cls}_{slot:04d}.npy", w)
        expansion_count = 0
        for sub in range(1, 13):
            if expansion_count >= 4:
                break
            wx = render(recipe, stable_seed(f"{source}:{cls}:{slot}:x:{sub}"))
            rpx = verifier.verify(wx, cls)
            if rpx["feasible"]:
                np.save(out_dir / f"{cls}_{slot:04d}_x{expansion_count}.npy", wx)
                expansion_count += 1
        record["n_feasible_expansions"] = expansion_count
    rec_path.write_text(json.dumps(tolist(record), separators=(",", ":")))
    return cls, slot, accepted


def _feature_embedding(w: np.ndarray) -> np.ndarray:
    vals = []
    for ch in range(3):
        st = time_stats(w[ch])
        vals.extend(st[k] for k in ("rms", "kurtosis", "crest"))
    return np.asarray(vals, dtype=float)


def diversity_mask(X: np.ndarray, y: np.ndarray, Xr: np.ndarray, yr: np.ndarray, pctl: float = 1.0, seed: int = 0) -> np.ndarray:
    keep = np.zeros(len(X), dtype=bool)
    rng = np.random.default_rng(seed)
    for ci in np.unique(y):
        si = np.where(y == ci)[0]
        ri = np.where(yr == ci)[0]
        ri = rng.choice(ri, min(200, len(ri)), replace=False)
        Fr = np.asarray([_feature_embedding(w) for w in Xr[ri]])
        mu, sd = Fr.mean(axis=0), Fr.std(axis=0) + 1e-9
        Zr = (Fr - mu) / sd
        Dr = np.sqrt(((Zr[:, None] - Zr[None]) ** 2).sum(axis=-1))
        np.fill_diagonal(Dr, np.inf)
        threshold = float(np.percentile(Dr.min(axis=1), pctl))
        Zs = (np.asarray([_feature_embedding(w) for w in X[si]]) - mu) / sd
        taken: list[int] = []
        for local_idx, z in enumerate(Zs):
            if not taken:
                taken.append(local_idx)
                continue
            nearest = min(float(np.sqrt(((z - Zs[t]) ** 2).sum())) for t in taken)
            if nearest >= threshold:
                taken.append(local_idx)
        keep[si[taken]] = True
    return keep


def build_pool(source: str, out_dir: Path, Xtr: np.ndarray, ytr: np.ndarray) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    Xs, ys, manifest = [], [], []
    slot_rows = []
    for rec_path in sorted(out_dir.glob("*.json")):
        rec = read_json(rec_path)
        if "class" not in rec or "slot" not in rec:
            continue
        cls = rec["class"]
        ci = CLASSES.index(cls)
        slot = int(rec["slot"])
        selected = out_dir / f"{cls}_{slot:04d}.npy"
        accepted = bool(rec.get("accepted")) and selected.exists()
        n_exp = 0
        if accepted:
            Xs.append(np.load(selected))
            ys.append(ci)
            manifest.append({"source": source, "class": cls, "slot": slot, "kind": "selected", "path": str(selected)})
            for exp_path in sorted(out_dir.glob(f"{cls}_{slot:04d}_x*.npy")):
                Xs.append(np.load(exp_path))
                ys.append(ci)
                n_exp += 1
                manifest.append({"source": source, "class": cls, "slot": slot, "kind": "expansion", "path": str(exp_path)})
        slot_rows.append(
            {
                "source": source,
                "class": cls,
                "slot": slot,
                "accepted_slot": accepted,
                "n_candidates": len(rec.get("history", [])),
                "n_feasible_expansions": n_exp,
            }
        )
    if Xs:
        X = np.stack(Xs).astype(np.float32)
        y = np.asarray(ys, dtype=np.int64)
        keep = diversity_mask(X, y, Xtr, ytr)
        X_keep, y_keep = X[keep], y[keep]
    else:
        X = np.zeros((0, 3, 2048), dtype=np.float32)
        y = np.zeros((0,), dtype=np.int64)
        keep = np.zeros((0,), dtype=bool)
        X_keep, y_keep = X, y
    for row, kept in zip(manifest, keep.tolist()):
        row["kept_after_diversity"] = bool(kept)
    np.savez_compressed(out_dir / "pool_v2.npz", X=X_keep, y=y_keep)
    with (out_dir / "accepted_manifest.csv").open("w", newline="") as fh:
        fieldnames = ["source", "class", "slot", "kind", "path", "kept_after_diversity"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest)
    with (out_dir / "slot_summary.csv").open("w", newline="") as fh:
        fieldnames = ["source", "class", "slot", "accepted_slot", "n_candidates", "n_feasible_expansions"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(slot_rows)
    summary = summarize_source(source, slot_rows, manifest, y_keep)
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2))
    return summary, manifest


def summarize_source(
    source: str,
    slot_rows: list[dict[str, Any]],
    manifest: list[dict[str, Any]],
    y_keep: np.ndarray,
) -> dict[str, Any]:
    total_slots = len(slot_rows)
    accepted_slots = sum(1 for r in slot_rows if r["accepted_slot"])
    kept_counts = {CLASSES[i]: int((y_keep == i).sum()) for i in range(len(CLASSES))}
    by_class = {}
    for cls in CLASSES:
        rows = [r for r in slot_rows if r["class"] == cls]
        items = [m for m in manifest if m["class"] == cls]
        kept = [m for m in items if m.get("kept_after_diversity")]
        by_class[cls] = {
            "slots": len(rows),
            "accepted_slots": sum(1 for r in rows if r["accepted_slot"]),
            "accepted_items_before_diversity": len(items),
            "kept_after_diversity": len(kept),
            "acceptance": (sum(1 for r in rows if r["accepted_slot"]) / len(rows)) if rows else 0.0,
        }
    return {
        "source": source,
        "slots": total_slots,
        "accepted_slots": accepted_slots,
        "acceptance": accepted_slots / total_slots if total_slots else 0.0,
        "accepted_items_before_diversity": len(manifest),
        "kept_after_diversity": int(len(y_keep)),
        "kept_counts": kept_counts,
        "by_class": by_class,
    }


def fail_reason_rows(source: str, out_dir: Path) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    totals: Counter[str] = Counter()
    for rec_path in sorted(out_dir.glob("*.json")):
        rec = read_json(rec_path)
        if "class" not in rec or "slot" not in rec:
            continue
        cls = rec["class"]
        totals[cls] += 1
        hist = rec.get("history", [])
        if not hist:
            counts[(cls, "missing_history")] += 1
            continue
        if rec.get("accepted"):
            continue
        gp = hist[-1].get("gate_pass", {})
        failed = [gate for gate, ok in gp.items() if ok is False]
        if not failed:
            failed = ["unknown_or_runtime_error"]
        for gate in failed:
            counts[(cls, gate)] += 1
    rows = []
    for (cls, gate), count in sorted(counts.items()):
        rows.append(
            {
                "source": source,
                "class": cls,
                "gate": gate,
                "count": count,
                "slots": totals[cls],
                "rate_per_slot": count / totals[cls] if totals[cls] else 0.0,
            }
        )
    return rows


def write_overall_outputs(summaries: list[dict[str, Any]], fail_rows: list[dict[str, Any]], tag: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary_path = RESULTS / f"recipe_ablation_summary_{tag}.csv"
    fail_path = RESULTS / f"recipe_ablation_fail_reasons_{tag}.csv"
    flat = []
    for s in summaries:
        flat.append(
            {
                "source": s["source"],
                "class": "all",
                "slots": s["slots"],
                "accepted_slots": s["accepted_slots"],
                "acceptance": s["acceptance"],
                "accepted_items_before_diversity": s["accepted_items_before_diversity"],
                "kept_after_diversity": s["kept_after_diversity"],
                "kept_healthy": s["kept_counts"].get("healthy", 0),
                "kept_OR": s["kept_counts"].get("OR", 0),
                "kept_IR": s["kept_counts"].get("IR", 0),
            }
        )
        for cls, row in s["by_class"].items():
            flat.append(
                {
                    "source": s["source"],
                    "class": cls,
                    "slots": row["slots"],
                    "accepted_slots": row["accepted_slots"],
                    "acceptance": row["acceptance"],
                    "accepted_items_before_diversity": row["accepted_items_before_diversity"],
                    "kept_after_diversity": row["kept_after_diversity"],
                    "kept_healthy": "",
                    "kept_OR": "",
                    "kept_IR": "",
                }
            )
    with summary_path.open("w", newline="") as fh:
        fieldnames = list(flat[0].keys()) if flat else [
            "source",
            "class",
            "slots",
            "accepted_slots",
            "acceptance",
            "accepted_items_before_diversity",
            "kept_after_diversity",
            "kept_healthy",
            "kept_OR",
            "kept_IR",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat)
    with fail_path.open("w", newline="") as fh:
        fieldnames = ["source", "class", "gate", "count", "slots", "rate_per_slot"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(fail_rows)
    report_path = REPORTS / f"recipe_ablation_report_{tag}.md"
    lines = [
        "# Recipe-Source Ablation",
        "",
        f"Tag: `{tag}`",
        "",
        f"Summary CSV: `{summary_path.relative_to(ROOT)}`",
        f"Fail-reason CSV: `{fail_path.relative_to(ROOT)}`",
        "",
        "## Summary",
        "",
        "| source | class | slots | accepted slots | acceptance | items before diversity | kept after diversity |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in flat:
        lines.append(
            "| {source} | {class} | {slots} | {accepted_slots} | {acceptance:.4f} | {accepted_items_before_diversity} | {kept_after_diversity} |".format(
                **{
                    **row,
                    "acceptance": float(row["acceptance"]),
                }
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation Guardrail",
            "",
            "This ablation compares recipe sources under the same deterministic renderer and v2 verifier. It does not create new LLM calls. A downstream or acceptance advantage of LLM recipes over these non-LLM recipes is required before the manuscript can claim that LLM-guided generation is independently reliable.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n")
    print(f"wrote {summary_path}")
    print(f"wrote {fail_path}")
    print(f"wrote {report_path}")


def load_or_calibrate_v2(cond: str) -> BreezeVerifierV2:
    vpath = RUNS / f"verifier_v2_{cond}_c90_soft_w1.json"
    if vpath.exists():
        return BreezeVerifierV2.load(vpath)
    Xtr, ytr, btr = load_file_split("train", cond)
    verifier = BreezeVerifierV2(coverage=0.90, profile="soft_w1")
    verifier.calibrate(Xtr.astype(np.float32), ytr, cond, bearings=btr)
    verifier.save(vpath)
    return verifier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        choices=["random", "rule", "empirical", "both", "all"],
        default="both",
    )
    parser.add_argument("--cond", default=MAIN_COND)
    parser.add_argument("--n", type=int, default=150)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--tag",
        default=None,
        help="Explicit output suffix; use a new tag for every protocol version.",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        choices=CLASSES,
        default=list(CLASSES),
        help="Class subset to generate. Useful for checkpointed class-only extensions.",
    )
    args = parser.parse_args()

    n_slots = 5 if args.smoke else args.n
    tag = args.tag or ("smoke" if args.smoke else "full")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", tag) is None:
        raise ValueError(f"unsafe tag: {tag!r}")
    if args.source == "both":
        sources = ["random", "rule"]
    elif args.source == "all":
        sources = ["random", "rule", "empirical"]
    else:
        sources = [args.source]
    Xtr, ytr, _ = load_file_split("train", args.cond)
    Xtr = Xtr.astype(np.float32)
    profiles = build_profiles(Xtr, ytr)
    verifier = load_or_calibrate_v2(args.cond)
    freqs = fault_freqs(CONDITIONS[args.cond][0] / 60.0)

    summaries: list[dict[str, Any]] = []
    all_fail_rows: list[dict[str, Any]] = []
    for source in sources:
        out_dir = RUNS / f"recipe_ablation_{source}_v2_{tag}"
        out_dir.mkdir(parents=True, exist_ok=True)
        tasks = [
            (source, cls, slot, out_dir, verifier, freqs, profiles)
            for cls in args.classes
            for slot in range(n_slots)
            if not (out_dir / f"{cls}_{slot:04d}.json").exists()
        ]
        print(f"{source}: {len(tasks)} slots to run ({n_slots}/class, tag={tag})", flush=True)
        completed = accepted = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_slot, *task) for task in tasks]
            for fut in as_completed(futures):
                result = fut.result()
                if result is None:
                    continue
                completed += 1
                accepted += int(result[2])
                if completed % 10 == 0 or completed == len(tasks):
                    print(f"{source}: {completed}/{len(tasks)} new slots, acceptance={accepted/max(completed,1):.3f}", flush=True)
        summary, _ = build_pool(source, out_dir, Xtr, ytr)
        summaries.append(summary)
        all_fail_rows.extend(fail_reason_rows(source, out_dir))
        print(f"{source}: pool {out_dir / 'pool_v2.npz'} kept={summary['kept_after_diversity']}", flush=True)
    write_overall_outputs(summaries, all_fail_rows, tag)


if __name__ == "__main__":
    main()
