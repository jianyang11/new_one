"""Create Phase-B CWRU physics/verifier configuration.

The configuration is derived from the official CWRU Bearing Information page
and the local split metadata. It is a design artifact for the dataset-specific
renderer/verifier; it does not generate synthetic windows.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
PROC = ROOT / "proc"
RESULTS = BREEZE / "results"
sys.path.insert(0, str(BREEZE / "src"))
from kinematics import BearingKinematicsPlugin  # noqa: E402

SOURCE_URL = "https://engineering.case.edu/bearingdatacenter/bearing-information"
FS = 12_000
WIN = 2048
HOP = 2048
CWRU_CLASSES = ("healthy", "IR", "B", "OR")

# Official CWRU drive-end 6205-2RS JEM SKF values.
DRIVE_END_6205 = {
    "bearing": "6205-2RS JEM SKF",
    "inside_diameter_in": 0.9843,
    "outside_diameter_in": 2.0472,
    "thickness_in": 0.5906,
    "ball_diameter_in": 0.3126,
    "pitch_diameter_in": 1.537,
    "number_of_balls": 9,
    "contact_angle_deg": 0.0,
    "ball_spin_harmonic_factor": 2.0,
    "defect_frequency_multiples": {
        "BPFI": 5.415175016265452,
        "BPFO": 3.5848249837345483,
        "FTF": 0.3983138870816165,
        "BSF": 4.713506277093279,
    },
    "source_url": SOURCE_URL,
}


def cwru_plugin(shaft_hz: float) -> BearingKinematicsPlugin:
    return BearingKinematicsPlugin(
        shaft_hz=shaft_hz,
        n_balls=int(DRIVE_END_6205["number_of_balls"]),
        ball_diameter=float(DRIVE_END_6205["ball_diameter_in"]),
        pitch_diameter=float(DRIVE_END_6205["pitch_diameter_in"]),
        contact_angle_deg=float(DRIVE_END_6205["contact_angle_deg"]),
        ball_spin_harmonic_factor=float(DRIVE_END_6205["ball_spin_harmonic_factor"]),
        class_to_frequency={"healthy": None, "IR": "BPFI", "B": "BSF", "OR": "BPFO"},
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def metadata(path: Path) -> list[dict[str, Any]]:
    data = np.load(path, allow_pickle=True)
    return [json.loads(str(item)) for item in data["metadata"]]


def freq_ranges(records: list[dict[str, Any]]) -> dict[str, Any]:
    rpm = np.asarray([float(r["rpm"]) for r in records], dtype=float)
    fr = rpm / 60.0
    keys = ("BPFI", "BPFO", "FTF", "BSF")
    out = {
        "rpm_min": float(np.min(rpm)),
        "rpm_median": float(np.median(rpm)),
        "rpm_max": float(np.max(rpm)),
        "fr_hz_min": float(np.min(fr)),
        "fr_hz_median": float(np.median(fr)),
        "fr_hz_max": float(np.max(fr)),
    }
    vals_by_key = {key: np.asarray([cwru_plugin(v).char_freqs()[key] for v in fr]) for key in keys}
    for key, vals in vals_by_key.items():
        out[f"{key}_hz_min"] = float(np.min(vals))
        out[f"{key}_hz_median"] = float(np.median(vals))
        out[f"{key}_hz_max"] = float(np.max(vals))
    return out


def split_rows() -> list[dict[str, Any]]:
    protocol = read_csv(RESULTS / "phaseB_cwru_protocol_summary.csv")
    rows: list[dict[str, Any]] = []
    for rec in protocol:
        train_path = ROOT / rec["train_path"]
        test_path = ROOT / rec["test_path"]
        train_meta = metadata(train_path)
        test_meta = metadata(test_path)
        train_freq = freq_ranges(train_meta)
        test_freq = freq_ranges(test_meta)
        rows.append(
            {
                "split": rec["split"],
                "train_path": rec["train_path"],
                "test_path": rec["test_path"],
                "train_rpm_min": train_freq["rpm_min"],
                "train_rpm_median": train_freq["rpm_median"],
                "train_rpm_max": train_freq["rpm_max"],
                "test_rpm_min": test_freq["rpm_min"],
                "test_rpm_median": test_freq["rpm_median"],
                "test_rpm_max": test_freq["rpm_max"],
                "train_BPFO_hz_range": f"{train_freq['BPFO_hz_min']:.3f}-{train_freq['BPFO_hz_max']:.3f}",
                "train_BPFI_hz_range": f"{train_freq['BPFI_hz_min']:.3f}-{train_freq['BPFI_hz_max']:.3f}",
                "train_BSF_hz_range": f"{train_freq['BSF_hz_min']:.3f}-{train_freq['BSF_hz_max']:.3f}",
                "train_FTF_hz_range": f"{train_freq['FTF_hz_min']:.3f}-{train_freq['FTF_hz_max']:.3f}",
                "test_BPFO_hz_range": f"{test_freq['BPFO_hz_min']:.3f}-{test_freq['BPFO_hz_max']:.3f}",
                "test_BPFI_hz_range": f"{test_freq['BPFI_hz_min']:.3f}-{test_freq['BPFI_hz_max']:.3f}",
                "test_BSF_hz_range": f"{test_freq['BSF_hz_min']:.3f}-{test_freq['BSF_hz_max']:.3f}",
                "test_FTF_hz_range": f"{test_freq['FTF_hz_min']:.3f}-{test_freq['FTF_hz_max']:.3f}",
            }
        )
    return rows


def write_report(rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase-B CWRU Physics Configuration",
        "",
        "Date: 2026-07-05",
        "",
        f"Official source: {SOURCE_URL}",
        "",
        "The Phase-B CWRU protocol uses the drive-end 12 kHz channel, so the drive-end 6205-2RS JEM SKF bearing geometry and defect-frequency multiples are used. The existing PU renderer/verifier is not reused because it assumes PU 6203 geometry, 8 kHz sampling, and two motor-current channels.",
        "",
        "## Bearing Specification",
        "",
        "| field | value |",
        "| --- | --- |",
    ]
    for key, value in DRIVE_END_6205.items():
        if key == "defect_frequency_multiples":
            continue
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "Defect-frequency multiples of running speed: BPFI=5.4152, BPFO=3.5848, FTF=0.39828, BSF=4.7135.",
            "",
            "## Class-To-Physics Mapping",
            "",
            "| class | physical target | verifier implication |",
            "| --- | --- | --- |",
            "| healthy | no periodic fault impulse target | time/stat/PSD boundary and absence of strong fault-envelope peaks |",
            "| IR | BPFI | envelope peaks at BPFI and harmonic/shaft-modulated sidebands |",
            "| B | BSF / rolling element | envelope peaks at BSF and harmonics; no inner/outer race target substitution |",
            "| OR | BPFO | envelope peaks at BPFO and harmonic consistency |",
            "",
            "## Gate Design",
            "",
            "- Sanity: finite single-channel window with shape (1, 2048).",
            "- Statistics: robust train-only intervals for rms, peak, std, kurtosis, skewness, and crest.",
            "- Spectrum: train-only soft spectral-band intervals and PSD-CDF Wasserstein thresholds at c=90, with c85/c95 sensitivity to be computed later.",
            "- Envelope: train-calibrated resonance bands; target frequencies are computed from per-split rpm and official defect-frequency multiples.",
            "- MCSA/current gate: omitted for CWRU because the official CWRU files are vibration-only; this omission must be stated in the manuscript instead of being patched with synthetic current channels.",
            "",
            "## Split Frequency Ranges",
            "",
            "| split | train rpm | test rpm | train BPFO Hz | train BPFI Hz | train BSF Hz | test BPFO Hz | test BPFI Hz | test BSF Hz |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['split']} | {row['train_rpm_min']:.0f}-{row['train_rpm_max']:.0f} | {row['test_rpm_min']:.0f}-{row['test_rpm_max']:.0f} | {row['train_BPFO_hz_range']} | {row['train_BPFI_hz_range']} | {row['train_BSF_hz_range']} | {row['test_BPFO_hz_range']} | {row['test_BPFI_hz_range']} | {row['test_BSF_hz_range']} |"
        )
    (RESULTS / "phaseB_cwru_verifier_renderer_design.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    rows = split_rows()
    write_csv(RESULTS / "phaseB_cwru_physics_config.csv", rows)
    config = {
        "dataset": "CWRU",
        "sampling_rate_hz": FS,
        "window": WIN,
        "hop": HOP,
        "classes": CWRU_CLASSES,
        "drive_end_bearing": DRIVE_END_6205,
        "class_to_frequency_key": {
            "healthy": None,
            "IR": "BPFI",
            "B": "BSF",
            "OR": "BPFO",
        },
        "split_frequency_ranges_csv": str((RESULTS / "phaseB_cwru_physics_config.csv").relative_to(ROOT)),
    }
    (RESULTS / "phaseB_cwru_physics_config.json").write_text(json.dumps(config, indent=2) + "\n")
    write_report(rows)
    print(f"wrote {RESULTS / 'phaseB_cwru_physics_config.csv'}")
    print(f"wrote {RESULTS / 'phaseB_cwru_physics_config.json'}")
    print(f"wrote {RESULTS / 'phaseB_cwru_verifier_renderer_design.md'}")


if __name__ == "__main__":
    main()
