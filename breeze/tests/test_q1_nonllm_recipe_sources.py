from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "breeze" / "scripts"
SRC = ROOT / "breeze" / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SCRIPTS))

from recipe_ablation import ClassProfile, empirical_recipe, recipe_for
from renderer import render


def _profile(scale: float) -> ClassProfile:
    return ClassProfile(
        rms_q05=0.8 * scale,
        rms_q50=1.0 * scale,
        rms_q95=1.2 * scale,
        kurtosis_q50=4.0,
        band_median=[0.125] * 8,
        components=[{"freq_hz": 100.0, "amp": 0.05 * scale}],
        current_rms_q05=0.8,
        current_rms_q50=1.0,
        current_rms_q95=1.2,
        current_kurtosis_q50=1.505,
        current_crest_q50=1.49,
        peak_q50=4.0 * scale,
        rms_values=[0.9 * scale, 1.0 * scale, 1.1 * scale],
        peak_values=[3.5 * scale, 4.0 * scale, 4.5 * scale],
        kurtosis_values=[3.5, 4.0, 4.5],
        band_pool=[[0.125] * 8, [0.10, 0.15, 0.10, 0.15, 0.10, 0.15, 0.10, 0.15]],
        current_rms_values=[0.9, 1.0, 1.1],
        current_kurtosis_values=[1.50, 1.505, 1.51],
        current_crest_values=[1.47, 1.49, 1.51],
    )


def test_empirical_recipe_is_deterministic_and_renderable() -> None:
    profiles = {name: _profile(index + 1.0) for index, name in enumerate(("healthy", "OR", "IR"))}
    freqs = {"fr": 15.0, "BPFO": 45.0, "BPFI": 75.0}
    first = empirical_recipe("OR", freqs, profiles, slot=7)
    second = empirical_recipe("OR", freqs, profiles, slot=7)
    assert first == second
    assert recipe_for("empirical", "OR", freqs, profiles, slot=7) == first
    waveform = render(first, seed=123)
    assert waveform.shape == (3, 2048)
    assert waveform.dtype == np.float32
    assert np.isfinite(waveform).all()
