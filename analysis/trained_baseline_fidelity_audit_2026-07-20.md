# Trained-baseline implementation fidelity audit

Date: 2026-07-20
Scope: PU formal trained baselines only; no LLM API use; no frozen result was modified.

## Decision

`formal_pu_v3` is an incomplete development run and must not enter a paper
claim. Its completed TimeGAN branch is retained as an auditable
**ConvTimeGAN-style 1-D adaptation**, not as a faithful reproduction of the
original TimeGAN implementation. Its DDPM branch is invalidated because the
registered 50-step forward process does not approach the Gaussian prior from
which reverse sampling starts. The DDPM runner was stopped at the next durable
epoch boundary and must not be resumed from the v3 checkpoint.

Any corrected implementation must use a new output root and a new source hash.
No smoke, single-seed, partial-checkpoint, or v3 DDPM value may be reported as
experimental evidence.

## TimeGAN audit

Primary reference: Yoon, Jarrett, and van der Schaar, *Time-series Generative
Adversarial Networks*, NeurIPS 2019. The paper defines embedding/recovery,
generator, supervisor, and discriminator components, combines supervised and
adversarial objectives, and states that alternative sequence models such as
temporal convolutions are permissible provided they respect causal temporal
ordering. It reports a recurrent implementation and a bidirectional recurrent
discriminator.

The paper author's standalone repository was frozen for comparison at commit
`8f6181cb9b9d2fa0c930cd902411d9ac8a308e07` and declares Apache License 2.0.
Its defaults are GRU, hidden width 24, three layers, 50,000 training
iterations, and batch size 128; the repository explicitly says these network
parameters should be optimized for different datasets. The local v3 values
were not an implementation of those defaults and had no completed train-only
selection audit, reinforcing the adaptation-only label.

The local implementation preserves the four named components, staged
embedding/supervisor/joint optimization, an autoregressive latent GRU, a
supervised next-step loss, adversarial loss, reconstruction loss, and moment
matching. It differs materially from the reference implementation:

| Item | Original TimeGAN | Local v3 implementation | Consequence |
|---|---|---|---|
| Embedder/recovery | recurrent reference implementation; alternatives must preserve causal order | symmetric-padded strided `Conv1d` plus `ConvTranspose1d` | receptive fields are not causally ordered |
| Discriminator | bidirectional recurrent implementation | unidirectional GRU with time-mean logit | implementation adaptation |
| Joint adversarial terms | reference objective includes the specified latent adversarial paths | one supervised-generator latent path is used | objective is TimeGAN-style, not an exact reproduction |
| Sequence resolution | native temporal sequence | 2048 samples compressed to 128 latent steps | engineering adaptation for long 1-D windows |
| Conditioning | multivariate time series, not class-conditional | one unconditional model per class | valid experimental conditioning choice, but different implementation |

Therefore the accurate label for the completed v3 branch is
“ConvTimeGAN-style 1-D adaptation.” It can describe engineering observations
and timing only after the entire registered matrix is complete, but it cannot
be cited as an original-TimeGAN reproduction. A paper claim that explicitly
requires “TimeGAN” needs either the official recurrent implementation or a
causally ordered convolutional implementation whose remaining objective
differences are disclosed and preregistered.

The completed seed-0 branch remains incomplete evidence: all 12 class fits are
checkpoint-complete and all recorded losses are finite, but class 0 and class
2 show discriminator-collapse-like trajectories. No rescue tuning is allowed.

### Corrected recurrent TimeGAN v5

The corrected implementation follows the author's five recurrent networks and
official defaults: GRU, hidden width 24, three layers (two in the supervisor),
50,000 iterations per training stage, batch size 128, learning rate `1e-3`,
`gamma=1`, and the discriminator update threshold `D_loss>0.15`. It implements
both latent adversarial paths, next-step supervised loss, the published
`100*sqrt(L_S)` and `100*L_V` terms, two generator/embedder updates per joint
iteration, and featurewise MinMax normalization.

To preserve the full 2048-by-3 PU window without the v3 noncausal convolution,
each consecutive 16-sample, three-channel block is reshaped losslessly into one
48-dimensional step. The resulting 128-by-48 sequence is exactly invertible;
no filtering, interpolation, or learned compression is introduced. The method
is accurately named **TimeGAN with a lossless block-sequence 1-D adapter**,
because the PyTorch framework and PU representation are adaptations even though
the network roles and objective follow the author code.

`smoke_v10_timegan_faithful_mps` passed its version-specific end-to-end audit.
After both implementations were finalized, the combined
`smoke_v11_faithful_combined_mps` superseded the separate v9/v10 checks and
passed against the final common source hash: six complete checkpoints, twelve
finite dynamics rows, two six-window pools, two downstream rows, zero failures,
and exact source hashes. This one-iteration/one-epoch smoke is prohibited from
scientific claims.

### Cost gate

The non-reportable `cost_probe_timegan_100iter_fullfold_mps` used the actual
full-fold class-0 data and batch size 128. Its atomically complete checkpoint
measured 297.438848 seconds for 100 iterations in each stage: 22.141455 seconds
for embedding, 10.015043 seconds for supervisor, and 265.282350 seconds for
joint training. Linear projection of the frozen 50,000-iteration default is
148,719 seconds (41.31 hours) per class model, excluding checkpoint overhead.
The registered grid contains 480 class models, implying roughly 826 serial
days on the available Apple MPS device. Even a one-fixed-pool-per-regime design
requires 12 class models per method, or about 20.7 serial days for TimeGAN
alone. Therefore the 40-seed formal grid was not started. A partial class-1
cost-probe checkpoint is retained but must not enter any result or claim.

## DDPM audit and invalidation

