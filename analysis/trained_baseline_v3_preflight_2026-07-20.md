# PU trained-baseline v3 preflight

Status: pipeline mechanics passed, but the v3 fidelity audit invalidated its
DDPM configuration; formal results are not yet available.

## Authorized scope

On 2026-07-20 the user explicitly authorized new training for the experiment-completion round. This authorization does not include deletion of existing data or new LLM API requests. The formal target remains PU `N09_M07_F10`, TimeGAN and 1-D DDPM, full-fold and few-shot-only generator fitting, `n_real={5,10,25}`, 20 synthetic windows per class, 40 paired seeds, and the frozen CNN downstream protocol.

## Corrected execution matrix

The v2 runner nested `n_real` outside the generator fit and therefore retrained an identical full-fold generator separately at 5, 10, and 25 shots. V3 removes that redundant optimization: a full-fold model and sampled pool are identified by `(method, seed, class)` and reused across the three downstream shot levels. Few-shot generators remain distinct for each `(method, n_real, seed, class)`. This preserves all registered downstream cells while reducing the class-level fitting count from 1,200 to 960.

The formal matrix contains 480 downstream cells, 320 independently seeded pools, and 960 class-level generator fits. Full-fold reuse is recorded in the run manifest and is asserted by the smoke audit.

## Runtime contract

- Each TimeGAN stage and DDPM epoch writes an atomic checkpoint before emitting progress.
- `heartbeat.jsonl` and `runner.log` are append-only, flushed, and `fsync`ed after every checkpointed epoch.
- `SIGINT` and `SIGTERM` request a stop at the next durable epoch boundary.
- Resume restores model, optimizer, normalization, elapsed time, and checkpointed history.
- A deterministic test interrupts both methods after the first epoch; resumed samples are elementwise identical to uninterrupted samples (`2 passed`).
- The output-root advisory lock prevents a second writer from appending to the same formal ledgers.

## Smoke evidence

`breeze/results/trained_baselines_2026-07-20/smoke_v4_final/` completed all 12 wiring cells (two methods, two training modes, three shot levels, one seed). It produced 12 unique downstream rows, 24 unique class-training cost rows, and 48 unique dynamics rows. For each method, the three full-fold downstream rows reference one identical pool path and SHA-256. These values are smoke-only and prohibited from manuscript claims.

After the final manifest extension, `breeze/results/trained_baselines_2026-07-20/smoke_v5_manifest/` completed four targeted wiring cells and verified four exact PU array hashes, the project interpreter, PyTorch/NumPy versions, CPU-only execution, and model parameter counts (TimeGAN adaptation: 39,364; DDPM-1D: 75,811).

## Storage and device gate

PyTorch 2.12.1 reports `mps_available=false`; formal execution is therefore CPU-only. The complete v4 smoke root occupies 29 MiB. Scaling its checkpoint/pool footprint to 960 class-level training units gives an approximate structured-output requirement near 1.2 GiB, before filesystem and system-swap margin. Available system space was approximately 4.4 GiB after an unrelated archived gate-ablation process completed. Consequently, v3 begins with a single formal seed to measure actual time and bytes; the full queue may continue only if the measured projection retains a safe system-space floor. No scientific setting will be reduced to fit storage.

## Claim boundary

Neither smoke output nor an incomplete formal root is evidence. TimeGAN/DDPM may enter the paper only after all expected rows, pools, costs, dynamics, failures, hashes, physical metrics, and paired downstream statistics pass the completeness freeze.

## Formal progress audit

The first complete formal generator cell is TimeGAN/full-fold/seed 0. All three
class checkpoints are `stage=complete`; each contains 320 epoch records, giving
960 finite dynamics rows. Class-level fit wall times are 1702.665, 1593.773,
and 1930.596 seconds (5227.035 seconds total). Checkpointed epoch-compute time
totals 5220.582 seconds; the 6.452-second difference is fit-call overhead such
as checkpoint/progress IO. The cost table therefore uses
`training_cost.wall_seconds`; the legacy downstream column
`generator_train_seconds` is interpreted only as epoch-compute time.

The sampled pool has shape `(60, 3, 2048)`, finite values, 20 windows per
class, and SHA-256
`7509785ea9fa62e1ac710ea82f9e5ecfe411aa0e2bcaaa165abf54ba1adb767a`.
The n=5/10/25 downstream rows reference that same path and hash, proving the
registered full-fold reuse policy for this seed. The three single-seed
downstream values are not aggregated or promoted to manuscript evidence.

Raw TimeGAN dynamics are not uniformly benign: class 0 and class 2 show
discriminator loss approaching zero while generator loss rises later in joint
training, whereas class 1 does not show the same trajectory. This is preserved
as a descriptive instability signal; no rescue tuning is authorized. TimeGAN
few-shot seed 0 has also completed all three shot levels. A subsequent
paper-to-code audit also showed that the symmetric convolutional
embedder/recovery do not satisfy the causal-ordering condition stated for
TimeGAN alternatives. The accurate implementation name is therefore
“ConvTimeGAN-style 1-D adaptation,” not an original-TimeGAN reproduction.

The TimeGAN few-shot three-class fit wall times are 33.383 seconds at n=5,
35.973 seconds at n=10, and 74.160 seconds at n=25. Together with the full-fold
pool, seed 0 therefore has four distinct TimeGAN pools and six downstream rows;
the three full-fold rows alone share one pool. All 12 TimeGAN class checkpoints
are complete, all 3,840 relevant dynamics values are finite, and all four pools
contain exactly 20 finite windows per class. These single-seed outputs remain
incomplete formal evidence.

DDPM/full-fold seed 0 was safely stopped at its epoch-110 atomic checkpoint
after a schedule audit found a hard endpoint mismatch. With 50 linearly spaced
betas from `1e-4` to `2e-2`, terminal `alpha_bar` is 0.6029516, so the forward
process retains substantial signal even though reverse sampling starts from a
standard Gaussian. The checkpoint and logs are preserved, but v3 DDPM must not
be resumed or reported. A corrected implementation requires a new source hash,
a new output root, the canonical 1000-step schedule (terminal `alpha_bar`
0.00004036), and posterior-transition tests. See
`analysis/trained_baseline_fidelity_audit_2026-07-20.md`.

## Corrected DDPM v4 smoke

The independent v4 implementation uses the canonical 1,000-step linear
schedule and the closed-form posterior reverse transition. Seven focused
schedule, posterior, loss-summary, and checkpoint-resume tests pass. The
formal runner refuses a non-1,000-step DDPM schedule; the same schedule is also
required in smoke mode so the actual reverse path is exercised.

`smoke_v6_ddpm_posterior` completed a deliberately tiny one-epoch wiring run
with two samples per class. The strict completeness audit reports one unique
finite `(6, 3, 2048)` pool, one downstream row, three complete class
checkpoints/cost rows, three finite dynamics rows, zero failure rows, exact
source hashes, and terminal `alpha_bar=4.0358303522e-05`. Its performance
value is smoke-only and prohibited from all manuscript claims. The v4
algorithmic path is now mechanically valid; model-capacity and training-budget
provenance remain open before a full scientific cell can start.
