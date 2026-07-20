from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "src" / "trained_baselines.py"
SPEC = importlib.util.spec_from_file_location("trained_baselines_resume_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def fixture_windows() -> np.ndarray:
    rng = np.random.default_rng(20260720)
    return rng.normal(size=(8, 3, 2048)).astype(np.float32)


@pytest.mark.parametrize(
    ("method", "timegan_config", "ddpm_config", "expected_history"),
    [
        (
            "timegan",
            MODULE.TimeGANConfig(
                latent_channels=8,
                batch_size=4,
                embedding_epochs=2,
                supervisor_epochs=1,
                joint_epochs=1,
            ),
            MODULE.DDPMConfig(hidden_channels=8, batch_size=4, epochs=1, diffusion_steps=4),
            4,
        ),
        (
            "ddpm",
            MODULE.TimeGANConfig(
                latent_channels=8,
                batch_size=4,
                embedding_epochs=1,
                supervisor_epochs=1,
                joint_epochs=1,
            ),
            MODULE.DDPMConfig(hidden_channels=8, batch_size=4, epochs=3, diffusion_steps=4),
            3,
        ),
    ],
)
def test_epoch_checkpoint_resume_matches_uninterrupted(
    tmp_path: Path,
    method: str,
    timegan_config: object,
    ddpm_config: object,
    expected_history: int,
) -> None:
    x = fixture_windows()

    uninterrupted = MODULE.make_trainer(
        method,
        channels=3,
        length=2048,
        seed=17,
        timegan_config=timegan_config,
        ddpm_config=ddpm_config,
    )
    uninterrupted.fit(x, tmp_path / "uninterrupted.pt")
    expected = uninterrupted.sample(3, sample_seed=91)

    interrupted = MODULE.make_trainer(
        method,
        channels=3,
        length=2048,
        seed=17,
        timegan_config=timegan_config,
        ddpm_config=ddpm_config,
    )

    def stop_after_first_checkpoint(_event: dict) -> None:
        raise RuntimeError("intentional test interruption")

    with pytest.raises(RuntimeError, match="intentional test interruption"):
        interrupted.fit(
            x,
            tmp_path / "resumed.pt",
            progress_callback=stop_after_first_checkpoint,
        )

    resumed = MODULE.make_trainer(
        method,
        channels=3,
        length=2048,
        seed=17,
        timegan_config=timegan_config,
        ddpm_config=ddpm_config,
    )
    resumed.fit(x, tmp_path / "resumed.pt")
    observed = resumed.sample(3, sample_seed=91)

    assert len(resumed.training_history()) == expected_history
    np.testing.assert_array_equal(observed, expected)
