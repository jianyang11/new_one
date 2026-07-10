"""Deterministic signal features used by the BREEZE physics verifier.

All functions are training-free: pure signal processing + bearing kinematics.
"""
import numpy as np
from scipy.signal import welch, hilbert, firwin, filtfilt
from scipy.stats import kurtosis, skew


# ---------------- time-domain statistics ----------------

def time_stats(x: np.ndarray) -> dict:
    rms = float(np.sqrt(np.mean(x ** 2)))
    peak = float(np.max(np.abs(x)))
    return {
        "rms": rms,
        "peak": peak,
        "std": float(np.std(x)),
        "kurtosis": float(kurtosis(x, fisher=False)),
        "skewness": float(skew(x)),
        "crest": float(peak / rms) if rms > 0 else 0.0,
    }


# ---------------- spectral features ----------------

def psd(x: np.ndarray, fs: int, nperseg: int = 512):
    f, p = welch(x, fs=fs, nperseg=nperseg)
    return f, p


def band_energy_ratio(x: np.ndarray, fs: int, band: tuple) -> float:
    f, p = psd(x, fs)
    tot = np.trapezoid(p, f)
    m = (f >= band[0]) & (f <= band[1])
    return float(np.trapezoid(p[m], f[m]) / tot) if tot > 0 else 0.0


def spectral_kurtosis(x: np.ndarray, fs: int, nperseg: int = 128) -> tuple:
    """Short-time-Fourier-based spectral kurtosis (Antoni 2006 style)."""
    from scipy.signal import stft
    f, _, Z = stft(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2)
    A2 = np.abs(Z) ** 2
    sk = (np.mean(A2 ** 2, axis=1) / (np.mean(A2, axis=1) ** 2 + 1e-30)) - 2.0
    return f, sk


def select_resonance_band(train_windows: np.ndarray, fs: int,
                          width: float = 1000.0) -> tuple:
    """Pick the demodulation band maximizing mean spectral kurtosis over the
    real fault training windows (deterministic, train-split only)."""
    sks = []
    for w in train_windows:
        f, sk = spectral_kurtosis(w, fs)
        sks.append(sk)
    f, _ = spectral_kurtosis(train_windows[0], fs)
    mean_sk = np.mean(sks, axis=0)
    best, best_val = (200.0, 200.0 + width), -np.inf
    lo = 200.0
    while lo + width <= fs / 2 - 50:
        m = (f >= lo) & (f <= lo + width)
        v = float(np.mean(mean_sk[m]))
        if v > best_val:
            best_val, best = v, (lo, lo + width)
        lo += 100.0
    return best


def envelope_spectrum(x: np.ndarray, fs: int, band: tuple):
    """Squared envelope spectrum after bandpass to the resonance band."""
    ny = fs / 2
    taps = firwin(129, [band[0] / ny, min(band[1] / ny, 0.99)],
                  pass_zero=False)
    xb = filtfilt(taps, [1.0], x)
    env = np.abs(hilbert(xb)) ** 2
    env = env - np.mean(env)
    n = len(env)
    spec = np.abs(np.fft.rfft(env * np.hanning(n))) / n
    freqs = np.fft.rfftfreq(n, 1 / fs)
    return freqs, spec


def env_peak_metrics(freqs: np.ndarray, spec: np.ndarray, f_target: float,
                     tol: float) -> dict:
    """Peak proximity/prominence near a target fault frequency.

    prominence = peak amplitude in [f_target±tol] divided by the median
    envelope-spectrum level in a broad neighborhood (robust noise floor).
    """
    m = (freqs >= f_target - tol) & (freqs <= f_target + tol)
    if not np.any(m):
        return {"prominence": 0.0, "proximity_err": tol, "peak_freq": np.nan}
    i = np.argmax(spec[m])
    pk_f = float(freqs[m][i])
    pk_a = float(spec[m][i])
    nb = (freqs >= max(2.0, f_target - 10 * tol)) & (freqs <= f_target + 10 * tol)
    floor = float(np.median(spec[nb])) + 1e-30
    return {"prominence": pk_a / floor,
            "proximity_err": abs(pk_f - f_target),
            "peak_freq": pk_f}


def envelope_fault_score(x: np.ndarray, fs: int, band: tuple,
                         freqs_hz: dict, fault: str) -> dict:
    """Composite envelope-spectrum evidence for a fault type.

    fault in {"OR","IR"}: checks fundamental + 2nd harmonic; IR additionally
    checks rotating-frequency modulation sidebands (BPFI ± fr).
    """
    F, S = envelope_spectrum(x, fs, band)
    df = F[1] - F[0]
    fr = freqs_hz["fr"]
    f0 = freqs_hz["BPFO"] if fault == "OR" else freqs_hz["BPFI"]
    tol = max(2 * df, 0.02 * f0)  # resolution- and speed-tolerance-based
    out = {"tol": tol}
    fund = env_peak_metrics(F, S, f0, tol)
    harm = env_peak_metrics(F, S, 2 * f0, max(2 * df, 0.02 * 2 * f0))
    out["fund_prominence"] = fund["prominence"]
    out["fund_proximity_err"] = fund["proximity_err"]
    out["harm2_prominence"] = harm["prominence"]
    if fault == "IR":
        sb = [env_peak_metrics(F, S, f0 + s * fr, tol)["prominence"]
              for s in (-1, +1)]
        out["sideband_prominence"] = float(np.mean(sb))
    return out


# ---------------- MCSA ----------------

def mcsa_features(cur: np.ndarray, fs: int, freqs_hz: dict, fault: str) -> dict:
    """Motor-current sideband evidence: fe ± f_fault around detected supply
    fundamental fe (estimated from the current spectrum itself)."""
    n = len(cur)
    spec = np.abs(np.fft.rfft((cur - np.mean(cur)) * np.hanning(n))) / n
    F = np.fft.rfftfreq(n, 1 / fs)
    m = (F > 5) & (F < 500)
    fe = float(F[m][np.argmax(spec[m])])
    f_fault = freqs_hz["BPFO"] if fault == "OR" else freqs_hz["BPFI"]
    df = F[1] - F[0]
    tol = max(2 * df, 0.02 * f_fault)
    sbs = [env_peak_metrics(F, spec, fe + s * f_fault, tol)["prominence"]
           for s in (-1, +1)]
    return {"fe": fe, "sideband_prominence": float(np.mean(sbs))}
