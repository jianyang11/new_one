from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "scripts"))

from summarize_trained_baseline_dynamics import summarize


def _row(epoch: int, reconstruction: str = "", generator: str = "") -> dict[str, str]:
    return {
        "method": "timegan",
        "train_mode": "full_train",
        "n_real": "0",
        "seed": "0",
        "class_id": "0",
        "stage": "joint",
        "epoch": str(epoch),
        "reconstruction_loss": reconstruction,
        "supervisor_loss": "",
        "discriminator_loss": "",
        "generator_loss": generator,
        "noise_prediction_mse": "",
    }


def test_summary_ignores_structural_blanks_but_retains_nonfinite_values() -> None:
    rows = [_row(2, "2.0", "nan"), _row(1, "4.0", "3.0")]
    result = summarize(rows)
    reconstruction = next(row for row in result if row["metric"] == "reconstruction_loss")
    generator = next(row for row in result if row["metric"] == "generator_loss")
    assert reconstruction["first"] == 4.0
    assert reconstruction["last"] == 2.0
    assert reconstruction["median"] == 3.0
    assert reconstruction["all_finite"] is True
    assert generator["all_finite"] is False
    assert generator["minimum"] == 3.0


def test_duplicate_epoch_fails() -> None:
    with pytest.raises(ValueError, match="duplicate epoch"):
        summarize([_row(1, "1.0"), _row(1, "2.0")])