Primary reference: Ho, Jain, and Abbeel, *Denoising Diffusion Probabilistic
Models*, NeurIPS 2020; the authors' public implementation uses the linear beta
schedule, epsilon-prediction objective, posterior quantities, and reverse
sampling from terminal Gaussian noise.

The authors' repository was frozen for formula comparison at commit
`1e0dceb3b3495bbe19116a5e1b3596cd0706c543`. No license file is present in the
repository root, so no source was copied into BREEZE; the local PyTorch code is
an independent implementation of the published equations.

The local v3 implementation used 50 diffusion steps with
`beta_1=1e-4` and `beta_T=2e-2`, sampled training timesteps uniformly, optimized
epsilon-prediction MSE, and initialized reverse sampling from `N(0,I)`.
Numerical recomputation gives:

| Schedule | terminal alpha product | retained signal standard deviation | injected noise standard deviation | terminal SNR |
|---|---:|---:|---:|---:|
| v3: 50 linear steps | 0.6029515862 | 0.7764996 | 0.6301178 | 1.5185846 |
| canonical: 1000 linear steps | 0.0000403583 | 0.0063528 | 0.9999798 | 0.0000404 |

The v3 terminal training distribution retains strong signal and is not close
to the standard Gaussian used as the sampling start. This is an endpoint
distribution mismatch, not merely an unfavorable hyperparameter or a weak
result. Consequently:

- the v3 DDPM run was stopped after its atomically saved epoch-110 checkpoint;
- its checkpoint reports 4,379.188 seconds and 110 finite epoch-loss records,
  with final noise-prediction MSE 0.258365;
- no DDPM pool, downstream row, or cost row was completed;
- the partial checkpoint and append-only log are preserved for audit only;
- resuming this configuration or reporting its numbers is prohibited.

## Corrected DDPM--DiffWave-style v5 protocol

The modality-specific denoiser and training budget were frozen from two
primary waveform/vibration sources before a formal run was started:

- LMNT's Apache-2.0 DiffWave implementation, frozen at commit
  `0594106093b8d8c444de8bd8cd26482f653c569f`, supplies the unconditional
  waveform denoiser defaults: 30 gated residual/skip layers, 64 residual
  channels, dilation cycle 10, batch size 16, and learning rate `2e-4`.
- Yi et al.'s vibration DDPM study uses length-2048 bearing windows and reports
  200 epochs (batch size 10 and 3,000 diffusion steps). The local protocol uses
  its 200-epoch modality-specific budget, but retains batch 16 from the chosen
  DiffWave architecture and the canonical 1,000-step DDPM chain already frozen
  above. These choices are declared rather than presented as an exact TSDM
  reproduction.

The accurate method name is therefore **DDPM--DiffWave-style 1-D adaptation**.
It has 2,308,995 trainable parameters for the three-channel PU input. Apple MPS
is an execution device only and is recorded in each manifest; seeds remain
explicit through device-local PyTorch generators.

The fresh `smoke_v9_ddpm_diffwave_mps` root completed a genuine 1,000-step
reverse chain for all three classes. The final-source combined v11 smoke then
repeated that chain alongside TimeGAN. Its strict audit reports terminal alpha
product `4.0358303522e-5`, exact source hashes, and no failures. Both are wiring
checks and are prohibited from all scientific claims.

## Formal protocol requirements

1. Use a new root (`formal_pu_v4` or a more specific new name); v3 remains
   immutable development evidence.
2. Train with the canonical 1000-step linear beta schedule
   (`1e-4` to `2e-2`) so the terminal forward distribution is consistent with
   a Gaussian reverse-process start.
3. Implement the published epsilon-parameterized reverse mean and the authors'
   CIFAR default `fixedlarge` variance, with no image-specific clipping of
   standardized vibration signals.
4. Use the authors' Adam defaults that transfer across modalities: learning
   rate `2e-4`, 5,000-step warmup, gradient clipping at 1.0, EMA decay 0.9999,
   and EMA weights for sampling. The separately sourced 1-D denoiser, batch,
   and epoch settings above are frozen before formal execution.
5. If accelerated inference is later desired, specify and cite a distinct
   sampler (for example, DDIM) before running it. Do not silently rescale the
   50-step beta schedule.
6. Add numerical schedule, posterior, deterministic resume, shape, finite,
   source-hash, and pool-hash tests before a single-cell smoke.
7. Measure one complete class cell before projecting the 40-seed wall time and
   storage. Changing the number of training epochs or model capacity requires
   a separate evidence-based preregistration; it cannot be done to rescue cost
   or performance.
8. Describe the model as a “DDPM--DiffWave-style 1-D adaptation,” not as an
   exact reproduction of an image-domain U-Net DDPM or TSDM.

## Source links

- TimeGAN paper: <https://proceedings.neurips.cc/paper_files/paper/2019/file/c9efe5f26cd17ba6216bbe2a7d26d490-Paper.pdf>
- TimeGAN author's repository: <https://github.com/jsyoon0823/TimeGAN/tree/8f6181cb9b9d2fa0c930cd902411d9ac8a308e07>
- DDPM paper: <https://proceedings.neurips.cc/paper/2020/hash/4c5bcfec8584af0d967f1ab10179ca4b-Abstract.html>
- DDPM authors' repository: <https://github.com/hojonathanho/diffusion/tree/1e0dceb3b3495bbe19116a5e1b3596cd0706c543>
- DiffWave paper: <https://openreview.net/forum?id=a-xFK8Ymz5J>
- DiffWave author's repository: <https://github.com/lmnt-com/diffwave/tree/0594106093b8d8c444de8bd8cd26482f653c569f>
- Yi et al., vibration TSDM: <https://arxiv.org/abs/2312.07981>
