# PU trained-baseline v3 preflight

Status: pipeline preflight passed; formal results are not yet available.

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
