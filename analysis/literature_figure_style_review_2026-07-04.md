# Literature and Figure-Style Review for BREEZE

Date: 2026-07-04

Scope: this review supports the current BREEZE revision task. It uses the installed `nature-figure`, `huashu-nuwa`, and `awesome-ai-research-writing` skills as operating constraints: figures must be argument-led, source-data-backed, visually restrained, and claims must not exceed the available experiments.

## Skill-Distilled Evidence Logic

The closest literature repeatedly uses the same evidence chain:

1. Define the generator mechanism and responsibility boundary.
2. Show physical signal plausibility with time waveform, FFT/PSD, and envelope spectrum.
3. Quantify real-synthetic distribution distance and diversity.
4. Test downstream diagnosis under low-data or imbalance settings.
5. Report ablation, cost, and failure/limitation cases.

BREEZE currently supports items 2-5 for one PU condition plus verifier audits on additional PU conditions. It does not yet support a strong claim that the LLM itself is an irreplaceable generator, because the available v2 result is an offline rescreening of existing candidates and no new closed-loop LLM run, prompt log, or API replay record has been provided.

## Verified Similar Literature

| Paper | Method | Data and Conditions | Baselines | Metrics | Figure/Table Style | Takeaway for BREEZE |
|---|---|---|---|---|---|---|
| BearGen: LLM-guided signal generation framework for bearing fault diagnosis, Advanced Engineering Informatics 71, 104400, 2026. DOI: https://doi.org/10.1016/j.aei.2026.104400. User-provided PDF: `/Users/jianyang/Downloads/1-s2.0-S1474034626000923-main.pdf`. | LLM-generated descriptions condition a locally deployed LLM and a description-guided diffusion generator. | Eight public bearing datasets after preprocessing: CWRU, PU, HIT, IMS, XJTU, DIRG, JUST, NCEPU. The paper reports 135,516 segments, 262 operating conditions, and up to 10 labels. | w/o generation, Time-GAN, SigCWGAN, TTS-GAN, TTS-CGAN, DDPM, CFG-DDPM, BearGen. | FID, KID, accuracy, F1, few-shot accuracy/F1, severe imbalance, guidance-scale ablation, training/inference cost. | Large phase-based workflow figure; local-LLM architecture figure; dataset example plates; label-distribution bars; FID bars; real/generated waveform overlay; time/FFT/envelope-spectrum grid with dashed peak markers; phase KDE; t-SNE as auxiliary; few-shot grouped bars; cost tables. | BREEZE should use phase panels and explicit responsibility boundaries. Its waveform figure should mirror the time/FFT/envelope evidence grid, but captions must state that t-SNE-like plots are auxiliary and not core evidence. |
| Gao et al., Bearing fault signal generation method by fusion of physical constraints and multimodal features, Measurement Science and Technology 36(11), 116109, 2025. DOI: https://doi.org/10.1088/1361-6501/ae1a04. | Time-frequency physics-guided multimodal GAN with differentiable bearing priors: decaying impact response and rotation-speed-induced modulation; dual-path time/frequency generator and multiscale discriminator. | Crossref abstract verifies two public bearing datasets, named Dataset A and Dataset B in metadata. Exact dataset names and visual figure layouts require the publisher PDF. | Representative GAN-based comparison is implied by method class; Crossref abstract does not list full baseline names. | DTW, envelope spectral deviation/MSE, statistical similarity, coverage, downstream F1. | PDF visual layout was not successfully downloaded in this workspace; metadata confirms a physics-mechanism and multidimensional fidelity framing. | BREEZE should report physical gates as evidence checks, not as formal physical validity. Failure reason breakdown and envelope evidence are important because this literature treats envelope deviation as a primary fidelity metric. |
| Liu et al., Data synthesis using deep feature enhanced generative adversarial networks for rolling bearing imbalanced fault diagnosis, Mechanical Systems and Signal Processing 163, 108139, 2022. DOI: https://doi.org/10.1016/j.ymssp.2021.108139. | Deep feature enhanced GAN for imbalanced bearing diagnosis. | Crossref confirms rolling bearing imbalanced fault diagnosis; references include CWRU and GAN/WGAN variants. | GAN-family and imbalanced-learning baselines. | Downstream fault-diagnosis performance; distribution-quality evidence in paper likely includes feature-space and confusion/performance tables. | Detailed visual extraction requires PDF access. | BREEZE's GAN/VAE baselines must be described conservatively because the current local GAN/VAE are compact baselines, not optimized state-of-the-art physics-informed generators. |
| Qiao et al., DDPM-LFR: an enhanced local feature refinement diffusion model for helicopter tail drive system fault diagnosis, Mechanical Systems and Signal Processing 238, 113170, 2025. DOI: https://doi.org/10.1016/j.ymssp.2025.113170. | Diffusion augmentation with local feature refinement for a helicopter tail-drive fault-diagnosis system. | Crossref confirms helicopter tail-drive diagnosis and references multiple DDPM/GAN augmentation works. | Diffusion and GAN augmentation baselines from the references; exact tables require PDF access. | Downstream diagnostic metrics and diffusion-quality comparisons. | Detailed visual extraction requires PDF access. | A diffusion baseline is now a strong expected comparator. If not implemented rigorously on the local CPU environment, BREEZE must mark it as blocker rather than insert a weak placeholder. |
| Liu et al., Physics-informed diffusion-based augmentation for vibration-based fault diagnosis of rotating machinery, Journal of Vibration and Control, online 2026-06-14. DOI: https://doi.org/10.1177/10775463261455715. | Wavelet-preprocessed temporal-attention diffusion with multiscale wavelet priors, temporal attention in reverse denoising, and asymmetric U-Net. | Crossref abstract verifies two bearing test platforms. | Representative generative baselines. | Physical fidelity and downstream diagnostic performance. | PDF visual extraction was blocked, but the abstract confirms wavelet/physical-prior diffusion as a current comparator. | BREEZE should avoid claiming superiority over physics-informed diffusion until a fair implementation or cited comparison is available. |
| HAWAN-PIR 2025. | Not verified. | Not verified. | Not verified. | Not verified. | No DOI or publisher page was found in the available search/Crossref checks. | Do not cite or use as evidence until the user provides a DOI, PDF, or stable publisher page. |

