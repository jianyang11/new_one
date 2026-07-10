"""Deterministic kinematics-based waveform renderer.

Maps an LLM-proposed JSON "signal recipe" to a (3, WIN) window at FS.
The renderer imposes no feasibility: wrong parameters yield infeasible
signals that the BREEZE verifier rejects.
"""
import numpy as np
from scipy.stats import kurtosis as _k, skew as _sk
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import FS, WIN

T = np.arange(WIN) / FS
BANDS = [(0, 250), (250, 500), (500, 1000), (1000, 1500), (1500, 2000),
         (2000, 2500), (2500, 3000), (3000, 4000)]


def _band_shaped_noise(rng, rms, weights, n=WIN):
    """Gaussian noise whose PSD follows relative band energies `weights`
    over the fixed BANDS grid."""
    x = rng.normal(0, 1, n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / FS)
    g = np.zeros_like(f)
    for (a, b), w in zip(BANDS, weights):
        m = (f >= a) & (f < b)
        g[m] = np.sqrt(max(float(w), 0.0) / max(b - a, 1.0))
    x = np.fft.irfft(X * g, n)
    return x / (np.std(x) + 1e-12) * rms


def _colored_noise(rng, rms, color, n=WIN):
    x = rng.normal(0, 1, n)
    if color == "pink":
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(n, 1 / FS)
        X[1:] /= np.sqrt(f[1:])
        x = np.fft.irfft(X, n)
    x = x / (np.std(x) + 1e-12) * rms
    return x


def _impulse_train(rng, rate_hz, amp, decay_ms, resonance_hz, jitter_pct,
                   amp_var_pct, mod_type, mod_depth, fr_hz):
    x = np.zeros(WIN)
    period = FS / max(rate_hz, 1e-3)
    t0 = rng.uniform(0, period)
    positions = []
    while t0 < WIN:
        positions.append(t0)
        t0 += period * (1 + rng.normal(0, jitter_pct / 100))
    tau = decay_ms / 1000.0
    L = min(int(6 * tau * FS) + 1, WIN)
    tt = np.arange(L) / FS
    env = np.exp(-tt / tau)
    for p in positions:
        i = int(p)
        a = amp * (1 + rng.normal(0, amp_var_pct / 100))
        if mod_type == "shaft":  # inner-race: load-zone modulation at fr
            a *= (1 + mod_depth * np.cos(2 * np.pi * fr_hz * p / FS))
        seg = min(L, WIN - i)
        kernel = env * np.sin(2 * np.pi * resonance_hz * tt
                              + rng.uniform(0, 2 * np.pi))
        x[i:i + seg] += a * kernel[:seg]
    return x


def _band_energies(x):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / FS)
    p = np.abs(X) ** 2
    return np.array([p[(f >= a) & (f < b)].sum() for a, b in BANDS])


