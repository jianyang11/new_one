"""BREEZE physics verifier: feasible-set membership + structured reports.

Training-free: all thresholds derive from real TRAIN-split windows via robust
quantiles calibrated to a target coverage (default 90%); the test split is
never touched.
"""
import json
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))
from config import FS, WIN, CLASSES, fault_freqs, CONDITIONS
from verifier.features import (time_stats, band_energy_ratio,
                               select_resonance_band, envelope_fault_score,
                               mcsa_features, psd)

SPEC_BANDS = [(0, 250), (250, 500), (500, 1000), (1000, 1500), (1500, 2000),
              (2000, 2500), (2500, 3000), (3000, 4000)]


def spec_fracs(x, fs):
    f, p = psd(x, fs)
    tot = np.trapezoid(p, f) + 1e-30
    return np.array([np.trapezoid(p[(f >= a) & (f < b)],
                                  f[(f >= a) & (f < b)]) / tot
                     for a, b in SPEC_BANDS])

STAT_KEYS = ["rms", "peak", "std", "kurtosis", "skewness", "crest"]
CH_NAMES = ["X", "Y", "Z"]  # vibration, current1, current2


class BreezeVerifier:
    """Calibrate on real train windows; verify candidates; emit reports."""

    def __init__(self, coverage: float = 0.90, gates: dict | None = None):
        self.coverage = coverage
        # gate switches (for ablations)
        self.gates = {"sanity": True, "boundary": True, "energy": True,
                      "envelope": True, "mcsa": True, "spectrum": True}
        if gates:
            self.gates.update(gates)
        self.calib = {}

    # ---------------- calibration ----------------
    def calibrate(self, X_train: np.ndarray, y_train: np.ndarray,
                  cond: str, bearings: np.ndarray | None = None):
        """If per-window bearing IDs are given, each threshold is the UNION of
        per-bearing quantile intervals, so bounds cover between-bearing
        variability of the train split (still test-free)."""
        rpm = CONDITIONS[cond][0]
        self.freqs = fault_freqs(rpm / 60.0)
        self.cond = cond
        # distribute the coverage budget across active gates so the JOINT
        # real-train pass rate ~ coverage (gates behave multiplicatively)
        n_gate_fault = sum(self.gates[g] for g in
                           ("boundary", "energy", "envelope", "mcsa",
                            "spectrum"))
        n_gate_healthy = sum(self.gates[g] for g in
                             ("boundary", "envelope", "spectrum"))
        for ci, cls in enumerate(CLASSES):
            G = n_gate_fault if cls in ("OR", "IR") else n_gate_healthy
            cov_g = self.coverage ** (1.0 / max(G, 1))
            Wc = X_train[y_train == ci]
            rng = np.random.default_rng(0)
            sub = lambda W, n=300: W[rng.choice(len(W), min(n, len(W)),
                                               replace=False)]
            entry = {"stats": {}, "energy": {}}
            # per-channel stat bounds, alpha calibrated for joint coverage
            feats = {ch: np.array([[time_stats(w[j])[k] for k in STAT_KEYS]
                                   for w in Wc])
                     for j, ch in enumerate(CH_NAMES)}
            alpha = self._calibrate_alpha(feats, cov_g)
            entry["alpha"] = alpha
            bc = bearings[y_train == ci] if bearings is not None else None
            for ch in CH_NAMES:
                F = feats[ch]
                if bc is not None:
                    los, his = [], []
                    for b in np.unique(bc):
                        Fb = F[bc == b]
                        los.append(np.quantile(Fb, alpha / 2, axis=0))
                        his.append(np.quantile(Fb, 1 - alpha / 2, axis=0))
                    lo = np.min(los, axis=0)
                    hi = np.max(his, axis=0)
                else:
                    lo = np.quantile(F, alpha / 2, axis=0)
                    hi = np.quantile(F, 1 - alpha / 2, axis=0)
                entry["stats"][ch] = {k: (float(lo[i]), float(hi[i]))
                                      for i, k in enumerate(STAT_KEYS)}
            # spectral-shape gate: per-band energy-fraction intervals
            if self.gates["spectrum"]:
                SF = np.array([spec_fracs(w[0], FS) for w in sub(Wc)])
                a_s = self._calibrate_alpha({"S": SF}, cov_g)
                if bc is not None:
                    los, his = [], []
                    for b in np.unique(bc):
                        Wb = Wc[bc == b]
                        SFb = np.array([spec_fracs(w[0], FS)
                                        for w in sub(Wb, 120)])
                        los.append(np.quantile(SFb, a_s / 2, axis=0))
                        his.append(np.quantile(SFb, 1 - a_s / 2, axis=0))
                    lo_s, hi_s = np.min(los, axis=0), np.max(his, axis=0)
                else:
                    lo_s = np.quantile(SF, a_s / 2, axis=0)
                    hi_s = np.quantile(SF, 1 - a_s / 2, axis=0)
                entry["spec"] = [(float(l), float(h))
                                 for l, h in zip(lo_s, hi_s)]
            # resonance band from fault train windows (vibration channel)
            if cls in ("OR", "IR"):
                entry["band"] = select_resonance_band(sub(Wc, 100)[:, 0, :], FS)
                # envelope prominence threshold: quantile of real fault windows
                def per_bearing(vals_fn, agg):
                    if bc is None:
                        return None
                    outs = []
                    for b in np.unique(bc):
                        Wb = Wc[bc == b]
                        outs.append(vals_fn(sub(Wb, 120)))
                    return agg(outs)

                proms_fn = lambda W: np.quantile(
                    [envelope_fault_score(w[0], FS, entry["band"],
                                          self.freqs, cls)["fund_prominence"]
                     for w in W], 1 - cov_g)
                pb = per_bearing(proms_fn, min)
                entry["env_prom_min"] = float(pb) if pb is not None else float(
                    np.quantile([envelope_fault_score(
                        w[0], FS, entry["band"], self.freqs,
                        cls)["fund_prominence"] for w in sub(Wc)], 1 - cov_g))
                mcsa_fn = lambda W: np.quantile(
                    [mcsa_features(w[1], FS, self.freqs,
                                   cls)["sideband_prominence"] for w in W],
                    1 - cov_g)
                mb = per_bearing(mcsa_fn, min)
                entry["mcsa_min"] = float(mb) if mb is not None else float(
                    np.quantile([mcsa_features(w[1], FS, self.freqs,
                                               cls)["sideband_prominence"]
                                 for w in sub(Wc)], 1 - cov_g))
                blo_fn = lambda W: np.quantile(
                    [band_energy_ratio(w[0], FS, entry["band"]) for w in W],
                    (1 - cov_g) / 2)
                bhi_fn = lambda W: np.quantile(
                    [band_energy_ratio(w[0], FS, entry["band"]) for w in W],
                    1 - (1 - cov_g) / 2)
                blo, bhi = per_bearing(blo_fn, min), per_bearing(bhi_fn, max)
                if blo is None:
                    bers = [band_energy_ratio(w[0], FS, entry["band"])
                            for w in sub(Wc)]
                    blo = np.quantile(bers, (1 - cov_g) / 2)
                    bhi = np.quantile(bers, 1 - (1 - cov_g) / 2)
                entry["energy"]["band_ratio"] = (float(blo), float(bhi))
            else:
                # healthy: fault peaks must NOT be prominent
                band = select_resonance_band(
                    np.concatenate([sub(X_train[y_train == CLASSES.index(c)], 50)[:, 0]
                                    for c in ("OR", "IR")]), FS)
                entry["band"] = band
                Ws = sub(Wc)
                promsO = [envelope_fault_score(w[0], FS, band, self.freqs,
                                               "OR")["fund_prominence"]
                          for w in Ws]
                promsI = [envelope_fault_score(w[0], FS, band, self.freqs,
                                               "IR")["fund_prominence"]
                          for w in Ws]
                if bc is not None:
                    mx = []
                    for b in np.unique(bc):
                        Wb = sub(Wc[bc == b], 120)
                        pO = [envelope_fault_score(w[0], FS, band, self.freqs,
                                                   "OR")["fund_prominence"]
                              for w in Wb]
                        pI = [envelope_fault_score(w[0], FS, band, self.freqs,
                                                   "IR")["fund_prominence"]
                              for w in Wb]
                        mx.append(np.quantile(np.maximum(pO, pI), cov_g))
                    entry["env_prom_max"] = float(max(mx))
                else:
                    entry["env_prom_max"] = float(np.quantile(
                        np.maximum(promsO, promsI), cov_g))
            self.calib[cls] = entry

    def _calibrate_alpha(self, feats: dict, target: float) -> float:
        """Find per-feature tail alpha so joint boundary pass rate ~ target."""
        best_alpha, best_gap = 0.01, 1e9
        for alpha in np.linspace(0.001, 0.10, 40):
            passed = None
            for ch, F in feats.items():
                lo = np.quantile(F, alpha / 2, axis=0)
                hi = np.quantile(F, 1 - alpha / 2, axis=0)
                ok = np.all((F >= lo) & (F <= hi), axis=1)
                passed = ok if passed is None else (passed & ok)
            rate = float(np.mean(passed))
            if abs(rate - target) < best_gap:
                best_gap, best_alpha = abs(rate - target), float(alpha)
        return best_alpha

    # ---------------- verification ----------------
    def verify(self, w: np.ndarray, cls: str) -> dict:
        """w: (3, WIN) candidate window. Returns structured report."""
        report = {"class": cls, "gates": {}, "feasible": True,
                  "instructions": []}
        g = report["gates"]

        def fail(gate, msg, instr):
            g[gate]["passed"] = False
            g[gate]["messages"].append(msg)
            report["feasible"] = False
            if instr:
                report["instructions"].append(instr)

        # --- sanity gate ---
        g["sanity"] = {"passed": True, "messages": []}
        if self.gates["sanity"]:
            if w.shape != (3, WIN):
                fail("sanity", f"shape {w.shape} != (3,{WIN})",
                     f"Output exactly {WIN} rows with 3 numeric values each.")
                return report
            if not np.all(np.isfinite(w)):
                fail("sanity", "non-finite values",
                     "All values must be finite decimal numbers.")
                return report
            for j, ch in enumerate(CH_NAMES):
                if np.std(w[j]) < 1e-8:
                    fail("sanity", f"{ch} constant", f"Channel {ch} must not be constant.")
            d = np.diff(w, axis=1)
            if np.mean(np.all(d == 0, axis=0)) > 0.2:
                fail("sanity", "large repeated segments",
                     "Do not repeat identical consecutive rows.")
            if not report["feasible"]:
                return report

        cal = self.calib[cls]
        # --- boundary statistics gate ---
        g["boundary"] = {"passed": True, "messages": []}
        if self.gates["boundary"]:
            for j, ch in enumerate(CH_NAMES):
                st = time_stats(w[j])
                for k in STAT_KEYS:
                    lo, hi = cal["stats"][ch][k]
                    v = st[k]
                    if v < lo or v > hi:
                        direction = "below" if v < lo else "above"
                        ratio = v / hi if v > hi else (v / lo if lo != 0 else v)
                        msg = (f"{ch}_{k}={v:.4g} is {direction} the "
                               f"class-specific bound [{lo:.4g},{hi:.4g}]")
                        instr = self._stat_instruction(ch, k, v, lo, hi)
                        fail("boundary", msg, instr)

        # --- energy / fault-band gate ---
        g["energy"] = {"passed": True, "messages": []}
        if self.gates["energy"] and cls in ("OR", "IR"):
            lo, hi = cal["energy"]["band_ratio"]
            ber = band_energy_ratio(w[0], FS, cal["band"])
            if ber < lo or ber > hi:
                direction = "below" if ber < lo else "above"
                fail("energy",
                     f"resonance-band ({cal['band'][0]:.0f}-{cal['band'][1]:.0f} Hz) "
                     f"energy ratio {ber:.3f} {direction} [{lo:.3f},{hi:.3f}]",
                     f"The fraction of vibration energy in the "
                     f"{cal['band'][0]:.0f}-{cal['band'][1]:.0f} Hz band must be "
                     f"~{(lo+hi)/2:.2f} (now {ber:.2f}). "
                     + ("Increase impact sharpness or move resonance content "
                        "into this band." if ber < lo else
                        "Move most vibration energy OUTSIDE this band: use a "
                        "lower resonance frequency and/or stronger "
                        "low-frequency background components, keeping only "
                        "weak impact energy in this band."))

        # --- envelope-spectrum gate ---
        g["envelope"] = {"passed": True, "messages": []}
        if self.gates["envelope"]:
            if cls in ("OR", "IR"):
                sc = envelope_fault_score(w[0], FS, cal["band"], self.freqs, cls)
                f0 = self.freqs["BPFO"] if cls == "OR" else self.freqs["BPFI"]
                if sc["fund_prominence"] < cal["env_prom_min"]:
                    fail("envelope",
                         f"envelope-spectrum peak near {f0:.1f} Hz "
                         f"({'BPFO' if cls=='OR' else 'BPFI'}) prominence "
                         f"{sc['fund_prominence']:.2f} < {cal['env_prom_min']:.2f}",
                         f"Insert sparse exponentially decaying impulses repeating "
                         f"at {f0:.1f} Hz (every {1000/f0:.1f} ms, ~"
                         f"{int(round(FS/f0))} samples apart) in the vibration "
                         f"channel X so its envelope spectrum shows a clear peak "
                         f"at {f0:.1f} Hz.")
                report.setdefault("scores", {})["envelope"] = sc
            else:
                sc_o = envelope_fault_score(w[0], FS, cal["band"], self.freqs, "OR")
                sc_i = envelope_fault_score(w[0], FS, cal["band"], self.freqs, "IR")
                worst = max(sc_o["fund_prominence"], sc_i["fund_prominence"])
                if worst > cal["env_prom_max"]:
                    fail("envelope",
                         f"healthy signal shows fault-frequency envelope peak "
                         f"(prominence {worst:.2f} > {cal['env_prom_max']:.2f})",
                         "Remove periodic impact patterns; healthy vibration must "
                         "not contain repetitive impulses at bearing fault frequencies.")

        # --- spectral-shape gate ---
        g["spectrum"] = {"passed": True, "messages": []}
        if self.gates["spectrum"] and "spec" in cal:
            fr = spec_fracs(w[0], FS)
            for (a, b), v, (lo, hi) in zip(SPEC_BANDS, fr, cal["spec"]):
                if v < lo or v > hi:
                    direction = "below" if v < lo else "above"
                    fail("spectrum",
                         f"vibration energy fraction in {a}-{b} Hz = {v:.3f} "
                         f"{direction} [{lo:.3f},{hi:.3f}]",
                         f"Set the background band_weights so the vibration "
                         f"energy fraction in {a}-{b} Hz is ~{(lo+hi)/2:.2f} "
                         f"(now {v:.2f}).")

        # --- MCSA gate (optional) ---
        g["mcsa"] = {"passed": True, "messages": []}
        if self.gates["mcsa"] and cls in ("OR", "IR"):
            mc = mcsa_features(w[1], FS, self.freqs, cls)
            if mc["sideband_prominence"] < cal["mcsa_min"]:
                f0 = self.freqs["BPFO"] if cls == "OR" else self.freqs["BPFI"]
                fail("mcsa",
                     f"current sidebands fe±{f0:.1f} Hz prominence "
                     f"{mc['sideband_prominence']:.2f} < {cal['mcsa_min']:.2f}",
                     f"Keep the phase currents smooth sinusoids at the supply "
                     f"frequency but add weak amplitude-modulation sidebands at "
                     f"±{f0:.1f} Hz around the fundamental.")

        return report

    @staticmethod
    def _stat_instruction(ch, k, v, lo, hi):
        target = (lo + hi) / 2
        if k in ("rms", "std", "peak"):
            if v > hi:
                return (f"Reduce the overall amplitude of channel {ch} "
                        f"(current {k}={v:.3g}, target ≈{target:.3g}).")
            return (f"Increase the overall amplitude of channel {ch} "
                    f"(current {k}={v:.3g}, target ≈{target:.3g}).")
        if k == "kurtosis":
            if ch == "X":
                if v < lo:
                    return (f"Channel X lacks impulsiveness (kurtosis {v:.3g} < "
                            f"{lo:.3g}): raise the impact-amplitude-to-"
                            f"background-noise ratio (stronger impacts and/or "
                            f"lower broadband noise).")
                return (f"Channel X is too impulsive (kurtosis {v:.3g} > "
                        f"{hi:.3g}): weaker impacts or more background noise.")
            if v < lo:
                return (f"Current channel {ch} kurtosis {v:.3g} < {lo:.3g}: "
                        f"reduce amplitude-modulation depth and add a little "
                        f"broadband noise so the waveform is a near-pure "
                        f"sinusoid (kurtosis ~1.5).")
            return (f"Current channel {ch} kurtosis {v:.3g} > {hi:.3g}: "
                    f"reduce noise/distortion; keep a clean sinusoid "
                    f"(kurtosis ~1.5).")
        if k == "crest":
            if ch in ("Y", "Z"):
                if v < lo:
                    return (f"Current channel {ch} crest {v:.3g} < {lo:.3g}: "
                            f"raise the \"kurtosis\" value slightly (e.g. "
                            f"+0.005) -- a bit more inverter noise increases "
                            f"the peak-to-RMS ratio.")
                return (f"Current channel {ch} crest {v:.3g} > {hi:.3g}: "
                        f"lower the \"kurtosis\" value slightly (e.g. -0.005).")
            return (f"Adjust the peak-to-RMS ratio of channel {ch} toward "
                    f"{target:.3g} (now {v:.3g}).")
        return (f"Adjust {k} of channel {ch} into [{lo:.3g},{hi:.3g}].")

    # ---------------- persistence ----------------
    def save(self, path: Path):
        d = {"coverage": self.coverage, "gates": self.gates,
             "cond": self.cond, "freqs": self.freqs, "calib": self.calib}
        path.write_text(json.dumps(d, indent=1))

    @classmethod
    def load(cls, path: Path):
        d = json.loads(path.read_text())
        v = cls(coverage=d["coverage"], gates=d["gates"])
        v.cond, v.freqs = d["cond"], d["freqs"]
        # tuples were serialized as lists
        v.calib = d["calib"]
        for c in v.calib.values():
            if "band" in c:
                c["band"] = tuple(c["band"])
            for ch in c.get("stats", {}):
                c["stats"][ch] = {k: tuple(b) for k, b in c["stats"][ch].items()}
            if "spec" in c:
                c["spec"] = [tuple(b) for b in c["spec"]]
            if "band_ratio" in c.get("energy", {}):
                c["energy"]["band_ratio"] = tuple(c["energy"]["band_ratio"])
        return v
