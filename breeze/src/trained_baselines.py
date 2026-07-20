"""Training-based 1D synthetic-signal baselines for the closing protocol.

The implementations are intentionally independent of BREEZE's verifier and
recipe machinery.  They learn only from the outer-training windows provided by
the caller, train one unconditional model per class, and produce complete
three-channel windows. TimeGAN follows the author's five recurrent networks,
three-stage objective, and official defaults; a lossless chronological block
adapter maps each 2048-by-3 window to a 128-by-48 sequence. DDPM uses
the canonical 1,000-step linear forward schedule, the epsilon-prediction
objective, posterior ancestral reverse sampling, and an unconditional
DiffWave-style 1-D gated residual/skip denoiser. The denoiser dimensions follow
the LMNT DiffWave defaults (30 layers, 64 residual channels, dilation cycle 10),
while the 200-epoch vibration-signal training budget follows the 2048-sample
bearing experiment of Yi et al. (2023). This is an explicitly documented 1-D
adaptation, not a claim of reproducing either image DDPM or TSDM verbatim.

Every training stage writes atomic checkpoints. Because each iteration/epoch
and batch derives its own seed, a resumed run is equivalent to an uninterrupted
run at a checkpoint boundary.
"""

from __future__ import annotations

import math
import os
import tempfile
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, Literal

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


DeviceName = Literal["cpu", "mps"]
ProgressCallback = Callable[[dict[str, float | int | str]], None]


@dataclass(frozen=True)
class TimeGANConfig:
    hidden_dim: int = 24
    num_layers: int = 3
    batch_size: int = 128
    iterations: int = 50_000
    block_size: int = 16
    learning_rate: float = 1e-3
    gamma: float = 1.0
    discriminator_threshold: float = 0.15
    checkpoint_interval: int = 100


@dataclass(frozen=True)
class DDPMConfig:
    hidden_channels: int = 64
    residual_layers: int = 30
    dilation_cycle_length: int = 10
    batch_size: int = 16
    epochs: int = 200
    diffusion_steps: int = 1000
    learning_rate: float = 2e-4
    ema_decay: float = 0.9999
    warmup_steps: int = 5000
    gradient_clip_norm: float = 1.0
    reverse_variance: str = "fixed_large"