def render(recipe: dict, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    r = recipe
    bg = r.get("background", {})
    x = np.zeros(WIN)
    for c in bg.get("components", []):
        x += float(c["amp"]) * np.sin(2 * np.pi * float(c["freq_hz"]) * T
                                      + rng.uniform(0, 2 * np.pi))
    ri = bg.get("random_impulses")
    if ri and float(ri.get("amp", 0)) > 0:
        # Poisson-distributed non-periodic transients (machine background)
        n_imp = rng.poisson(float(ri.get("rate_hz", 20)) * WIN / FS)
        tau = float(ri.get("decay_ms", 1.0)) / 1000
        L = min(int(6 * tau * FS) + 1, WIN)
        tt = np.arange(L) / FS
        fres = float(ri.get("resonance_hz", 2500))
        env = np.exp(-tt / tau)
        for _ in range(n_imp):
            i = rng.integers(0, WIN)
            a = float(ri["amp"]) * rng.uniform(0.3, 1.5)
            seg = min(L, WIN - i)
            kern = env * np.sin(2 * np.pi * fres * tt
                                + rng.uniform(0, 2 * np.pi))
            x[i:i + seg] += a * kern[:seg]
    imp = r.get("impacts")
    if imp and float(imp.get("amp", 0)) > 0:
        x += _impulse_train(
            rng, float(imp["rate_hz"]), float(imp["amp"]),
            float(imp.get("decay_ms", 2.0)), float(imp.get("resonance_hz", 2000)),
            float(imp.get("jitter_pct", 1.0)), float(imp.get("amp_var_pct", 10)),
            imp.get("modulation", {}).get("type", "none"),
            float(imp.get("modulation", {}).get("depth", 0.0)),
            float(r.get("fr_hz", 15.0)))
    if "band_weights" in bg and len(bg["band_weights"]) == len(BANDS):
        # band_weights specify the TOTAL vibration spectral shape: the
        # background noise fills whatever the deterministic components
        # (impacts, transients, sinusoids) leave open in each band
        wts = np.clip(np.array([float(w) for w in bg["band_weights"]]),
                      0, None)
        wts = wts / (wts.sum() + 1e-12)
        e_det = _band_energies(x)
        # Parseval on the rfft grid: sum_k |X_k|^2 ~ rms^2 * WIN^2 / 2
        if "target_rms" in r:
            e_tot = float(r["target_rms"]) ** 2 * WIN * WIN / 2
        else:
            e_noise = float(bg.get("noise_rms", 0.02)) ** 2 * WIN * WIN / 2
            e_tot = e_det.sum() + e_noise
        fill = np.clip(wts * e_tot - e_det, 0, None)
        if fill.sum() > 1e-12:
            nrms = np.sqrt(2 * fill.sum() / (WIN * WIN))
            x += _band_shaped_noise(rng, nrms, fill)
        # gentle per-band equalisation toward the requested shape (the
        # additive fill cannot remove excess deterministic energy)
        e_now = _band_energies(x)
        tgt = wts * e_now.sum()
        gains = np.clip(np.sqrt(tgt / (e_now + 1e-30)), 0.7, 1.4)
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(WIN, 1 / FS)
        g = np.ones_like(f)
        for (a_, b_), gv in zip(BANDS, gains):
            g[(f >= a_) & (f < b_)] = gv
        x = np.fft.irfft(X * g, WIN)
        if "target_rms" in r:
            x = x / (np.sqrt(np.mean(x ** 2)) + 1e-12) * float(r["target_rms"])
    else:
        x += _colored_noise(rng, float(bg.get("noise_rms", 0.02)),
                            bg.get("color", "white"))
    cur = r.get("currents", {})
    fe = float(cur.get("fe_hz", 60.0))
    a = float(cur.get("amp", 1.0))
    thd = float(cur.get("thd", 0.03))
    sb = float(cur.get("sideband_depth", 0.0))
    f_flt = float(cur.get("fault_freq_hz", 0.0))
    nz = float(cur.get("noise_rms", 0.01))
    nz = max(nz, 0.008)  # PWM inverter switching-noise floor
    kur_target = cur.get("kurtosis")

    def _lp_noise():
        n_ = _colored_noise(rng, 1.0, "white")
        NF = np.fft.rfft(n_)
        NF[np.fft.rfftfreq(WIN, 1 / FS) > 150] = 0
        n_ = np.fft.irfft(NF, WIN)
        return n_ / (np.std(n_) + 1e-12)

    def _distorted(ph0, dph):
        c_ = np.sin(2 * np.pi * fe * T + ph0 + dph)
        for order in (3, 5, 7):
            c_ += (thd / order) * np.sin(2 * np.pi * order * fe * T
                                         + rng.uniform(0, 2 * np.pi))
        if sb > 0 and f_flt > 0:
            c_ *= (1 + sb * np.cos(2 * np.pi * f_flt * T))
        return c_

    chans = []
    for dph in (0.0, 2 * np.pi / 3):
        if kur_target is not None:
            # window start is arbitrary relative to the supply phase, and
            # the interharmonic residual level follows the specified
            # kurtosis/crest targets (both calibrated numerically)
            kt = float(kur_target)
            crest_t = float(cur.get("crest", 1.49))
            best, best_err = None, np.inf
            for _ in range(12):
                ph0 = rng.uniform(0, 2 * np.pi)
                c_ = _distorted(ph0, dph)
                if _k(c_, fisher=False) > kt - 0.004:
                    continue  # this window phase leaves no noise headroom
                nz_try = _lp_noise()
                lo_g, hi_g = 0.0, 0.3
                for _ in range(35):
                    mid = (lo_g + hi_g) / 2
                    if _k(c_ + mid * nz_try, fisher=False) < kt:
                        lo_g = mid
                    else:
                        hi_g = mid
                cand = c_ + ((lo_g + hi_g) / 2) * nz_try
                cr = np.max(np.abs(cand)) / (np.sqrt(np.mean(cand ** 2))
                                             + 1e-12)
                err = abs(cr - crest_t) / 0.05 + abs(_sk(cand)) / 0.03
                if err < best_err:
                    best, best_err = cand, err
            if best is None:
                best = _distorted(rng.uniform(0, 2 * np.pi), dph)
            c = a * best
        else:
            c = a * _distorted(0.0, dph) + nz * a * _lp_noise()
        if "rms" in cur:  # amplitude calibration to a specified rms
            c = c / (np.sqrt(np.mean(c ** 2)) + 1e-12) * float(cur["rms"])
        chans.append(c)
    if "target_rms" in r:  # accelerometer-gain calibration
        x = x / (np.sqrt(np.mean(x ** 2)) + 1e-12) * float(r["target_rms"])
    return np.stack([x, chans[0], chans[1]]).astype(np.float32)
