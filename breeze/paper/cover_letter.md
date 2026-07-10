# Cover Letter Draft

Dear Editor,

We submit the manuscript "BREEZE: A Training-Free Closed-Loop
Physical-Gate Admission Framework for LLM-Generated
Bearing Fault Signals" for consideration in Advanced Engineering Informatics.

The paper addresses a practical gap in LLM-based signal synthesis for
intelligent fault diagnosis. Existing LLM generators can produce useful
augmentation data, but they are typically open-loop: generated windows can
enter the training pool without deterministic checks for physically meaningful
statistics, spectral structure, envelope-spectrum evidence, or current-sideband
consistency. BREEZE wraps a black-box generator with a training-free verifier,
turns failed checks into structured feedback, and admits only gate-verified samples
without waveform repair or generator training.

The manuscript reports reproducible experiments on the Paderborn University
bearing benchmark. The original K=3 loop accepts 78.89% of generation slots
with 2.05 LLM calls per slot. A stricter v2 gate audit admits 757 windows
after diversity screening and improves real-only few-shot diagnosis by 14.33,
7.12, and 5.70 percentage points for 10, 25, and 50 real windows per class,
respectively. The paper also reports physical fidelity metrics, threshold
sensitivity, paired Wilcoxon tests, and a private four-channel machine-tool
portability study.

We believe the manuscript fits the journal because it combines industrial
AI, condition monitoring, signal-processing verification, and trustworthy use
of synthetic data. The work is not a new trainable generator; its contribution
is a generator-agnostic physical-gate admission layer that can be audited and
attached to existing LLM-based synthesis pipelines.

The manuscript is original and is not under consideration elsewhere. All
authors have approved the submission. Author names, affiliations, and any
required conflict-of-interest statements should be finalized by the authors
before submission.

Sincerely,

The authors
