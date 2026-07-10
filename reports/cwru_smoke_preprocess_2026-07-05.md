# CWRU Smoke Preprocessing Report

Date: 2026-07-05

Protocol: official CWRU 12 kHz drive-end 0-load smoke subset using common DE and FE vibration channels. BA is excluded because the normal baseline file does not contain BA.

Sampling rate: 12000 Hz
Window: 2048 samples
Hop: 2048 samples
Classes: healthy, IR, B, OR

## Files

| file | label | fault diameter | load | rpm | windows | train | test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 97.mat | healthy | none | 0 | 1796 | 119 | 83 | 36 |
| 105.mat | IR | 0.007 | 0 | 1797 | 59 | 41 | 18 |
| 118.mat | B | 0.007 | 0 | 1796 | 59 | 41 | 18 |
| 130.mat | OR | 0.007 | 0 | 1796 | 59 | 41 | 18 |

## Split

Train shape: (206, 2, 2048); counts: healthy:83, IR:41, B:41, OR:41
Test shape: (90, 2, 2048); counts: healthy:36, IR:18, B:18, OR:18

This smoke split is chronological within each source file and is used only to validate loaders, classifiers, and metric scripts. It is not a leakage-free final CWRU benchmark because each class currently has one source file. Full CWRU experiments must use multiple loads/fault sizes/locations with explicit file- or condition-held-out splits.
