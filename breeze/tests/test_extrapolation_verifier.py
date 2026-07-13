from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "src"))

from config import CLASSES, CONDITIONS, FS, WIN, fault_freqs  # noqa: E402
from verifier.v2 import BreezeVerifierV2  # noqa: E402


def _fault_window(cls: str, condition: str, index: int, *, wrong_rate: bool = False) -> np.ndarray:
    """Small deterministic physical fixture with a selectable envelope rate."""
    time = np.arange(WIN, dtype=float) / FS
    freqs = fault_freqs(CONDITIONS[condition][0] / 60.0)
    rate = freqs["BPFI"] if cls == "IR" else freqs["BPFO"]
    if wrong_rate:
        rate = freqs["BPFI"] if cls == "OR" else freqs["BPFO"]
    carrier = 800.0 if cls == "OR" else 3300.0
    rng = np.random.default_rng(index)
    modulation = 1.0 + (0.75 if cls != "healthy" else 0.02) * np.sin(2 * np.pi * rate * time)
    vibration = 0.12 * modulation * np.sin(2 * np.pi * carrier * time) + 0.004 * rng.normal(size=WIN)
    current_1 = np.sin(2 * np.pi * 60.0 * time) + 0.002 * rng.normal(size=WIN)
    current_2 = np.sin(2 * np.pi * 60.0 * time + 2.1) + 0.002 * rng.normal(size=WIN)
    return np.stack([vibration, current_1, current_2]).astype(np.float32)


def _source_fixture(target: str = "N09_M07_F10") -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], str]:
    sources = [condition for condition in CONDITIONS if condition != target]
    windows, labels, bearings, conditions = [], [], [], []
    for condition_index, condition in enumerate(sources):
        for class_index, cls in enumerate(CLASSES):
            for sample in range(4):
                windows.append(_fault_window(cls, condition, 1000 * condition_index + 100 * class_index + sample))
                labels.append(class_index)
                bearings.append(f"B{condition_index}{class_index}")
                conditions.append(condition)
    return (
        np.stack(windows),
        np.asarray(labels, dtype=np.int64),
        np.asarray(bearings),
        np.asarray(conditions),
        sources,
        target,
    )


def _calibrated() -> tuple[BreezeVerifierV2, list[str], str]:
    X, y, bearings, condition_labels, sources, target = _source_fixture()
    verifier = BreezeVerifierV2(regime="extrapolation")
    verifier.calibrate(
        X,
        y,
        sources[0],
        bearings=bearings,
        source_conditions=sources,
        target_condition=target,
        condition_labels=condition_labels,
    )
    return verifier, sources, target


def test_in_domain_is_the_unchanged_default_regime():
    assert BreezeVerifierV2().regime == "in_domain"


def test_extrapolation_requires_explicit_source_only_condition_labels():
    X, y, bearings, labels, sources, target = _source_fixture()
    verifier = BreezeVerifierV2(regime="extrapolation")
    with pytest.raises(ValueError, match="condition_labels"):
        verifier.calibrate(X, y, sources[0], bearings=bearings, source_conditions=sources, target_condition=target)
    with pytest.raises(ValueError, match="target condition"):
        verifier.calibrate(
            X,
            y,
            sources[0],
            bearings=bearings,
            source_conditions=sources,
            target_condition=sources[0],
            condition_labels=labels,
        )


def test_extrapolation_certificate_keeps_report_only_and_strict_fault_rate_gate():
    verifier, sources, target = _calibrated()
    candidate = _fault_window("OR", sources[0], 99, wrong_rate=True)
    report = verifier.verify(candidate, "OR", observed_condition=sources[0])

    assert report["regime"] == "extrapolation"
    assert report["morphology_target_condition"] == target
    assert report["kinematics_condition"] == sources[0]
    assert report["gates"]["source_domain_report_only"]["passed"] is True
    assert report["gates"]["source_domain_report_only"]["boundary_source"] == "report_only_source_empirical_union"
    assert report["gates"]["envelope_kinematics"]["passed"] is False


def test_extrapolation_constant_window_still_fails_strict_sanity():
    verifier, _, _ = _calibrated()
    report = verifier.verify(np.zeros((3, WIN), dtype=np.float32), "healthy")

    assert report["feasible"] is False
    assert report["gates"]["sanity"]["passed"] is False
    assert report["gates"]["sanity"]["boundary_source"] == "strict_signal_validity"


def test_extrapolation_wrong_class_and_white_noise_are_not_admitted():
    verifier, sources, _ = _calibrated()
    wrong_class = verifier.verify(_fault_window("OR", sources[0], 77), "IR", observed_condition=sources[0])
    white_noise = verifier.verify(np.random.default_rng(7).normal(size=(3, WIN)).astype(np.float32), "OR")

    assert wrong_class["feasible"] is False
    assert white_noise["feasible"] is False


def test_extrapolation_save_load_preserves_regime_and_certificate(tmp_path: Path):
    verifier, sources, target = _calibrated()
    path = tmp_path / "extrapolation.json"
    verifier.save(path)
    restored = BreezeVerifierV2.load(path)
    report = restored.verify(_fault_window("healthy", sources[0], 21), "healthy", observed_condition=sources[0])

    assert restored.regime == "extrapolation"
    assert report["regime"] == "extrapolation"
    assert report["morphology_target_condition"] == target
