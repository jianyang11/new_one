"""Pluggable kinematics interface for BREEZE machinery instances.

The core BREEZE renderer/verifier should consume characteristic frequencies,
class-wise modulation expectations, and frequency-band priors through this
small interface instead of hard-coding a specific machine geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, radians
from typing import Protocol


class KinematicsPlugin(Protocol):
    """Machine-specific physical priors consumed by generic BREEZE stages."""

    def char_freqs(self) -> dict[str, float | list[float]]:
        """Return characteristic frequencies in Hz for the configured state."""

    def modulation_pattern(self, cls: str) -> dict[str, float | str | list[float]]:
        """Return the expected impact/modulation pattern for a class label."""

    def band_priors(self) -> dict[str, object]:
        """Return frequency-band or process-feature priors for verifier gates."""


@dataclass(frozen=True)
class BearingKinematicsPlugin:
    """Rolling-element bearing kinematics.

    The plugin supports PU/CWRU/XJTU-style bearings by changing only geometry
    and shaft speed. Units for ball and pitch diameters only need to be
    consistent because the formulas use their ratio.
    """

    shaft_hz: float
    n_balls: int
    ball_diameter: float
    pitch_diameter: float
    contact_angle_deg: float = 0.0
    ball_spin_harmonic_factor: float = 1.0
    class_to_frequency: dict[str, str | None] = field(
        default_factory=lambda: {
            "healthy": None,
            "normal": None,
            "OR": "BPFO",
            "outer": "BPFO",
            "outer_race": "BPFO",
            "IR": "BPFI",
            "inner": "BPFI",
            "inner_race": "BPFI",
            "B": "BSF",
            "ball": "BSF",
            "rolling_element": "BSF",
            "cage": "FTF",
        }
    )

    def _ratio(self) -> float:
        return (self.ball_diameter / self.pitch_diameter) * cos(radians(self.contact_angle_deg))

    def char_freqs(self) -> dict[str, float]:
        ratio = self._ratio()
        fr = float(self.shaft_hz)
        return {
            "fr": fr,
            "BPFO": 0.5 * self.n_balls * fr * (1.0 - ratio),
            "BPFI": 0.5 * self.n_balls * fr * (1.0 + ratio),
            "FTF": 0.5 * fr * (1.0 - ratio),
            "BSF": self.ball_spin_harmonic_factor
            * 0.5
            * (self.pitch_diameter / self.ball_diameter)
            * fr
            * (1.0 - ratio**2),
        }

    def modulation_pattern(self, cls: str) -> dict[str, float | str]:
        key = self.class_to_frequency.get(cls)
        freqs = self.char_freqs()
        if key is None:
            return {
                "kind": "none",
                "fault_frequency_key": "none",
                "fault_frequency_hz": 0.0,
                "impact_train": 0.0,
                "shaft_modulation_depth_hint": 0.0,
            }
        if key == "BPFI":
            mod_type, depth = "shaft", 0.5
        elif key == "BSF":
            mod_type, depth = "cage", 0.3
        else:
            mod_type, depth = "none", 0.0
        return {
            "kind": "periodic_impacts",
            "fault_frequency_key": key,
            "fault_frequency_hz": float(freqs[key]),
            "impact_train": 1.0,
            "modulation_type": mod_type,
            "shaft_modulation_depth_hint": depth,
        }

    def band_priors(self) -> dict[str, object]:
        freqs = self.char_freqs()
        harmonic_keys = ("BPFO", "BPFI", "BSF", "FTF", "fr")
        return {
            "frequency_keys": list(harmonic_keys),
            "harmonics": {key: [float(freqs[key] * h) for h in range(1, 5)] for key in harmonic_keys},
            "requires_envelope": True,
            "requires_current_mcsa": False,
            "notes": "Use train-supported resonance bands; characteristic frequencies constrain envelope peaks, not raw high-frequency carrier location.",
        }


@dataclass(frozen=True)
class MillingKinematicsPlugin:
    """Low-frequency CNC/milling process kinematics.

    This plugin intentionally avoids bearing-style envelope assumptions. It
    exposes spindle and tooth-passing frequencies plus process-feature priors
    suitable for low-sampling-rate milling data.
    """

    spindle_hz: float
    n_teeth: int
    fs_hz: float
    harmonic_count: int = 5

    def _harmonics_below_nyquist(self, base: float) -> list[float]:
        nyq = 0.5 * self.fs_hz
        return [float(base * h) for h in range(1, self.harmonic_count + 1) if base * h < 0.95 * nyq]

    def char_freqs(self) -> dict[str, float | list[float]]:
        tpf = float(self.spindle_hz * self.n_teeth)
        spindle = float(self.spindle_hz)
        return {
            "spindle_hz": spindle,
            "TPF": tpf,
            "spindle_harmonics": self._harmonics_below_nyquist(spindle),
            "TPF_harmonics": self._harmonics_below_nyquist(tpf),
        }

    def modulation_pattern(self, cls: str) -> dict[str, float | str | list[float]]:
        label = cls.lower()
        severity = 0.0
        if label in {"worn", "worn_tool", "wear", "medium", "worn_0p2_0p45", "degradation", "degraded"}:
            severity = 0.5
        elif label in {"severe", "severe_wear", "failed", "failure", "vb_gt_0p45", "vb_ge_0p7"}:
            severity = 1.0
        return {
            "kind": "tooth_passing_process",
            "fault_frequency_key": "TPF",
            "fault_frequency_hz": float(self.char_freqs()["TPF"]),
            "severity_hint": severity,
            "expected_changes": [
                "TPF harmonic amplitude ratio increases with wear",
                "per-tooth cycle RMS and crest statistics drift with wear",
                "axis/spindle current correlations change under worn cutting",
            ],
        }

    def band_priors(self) -> dict[str, object]:
        freqs = self.char_freqs()
        return {
            "requires_envelope": False,
            "requires_current_mcsa": False,
            "low_sampling_rate": True,
            "process_features": [
                "TPF_harmonic_amplitude_ratios",
                "spindle_harmonic_amplitude_ratios",
                "per_tooth_cycle_rms",
                "rms_trend",
                "channel_correlation",
                "psd_wasserstein",
            ],
            "TPF_harmonics": freqs["TPF_harmonics"],
            "spindle_harmonics": freqs["spindle_harmonics"],
        }


def bearing_fault_freqs(
    shaft_hz: float,
    n_balls: int,
    ball_diameter: float,
    pitch_diameter: float,
    contact_angle_deg: float = 0.0,
    ball_spin_harmonic_factor: float = 1.0,
) -> dict[str, float]:
    """Compatibility helper for code paths that expect a frequency dict."""
    return BearingKinematicsPlugin(
        shaft_hz=shaft_hz,
        n_balls=n_balls,
        ball_diameter=ball_diameter,
        pitch_diameter=pitch_diameter,
        contact_angle_deg=contact_angle_deg,
        ball_spin_harmonic_factor=ball_spin_harmonic_factor,
    ).char_freqs()
