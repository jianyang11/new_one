# Phase-B DIRG Verifier/Renderer Design

Date: 2026-07-05

DIRG VariableSpeedAndLoad is retained as a Phase-B supervised public benchmark because the local preprocessing contains 7 labelled classes, 17 speed-load operating conditions, 6 vibration channels, and a held-out speed/load split with no shared acquisition files.

## Local Protocol

- Source archive: `data/dirg/raw/VariableSpeedAndLoad.zip`
- Processed full NPZ: `proc/dirg_variable_all.npz`
- Held-out split: `proc/dirg_variable_loco_speed300_load1400_train.npz` / `proc/dirg_variable_loco_speed300_load1400_test.npz`
- Sampling rate: 51200 Hz
- Window/hop: 4096/4096 samples
- Classes: healthy, IR450, IR250, IR150, roller450, roller250, roller150
- Train/test condition split: train excludes speed=300 Hz and nominal load=1400 N; test contains only that held-out condition.

## Claim Boundary

The current local DIRG metadata gives speed, load, damage location, and severity, but not bearing geometry. Therefore DIRG must not be used for BPFO/BPFI/BSF/FTF peak-error claims unless a verifiable geometry source is added later.

For Phase B, DIRG can support:

- cross-condition diagnostic performance under a strict held-out speed/load split;
- train-only statistical and spectral verifier admission;
- PSD-Wasserstein, band-energy distance, spectral centroid, MMD, discriminator AUROC, and nearest-neighbor non-copying checks;
- severity-aware class analysis for inner-ring and roller defects.

DIRG cannot yet support:

- characteristic fault-frequency error targets in Hz;
- BPFO/BPFI/BSF/FTF envelope peak error tables;
- claims that a renderer reproduces DIRG bearing kinematics.

## Verifier Design

- Sanity: finite 6-channel windows with shape `(6, 4096)`.
- Statistics: train-only robust intervals for each channel's rms, peak, std, kurtosis, skewness, and crest.
- Spectrum: train-only soft spectral-band intervals over 0-25.6 kHz and PSD-CDF Wasserstein thresholds at c=90, with c85/c95 sensitivity later.
- Envelope/spectral impulsiveness: use train-selected high-kurtosis bands as quality descriptors, not as characteristic-frequency gates.
- Diversity/non-copying: compare synthetic-to-real nearest-neighbor distances against real-to-real distances in the same feature space.

## Renderer Design

The first DIRG renderer should be spectral/statistical, not kinematic:

- generate 6-channel windows with class-conditioned RMS, crest/kurtosis, PSD template, and cross-channel energy structure learned only from the train split;
- encode speed/load as recipe fields controlling amplitude and band-energy scaling;
- encode fault location/severity as recipe fields controlling impulsiveness and high-frequency energy, not BPFO/BPFI rates;
- keep rule/random/LLM recipe budgets class-balanced and split-specific.

Any later kinematic renderer requires a documented DIRG bearing-geometry source before entering the manuscript.