def _atomic_torch_save(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_path = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(raw_path)
    try:
        torch.save(payload, tmp_path)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _seeded_randn(shape: tuple[int, ...], seed: int, device: torch.device) -> torch.Tensor:
    generator = torch.Generator(device=device).manual_seed(seed)
    return torch.randn(shape, generator=generator, device=device)


def _batch_indices(n: int, batch_size: int, seed: int) -> list[torch.Tensor]:
    generator = torch.Generator().manual_seed(seed)
    permutation = torch.randperm(n, generator=generator)
    return [permutation[start : start + batch_size] for start in range(0, n, batch_size)]


class TimeGANSequenceNetwork(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        num_layers: int,
        sigmoid_output: bool,
    ):
        super().__init__()
        self.recurrent = nn.GRU(
            input_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
        )
        self.projection = nn.Linear(hidden_dim, output_dim)
        self.sigmoid_output = sigmoid_output

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        output, _ = self.recurrent(sequence)
        projected = self.projection(output)
        return torch.sigmoid(projected) if self.sigmoid_output else projected


class TimeGAN(nn.Module):
    """PyTorch realization of the five recurrent networks in official TimeGAN."""

    def __init__(self, feature_dim: int, hidden_dim: int, num_layers: int):
        super().__init__()
        if num_layers < 2:
            raise ValueError("TimeGAN requires at least two recurrent layers")
        self.feature_dim = feature_dim
        self.hidden_dim = hidden_dim
        self.embedder = TimeGANSequenceNetwork(
            feature_dim, hidden_dim, hidden_dim, num_layers, True
        )
        self.recovery = TimeGANSequenceNetwork(
            hidden_dim, hidden_dim, feature_dim, num_layers, True
        )
        self.generator = TimeGANSequenceNetwork(
            feature_dim, hidden_dim, hidden_dim, num_layers, True
        )
        self.supervisor = TimeGANSequenceNetwork(
            hidden_dim, hidden_dim, hidden_dim, num_layers - 1, True
        )
        self.discriminator = TimeGANSequenceNetwork(
            hidden_dim, hidden_dim, 1, num_layers, False
        )


class TimeGANTrainer:
    """Official-objective TimeGAN with a lossless block-sequence PU adapter."""

    def __init__(
        self,
        channels: int,
        length: int,
        config: TimeGANConfig,
        seed: int,
        device_name: DeviceName = "cpu",
    ):
        if length != 2048:
            raise ValueError(f"TimeGAN baseline is registered for 2048-sample PU windows, got {length}")
        if length % config.block_size:
            raise ValueError("TimeGAN block_size must divide the window length exactly")
        if config.iterations <= 0 or config.checkpoint_interval <= 0:
            raise ValueError("TimeGAN iterations and checkpoint_interval must be positive")
        if device_name == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested but is unavailable")
        self.config = config
        self.seed = seed
        self.channels = channels
        self.length = length
        self.sequence_length = length // config.block_size
        self.feature_dim = channels * config.block_size
        self.device = torch.device(device_name)
        torch.manual_seed(seed)
        self.model = TimeGAN(self.feature_dim, config.hidden_dim, config.num_layers).to(self.device)
        embed_parameters = list(self.model.embedder.parameters()) + list(self.model.recovery.parameters())
        generator_parameters = list(self.model.generator.parameters()) + list(self.model.supervisor.parameters())
        self.opt_embed_pretrain = torch.optim.Adam(embed_parameters, lr=config.learning_rate)
        self.opt_embed_joint = torch.optim.Adam(embed_parameters, lr=config.learning_rate)
        self.opt_supervisor = torch.optim.Adam(generator_parameters, lr=config.learning_rate)
        self.opt_generator = torch.optim.Adam(generator_parameters, lr=config.learning_rate)
        self.opt_discriminator = torch.optim.Adam(
            self.model.discriminator.parameters(), lr=config.learning_rate
        )
        self.minimum: torch.Tensor | None = None
        self.value_range: torch.Tensor | None = None
        self.history: list[dict[str, float | int | str]] = []

    def _to_sequence(self, windows: torch.Tensor) -> torch.Tensor:
        batch = windows.shape[0]
        return (
            windows.transpose(1, 2)
            .contiguous()
            .reshape(batch, self.sequence_length, self.feature_dim)
        )

    def _to_windows(self, sequence: torch.Tensor) -> torch.Tensor:
        batch = sequence.shape[0]
        return (
            sequence.reshape(
                batch,
                self.sequence_length,
                self.config.block_size,
                self.channels,
            )
            .reshape(batch, self.length, self.channels)
            .transpose(1, 2)
            .contiguous()
        )

    def _batch(self, sequence: torch.Tensor, seed: int) -> torch.Tensor:
        generator = torch.Generator().manual_seed(seed)
        indexes = torch.randperm(len(sequence), generator=generator)[: self.config.batch_size]
        return sequence[indexes.to(self.device)]

    def _uniform_noise(self, batch_size: int, seed: int) -> torch.Tensor:
        generator = torch.Generator(device=self.device).manual_seed(seed)
        return torch.rand(
            (batch_size, self.sequence_length, self.feature_dim),
            generator=generator,
            device=self.device,
        )

    def _zero_all_gradients(self) -> None:
        for parameter in self.model.parameters():
            parameter.grad = None

    @staticmethod
    def _supervised_loss(real_latent: torch.Tensor, predicted_latent: torch.Tensor) -> torch.Tensor:
        return F.mse_loss(real_latent[:, 1:, :], predicted_latent[:, :-1, :])

    def _checkpoint(
        self,
        path: Path,
        stage: str,
        completed_iteration: int,
        elapsed_seconds: float,
    ) -> None:
        if self.minimum is None or self.value_range is None:
            raise RuntimeError("normalization state is unavailable")
        _atomic_torch_save(
            {
                "algorithm": "timegan_gru_block16_v5",
                "config": asdict(self.config),
                "seed": self.seed,
                "stage": stage,
                "completed_iteration": completed_iteration,
                "elapsed_seconds": elapsed_seconds,
                "model": self.model.state_dict(),
                "opt_embed_pretrain": self.opt_embed_pretrain.state_dict(),
                "opt_embed_joint": self.opt_embed_joint.state_dict(),
                "opt_supervisor": self.opt_supervisor.state_dict(),
                "opt_generator": self.opt_generator.state_dict(),
                "opt_discriminator": self.opt_discriminator.state_dict(),
                "minimum": self.minimum.cpu(),
                "value_range": self.value_range.cpu(),
                "history": self.history,
            },
            path,
        )

    def _restore(self, path: Path) -> tuple[str, int, float]:
        state = torch.load(path, map_location=self.device, weights_only=False)
        if state.get("algorithm") != "timegan_gru_block16_v5" or state.get("config") != asdict(self.config):
            raise RuntimeError(f"checkpoint configuration mismatch: {path}")
        self.model.load_state_dict(state["model"])
        self.opt_embed_pretrain.load_state_dict(state["opt_embed_pretrain"])
        self.opt_embed_joint.load_state_dict(state["opt_embed_joint"])
        self.opt_supervisor.load_state_dict(state["opt_supervisor"])
        self.opt_generator.load_state_dict(state["opt_generator"])
        self.opt_discriminator.load_state_dict(state["opt_discriminator"])
        self.minimum = state["minimum"].to(self.device)
        self.value_range = state["value_range"].to(self.device)
        self.history = list(state.get("history", []))
        return (
            str(state["stage"]),
            int(state["completed_iteration"]),
            float(state["elapsed_seconds"]),
        )

    def training_history(self) -> list[dict[str, float | int | str]]:
        return [dict(row) for row in self.history]

    def _record_checkpoint(
        self,
        checkpoint: Path,
        stage: str,
        iteration: int,
        elapsed: float,
        losses: dict[str, float],
        progress_callback: ProgressCallback | None,
    ) -> None:
        record: dict[str, float | int | str] = {
            "stage": stage,
            "epoch": iteration,
            **losses,
        }
        self.history.append(record)
        self._checkpoint(checkpoint, stage, iteration, elapsed)
        if progress_callback is not None:
            progress_callback(
                {
                    **record,
                    "completed": iteration,
                    "total": self.config.iterations,
                    "elapsed_seconds": elapsed,
                }
            )

    def fit(
        self,
        x: np.ndarray,
        checkpoint: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> float:
        if x.ndim != 3:
            raise ValueError(f"expected (windows, channels, samples), got {x.shape}")
        if not np.isfinite(x).all():
            raise ValueError("TimeGAN cannot train on non-finite windows")
        windows = torch.as_tensor(x, dtype=torch.float32, device=self.device)
        sequence = self._to_sequence(windows)
        stage_order = ("embed", "supervisor", "joint", "complete")
        stage, completed_iteration, elapsed = ("embed", 0, 0.0)
        if checkpoint.exists():
            stage, completed_iteration, elapsed = self._restore(checkpoint)
        else:
            self.minimum = sequence.amin(dim=(0, 1), keepdim=True)
            self.value_range = (
                sequence.amax(dim=(0, 1), keepdim=True) - self.minimum
            ).clamp_min(1e-7)
        if self.minimum is None or self.value_range is None:
            raise RuntimeError("missing normalization state")
        normalized = (sequence - self.minimum) / self.value_range
        if stage == "complete":
            return elapsed

        start_stage = stage_order.index(stage)
        for stage_index in range(start_stage, 3):
            active_stage = stage_order[stage_index]
            first_iteration = completed_iteration if active_stage == stage else 0
            for iteration in range(first_iteration, self.config.iterations):
                tic = perf_counter()
                batch_seed = self.seed + stage_index * 10_000_000 + iteration * 10
                losses: dict[str, float]
                if active_stage == "embed":
                    batch = self._batch(normalized, batch_seed)
                    latent = self.model.embedder(batch)
                    reconstructed = self.model.recovery(latent)
                    reconstruction = F.mse_loss(reconstructed, batch)
                    objective = 10.0 * torch.sqrt(reconstruction.clamp_min(1e-12))
                    self._zero_all_gradients()
                    objective.backward()
                    self.opt_embed_pretrain.step()
                    losses = {"reconstruction_loss": float(reconstruction.detach().cpu())}
                elif active_stage == "supervisor":
                    batch = self._batch(normalized, batch_seed)
                    with torch.no_grad():
                        latent = self.model.embedder(batch)
                    predicted = self.model.supervisor(latent)
                    supervised = self._supervised_loss(latent, predicted)
                    self._zero_all_gradients()
                    supervised.backward()
                    self.opt_supervisor.step()
                    losses = {"supervisor_loss": float(supervised.detach().cpu())}
                else:
                    last_generator = torch.tensor(float("nan"), device=self.device)
                    last_supervised = torch.tensor(float("nan"), device=self.device)
                    last_reconstruction = torch.tensor(float("nan"), device=self.device)
                    for generator_update in range(2):
                        joint_seed = batch_seed + generator_update
                        batch = self._batch(normalized, joint_seed)
                        noise = self._uniform_noise(len(batch), joint_seed + 1_000_000)
                        with torch.no_grad():
                            real_latent = self.model.embedder(batch)
                        raw_fake = self.model.generator(noise)
                        fake_latent = self.model.supervisor(raw_fake)
                        supervised_fake = self.model.supervisor(real_latent)
                        generated = self.model.recovery(fake_latent)
                        fake_logits = self.model.discriminator(fake_latent)
                        raw_fake_logits = self.model.discriminator(raw_fake)
                        adversarial = F.binary_cross_entropy_with_logits(
                            fake_logits, torch.ones_like(fake_logits)
                        )
                        adversarial_raw = F.binary_cross_entropy_with_logits(
                            raw_fake_logits, torch.ones_like(raw_fake_logits)
                        )
                        supervised = self._supervised_loss(real_latent, supervised_fake)
                        generated_variance, generated_mean = torch.var_mean(
                            generated, dim=0, unbiased=False
                        )
                        real_variance, real_mean = torch.var_mean(batch, dim=0, unbiased=False)
                        moment = torch.mean(
                            torch.abs(
                                torch.sqrt(generated_variance + 1e-6)
                                - torch.sqrt(real_variance + 1e-6)
                            )
                        ) + torch.mean(torch.abs(generated_mean - real_mean))
                        generator_loss = (
                            adversarial
                            + self.config.gamma * adversarial_raw
                            + 100.0 * torch.sqrt(supervised.clamp_min(1e-12))
                            + 100.0 * moment
                        )
                        self._zero_all_gradients()
                        generator_loss.backward()
                        self.opt_generator.step()

                        embed_latent = self.model.embedder(batch)
                        reconstructed = self.model.recovery(embed_latent)
                        predicted_latent = self.model.supervisor(embed_latent)
                        reconstruction = F.mse_loss(reconstructed, batch)
                        embed_supervised = self._supervised_loss(embed_latent, predicted_latent)
                        embed_loss = (
                            10.0 * torch.sqrt(reconstruction.clamp_min(1e-12))
                            + 0.1 * embed_supervised
                        )
                        self._zero_all_gradients()
                        embed_loss.backward()
                        self.opt_embed_joint.step()
                        last_generator = generator_loss.detach()
                        last_supervised = supervised.detach()
                        last_reconstruction = reconstruction.detach()

                    discriminator_batch = self._batch(normalized, batch_seed + 2)
                    discriminator_noise = self._uniform_noise(
                        len(discriminator_batch), batch_seed + 1_000_002
                    )
                    with torch.no_grad():
                        real_latent = self.model.embedder(discriminator_batch)
                        raw_fake = self.model.generator(discriminator_noise)
                        fake_latent = self.model.supervisor(raw_fake)
                    real_logits = self.model.discriminator(real_latent)
                    fake_logits = self.model.discriminator(fake_latent)
                    raw_fake_logits = self.model.discriminator(raw_fake)
                    discriminator_loss = (
                        F.binary_cross_entropy_with_logits(
                            real_logits, torch.ones_like(real_logits)
                        )
                        + F.binary_cross_entropy_with_logits(
                            fake_logits, torch.zeros_like(fake_logits)
                        )
                        + self.config.gamma
                        * F.binary_cross_entropy_with_logits(
                            raw_fake_logits, torch.zeros_like(raw_fake_logits)
                        )
                    )
                    if float(discriminator_loss.detach().cpu()) > self.config.discriminator_threshold:
                        self._zero_all_gradients()
                        discriminator_loss.backward()
                        self.opt_discriminator.step()
                    losses = {
                        "reconstruction_loss": float(last_reconstruction.cpu()),
                        "supervisor_loss": float(last_supervised.cpu()),
                        "discriminator_loss": float(discriminator_loss.detach().cpu()),
                        "generator_loss": float(last_generator.cpu()),
                    }

                if not all(math.isfinite(value) for value in losses.values()):
                    raise FloatingPointError(
                        f"non-finite TimeGAN loss at {active_stage} iteration {iteration + 1}"
                    )
                elapsed += perf_counter() - tic
                completed = iteration + 1
                if (
                    completed % self.config.checkpoint_interval == 0
                    or completed == self.config.iterations
                ):
                    self._record_checkpoint(
                        checkpoint,
                        active_stage,
                        completed,
                        elapsed,
                        losses,
                        progress_callback,
                    )
            completed_iteration = 0
            stage = active_stage
        self._checkpoint(checkpoint, "complete", self.config.iterations, elapsed)
        return elapsed

    def sample(self, n: int, sample_seed: int) -> np.ndarray:
        if n <= 0:
            raise ValueError("n must be positive")
        if self.minimum is None or self.value_range is None:
            raise RuntimeError("fit or checkpoint restore is required before sample")
        self.model.eval()
        with torch.no_grad():
            noise = self._uniform_noise(n, sample_seed)
            generated_latent = self.model.supervisor(self.model.generator(noise))
            generated = self.model.recovery(generated_latent)
            sequence = generated * self.value_range + self.minimum
            return self._to_windows(sequence).cpu().numpy().astype(np.float32)


def _sinusoidal_embedding(t: torch.Tensor, width: int) -> torch.Tensor:
    half = width // 2
    exponent = torch.arange(half, device=t.device, dtype=torch.float32) / max(half - 1, 1)
    frequencies = torch.exp(-math.log(10_000.0) * exponent)
    values = t.float().unsqueeze(1) * frequencies.unsqueeze(0)
    embedding = torch.cat([torch.sin(values), torch.cos(values)], dim=1)
    return embedding if width % 2 == 0 else F.pad(embedding, (0, 1))


def _diffwave_conv1d(*args, **kwargs) -> nn.Conv1d:
    layer = nn.Conv1d(*args, **kwargs)
    nn.init.kaiming_normal_(layer.weight)
    return layer


class DiffWaveResidualBlock1D(nn.Module):
    """Unconditional DiffWave gated residual block for multichannel signals."""

    def __init__(self, width: int, dilation: int, time_width: int):
        super().__init__()
        self.dilated_conv = _diffwave_conv1d(
            width,
            2 * width,
            kernel_size=3,
            padding=dilation,
            dilation=dilation,
        )
        self.diffusion_projection = nn.Linear(time_width, width)
        self.output_projection = _diffwave_conv1d(width, 2 * width, kernel_size=1)

    def forward(
        self,
        x: torch.Tensor,
        time_embedding: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        projected_time = self.diffusion_projection(time_embedding).unsqueeze(-1)
        gate, value = torch.chunk(self.dilated_conv(x + projected_time), 2, dim=1)
        activated = torch.sigmoid(gate) * torch.tanh(value)
        residual, skip = torch.chunk(self.output_projection(activated), 2, dim=1)
        return (x + residual) / math.sqrt(2.0), skip


class DDPMDenoiser1D(nn.Module):
    """DiffWave-style unconditional epsilon predictor for 3-channel PU windows."""

    def __init__(
        self,
        channels: int,
        width: int,
        residual_layers: int,
        dilation_cycle_length: int,
    ):
        super().__init__()
        if residual_layers <= 0:
            raise ValueError("residual_layers must be positive")
        if dilation_cycle_length <= 0:
            raise ValueError("dilation_cycle_length must be positive")
        self.time_width = 512
        self.time_mlp = nn.Sequential(
            nn.Linear(128, self.time_width),
            nn.SiLU(),
            nn.Linear(self.time_width, self.time_width),
            nn.SiLU(),
        )
        self.input = _diffwave_conv1d(channels, width, kernel_size=1)
        self.blocks = nn.ModuleList(
            [
                DiffWaveResidualBlock1D(
                    width,
                    dilation=2 ** (index % dilation_cycle_length),
                    time_width=self.time_width,
                )
                for index in range(residual_layers)
            ]
        )
        self.skip_projection = _diffwave_conv1d(width, width, kernel_size=1)
        self.output_projection = _diffwave_conv1d(width, channels, kernel_size=1)
        nn.init.zeros_(self.output_projection.weight)

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        te = self.time_mlp(_sinusoidal_embedding(t, 128))
        h = F.relu(self.input(x))
        skip_sum: torch.Tensor | None = None
        for block in self.blocks:
            h, skip = block(h, te)
            skip_sum = skip if skip_sum is None else skip_sum + skip
        if skip_sum is None:
            raise RuntimeError("DDPM denoiser has no residual blocks")
        h = skip_sum / math.sqrt(len(self.blocks))
        return self.output_projection(F.relu(self.skip_projection(h)))


def linear_beta_schedule(diffusion_steps: int, device: torch.device) -> torch.Tensor:
    """Return the DDPM linear schedule used by Ho et al. (2020)."""
    if diffusion_steps < 2:
        raise ValueError("diffusion_steps must be at least 2")
    return torch.linspace(1e-4, 2e-2, diffusion_steps, device=device)


class DDPMTrainer:
    def __init__(
        self,
        channels: int,
        length: int,
        config: DDPMConfig,
        seed: int,
        device_name: DeviceName = "cpu",
    ):
        if length != 2048:
            raise ValueError(f"DDPM baseline is registered for 2048-sample PU windows, got {length}")
        if not 0.0 <= config.ema_decay < 1.0:
            raise ValueError("ema_decay must lie in [0, 1)")
        if config.warmup_steps <= 0:
            raise ValueError("warmup_steps must be positive")
        if config.gradient_clip_norm <= 0:
            raise ValueError("gradient_clip_norm must be positive")
        self.config = config
        self.seed = seed
        if device_name == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested but is unavailable")
        self.device = torch.device(device_name)
        torch.manual_seed(seed)
        self.model = DDPMDenoiser1D(
            channels,
            config.hidden_channels,
            config.residual_layers,
            config.dilation_cycle_length,
        ).to(self.device)
        self.ema_model = deepcopy(self.model).to(self.device).eval()
        self.ema_model.requires_grad_(False)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=config.learning_rate)
        beta = linear_beta_schedule(config.diffusion_steps, self.device)
        self.beta = beta
        self.alpha = 1.0 - beta
        self.alpha_bar = torch.cumprod(self.alpha, dim=0)
        self.alpha_bar_previous = torch.cat(
            [torch.ones(1, device=self.device), self.alpha_bar[:-1]], dim=0
        )
        self.posterior_variance = self.beta * (
            1.0 - self.alpha_bar_previous
        ) / (1.0 - self.alpha_bar)
        self.posterior_mean_coefficient_x0 = (
            self.beta * torch.sqrt(self.alpha_bar_previous) / (1.0 - self.alpha_bar)
        )
        self.posterior_mean_coefficient_xt = (
            (1.0 - self.alpha_bar_previous)
            * torch.sqrt(self.alpha)
            / (1.0 - self.alpha_bar)
        )
        if config.reverse_variance == "fixed_large":
            self.reverse_variance = self.beta
        elif config.reverse_variance == "fixed_small":
            self.reverse_variance = self.posterior_variance
        else:
            raise ValueError(f"unknown DDPM reverse variance: {config.reverse_variance}")
        self.mean: torch.Tensor | None = None
        self.std: torch.Tensor | None = None
        self.history: list[dict[str, float | int | str]] = []
        self.optimizer_step = 0

    @torch.no_grad()
    def _update_ema(self) -> None:
        decay = 0.0 if self.optimizer_step == 0 else self.config.ema_decay
        for ema_parameter, parameter in zip(self.ema_model.parameters(), self.model.parameters()):
            ema_parameter.mul_(decay).add_(parameter, alpha=1.0 - decay)
        for ema_buffer, buffer in zip(self.ema_model.buffers(), self.model.buffers()):
            ema_buffer.copy_(buffer)

    def _checkpoint(self, path: Path, completed_epoch: int, elapsed_seconds: float) -> None:
        if self.mean is None or self.std is None:
            raise RuntimeError("normalization state is unavailable")
        _atomic_torch_save(
            {
                "algorithm": "ddpm_diffwave_1d_v5",
                "config": asdict(self.config),
                "seed": self.seed,
                "completed_epoch": completed_epoch,
                "elapsed_seconds": elapsed_seconds,
                "model": self.model.state_dict(),
                "ema_model": self.ema_model.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "optimizer_step": self.optimizer_step,
                "mean": self.mean.cpu(),
                "std": self.std.cpu(),
                "history": self.history,
            },
            path,
        )

    def _restore(self, path: Path) -> tuple[int, float]:
        state = torch.load(path, map_location=self.device, weights_only=False)
        if state.get("algorithm") != "ddpm_diffwave_1d_v5" or state.get("config") != asdict(self.config):
            raise RuntimeError(f"checkpoint configuration mismatch: {path}")
        self.model.load_state_dict(state["model"])
        self.ema_model.load_state_dict(state["ema_model"])
        self.optimizer.load_state_dict(state["optimizer"])
        self.optimizer_step = int(state["optimizer_step"])
        self.mean = state["mean"].to(self.device)
        self.std = state["std"].to(self.device)
        self.history = list(state.get("history", []))
        return int(state["completed_epoch"]), float(state["elapsed_seconds"])

    def training_history(self) -> list[dict[str, float | int | str]]:
        """Return the complete checkpointed epoch-level optimization record."""
        return [dict(row) for row in self.history]

    def fit(
        self,
        x: np.ndarray,
        checkpoint: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> float:
        if x.ndim != 3:
            raise ValueError(f"expected (windows, channels, samples), got {x.shape}")
        if not np.isfinite(x).all():
            raise ValueError("DDPM cannot train on non-finite windows")
        x_tensor = torch.as_tensor(x, dtype=torch.float32, device=self.device)
        start_epoch, elapsed = 0, 0.0
        if checkpoint.exists():
            start_epoch, elapsed = self._restore(checkpoint)
        else:
            self.mean = x_tensor.mean(dim=(0, 2), keepdim=True)
            self.std = x_tensor.std(dim=(0, 2), keepdim=True).clamp_min(1e-6)
        if self.mean is None or self.std is None:
            raise RuntimeError("missing normalization state")
        xn = (x_tensor - self.mean) / self.std
        for epoch in range(start_epoch, self.config.epochs):
            tic = perf_counter()
            noise_losses: list[float] = []
            for batch_index, idx in enumerate(_batch_indices(len(xn), self.config.batch_size, self.seed + epoch)):
                batch = xn[idx.to(self.device)]
                generator = torch.Generator(device=self.device).manual_seed(self.seed + epoch * 10_000 + batch_index)
                t = torch.randint(0, self.config.diffusion_steps, (len(batch),), generator=generator, device=self.device)
                noise = torch.randn(tuple(batch.shape), generator=generator, device=self.device)
                alpha_bar_t = self.alpha_bar[t].view(-1, 1, 1)
                noised = torch.sqrt(alpha_bar_t) * batch + torch.sqrt(1.0 - alpha_bar_t) * noise
                predicted = self.model(noised, t)
                loss = F.mse_loss(predicted, noise)
                if not torch.isfinite(loss):
                    raise FloatingPointError(f"non-finite DDPM noise-prediction loss at epoch {epoch}")
                self.optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), max_norm=self.config.gradient_clip_norm
                )
                learning_rate_scale = min(
                    (self.optimizer_step + 1) / self.config.warmup_steps, 1.0
                )
                for group in self.optimizer.param_groups:
                    group["lr"] = self.config.learning_rate * learning_rate_scale
                self.optimizer.step()
                self._update_ema()
                self.optimizer_step += 1
                noise_losses.append(float(loss.detach().cpu()))
            elapsed += perf_counter() - tic
            self.history.append({"stage": "ddpm", "epoch": epoch + 1, "noise_prediction_mse": float(np.mean(noise_losses))})
            self._checkpoint(checkpoint, epoch + 1, elapsed)
            if progress_callback is not None:
                progress_callback(
                    {
                        **self.history[-1],
                        "completed": epoch + 1,
                        "total": self.config.epochs,
                        "elapsed_seconds": elapsed,
                    }
                )
        return elapsed

    def sample(self, n: int, sample_seed: int) -> np.ndarray:
        if n <= 0:
            raise ValueError("n must be positive")
        if self.mean is None or self.std is None:
            raise RuntimeError("fit or checkpoint restore is required before sample")
        self.model.eval()
        with torch.no_grad():
            x = _seeded_randn((n, self.mean.shape[1], 2048), sample_seed, self.device)
            for step in range(self.config.diffusion_steps - 1, -1, -1):
                t = torch.full((n,), step, dtype=torch.long, device=self.device)
                predicted_noise = self.ema_model(x, t)
                alpha_bar = self.alpha_bar[step]
                predicted_x0 = (
                    x - torch.sqrt(1.0 - alpha_bar) * predicted_noise
                ) / torch.sqrt(alpha_bar)
                mean = (
                    self.posterior_mean_coefficient_x0[step] * predicted_x0
                    + self.posterior_mean_coefficient_xt[step] * x
                )
                if step > 0:
                    x = mean + torch.sqrt(self.reverse_variance[step]) * _seeded_randn(
                        tuple(x.shape), sample_seed + step, self.device
                    )
                else:
                    x = mean
            return (x * self.std + self.mean).cpu().numpy().astype(np.float32)


def make_trainer(
    method: str,
    channels: int,
    length: int,
    seed: int,
    timegan_config: TimeGANConfig,
    ddpm_config: DDPMConfig,
    device_name: DeviceName = "cpu",
) -> TimeGANTrainer | DDPMTrainer:
    if method == "timegan":
        return TimeGANTrainer(channels, length, timegan_config, seed, device_name=device_name)
    if method == "ddpm":
        return DDPMTrainer(channels, length, ddpm_config, seed, device_name=device_name)
    raise ValueError(f"unknown trained baseline: {method}")
