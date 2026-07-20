"""Train-only objective utilities for matched recipe-search baselines.

This module does not propose recipes and never accesses a downstream model or
an outer-test split. It converts a v2 verifier report into an L-infinity
normalized constraint violation. Binary admission remains the primary outcome;
the continuous score is only an optimizer feedback signal.
"""

from __future__ import annotations

from typing import Any

import numpy as np


KNOWN_GATES = {
    "sanity",
    "stats_union",
    "soft_spectrum",
    "psd_w1",
    "envelope_multi",
    "vector_mcsa",
}


def _upper_violation(value: float, upper: float) -> float:
    if upper <= 0:
        return 0.0 if value <= upper else float("inf")
    return max(0.0, value / upper - 1.0)


def _lower_violation(value: float, lower: float) -> float:
    if lower <= 0:
        return 0.0 if value >= lower else float("inf")
    return max(0.0, lower / max(value, np.finfo(float).tiny) - 1.0)


def _interval_violation(value: float, lower: float, upper: float) -> float:
    width = upper - lower
    if width <= 0:
        raise ValueError(f"invalid verifier interval [{lower}, {upper}]")
    if value < lower:
        return (lower - value) / width
    if value > upper:
        return (value - upper) / width
    return 0.0


def verifier_gate_violations(
    report: dict[str, Any],
    verifier_calibration: dict[str, Any],
    cls: str,
) -> dict[str, float]:
    """Return one dimensionless violation per active hard gate.

    Each value is zero when its archived gate passes. Failed continuous
    constraints are normalized by their own calibrated threshold or interval;
    disjunctive envelope bands use the least-violating valid band. An unknown
    failing gate raises instead of being silently omitted.
    """

    gates = report.get("gates", {})
    unknown_failed = [name for name, entry in gates.items() if name not in KNOWN_GATES and not entry.get("passed", False)]
    if unknown_failed:
        raise ValueError(f"unsupported failing verifier gates: {unknown_failed}")
    calibration = verifier_calibration["classes"][cls]
    scores = report.get("scores", {})
    out: dict[str, float] = {}

    if "sanity" in gates:
        out["sanity"] = 0.0 if gates["sanity"]["passed"] else float("inf")

    if "stats_union" in gates:
        if gates["stats_union"]["passed"]:
            out["stats_union"] = 0.0
        else:
            score = scores["stats_union"]
            out["stats_union"] = _upper_violation(
                float(score["axis_distance"]),
                float(score["axis_threshold"]),
            )

    if "soft_spectrum" in gates:
        if gates["soft_spectrum"]["passed"]:
            out["soft_spectrum"] = 0.0
        else:
            values = np.asarray(scores["soft_spectrum"], dtype=float)
            lower = np.asarray(calibration["soft_spectrum"]["lo"], dtype=float)
            upper = np.asarray(calibration["soft_spectrum"]["hi"], dtype=float)
            if values.shape != lower.shape or values.shape != upper.shape:
                raise ValueError("soft-spectrum score/calibration shape mismatch")
            out["soft_spectrum"] = max(
                _interval_violation(float(value), float(lo), float(hi))
                for value, lo, hi in zip(values, lower, upper)
            )

    if "psd_w1" in gates:
        if gates["psd_w1"]["passed"]:
            out["psd_w1"] = 0.0
        else:
            out["psd_w1"] = _upper_violation(
                float(scores["psd_w1"]),
                float(calibration["psd_w1"]["threshold"]),
            )

    if "envelope_multi" in gates:
        if gates["envelope_multi"]["passed"]:
            out["envelope_multi"] = 0.0
        elif cls in ("OR", "IR"):
            band_scores = scores["envelope_multi"]
            band_calibration = calibration["resonance"]["bands"]
            if len(band_scores) != len(band_calibration) or not band_scores:
                raise ValueError("fault-envelope score/calibration mismatch")
            per_band = []
            for score, bounds in zip(band_scores, band_calibration):
                per_band.append(
                    max(
                        _lower_violation(float(score["fund_prominence"]), float(bounds["prom_min"])),
                        _interval_violation(
                            float(score["energy_ratio"]),
                            float(bounds["energy_lo"]),
                            float(bounds["energy_hi"]),
                        ),
                    )
                )
            out["envelope_multi"] = min(per_band)
        else:
            forbidden = calibration["resonance"]["healthy_forbidden_fault_bands"]
            band_scores = scores["envelope_multi"]
            if len(band_scores) != len(forbidden):
                raise ValueError("healthy-envelope score/calibration mismatch")
            out["envelope_multi"] = max(
                (_upper_violation(float(score["fund_prominence"]), float(bounds["prom_max"]))
                 for score, bounds in zip(band_scores, forbidden)),
                default=0.0,
            )

    if "vector_mcsa" in gates:
        mcsa_calibration = calibration["mcsa"]
        if gates["vector_mcsa"]["passed"]:
            out["vector_mcsa"] = 0.0
        elif not mcsa_calibration.get("hard_gate", False):
            raise ValueError("a report-only MCSA gate cannot fail")
        else:
            out["vector_mcsa"] = _lower_violation(
                float(scores["vector_mcsa"]["sideband_prominence"]),
                float(mcsa_calibration["fault_min"]),
            )

    return out


def verifier_nonconformity(
    report: dict[str, Any],
    verifier_calibration: dict[str, Any],
    cls: str,
) -> float:
    """L-infinity normalized constraint violation; zero iff all hard gates pass."""

    violations = verifier_gate_violations(report, verifier_calibration, cls)
    score = max(violations.values(), default=0.0)
    feasible = bool(report.get("feasible", False))
    if feasible != (score == 0.0):
        raise ValueError(
            f"verifier feasibility and normalized violations disagree: feasible={feasible}, score={score}"
        )
    return float(score)
