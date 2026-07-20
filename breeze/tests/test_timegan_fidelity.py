from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "src" / "trained_baselines.py"
SPEC = importlib.util.spec_from_file_location("trained_baselines_timegan_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_official_timegan_defaults_are_frozen() -> None:
    config = MODULE.TimeGANConfig()

    assert config.hidden_dim == 24
    assert config.num_layers == 3
    assert config.batch_size == 128
    assert config.iterations == 50_000
    assert config.gamma == 1.0
    assert config.discriminator_threshold == 0.15


def test_block_sequence_adapter_is_lossless_and_time_ordered() -> None:
    config = MODULE.TimeGANConfig(
        hidden_dim=8,
        num_layers=2,
        iterations=1,
        checkpoint_interval=1,
    )
    trainer = MODULE.TimeGANTrainer(3, 2048, config, seed=7)
    windows = torch.arange(2 * 3 * 2048, dtype=torch.float32).reshape(2, 3, 2048)

    sequence = trainer._to_sequence(windows)
    recovered = trainer._to_windows(sequence)

    assert sequence.shape == (2, 128, 48)
    torch.testing.assert_close(recovered, windows)
    torch.testing.assert_close(sequence[0, 0, :6], torch.tensor([0.0, 2048.0, 4096.0, 1.0, 2049.0, 4097.0]))


def test_five_network_topology_matches_official_roles() -> None:
    config = MODULE.TimeGANConfig(
        hidden_dim=8,
        num_layers=3,
        iterations=1,
        checkpoint_interval=1,
    )
    trainer = MODULE.TimeGANTrainer(3, 2048, config, seed=8)
    model = trainer.model
    batch = torch.rand(4, 128, 48, generator=torch.Generator().manual_seed(9))
    noise = torch.rand(4, 128, 48, generator=torch.Generator().manual_seed(10))

    embedded = model.embedder(batch)
    recovered = model.recovery(embedded)
    generated = model.generator(noise)
    supervised = model.supervisor(generated)
    logits = model.discriminator(supervised)

    assert model.embedder.recurrent.num_layers == 3
    assert model.recovery.recurrent.num_layers == 3
    assert model.generator.recurrent.num_layers == 3
    assert model.supervisor.recurrent.num_layers == 2
    assert model.discriminator.recurrent.num_layers == 3
    assert embedded.shape == (4, 128, 8)
    assert recovered.shape == batch.shape
    assert logits.shape == (4, 128, 1)
    assert torch.all((recovered >= 0.0) & (recovered <= 1.0))


def test_timegan_smoke_checkpoint_has_fidelity_tag(tmp_path: Path) -> None:
    config = MODULE.TimeGANConfig(
        hidden_dim=8,
        num_layers=2,
        batch_size=4,
        iterations=1,
        checkpoint_interval=1,
    )
    trainer = MODULE.TimeGANTrainer(3, 2048, config, seed=11)
    windows = np.random.default_rng(12).normal(size=(4, 3, 2048)).astype(np.float32)
    checkpoint = tmp_path / "timegan.pt"

    trainer.fit(windows, checkpoint)
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)

    assert state["algorithm"] == "timegan_gru_block16_v5"
    assert state["stage"] == "complete"
    assert state["completed_iteration"] == 1
    assert [row["stage"] for row in state["history"]] == ["embed", "supervisor", "joint"]
