"""BREEZE-v2 offline verifier components.

The v2 verifier keeps the original training-free boundary/sanity gates, but
replaces the high-risk rigid spectral and single-band checks with
train-supported signal-processing constraints:

- overlapping triangular spectral bands;
- PSD CDF Wasserstein distance to the class train distribution;
- robust multi-band resonance/envelope evidence;
- two-current vector-current MCSA with train-only reliability calibration;
- expanded physical embeddings for diversity admission.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from config import CLASSES, CONDITIONS, FS, WIN, fault_freqs
from verifier.features import (
    band_energy_ratio,
    envelope_fault_score,
    psd,
    spectral_kurtosis,
    time_stats,
)
from verifier.verifier import BreezeVerifier, SPEC_BANDS, STAT_KEYS


CH_NAMES = ["X", "Y", "Z"]
PROFILE_GATES = {
    "soft_w1": {
        "soft_spectrum": True,
        "psd_w1": True,
        "envelope_multi": True,
        "vector_mcsa": True,
    },
    "soft_only": {
        "soft_spectrum": True,
        "psd_w1": False,
        "envelope_multi": True,
        "vector_mcsa": True,
    },
    "w1_only": {
        "soft_spectrum": False,
        "psd_w1": True,
        "envelope_multi": True,
        "vector_mcsa": True,
    },
}


def _tolist(x: Any) -> Any:
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, dict):
        return {k: _tolist(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_tolist(v) for v in x]
    return x


def _joint_alpha(values: np.ndarray, target: float) -> float:
    """Per-coordinate tail alpha whose joint interval coverage is near target."""
    best_alpha, best_gap = 0.01, np.inf
    for alpha in np.linspace(0.001, 0.10, 40):
        lo = np.quantile(values, alpha / 2, axis=0)
        hi = np.quantile(values, 1 - alpha / 2, axis=0)
        rate = np.mean(np.all((values >= lo) & (values <= hi), axis=1))
        gap = abs(rate - target)
        if gap < best_gap:
            best_alpha, best_gap = float(alpha), float(gap)
    return best_alpha


def _union_interval(values: np.ndarray, bearings: np.ndarray | None, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    if bearings is None:
        return (
            np.quantile(values, alpha / 2, axis=0),
            np.quantile(values, 1 - alpha / 2, axis=0),
        )
    lows, highs = [], []
    for bearing in np.unique(bearings):
        vb = values[bearings == bearing]
        lows.append(np.quantile(vb, alpha / 2, axis=0))
        highs.append(np.quantile(vb, 1 - alpha / 2, axis=0))
    return np.min(lows, axis=0), np.max(highs, axis=0)


def _per_bearing_quantile(values: np.ndarray, bearings: np.ndarray | None, q: float, mode: str) -> float:
    if bearings is None:
        return float(np.quantile(values, q))
    qs = [np.quantile(values[bearings == b], q) for b in np.unique(bearings)]
    if mode == "min":
        return float(np.min(qs))
    if mode == "max":
        return float(np.max(qs))
    raise ValueError(mode)


def soft_band_fracs(x: np.ndarray, fs: int = FS) -> np.ndarray:
    """Overlapping triangular spectral-band energy fractions.

    Centers are inherited from the original verifier's band midpoints, but
    neighboring triangles overlap continuously so small peak shifts near hard
    boundaries cause small coordinate changes rather than discontinuities.
    """
    f, p = psd(x, fs)
    centers = np.array([(a + b) / 2 for a, b in SPEC_BANDS], dtype=float)
    weights = []
    for i, c in enumerate(centers):
        left = 0.0 if i == 0 else centers[i - 1]
        right = fs / 2 if i == len(centers) - 1 else centers[i + 1]
        w = np.zeros_like(f)
        ml = (f >= left) & (f <= c)
        mr = (f > c) & (f <= right)
        w[ml] = (f[ml] - left) / max(c - left, 1e-12)
        w[mr] = (right - f[mr]) / max(right - c, 1e-12)
        weights.append(np.clip(w, 0.0, 1.0))
    e = np.array([np.trapezoid(p * w, f) for w in weights])
    return e / (e.sum() + 1e-30)


def psd_cdf(x: np.ndarray, fs: int = FS) -> tuple[np.ndarray, np.ndarray]:
    f, p = psd(x, fs)
    p = np.maximum(p, 0)
    if p.sum() <= 0:
        return f, np.zeros_like(f)
    df = np.gradient(f)
    mass = p * df
    mass = mass / (mass.sum() + 1e-30)
    cdf = np.cumsum(mass)
    cdf = cdf / (cdf[-1] + 1e-30)
    return f, cdf


def psd_w1_from_ref(x: np.ndarray, ref_cdf: np.ndarray, fs: int = FS) -> float:
    f, cdf = psd_cdf(x, fs)
    return float(np.trapezoid(np.abs(cdf - ref_cdf), f))


def candidate_resonance_bands(fs: int = FS, width: float = 1000.0, step: float = 400.0) -> list[tuple[float, float]]:
    bands = []
    lo = 200.0
    while lo + width <= fs / 2:
        bands.append((float(lo), float(lo + width)))
        lo += step
    return bands


def _robust_z(values: np.ndarray) -> np.ndarray:
    med = np.median(values)
    mad = np.median(np.abs(values - med)) + 1e-12
    return (values - med) / (1.4826 * mad)


def _band_sk_value(x: np.ndarray, band: tuple[float, float], fs: int = FS) -> float:
    f, sk = spectral_kurtosis(x, fs)
    m = (f >= band[0]) & (f <= band[1])
    return float(np.median(sk[m])) if np.any(m) else 0.0


def vector_current_mcsa(i1: np.ndarray, i2: np.ndarray, freqs_hz: dict, fault: str, fs: int = FS) -> dict[str, float]:
    """Two-current MCSA score using a Clarke-like vector current spectrum."""
    n = len(i1)
    i3 = -(i1 + i2)
    i_alpha = i1
    i_beta = (i1 + 2 * i2) / np.sqrt(3.0)
    win = np.hanning(n)
    spec_a = np.abs(np.fft.rfft((i_alpha - np.mean(i_alpha)) * win)) / n
    spec_b = np.abs(np.fft.rfft((i_beta - np.mean(i_beta)) * win)) / n
    spec_3 = np.abs(np.fft.rfft((i3 - np.mean(i3)) * win)) / n
    spec = np.sqrt(spec_a**2 + spec_b**2 + 0.25 * spec_3**2)
    f = np.fft.rfftfreq(n, 1 / fs)
    carrier_mask = (f > 5) & (f < 500)
    fe = float(f[carrier_mask][np.argmax(spec[carrier_mask])])
    f_fault = freqs_hz["BPFO"] if fault == "OR" else freqs_hz["BPFI"]
    df = f[1] - f[0]
    tol = max(2 * df, 0.02 * f_fault)

    def local_peak(target: float) -> tuple[float, float]:
        m = (f >= target - tol) & (f <= target + tol)
        if not np.any(m):
            return 0.0, np.nan
        idx = np.argmax(spec[m])
        amp = float(spec[m][idx])
        peak_f = float(f[m][idx])
        nb = (f >= max(2.0, target - 10 * tol)) & (f <= target + 10 * tol)
        floor = float(np.median(spec[nb])) + 1e-30
        return amp / floor, peak_f

    left, lf = local_peak(fe - f_fault)
    right, rf = local_peak(fe + f_fault)
    carrier = float(spec[np.argmin(np.abs(f - fe))]) + 1e-30
    side_amp = 0.5 * (
        float(spec[np.argmin(np.abs(f - (fe - f_fault)))])
        + float(spec[np.argmin(np.abs(f - (fe + f_fault)))])
    )
    return {
        "fe": fe,
        "sideband_prominence": float((left + right) / 2),
        "left_peak_freq": lf,
        "right_peak_freq": rf,
        "sideband_to_carrier_db": float(20 * np.log10((side_amp + 1e-30) / carrier)),
    }


def physical_embedding(w: np.ndarray, cls: str, calib: dict) -> np.ndarray:
    vals = []
    for ch in range(3):
        st = time_stats(w[ch])
        vals.extend(st[k] for k in ("rms", "peak", "std", "kurtosis", "skewness", "crest"))
    vals.extend(soft_band_fracs(w[0]).tolist())
    cls_cal = calib["classes"][cls]
    vals.append(psd_w1_from_ref(w[0], np.array(cls_cal["psd_w1"]["ref_cdf"])))
    if cls in ("OR", "IR"):
        env_vals = []
        for band_rec in cls_cal["resonance"]["bands"]:
            band = tuple(band_rec["band"])
            env_vals.append(envelope_fault_score(w[0], FS, band, calib["freqs"], cls)["fund_prominence"])
            env_vals.append(band_energy_ratio(w[0], FS, band))
        vals.extend(env_vals)
        mc = vector_current_mcsa(w[1], w[2], calib["freqs"], cls)
        vals.extend([mc["sideband_prominence"], mc["sideband_to_carrier_db"]])
    else:
        vals.extend([0.0, 0.0])
    return np.asarray(vals, dtype=float)


def stat_vector(w: np.ndarray) -> np.ndarray:
    return np.asarray(
        [time_stats(w[j])[k] for j in range(3) for k in STAT_KEYS],
        dtype=float,
    )


@dataclass
class BreezeVerifierV2:
    coverage: float = 0.90
    profile: str = "soft_w1"
    regime: str = "in_domain"

    def __post_init__(self):
        if self.profile not in PROFILE_GATES:
            raise ValueError(f"unknown v2 profile {self.profile}")
        if self.regime not in ("in_domain", "extrapolation"):
            raise ValueError(f"unknown v2 regime {self.regime}")
        self.gates = PROFILE_GATES[self.profile].copy()
        self.calib: dict[str, Any] = {}
        self.boundary: BreezeVerifier | None = None

    def calibrate(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cond: str,
        bearings: np.ndarray | None = None,
        *,
        source_conditions: list[str] | None = None,
        target_condition: str | None = None,
        condition_labels: np.ndarray | None = None,
    ):
        if self.regime == "extrapolation":
            from verifier.extrapolation import calibrate_extrapolation

            self.calib, self.boundary = calibrate_extrapolation(
                X_train=X_train,
                y_train=y_train,
                bearings=bearings,
                coverage=self.coverage,
                profile=self.profile,
                source_conditions=source_conditions,
                target_condition=target_condition,
                condition_labels=condition_labels,
                vector_current_fn=vector_current_mcsa,
                soft_band_fn=soft_band_fracs,
                psd_cdf_fn=psd_cdf,
                psd_w1_fn=psd_w1_from_ref,
                stat_vector_fn=stat_vector,
            )
            return
        rpm = CONDITIONS[cond][0]
        freqs = fault_freqs(rpm / 60.0)
        boundary = BreezeVerifier(
            coverage=self.coverage,
            gates={"boundary": False, "energy": False, "envelope": False, "mcsa": False, "spectrum": False},
        )
        boundary.calibrate(X_train, y_train, cond, bearings=bearings)
        self.boundary = boundary
        self.calib = {
            "coverage": self.coverage,
            "profile": self.profile,
            "regime": "in_domain",
            "gates": self.gates,
            "cond": cond,
            "freqs": freqs,
            "classes": {},
            "boundary": {
                "coverage": boundary.coverage,
                "gates": boundary.gates,
                "cond": boundary.cond,
                "freqs": boundary.freqs,
                "calib": boundary.calib,
            },
        }
        for ci, cls in enumerate(CLASSES):
            idx = y_train == ci
            Wc = X_train[idx]
            bc = bearings[idx] if bearings is not None else None
            entry: dict[str, Any] = {}

            stats = np.array([stat_vector(w) for w in Wc])
            med = np.median(stats, axis=0)
            q25 = np.quantile(stats, 0.25, axis=0)
            q75 = np.quantile(stats, 0.75, axis=0)
            scale = (q75 - q25) / 1.349
            scale = np.where(scale > 1e-12, scale, np.std(stats, axis=0) + 1e-9)
            z_stats = (stats - med) / scale
            axis_dist = np.sqrt((z_stats**2).sum(axis=1))
            cov = np.cov(z_stats, rowvar=False)
            eps = 1e-8 * max(float(np.trace(cov)) / max(cov.shape[0], 1), 1.0)
            inv_cov = np.linalg.pinv(cov + eps * np.eye(cov.shape[0]))
            maha_dist = np.sqrt(np.einsum("ij,jk,ik->i", z_stats, inv_cov, z_stats))
            entry["stats_ellipsoid"] = {
                "median": med,
                "scale": scale,
                "inv_cov": inv_cov,
                "axis_threshold": _per_bearing_quantile(axis_dist, bc, self.coverage, "max"),
                "maha_threshold": _per_bearing_quantile(maha_dist, bc, self.coverage, "max"),
                "feature_names": [f"{ch}_{k}" for ch in CH_NAMES for k in STAT_KEYS],
                "hard_domains": ["legacy_quantile", "axis_ellipsoid"],
            }

            soft = np.array([soft_band_fracs(w[0]) for w in Wc])
            alpha = _joint_alpha(soft, self.coverage)
            lo, hi = _union_interval(soft, bc, alpha)
            entry["soft_spectrum"] = {"alpha": alpha, "lo": lo, "hi": hi}

            cdfs = np.array([psd_cdf(w[0])[1] for w in Wc])
            ref = np.median(cdfs, axis=0)
            dists = np.array([float(np.trapezoid(np.abs(c - ref), psd(Wc[0][0], FS)[0])) for c in cdfs])
            entry["psd_w1"] = {
                "ref_cdf": ref,
                "threshold": _per_bearing_quantile(dists, bc, self.coverage, "max"),
            }

            if cls in ("OR", "IR"):
                entry["resonance"] = self._calibrate_fault_resonance(Wc, bc, cls, freqs)
                entry["mcsa"] = self._calibrate_mcsa(X_train, y_train, bearings, cls, freqs)
            else:
                entry["resonance"] = self._calibrate_healthy_resonance(X_train, y_train, bearings, freqs)
                entry["mcsa"] = {"hard_gate": False, "reason": "healthy has no fault-current sideband requirement"}
            self.calib["classes"][cls] = entry

    def _calibrate_fault_resonance(self, Wc: np.ndarray, bc: np.ndarray | None, cls: str, freqs: dict) -> dict[str, Any]:
        bands = candidate_resonance_bands()
        rows = []
        for band in bands:
            proms = np.array([
                envelope_fault_score(w[0], FS, band, freqs, cls)["fund_prominence"]
                for w in Wc
            ])
            sks = np.array([_band_sk_value(w[0], band) for w in Wc])
            rows.append({
                "band": band,
                "median_log_prom": float(np.median(np.log1p(proms))),
                "median_sk": float(np.median(sks)),
                "proms": proms,
                "sks": sks,
            })
        prom_z = _robust_z(np.array([r["median_log_prom"] for r in rows]))
        sk_z = _robust_z(np.array([r["median_sk"] for r in rows]))
        order = np.argsort(-(prom_z + sk_z))[:3]
        selected = []
        for pos in order:
            row = rows[int(pos)]
            band = row["band"]
            proms = row["proms"]
            energies = np.array([band_energy_ratio(w[0], FS, band) for w in Wc])
            lo_e = _per_bearing_quantile(energies, bc, (1 - self.coverage) / 2, "min")
            hi_e = _per_bearing_quantile(energies, bc, 1 - (1 - self.coverage) / 2, "max")
            selected.append({
                "band": band,
                "score": float(prom_z[int(pos)] + sk_z[int(pos)]),
                "median_log_prom": row["median_log_prom"],
                "median_sk": row["median_sk"],
                "prom_min": _per_bearing_quantile(proms, bc, 1 - self.coverage, "min"),
                "energy_lo": lo_e,
                "energy_hi": hi_e,
            })
        return {"bands": selected}

    def _calibrate_healthy_resonance(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        bearings: np.ndarray | None,
        freqs: dict,
    ) -> dict[str, Any]:
        healthy = X_train[y_train == CLASSES.index("healthy")]
        bc = bearings[y_train == CLASSES.index("healthy")] if bearings is not None else None
        selected = []
        for fault in ("OR", "IR"):
            fault_idx = y_train == CLASSES.index(fault)
            fault_bearings = bearings[fault_idx] if bearings is not None else None
            fault_bands = self._calibrate_fault_resonance(X_train[fault_idx], fault_bearings, fault, freqs)["bands"]
            for rec in fault_bands:
                band = tuple(rec["band"])
                proms = np.array([
                    envelope_fault_score(w[0], FS, band, freqs, fault)["fund_prominence"]
                    for w in healthy
                ])
                selected.append({
                    "fault": fault,
                    "band": band,
                    "prom_max": _per_bearing_quantile(proms, bc, self.coverage, "max"),
                })
        return {"healthy_forbidden_fault_bands": selected}

    def _calibrate_mcsa(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        bearings: np.ndarray | None,
        cls: str,
        freqs: dict,
    ) -> dict[str, Any]:
        fault_idx = y_train == CLASSES.index(cls)
        healthy_idx = y_train == CLASSES.index("healthy")
        Wf, Wh = X_train[fault_idx], X_train[healthy_idx]
        bf = bearings[fault_idx] if bearings is not None else None
        bh = bearings[healthy_idx] if bearings is not None else None
        sf = np.array([vector_current_mcsa(w[1], w[2], freqs, cls)["sideband_prominence"] for w in Wf])
        sh = np.array([vector_current_mcsa(w[1], w[2], freqs, cls)["sideband_prominence"] for w in Wh])
        fault_min = _per_bearing_quantile(sf, bf, 1 - self.coverage, "min")
        healthy_max = _per_bearing_quantile(sh, bh, self.coverage, "max")
        return {
            "hard_gate": bool(fault_min > healthy_max),
            "fault_min": fault_min,
            "healthy_max": healthy_max,
            "fault_median": float(np.median(sf)),
            "healthy_median": float(np.median(sh)),
        }

    def verify(self, w: np.ndarray, cls: str, *, observed_condition: str | None = None) -> dict[str, Any]:
        if self.boundary is None:
            self._restore_boundary()
        assert self.boundary is not None
        if self.regime == "extrapolation":
            from verifier.extrapolation import verify_extrapolation

            return _tolist(verify_extrapolation(
                calib=self.calib,
                boundary=self.boundary,
                w=w,
                cls=cls,
                observed_condition=observed_condition,
                vector_current_fn=vector_current_mcsa,
                soft_band_fn=soft_band_fracs,
                psd_w1_fn=psd_w1_from_ref,
                stat_vector_fn=stat_vector,
            ))
        base = self.boundary.verify(w, cls)
        report = {
            "class": cls,
            "profile": self.profile,
            "feasible": bool(base["gates"]["sanity"]["passed"]),
            "gates": {
                "sanity": base["gates"]["sanity"],
            },
            "scores": {},
        }

        cal = self.calib["classes"][cls]

        st_cal = cal["stats_ellipsoid"]
        z = (stat_vector(w) - np.array(st_cal["median"])) / np.array(st_cal["scale"])
        inv_cov = np.array(st_cal["inv_cov"])
        axis_dist = float(np.sqrt((z**2).sum()))
        maha_dist = float(np.sqrt(z @ inv_cov @ z))
        legacy = self._legacy_stats_check(w, cls)
        axis_passed = axis_dist <= float(st_cal["axis_threshold"])
        maha_passed = maha_dist <= float(st_cal["maha_threshold"])
        st_passed = legacy["passed"] or axis_passed
        report["gates"]["stats_union"] = {
            "passed": st_passed,
            "messages": [] if st_passed else [
                "candidate is outside both train-supported statistical domains: "
                f"legacy_quantile={legacy['passed']}, "
                f"axis_dist={axis_dist:.3f}>{float(st_cal['axis_threshold']):.3f}"
            ],
        }
        if not st_passed:
            names = st_cal["feature_names"]
            order = np.argsort(-np.abs(z))[:5]
            report["gates"]["stats_union"]["messages"].append(
                "largest robust deviations: "
                + ", ".join(f"{names[i]}={z[i]:.2f} IQR-sigma" for i in order)
            )
            report["gates"]["stats_union"]["messages"].extend(legacy["messages"][:4])
        report["scores"]["stats_union"] = {
            "legacy_quantile_passed": legacy["passed"],
            "axis_distance": axis_dist,
            "axis_threshold": float(st_cal["axis_threshold"]),
            "mahalanobis_distance": maha_dist,
            "mahalanobis_threshold": float(st_cal["maha_threshold"]),
            "mahalanobis_passed": maha_passed,
        }
        report["feasible"] = report["feasible"] and st_passed

        if self.gates["soft_spectrum"]:
            vals = soft_band_fracs(w[0])
            lo = np.array(cal["soft_spectrum"]["lo"])
            hi = np.array(cal["soft_spectrum"]["hi"])
            bad = np.where((vals < lo) | (vals > hi))[0]
            report["gates"]["soft_spectrum"] = {"passed": len(bad) == 0, "messages": []}
            for i in bad:
                report["gates"]["soft_spectrum"]["messages"].append(
                    f"soft spectral coordinate {i}={vals[i]:.4f} outside [{lo[i]:.4f},{hi[i]:.4f}]"
                )
            report["scores"]["soft_spectrum"] = vals
            report["feasible"] = report["feasible"] and len(bad) == 0

        if self.gates["psd_w1"]:
            dist = psd_w1_from_ref(w[0], np.array(cal["psd_w1"]["ref_cdf"]))
            thr = float(cal["psd_w1"]["threshold"])
            passed = dist <= thr
            report["gates"]["psd_w1"] = {
                "passed": passed,
                "messages": [] if passed else [f"PSD W1 distance {dist:.4f} exceeds train-supported threshold {thr:.4f}"],
            }
            report["scores"]["psd_w1"] = dist
            report["feasible"] = report["feasible"] and passed

        if self.gates["envelope_multi"]:
            env_gate = self._verify_envelope(w, cls, cal)
            report["gates"]["envelope_multi"] = env_gate["gate"]
            report["scores"]["envelope_multi"] = env_gate["scores"]
            report["feasible"] = report["feasible"] and env_gate["gate"]["passed"]

        if self.gates["vector_mcsa"] and cls in ("OR", "IR"):
            mc = vector_current_mcsa(w[1], w[2], self.calib["freqs"], cls)
            mc_cal = cal["mcsa"]
            if mc_cal["hard_gate"]:
                passed = mc["sideband_prominence"] >= mc_cal["fault_min"]
                messages = [] if passed else [
                    f"vector-current sideband prominence {mc['sideband_prominence']:.3f} below train-supported minimum {mc_cal['fault_min']:.3f}"
                ]
            else:
                passed = True
                messages = [
                    "MCSA recorded as certificate score, not a hard gate because train fault-current sidebands do not separate from healthy"
                ]
            report["gates"]["vector_mcsa"] = {"passed": passed, "messages": messages}
            report["scores"]["vector_mcsa"] = mc
            report["feasible"] = report["feasible"] and passed

        return _tolist(report)

    def _verify_envelope(self, w: np.ndarray, cls: str, cal: dict) -> dict[str, Any]:
        messages = []
        scores = []
        if cls in ("OR", "IR"):
            passed_any = False
            for rec in cal["resonance"]["bands"]:
                band = tuple(rec["band"])
                sc = envelope_fault_score(w[0], FS, band, self.calib["freqs"], cls)
                er = band_energy_ratio(w[0], FS, band)
                ok = sc["fund_prominence"] >= rec["prom_min"] and rec["energy_lo"] <= er <= rec["energy_hi"]
                scores.append({"band": band, "fund_prominence": sc["fund_prominence"], "energy_ratio": er, "passed": ok})
                if ok:
                    passed_any = True
            if not passed_any:
                best = max(scores, key=lambda r: r["fund_prominence"]) if scores else {}
                messages.append(f"no train-supported resonance band passed envelope+energy constraints; best={best}")
            return {"gate": {"passed": passed_any, "messages": messages}, "scores": scores}

        passed = True
        for rec in cal["resonance"]["healthy_forbidden_fault_bands"]:
            band = tuple(rec["band"])
            sc = envelope_fault_score(w[0], FS, band, self.calib["freqs"], rec["fault"])
            score = {"fault": rec["fault"], "band": band, "fund_prominence": sc["fund_prominence"], "prom_max": rec["prom_max"]}
            if sc["fund_prominence"] > rec["prom_max"]:
                passed = False
                messages.append(
                    f"healthy candidate has {rec['fault']} envelope prominence {sc['fund_prominence']:.3f} above {rec['prom_max']:.3f} in band {band}"
                )
            scores.append(score)
        return {"gate": {"passed": passed, "messages": messages}, "scores": scores}

    def _legacy_stats_check(self, w: np.ndarray, cls: str) -> dict[str, Any]:
        bcal = self.calib["boundary"]["calib"][cls]["stats"]
        messages = []
        for j, ch in enumerate(CH_NAMES):
            st = time_stats(w[j])
            for key in STAT_KEYS:
                lo, hi = bcal[ch][key]
                val = st[key]
                if val < lo or val > hi:
                    direction = "below" if val < lo else "above"
                    messages.append(
                        f"{ch}_{key}={val:.4g} is {direction} legacy train quantile [{lo:.4g},{hi:.4g}]"
                    )
        return {"passed": len(messages) == 0, "messages": messages}

    def _restore_boundary(self):
        b = self.calib["boundary"]
        verifier = BreezeVerifier(coverage=b["coverage"], gates=b["gates"])
        verifier.cond = b["cond"]
        verifier.freqs = b["freqs"]
        verifier.calib = b["calib"]
        for c in verifier.calib.values():
            if "band" in c:
                c["band"] = tuple(c["band"])
            for ch in c.get("stats", {}):
                c["stats"][ch] = {k: tuple(v) for k, v in c["stats"][ch].items()}
        self.boundary = verifier

    def save(self, path: Path):
        path.write_text(json.dumps(_tolist(self.calib), indent=2))

    @classmethod
    def load(cls, path: Path):
        calib = json.loads(path.read_text())
        obj = cls(
            coverage=calib["coverage"],
            profile=calib["profile"],
            regime=calib.get("regime", "in_domain"),
        )
        obj.calib = calib
        obj._restore_boundary()
        return obj
