# Phase-B CWRU Physics Configuration

Date: 2026-07-05

Official source: https://engineering.case.edu/bearingdatacenter/bearing-information

The Phase-B CWRU protocol uses the drive-end 12 kHz channel, so the drive-end 6205-2RS JEM SKF bearing geometry and defect-frequency multiples are used. The existing PU renderer/verifier is not reused because it assumes PU 6203 geometry, 8 kHz sampling, and two motor-current channels.

## Bearing Specification

| field | value |
| --- | --- |
| bearing | 6205-2RS JEM SKF |
| inside_diameter_in | 0.9843 |
| outside_diameter_in | 2.0472 |
| thickness_in | 0.5906 |
| ball_diameter_in | 0.3126 |
| pitch_diameter_in | 1.537 |
| source_url | https://engineering.case.edu/bearingdatacenter/bearing-information |

Defect-frequency multiples of running speed: BPFI=5.4152, BPFO=3.5848, FTF=0.39828, BSF=4.7135.

## Class-To-Physics Mapping

| class | physical target | verifier implication |
| --- | --- | --- |
| healthy | no periodic fault impulse target | time/stat/PSD boundary and absence of strong fault-envelope peaks |
| IR | BPFI | envelope peaks at BPFI and harmonic/shaft-modulated sidebands |
| B | BSF / rolling element | envelope peaks at BSF and harmonics; no inner/outer race target substitution |
| OR | BPFO | envelope peaks at BPFO and harmonic consistency |

## Gate Design

- Sanity: finite single-channel window with shape (1, 2048).
- Statistics: robust train-only intervals for rms, peak, std, kurtosis, skewness, and crest.
- Spectrum: train-only soft spectral-band intervals and PSD-CDF Wasserstein thresholds at c=90, with c85/c95 sensitivity to be computed later.
- Envelope: train-calibrated resonance bands; target frequencies are computed from per-split rpm and official defect-frequency multiples.
- MCSA/current gate: omitted for CWRU because the official CWRU files are vibration-only; this omission must be stated in the manuscript instead of being patched with synthetic current channels.

## Split Frequency Ranges

| split | train rpm | test rpm | train BPFO Hz | train BPFI Hz | train BSF Hz | test BPFO Hz | test BPFI Hz | test BSF Hz |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lolo_load0 | 1718-1774 | 1796-1797 | 102.645-105.991 | 155.055-160.109 | 134.963-139.362 | 107.305-107.365 | 162.095-162.185 | 141.091-141.169 |
| lolo_load1 | 1718-1797 | 1771-1774 | 102.645-107.365 | 155.055-162.185 | 134.963-141.169 | 105.811-105.991 | 159.839-160.109 | 139.127-139.362 |
| lolo_load2 | 1718-1797 | 1746-1754 | 102.645-107.365 | 155.055-162.185 | 134.963-141.169 | 104.318-104.796 | 157.582-158.304 | 137.163-137.791 |
| lolo_load3 | 1746-1797 | 1718-1730 | 104.318-107.365 | 157.582-162.185 | 137.163-141.169 | 102.645-103.362 | 155.055-156.138 | 134.963-135.906 |
| train_load0_test_load1 | 1796-1797 | 1771-1774 | 107.305-107.365 | 162.095-162.185 | 141.091-141.169 | 105.811-105.991 | 159.839-160.109 | 139.127-139.362 |
| train_load0_test_load2 | 1796-1797 | 1746-1754 | 107.305-107.365 | 162.095-162.185 | 141.091-141.169 | 104.318-104.796 | 157.582-158.304 | 137.163-137.791 |
| train_load0_test_load3 | 1796-1797 | 1718-1730 | 107.305-107.365 | 162.095-162.185 | 141.091-141.169 | 102.645-103.362 | 155.055-156.138 | 134.963-135.906 |
| within_load0 | 1796-1797 | 1796-1797 | 107.305-107.365 | 162.095-162.185 | 141.091-141.169 | 107.305-107.365 | 162.095-162.185 | 141.091-141.169 |
| within_load1 | 1771-1774 | 1771-1774 | 105.811-105.991 | 159.839-160.109 | 139.127-139.362 | 105.811-105.991 | 159.839-160.109 | 139.127-139.362 |
| within_load2 | 1746-1754 | 1746-1754 | 104.318-104.796 | 157.582-158.304 | 137.163-137.791 | 104.318-104.796 | 157.582-158.304 | 137.163-137.791 |
| within_load3 | 1718-1730 | 1718-1730 | 102.645-103.362 | 155.055-156.138 | 134.963-135.906 | 102.645-103.362 | 155.055-156.138 | 134.963-135.906 |
