# Machine-Tool Synthetic Pool Protocol

Date: 2026-07-04

This protocol is a design document only. It does not report machine-tool
synthetic augmentation results because no audited machine-tool synthetic pool
exists in the workspace.

## Preconditions

Required before generating machine-tool synthetic data:

1. Class mapping for raw labels `1/2/3`.
   - Local documentation says the dataset contains normal machining,
     lead-screw anomaly, and base imbalance.
   - Current local evidence still supports only anonymous file-prefix labels
     `MT-1/MT-2/MT-3`, because the prefix-to-state mapping is not confirmed.
   - Without physical semantics, prompts must not name fault types.
2. Machine operating metadata if any physics-specific absolute-frequency claim
   is desired.
   - The acquisition sampling rate is available: 4000 Hz.
   - Machine geometry, spindle speed, and state-prefix mapping are not available
     in the audited workspace metadata, so verifier gates remain generic
     train-calibrated constraints rather than BPFO/BPFI or speed-order gates.
3. Generator configuration and API credentials.
   - Each generated slot must record model name, prompt hash, seed, round, and
     verifier certificate.

## Generator-Agnostic Prompt Scope

Until class semantics are known, prompts should describe only:

- target anonymous class ID;
- four-channel schema: `X`, `Y`, `Z`, `Current`;
- acquisition sampling rate: 4000 Hz;
- BREEZE window length: 2048 samples, equal to 0.512 s;
- BREEZE stride: 1024 samples, equal to 0.256 s;
- class-conditional train-supported ranges provided by the verifier report;
- no bearing BPFO/BPFI, because machine-tool bearing geometry and speed are
  unavailable.

## Verifier

Use `breeze/src/mt_verifier.py` and `breeze/runs/mt_verifier_c90.json`.

Hard gates:

- sanity: shape, finite values, non-constant channels, no long repeated
  segments;
- stats_union: time statistics plus robust structure-domain support;
- soft_spectrum: normalized overlapping PSD-band coordinate or ellipsoid
  support;
- psd_w1: per-channel normalized PSD-CDF W1 support.

Certificate-only scores:

- diversity embedding norm;
- real-real NN reference thresholds.

## Closed-Loop Generation

For each class:

1. Generate a slot with `K=0`.
2. Verify with the machine-tool verifier.
3. If rejected, build a structured feedback report listing only the failed
   train-supported constraints.
4. Regenerate for at most `K=3` rounds.
5. Admit only candidates that pass all hard gates and diversity admission.
6. Record every attempt in a resumable JSON/CSV schema:
   `sample_id`, `class`, `round`, `prompt_hash`, `model`, `seed`,
   `output_path`, `gate_scores`, `fail_reasons`, `accepted`.

## Downstream Evaluation

Only after an audited synthetic pool exists:

- use `breeze/src/eval_mt_real.py` as the starting point;
- add a separate synthetic-pool argument rather than modifying PU training;
- keep `SimpleCNN(in_ch=4, num_classes=3)`;
- run at least 8 seeds for `n_real = 10, 25, 50`;
- report accuracy, macro-F1, per-class F1, confusion matrices, pool size, and
  acceptance cost.

## Claims Allowed After Completion

Allowed only if the audited pool and downstream CSV are produced:

- BREEZE augmentation effect on the private machine-tool dataset;
- acceptance rate and cost for the machine-tool generator;
- class-wise utility changes.

Not allowed without additional metadata:

- bearing characteristic-frequency claims;
- BPFO/BPFI envelope conclusions;
- physical fault names for `MT-1/MT-2/MT-3`.
