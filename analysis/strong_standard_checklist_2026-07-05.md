# BREEZE Strong-Claim Standard Checklist

Date: 2026-07-05

This checklist maps the user's 11 revision standards to local evidence. A claim
can enter the formal manuscript only when the corresponding evidence exists as
code, CSV/JSON/NPZ output, figures, and manuscript text.

| Area | Required standard | Current evidence | Status | Next action |
| --- | --- | --- | --- | --- |
| Abstract | Multiple public datasets, multiple conditions, multiple baselines, highest or tied-highest Accuracy/Macro-F1 | PU Phase-A v2 full source ablation passed; CWRU and DIRG protocol audits plus downstream smoke are complete; CWRU has dataset-specific physics config and rule synthetic smoke. Full CWRU/DIRG LLM pools and full baseline comparisons are not yet run. IMS is downloaded/readable but run-to-failure without per-file fault-onset labels; XJTU-SY skipped by user; HIT/JUST not counted toward main claim | BLOCKED | Need API config for CWRU LLM recipe pool, then run full Phase-B grid and strongest baselines |
| Abstract | LLM recipe > random recipe > rule recipe | Phase-A v2 PU file-split CNN now uses budget-equal B=150/class pools, random open-loop, 20 seeds, n_real={5,10,25,50}. For n<=25, LLM K=3 significantly beats both random open-loop and rule for Accuracy and Macro-F1 under the pre-registered within-family Holm tests; at n=50 LLM has positive deltas over rule and real_only. Evidence: `breeze/results/phaseA_v2_downstream_cnn.csv`, `breeze/results/phaseA_v2_wilcoxon.csv`, `breeze/results/phaseA_v2_gate_report.md` | MET FOR PU PHASE-A V2 | Use only the scoped claim until multi-dataset evidence exists: few-shot n<=25 on PU, LLM recipe beats random/rule; n=50 not worse than rule |
| Abstract | Gains and significance vs strongest baseline | Current v2 loses to envelope-only at 10-shot and noise/open-loop baselines at 25/50-shot | NOT MET | Improve method or retract SOTA claim |
| Introduction | State hypotheses: LLM contribution, physical realism, stable diagnostic lift | Current intro frames admission, not strong LLM generation | TEXT PENDING | Rewrite only after experiments support the hypotheses |
| Introduction | Prove LLM-guided generation beats random/rule generation | Phase-A v2 resolves the old budget/random/statistical-power flaws: random+verifier remains 0/450 accepted, random open-loop is a real downstream control, and LLM beats rule/random for n<=25 with 20 seeds | MET FOR PU PHASE-A V2 | State this as a verified PU few-shot hypothesis; do not generalize to external datasets before Phase B results |
| Introduction | Hard target: public multi-dataset, multi-condition, multi-model, multi-metric stronger than baselines | Not yet true | BLOCKED | Complete external dataset and classifier experiments |
| Related Work | Taxonomy table for LLM-description, physics-informed GAN, physics-informed diffusion, verifier-guided admission | Current text has no taxonomy table | TEXT PENDING | Add table after dataset/method scope is finalized |
| Related Work | Compare BearGen and diffusion/GAN baselines including TimeGAN, SigCWGAN, TTS-GAN, TTS-CGAN, DDPM, CFG-DDPM | Current bibliography has TimeGAN but not all requested fault-generation baselines | PENDING | Verify sources, add citations, do not invent DOI |
| Method | Publish model, prompt, temperature, top-p, seed, schema, renderer equations | Model/prompt/schema/temperature/renderer present; top-p and API seed absent | PARTIAL | Document present metadata and explicit missing fields |
| Method | Full v2 closed-loop K=0/1/2/3 acceptance, failures, calls | v1 closed-loop K table exists; v2 is offline rescreening | BLOCKED unless API rerun succeeds | If API available, rerun v2 loop; otherwise keep v2 as offline |
| Method | random/rule/LLM recipe controls | Revised controls implemented: random+verifier 0/450 accepted, random open-loop B=150/class downstream control, rule IR supplemented to kept=151, all downstream groups use B=150/class, 20 seeds and checkpointed CSV | COMPLETED FOR PHASE-A V2 | Reuse the same budget-equality and pre-registration pattern for Phase B |
| Dataset | Remove private data from main experiment | Current manuscript already labels private data as schema audit | MET FOR CURRENT CLAIM | Keep private data out of core strong claim |
| Dataset | 5-8 public datasets | PU local plus CWRU and DIRG preprocessed; IMS archived and audited but not directly supervised-classification-ready; MFPT blocked by unavailable official endpoint; XJTU-SY skipped by user; HIT Channel-1 is present but label semantics are pending; JUST metadata is present but raw preprocessing is pending full download | BLOCKED | Continue official-source audits and preprocessing for viable datasets; do not count HIT/JUST toward physical-generation claims yet |
| Dataset | within-condition, cross-condition, leave-one-condition-out | Phase-B protocol audit covers PU file splits, CWRU within/cross/leave-one-load-out splits, and DIRG leave-one-speed/load-out split; smoke downstream completed for CWRU within_load0 and DIRG held-out condition | PARTIAL | Full synthetic augmentation and statistical comparisons still pending |
| Setup | CNN, ResNet1D, TCN, Transformer, SVM/RF | Current downstream uses compact CNN | NOT MET | Add model suite after data loaders are stable |
| Setup | shots 10/25/50/100/300/500 | Current main table 10/25/50 | PARTIAL | Extend shot grid with smoke then full |
| Setup | severe imbalance normal:fault=8:2 | Not present | NOT MET | Define and run imbalance protocol |
| Setup | same synthetic budget | Current PU baselines use caps, but new baselines need harmonization | PARTIAL | Add shared budget checker |
| Setup | At least 20 seeds and BH correction | Phase-A v2 PU source ablation uses 20 seeds and reports within-family Holm plus global BH reference. Broader baseline/classifier grids still need 20 seeds where feasible | PARTIAL | Carry the 20-seed/checkpointed CSV protocol into Phase B/C |
| Results | BREEZE-CNN exceeds all major baselines | Current v2 does not exceed strongest baseline | NOT MET | Improve method or avoid SOTA claim |
| Results | Per dataset/shot/classifier best baseline vs BREEZE delta | Current PU-CNN table has some deltas; no multi-dataset/classifier | PARTIAL | Generate full ranking table |
| Results | q < 0.05 after correction | v2 vs real-only significant; v2 vs strongest baseline not significant and often negative | NOT MET | Re-run after method improvements |
| Physical Realism | Frequency error within ±3%-5% | PU Phase-A v2 uses existing PU verifier evidence; CWRU frequency config now exists from official drive-end bearing multiples; DIRG is explicitly excluded from frequency-error claims until bearing geometry is verified | PENDING | Compute dedicated PU/CWRU frequency-error CSV after final synthetic pools exist |
| Physical Realism | Envelope prominence, SNR, harmonic consistency | Partial envelope gate scores exist; no unified report | PENDING | Implement class-wise report |
| Physical Realism | PSD-Wasserstein, band energy distance, spectral centroid | PSD-W1 exists in v2 verifier; no comparative summary table | PARTIAL | Add pooled metrics report |
| Physical Realism | real-vs-synthetic AUROC not near 1 | Not computed | PENDING | Implement discriminator AUROC |
| Physical Realism | nearest-neighbor distance proves no copying | Feature NN diversity exists; train-nearest report pending | PARTIAL | Add synthetic-to-real NN report |
| Ablation | no LLM, random, rule, LLM, LLM+verifier | Phase-A v2 source ablation completed for PU: real_only, random open-loop, rule, and LLM K=3 all run with 20 seeds and B=150/class; LLM significantly beats random open-loop and rule for n<=25 | MET FOR PU PHASE-A V2 | Extend ablation to external datasets only after each dataset has a faithful renderer/verifier protocol |
| Ablation | gate ablation stats/PSD/envelope/MCSA/diversity/full | Current stats-only and envelope-only downstream exist; full gate-by-gate v2 ablation absent | PARTIAL | Add v2 gate ablation if time/resources allow |
| Ablation | synthetic budget ablation | Not present | PENDING | Run budget sweep |
| Ablation | feedback round and quality improves with feedback | v1 K acceptance exists; quality monotonicity not established | PARTIAL | Add quality-vs-K metrics |
| Ablation | prompt and model-size ablation | Not present; API metadata incomplete | BLOCKED | Needs API/model access |
| Figures | Dataset distribution | Not present for external datasets | PENDING | Add after data registry/preprocessing |
| Figures | real/synthetic waveform + FFT + envelope per dataset | PU figure exists; external datasets pending | PARTIAL | Add per public dataset after pools exist |
| Figures | phase diversity/mode collapse | Not present | PENDING | Add diversity/mode-collapse plot |
| Figures | FID/KID/MMD overview | MMD exists; FID/KID not computed | PARTIAL | Add FID/KID-like feature metrics if defensible |
| Figures | cross-condition heatmap and SOTA ranking | Verifier heatmap exists; SOTA ranking absent | PARTIAL | Add ranking after full results |
| Discussion | Explain reliable generation rather than limitations | Current discussion is appropriately defensive because strong evidence is not met | PENDING | Rewrite only if new evidence supports it |

## Current Decision

Phase-A v2 now supports a scoped PU few-shot claim: under equal synthetic
budget and 20 seeds, LLM K=3 recipes outperform random open-loop and rule
recipes for n<=25 and are not worse than rule at n=50. The manuscript still
must not use the broader SOTA/multi-public-dataset claim until Phase B/C/D
evidence is produced. The immediate technical path is CWRU/DIRG/PU multi-
condition expansion, extended physical realism metrics, and multi-classifier
baseline tests.
