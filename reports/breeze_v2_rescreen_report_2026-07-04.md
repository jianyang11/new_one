# BREEZE-v2 离线重筛阶段报告

日期：2026-07-04

代码：
- `breeze/src/verifier/v2.py`
- `breeze/src/rescreen_v2.py`
- `breeze/src/eval_custom_pool.py`

输入：
- 原始生成 run：`breeze/runs/pool_physics_file_k3`
- 共享 v2 校准：`breeze/runs/verifier_v2_N09_M07_F10_c90_soft_w1.json`
- 数据划分：`load_file_split("train/test", N09_M07_F10)`

## 1. v2 gate 定义

v2 不修改原始 LLM 样本，也不回写 v1 结果。它只做训练集校准后的离线证书化重筛：

- `stats_union`：统计可行域为两个 train-supported 域的并集：
  - legacy per-feature quantile boundary；
  - robust axis ellipsoid（median/IQR 标准化后的欧氏距离）。
- `soft_spectrum`：用重叠三角滤波器组替代硬频带能量比例，减少频峰落在边界附近时的跳变。
- `psd_w1`：把 Welch PSD 归一化为频率分布，计算候选 PSD CDF 到 class train 参考 CDF 的 W1 距离。
- `envelope_multi`：用 train-supported top-3 resonance bands，而不是单一 SK 最大频带；fault 类要求任一支持频带通过 envelope prominence + band energy。
- `vector_mcsa`：用两相电流构造 vector-current MCSA 分数；如果 train 中 fault sideband 与 healthy 不可分，仅作为 certificate score，不作为 hard gate。
- `diversity`：用扩展物理 embedding 做 class-wise real-real NN 阈值筛选，阈值来自训练集。

## 2. 小样本与全量重筛

| run | slots | accepted slots | accepted items before diversity | kept after diversity | kept by class |
| --- | ---: | ---: | ---: | ---: | --- |
| `rescreen_v2_s10` | 30 | 19 | 50 | 50 | healthy 10 / OR 30 / IR 10 |
| `rescreen_v2_s50` | 150 | 97 | 268 | 268 | healthy 70 / OR 112 / IR 86 |
| `rescreen_v2_full` | 450 | 286 | 761 | 757 | healthy 192 / OR 304 / IR 261 |

全量输出：
- `breeze/runs/rescreen_v2_full/pool_v2.npz`：`X.shape=(757,3,2048)`，`y` counts = healthy 192 / OR 304 / IR 261。
- `breeze/runs/rescreen_v2_full/accepted_manifest.csv`
- `breeze/runs/rescreen_v2_full/slot_summary.csv`
- `breeze/runs/rescreen_v2_full/summary.json`

全量 fail gate 仍主要来自 `stats_union`，说明 LLM recipe 的电流 crest/peak/kurtosis 仍是主要物理一致性瓶颈；MCSA 在当前 PU train split 中未形成可靠 hard gate，只记录为证书分数。

## 3. 8-seed 快速下游评估

评估脚本：`breeze/src/eval_custom_pool.py`

结果文件：`breeze/results/custom_pool_eval.csv`

设置：
- `real_only` 与 `breeze_v2_full` 各 8 seeds。
- `n_real = 10/25/50`。
- v2 pool 按每类最多 200 个 synthetic 样本加入；由于 healthy 只有 192 个，实际 `n_syn=592`。

| baseline | n_real | acc mean±std | macro-F1 mean±std | F1 healthy | F1 OR | F1 IR |
| --- | ---: | --- | --- | --- | --- | --- |
| real_only | 10 | 0.6449 ± 0.1087 | 0.6040 ± 0.1292 | 0.8283 | 0.5178 | 0.4658 |
| breeze_v2_full | 10 | 0.7880 ± 0.0312 | 0.7906 ± 0.0289 | 0.9786 | 0.6673 | 0.7260 |
| real_only | 25 | 0.7371 ± 0.0372 | 0.7184 ± 0.0425 | 0.8577 | 0.5684 | 0.7293 |
| breeze_v2_full | 25 | 0.8082 ± 0.0324 | 0.8079 ± 0.0354 | 0.9795 | 0.6784 | 0.7657 |
| real_only | 50 | 0.7881 ± 0.0197 | 0.7743 ± 0.0253 | 0.9499 | 0.6087 | 0.7643 |
| breeze_v2_full | 50 | 0.8456 ± 0.0174 | 0.8484 ± 0.0178 | 0.9918 | 0.7619 | 0.7914 |

