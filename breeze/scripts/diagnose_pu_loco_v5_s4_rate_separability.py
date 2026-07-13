"""Measure source-only physical-rate separability before any S4 v1.2 proposal.

This diagnostic deliberately does not select a verifier threshold.  It records
whether each candidate physical feature has a source-domain gap between the
asserted class and both the opposite real class and white noise.  It loads
only `config.SPLIT['train']` windows from the four operating conditions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "src"))
sys.path.insert(0, str(ROOT / "breeze" / "scripts"))

from build_pu_loco_v3_internal_candidates import load_train_condition  # noqa: E402
from config import CLASSES, CONDITIONS, FS, WIN, fault_freqs  # noqa: E402
from verifier.extrapolation import DEMODULATION_BANDS, _envelope_evidence  # noqa: E402
from verifier.features import envelope_spectrum, env_peak_metrics  # noqa: E402


DEFAULT_OUT_DIR = "breeze/results/pu_loco_v5_s4_extrapolation_verifier_2026-07-13/v1_1/rate_separability"


def _quantiles(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "min": float(array.min()),
        "q01": float(np.quantile(array, 0.01)),
        "q05": float(np.quantile(array, 0.05)),
        "q10": float(np.quantile(array, 0.10)),
        "q50": float(np.quantile(array, 0.50)),
        "q90": float(np.quantile(array, 0.90)),
        "q95": float(np.quantile(array, 0.95)),
        "q99": float(np.quantile(array, 0.99)),
        "max": float(array.max()),
    }


def _features(window: np.ndarray, asserted: str, condition: str) -> dict[str, float]:
    freqs = fault_freqs(CONDITIONS[condition][0] / 60.0)
    evidence = _envelope_evidence(window[0], asserted, freqs)
    f, spectrum = envelope_spectrum(window[0], FS, DEMODULATION_BANDS[asserted])
    df = float(f[1] - f[0])
    target = float(freqs["BPFO"] if asserted == "OR" else freqs["BPFI"])
    harmonic = env_peak_metrics(f, spectrum, 2.0 * target, max(2.0 * df, 0.02 * 2.0 * target))["prominence"]
    if asserted == "IR":
        sidebands = [
            env_peak_metrics(f, spectrum, target + sign * freqs["fr"], max(2.0 * df, 0.02 * target))["prominence"]
            for sign in (-1.0, 1.0)
        ]
        modulation = float(np.mean(sidebands))
    else:
        modulation = 0.0
    return {
        "fund_prominence": float(evidence["fund_prominence"]),
        "rate_contrast": float(evidence["rate_contrast"]),
        "harm2_prominence": float(harmonic),
        "shaft_prominence": float(evidence["shaft_prominence"]),
        "ir_sideband_prominence": modulation,
    }


def _append(rows: dict[str, dict[str, list[float]]], group: str, features: dict[str, float]) -> None:
    for name, value in features.items():
        rows[group][name].append(float(value))


def _separation(true: dict[str, float], wrong: dict[str, float], white: dict[str, float]) -> dict[str, Any]:
    return {
        "q10_true_minus_q90_wrong": float(true["q10"] - wrong["q90"]),
        "q10_true_minus_q90_white": float(true["q10"] - white["q90"]),
        "min_true_minus_max_wrong": float(true["min"] - wrong["max"]),
        "min_true_minus_max_white": float(true["min"] - white["max"]),
        "q10_separates_wrong": bool(true["q10"] > wrong["q90"]),
        "q10_separates_white": bool(true["q10"] > white["q90"]),
    }


def diagnose(args: argparse.Namespace) -> dict[str, Any]:
    rng = np.random.default_rng(args.seed)
    result: dict[str, Any] = {
        "boundary": "only config.SPLIT train-bearing PU windows are loaded; pseudo-held-out and formal held-out windows are unread",
        "white_noise_per_condition": args.white_noise_per_condition,
        "conditions": list(CONDITIONS),
        "asserted": {},
    }
    for asserted in ("OR", "IR"):
        groups = {
            "true_class": {feature: [] for feature in _features(np.zeros((3, WIN), dtype=np.float32), asserted, next(iter(CONDITIONS)))},
            "wrong_class": {feature: [] for feature in _features(np.zeros((3, WIN), dtype=np.float32), asserted, next(iter(CONDITIONS)))},
            "white_noise": {feature: [] for feature in _features(np.zeros((3, WIN), dtype=np.float32), asserted, next(iter(CONDITIONS)))},
        }
        other = "IR" if asserted == "OR" else "OR"
        for condition in CONDITIONS:
            X, y, _ = load_train_condition(condition)
            for actual, group in ((asserted, "true_class"), (other, "wrong_class")):
                for window in X[y == CLASSES.index(actual)]:
                    _append(groups, group, _features(window, asserted, condition))
            for _ in range(args.white_noise_per_condition):
                white = rng.normal(0.0, 1.0, size=(3, WIN)).astype(np.float32)
                _append(groups, "white_noise", _features(white, asserted, condition))
        summary = {group: {feature: _quantiles(values) for feature, values in features.items()} for group, features in groups.items()}
        result["asserted"][asserted] = {
            "other_real_class": other,
            "quantiles": summary,
            "separation": {
                feature: _separation(summary["true_class"][feature], summary["wrong_class"][feature], summary["white_noise"][feature])
                for feature in groups["true_class"]
            },
        }
    return result


def write_report(out_dir: Path, result: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rate_separability_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# S4 source-only rate/harmonic/modulation separability", "", "## Boundary", "", result["boundary"], ""]
    lines.extend(["## Interpretation rule", "", "A feature is a candidate for a new strict source-only physical gate only if its true-class q10 exceeds both wrong-class and white-noise q90. This diagnostic does not choose a threshold or change S4 admission.", ""])
    lines.extend(["## Source distribution gaps", "", "| asserted class | feature | q10 true - q90 wrong | q10 true - q90 white | candidate separation |", "|---|---|---:|---:|---|"])
    for asserted, record in result["asserted"].items():
        for feature, separation in record["separation"].items():
            passed = separation["q10_separates_wrong"] and separation["q10_separates_white"]
            lines.append(f"| {asserted} | {feature} | {separation['q10_true_minus_q90_wrong']:.6f} | {separation['q10_true_minus_q90_white']:.6f} | {'yes' if passed else 'no'} |")
    (out_dir / "rate_separability_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--white-noise-per-condition", type=int, default=100)
    args = parser.parse_args()
    if args.white_noise_per_condition != 100:
        raise SystemExit("the v1.1 separability diagnostic freezes 100 white-noise windows per source condition")
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    result = diagnose(args)
    write_report(out_dir, result)
    candidates = {
        asserted: [feature for feature, rec in record["separation"].items() if rec["q10_separates_wrong"] and rec["q10_separates_white"]]
        for asserted, record in result["asserted"].items()
    }
    print(json.dumps({"candidate_features": candidates}, sort_keys=True))


if __name__ == "__main__":
    main()