## Common Figure Formats in the Closest Literature

| Format | Observed Use | BREEZE Mapping |
|---|---|---|
| Workflow figure | BearGen Fig. 1 uses three large phases with arrows and small signal thumbnails. | Redraw BREEZE Fig. 1 as phases: recipe proposal, deterministic rendering, train-calibrated verifier, admission/rejection feedback, downstream diagnosis. |
| Physical mechanism / architecture figure | BearGen Fig. 2 separates signal tokenization, prompt, local LLM, and training. Physics-guided GAN papers emphasize differentiable physical priors. | Add a responsibility-boundary figure separating LLM recipe, renderer equations, verifier gates, and failure feedback. |
| Waveform + FFT + envelope spectrum | BearGen Fig. 8 uses rows for time, FFT, envelope spectrum and columns for fault classes; real/generated curves are blue/orange, dominant peaks are dashed red lines. | Redraw BREEZE waveform figure as time/FFT/envelope grid with real and gate-admitted synthetic examples and BPFO/BPFI reference lines. |
| Distribution and physical metrics | BearGen uses FID/KID and phase KDE; physics-guided GAN uses DTW, envelope spectrum MSE, statistical similarity, coverage. | Keep MMD/NN diversity and add metric-distance bars; keep RMS/kurtosis distributions. |
| Downstream result table | BearGen Tables 4-5 compare many generators across datasets and report mean/std. | Keep BREEZE's selected table but do not mark the proposed method as SOTA because local results do not dominate all strong baselines. |
| Few-shot/ablation bars | BearGen Figs. 13-14 use grouped bars across shot counts and datasets; Table 9 is guidance-scale ablation. | Keep acceptance/K ablation and downstream bars, but style them with a restrained family palette and exact variance definitions. |
| Cross-condition result table | Common in fault-diagnosis papers, especially when claiming robustness. | Add a cross-condition heatmap from the existing verifier audit; keep the text clear that this is verifier coverage, not augmentation transfer. |
| t-SNE/UMAP | BearGen uses t-SNE for auxiliary feature-space inspection. | BREEZE should not add t-SNE as core evidence; if later added, it remains auxiliary. |
| Failure case / failure breakdown | Physics-verifier papers need failure cases to show gate behavior. | Add a rejected-slot failure breakdown from `revision_v2_rejected_slot_fail_reasons.csv`; add failure-case examples only if a specific rejected candidate and report are shown. |

## Immediate Figure Redesign Contract

1. `framework.pdf`: schematic-led composite. Core conclusion: BREEZE is a train-calibrated admission loop, not a trained generator.
2. `responsibility_boundary.pdf`: mechanism boundary. Core conclusion: LLM proposes recipes; renderer creates waveforms; verifier admits/rejects with auditable gates.
3. `waveforms.pdf`: physical signal evidence. Core conclusion: admitted examples can be inspected in time, FFT, and envelope domains against class-specific reference frequencies.
4. `boxplots.pdf` and `metric_distances.pdf`: physical/distribution evidence. Core conclusion: admission changes simple statistics and feature distances, but MMD is not claimed as universally minimized.
5. `cross_condition_heatmap.pdf`: portability boundary. Core conclusion: the verifier can be recalibrated across PU conditions; no cross-condition synthetic augmentation claim is made.
6. `acceptance_k.pdf` and `failure_reasons.pdf`: closed-loop diagnostics. Core conclusion: feedback raises acceptance, and rejected slots reveal which gates constrain generation.
7. `downstream_bars.pdf`: downstream utility. Core conclusion: v2 improves over real-only but is not uniformly best against all augmentation baselines.

## Blockers Identified During Review

- A full SOTA-style "LLM generates reliable fault signals" claim requires a new closed-loop LLM run with model version, prompt, temperature/top-p/seed, max tokens, feedback rounds, failure logs, and cost. These are not available locally.
- Fair comparison with physics-informed diffusion and the MST 2025 physics-guided multimodal GAN requires implementing or obtaining those baselines under the same split/budget. The current local CPU environment and available code do not yet support this as a completed result.
- HAWAN-PIR 2025 is not a verified citation in the current workspace.
- Private machine-tool data should not support the core reliable-bearing-generation claim because no audited synthetic pool and no precise machine-geometry/order model are available.
