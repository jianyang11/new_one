from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "src" / "trained_baselines.py"
SPEC = importlib.util.spec_from_file_location("trained_baselines_schedule_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_canonical_schedule_reaches_gaussian_terminal() -> None:
    beta = MODULE.linear_beta_schedule(1000, torch.device("cpu"))
    alpha_bar_terminal = torch.cumprod(1.0 - beta, dim=0)[-1]

    assert float(alpha_bar_terminal) == pytest.approx(4.03583035e-5, rel=1e-6)
    assert float(torch.sqrt(alpha_bar_terminal)) < 0.007


def test_legacy_50_step_schedule_does_not_reach_gaussian_terminal() -> None:
    beta = MODULE.linear_beta_schedule(50, torch.device("cpu"))
    alpha_bar_terminal = torch.cumprod(1.0 - beta, dim=0)[-1]

    assert float(alpha_bar_terminal) == pytest.approx(0.602951586, rel=1e-6)


def test_posterior_coefficients_reconstruct_closed_form_mean() -> None:
    trainer = MODULE.DDPMTrainer(
        channels=3,
        length=2048,
        config=MODULE.DDPMConfig(
            hidden_channels=8,
            residual_layers=2,
            dilation_cycle_length=2,
            epochs=1,
            diffusion_steps=4,
        ),
        seed=7,
    )
    step = 2
    x0 = torch.randn(2, 3, 16, generator=torch.Generator().manual_seed(9))
    noise = torch.randn(2, 3, 16, generator=torch.Generator().manual_seed(10))
    alpha_bar = trainer.alpha_bar[step]
    xt = torch.sqrt(alpha_bar) * x0 + torch.sqrt(1.0 - alpha_bar) * noise
    recovered_x0 = (xt - torch.sqrt(1.0 - alpha_bar) * noise) / torch.sqrt(alpha_bar)
    posterior_mean = (
        trainer.posterior_mean_coefficient_x0[step] * recovered_x0
        + trainer.posterior_mean_coefficient_xt[step] * xt
    )
    closed_form = (
        trainer.beta[step]
        * torch.sqrt(trainer.alpha_bar_previous[step])
        / (1.0 - trainer.alpha_bar[step])
        * x0
        + (1.0 - trainer.alpha_bar_previous[step])
        * torch.sqrt(trainer.alpha[step])
        / (1.0 - trainer.alpha_bar[step])
        * xt
    )

    torch.testing.assert_close(recovered_x0, x0)
    torch.testing.assert_close(posterior_mean, closed_form)
    assert float(trainer.posterior_variance[0]) == pytest.approx(0.0, abs=1e-12)
    assert torch.all(trainer.posterior_variance[1:] > 0)
    torch.testing.assert_close(trainer.reverse_variance, trainer.beta)


def test_ema_uses_registered_decay_and_is_checkpointed(tmp_path: Path) -> None:
    config = MODULE.DDPMConfig(
        hidden_channels=8,
        residual_layers=2,
        dilation_cycle_length=2,
        batch_size=4,
        epochs=1,
        diffusion_steps=4,
        ema_decay=0.9999,
    )
    trainer = MODULE.DDPMTrainer(channels=3, length=2048, config=config, seed=12)
    before = [parameter.detach().clone() for parameter in trainer.ema_model.parameters()]
    windows = torch.randn(4, 3, 2048, generator=torch.Generator().manual_seed(13)).numpy()
    checkpoint = tmp_path / "ddpm.pt"
    trainer.fit(windows, checkpoint)

    assert any(
        not torch.equal(initial, updated)
        for initial, updated in zip(before, trainer.ema_model.parameters())
    )
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    assert state["algorithm"] == "ddpm_diffwave_1d_v5"
    assert state["config"]["ema_decay"] == pytest.approx(0.9999)
    assert set(state["ema_model"]) == set(trainer.ema_model.state_dict())
    assert state["optimizer_step"] == 1
    assert state["optimizer"]["param_groups"][0]["lr"] == pytest.approx(2e-4 / 5000)
    for ema_parameter, parameter in zip(trainer.ema_model.parameters(), trainer.model.parameters()):
        torch.testing.assert_close(ema_parameter, parameter)


def test_fixed_small_variance_remains_explicitly_available() -> None:
    trainer = MODULE.DDPMTrainer(
        channels=3,
        length=2048,
        config=MODULE.DDPMConfig(
            hidden_channels=8,
            residual_layers=2,
            dilation_cycle_length=2,
            epochs=1,
            diffusion_steps=4,
            reverse_variance="fixed_small",
        ),
        seed=7,
    )
    torch.testing.assert_close(trainer.reverse_variance, trainer.posterior_variance)


def test_registered_diffwave_style_architecture() -> None:
    config = MODULE.DDPMConfig()
    trainer = MODULE.DDPMTrainer(channels=3, length=2048, config=config, seed=7)

    assert config.hidden_channels == 64
    assert config.residual_layers == 30
    assert config.dilation_cycle_length == 10
    assert config.batch_size == 16
    assert config.epochs == 200
    assert len(trainer.model.blocks) == 30
    assert [block.dilated_conv.dilation[0] for block in trainer.model.blocks[:11]] == [
        1,
        2,
        4,
        8,
        16,
        32,
        64,
        128,
        256,
        512,
        1,
    ]
    assert torch.count_nonzero(trainer.model.output_projection.weight) == 0