Paired Wilcoxon on accuracy, `breeze_v2_full` vs `real_only`:
- n_real=10: delta +0.1430, p=0.0078125
- n_real=25: delta +0.0711, p=0.015625
- n_real=50: delta +0.0575, p=0.0078125

## 4. Physical metrics

使用 `metrics.py::pool_metrics` 的同一 feature/MMD/NN-diversity protocol，输出到 `breeze/results/pool_metrics_v2.csv`。

| pool | class | n | MMD2 | NN diversity | real-real NN diversity |
| --- | --- | ---: | ---: | ---: | ---: |
| breeze_v2_full | healthy | 192 | 0.1507 | 0.3468 | 0.8910 |
| breeze_v2_full | OR | 304 | 0.0713 | 0.4212 | 0.4122 |
| breeze_v2_full | IR | 261 | 0.1254 | 0.7123 | 0.8598 |

Comparison notes:
- Compared with v1 `breeze_k3`, v2 improves MMD2 for OR (0.0776 -> 0.0713) and IR (0.1990 -> 0.1254), but healthy MMD2 is slightly worse (0.1378 -> 0.1507).
- Compared with `open_loop_basic`, v2 is much closer to the real feature distribution across all classes.
- Compared with `open_loop_phys`, v2 is not uniformly better on MMD2, so the v2 claim should focus on physical-gate admission robustness, per-class downstream gains, and interpretable failure reports rather than claiming universal physical-metric dominance.

## 5. Same-seed comparison with existing main baselines

Existing main table means from `results/downstream_file.csv`; v2 from `custom_pool_eval.csv`.

| n_real | real_only | breeze_k3 | stats_only | envelope_only | open_loop_phys | noise_aug | breeze_v2_full |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 0.6446 | 0.7283 | 0.7196 | 0.7964 | 0.7834 | 0.6992 | 0.7880 |
| 25 | 0.7370 | 0.7844 | 0.7754 | 0.8180 | 0.8186 | 0.8225 | 0.8082 |
| 50 | 0.7886 | 0.8317 | 0.8268 | 0.8439 | 0.8498 | 0.8616 | 0.8456 |

Paired Wilcoxon on accuracy, v2_full vs main baselines, is saved to `breeze/results/significance_v2_vs_main.csv`.

Key paired-test outcomes:
- v2_full vs v1 `breeze_k3`: +0.0597 (p=0.0156) at 10-shot, +0.0238 (p=0.0547) at 25-shot, +0.0139 (p=0.0391) at 50-shot.
- v2_full vs `noise_aug`: +0.0888 (p=0.0078) at 10-shot, but -0.0143 (p=0.3828) at 25-shot and -0.0160 (p=0.1484) at 50-shot.
- v2_full vs `open_loop_phys` and `envelope_only`: differences are small and not significant in the current table.

Interpretation:
- v2_full is clearly better than real_only and v1 `breeze_k3`.
- v2_full is competitive with `open_loop_phys` and `envelope_only`, but not uniformly best.
- `noise_aug` remains strongest at n_real=25/50 in the current main table.
- Therefore the paper still must not claim “BREEZE is the highest-accuracy method across all baselines.” The defensible claim is: v2 improves the gate-admitted BREEZE pool over v1 and yields significant gains over real-only, while the physical-gate admission value must be argued jointly with physical fidelity, acceptance cost, and audit-trail interpretability.

## 6. Next decisions

- Integrate `breeze_v2_full` into the final analysis tables without overwriting original Block 4 results.
- Add per-class F1 support to the main table or merge `custom_pool_eval.csv` carefully.
- If the manuscript wants BREEZE to beat every strong baseline, further work is needed; current data does not support that stronger claim.
