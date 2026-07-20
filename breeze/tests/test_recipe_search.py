from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "src"))

from recipe_search import verifier_gate_violations, verifier_nonconformity


def _calibration() -> dict:
    return {
        "classes": {
            "OR": {
                "soft_spectrum": {"lo": [0.1, 0.2], "hi": [0.3, 0.4]},
                "psd_w1": {"threshold": 10.0},
                "resonance": {
                    "bands": [
                        {"prom_min": 2.0, "energy_lo": 0.1, "energy_hi": 0.3},
                        {"prom_min": 3.0, "energy_lo": 0.2, "energy_hi": 0.4},
                    ]
                },
                "mcsa": {"hard_gate": True, "fault_min": 4.0},
            },
            "healthy": {
                "soft_spectrum": {"lo": [0.1], "hi": [0.3]},
                "psd_w1": {"threshold": 10.0},
                "resonance": {
                    "healthy_forbidden_fault_bands": [
                        {"prom_max": 2.0},
                        {"prom_max": 4.0},
                    ]
                },
                "mcsa": {"hard_gate": False},
            },
        }
    }


def test_fault_report_uses_linf_normalized_constraint_violation() -> None:
    report = {
        "feasible": False,
        "gates": {
            "sanity": {"passed": True},
            "stats_union": {"passed": False},
            "soft_spectrum": {"passed": False},
            "psd_w1": {"passed": False},
            "envelope_multi": {"passed": False},
            "vector_mcsa": {"passed": False},
        },
        "scores": {
            "stats_union": {"axis_distance": 12.0, "axis_threshold": 10.0},
            "soft_spectrum": [0.05, 0.5],
            "psd_w1": 12.0,
            "envelope_multi": [
                {"fund_prominence": 1.0, "energy_ratio": 0.2},
                {"fund_prominence": 2.0, "energy_ratio": 0.5},
            ],
            "vector_mcsa": {"sideband_prominence": 2.0},
        },
    }
    violations = verifier_gate_violations(report, _calibration(), "OR")
    assert violations == pytest.approx(
        {
            "sanity": 0.0,
            "stats_union": 0.2,
            "soft_spectrum": 0.5,
            "psd_w1": 0.2,
            "envelope_multi": 0.5,
            "vector_mcsa": 1.0,
        }
    )
    assert verifier_nonconformity(report, _calibration(), "OR") == pytest.approx(1.0)


def test_feasible_report_has_zero_nonconformity() -> None:
    report = {
        "feasible": True,
        "gates": {name: {"passed": True} for name in ("sanity", "stats_union", "soft_spectrum", "psd_w1", "envelope_multi")},
        "scores": {},
    }
    assert verifier_nonconformity(report, _calibration(), "healthy") == 0.0


def test_unknown_failed_gate_is_never_silently_ignored() -> None:
    report = {
        "feasible": False,
        "gates": {"sanity": {"passed": True}, "new_gate": {"passed": False}},
        "scores": {},
    }
    with pytest.raises(ValueError, match="unsupported failing verifier gates"):
        verifier_nonconformity(report, _calibration(), "healthy")


def test_feasibility_mismatch_fails_closed() -> None:
    report = {
        "feasible": False,
        "gates": {"sanity": {"passed": True}},
        "scores": {},
    }
    with pytest.raises(ValueError, match="feasibility and normalized violations disagree"):
        verifier_nonconformity(report, _calibration(), "healthy")
