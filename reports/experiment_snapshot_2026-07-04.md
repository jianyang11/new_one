# BREEZE 实验快照冻结报告

冻结日期：2026-07-04

项目根目录：`/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2`

## 1. 环境

- Python：`/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/.venv-breeze/bin/python` (`3.12.13`)
- Platform：`macOS-15.3-arm64-arm-64bit`
- Torch runtime：CUDA=False, MPS=False

| package | version |
| --- | --- |
| numpy | 2.5.0 |
| scipy | 1.18.0 |
| pandas | 3.0.3 |
| scikit-learn | 1.9.0 |
| torch | 2.12.1 |
| matplotlib | 3.11.0 |

## 2. 数据协议与通道

- 主工况：`N09_M07_F10`，转速 `900` rpm。
- 采样：原始 `64000` Hz，降采样因子 `8`，当前 `8000` Hz。
- 窗口：`2048` 点，hop `2048`。
- PU 当前保留通道：`vibration_1, phase_current_1, phase_current_2`。注意：代码内 X/Y/Z 短名分别是振动、相电流1、相电流2，不是三轴振动。
- 6203 主工况故障频率：{'fr': 15.0, 'BPFO': 46.059, 'BPFI': 73.941, 'FTF': 5.757, 'BSF': 30.535}

### 2.1 PU 预处理文件

| condition/class | npz files | windows | bearings |
| --- | --- | --- | --- |
| N09_M07_F10/IR | 6 | 1805 | KI04, KI14, KI16, KI17, KI18, KI21 |
| N09_M07_F10/OR | 5 | 1503 | KA04, KA15, KA16, KA22, KA30 |
| N09_M07_F10/healthy | 5 | 1500 | K001, K002, K003, K004, K005 |
| N15_M01_F10/IR | 6 | 1807 | KI04, KI14, KI16, KI17, KI18, KI21 |
| N15_M01_F10/OR | 5 | 1504 | KA04, KA15, KA16, KA22, KA30 |
| N15_M01_F10/healthy | 5 | 1503 | K001, K002, K003, K004, K005 |
| N15_M07_F04/IR | 6 | 1807 | KI04, KI14, KI16, KI17, KI18, KI21 |
| N15_M07_F04/OR | 5 | 1501 | KA04, KA15, KA16, KA22, KA30 |
| N15_M07_F04/healthy | 5 | 1502 | K001, K002, K003, K004, K005 |
| N15_M07_F10/IR | 6 | 1803 | KI04, KI14, KI16, KI17, KI18, KI21 |
| N15_M07_F10/OR | 5 | 1501 | KA04, KA15, KA16, KA22, KA30 |
| N15_M07_F10/healthy | 5 | 1501 | K001, K002, K003, K004, K005 |

### 2.2 主文件划分

| split | class | windows |
| --- | --- | --- |
| train | healthy | 1200 |
| train | OR | 1202 |
| train | IR | 1444 |
| test | healthy | 300 |
| test | OR | 301 |
| test | IR | 361 |
| train | total | 3846 |
| test | total | 962 |

- 文件划分泄漏检查：所有轴承 train/test file_id overlap 计数为 `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`。

### 2.3 实验室自建机床数据

| split | class | csv files | raw rows |
| --- | --- | --- | --- |
| train | 1 | 5 | 696320 |
| train | 2 | 5 | 397312 |
| train | 3 | 5 | 700416 |
| test | 1 | 2 | 172032 |
| test | 2 | 2 | 172032 |
| test | 3 | 2 | 159744 |

- CSV 表头集合：`{"('X', 'Y', 'Z', 'Current')": 21}`。

| npz | windows | shape |
| --- | --- | --- |
| mt_test_1.npz | 166 | [166, 4, 2048] |
| mt_test_2.npz | 166 | [166, 4, 2048] |
| mt_test_3.npz | 154 | [154, 4, 2048] |
| mt_train_1.npz | 675 | [675, 4, 2048] |
| mt_train_2.npz | 383 | [383, 4, 2048] |
| mt_train_3.npz | 679 | [679, 4, 2048] |

- 机床数据是三轴振动 + 单路电流，不能直接套用 PU 的 1 振动 + 2 电流 verifier schema。
- 后续本地补查 `sci_llm/论文全文.md` 确认自建数据采集介绍：NI 采集卡四通道同步采样，采样率 4000 Hz，工况包含正常加工、丝杠异常、底座不平衡；但文件前缀 `1/2/3` 到三种工况的精确映射仍未在本地材料中确认。

## 3. 物理验证器

| file | coverage | gates | freqs |
| --- | --- | --- | --- |
| verifier_N09_M07_F10_file_c85.json | 0.85 | {'sanity': True, 'boundary': True, 'energy': True, 'envelope': True, 'mcsa': True, 'spectrum': True} | {'fr': 15.0, 'BPFO': 46.059, 'BPFI': 73.941, 'FTF': 5.757, 'BSF': 30.535} |
| verifier_N09_M07_F10_file_c90.json | 0.9 | {'sanity': True, 'boundary': True, 'energy': True, 'envelope': True, 'mcsa': True, 'spectrum': True} | {'fr': 15.0, 'BPFO': 46.059, 'BPFI': 73.941, 'FTF': 5.757, 'BSF': 30.535} |
| verifier_N09_M07_F10_file_c95.json | 0.95 | {'sanity': True, 'boundary': True, 'energy': True, 'envelope': True, 'mcsa': True, 'spectrum': True} | {'fr': 15.0, 'BPFO': 46.059, 'BPFI': 73.941, 'FTF': 5.757, 'BSF': 30.535} |

| coverage | split | pass | n | rate | fail gates |
| --- | --- | --- | --- | --- | --- |
| c85 | train | 3571 | 3846 | 0.9285 | {'boundary': 78, 'energy': 25, 'envelope': 51, 'mcsa': 42, 'spectrum': 104} |
| c85 | test | 865 | 962 | 0.8992 | {'boundary': 23, 'energy': 14, 'envelope': 15, 'mcsa': 12, 'spectrum': 44} |
| c90 | train | 3603 | 3846 | 0.9368 | {'boundary': 75, 'energy': 16, 'envelope': 34, 'mcsa': 36, 'spectrum': 104} |
| c90 | test | 880 | 962 | 0.9148 | {'boundary': 22, 'energy': 7, 'envelope': 7, 'mcsa': 9, 'spectrum': 44} |
| c95 | train | 3631 | 3846 | 0.9441 | {'boundary': 75, 'energy': 10, 'envelope': 22, 'mcsa': 20, 'spectrum': 104} |
| c95 | test | 886 | 962 | 0.921 | {'boundary': 22, 'energy': 6, 'envelope': 7, 'mcsa': 4, 'spectrum': 44} |

复算说明：上表由 `breeze/scripts/freeze_snapshot.py` 逐窗口加载当前 verifier 文件和当前 `proc` 数据全量复算，作为本冻结快照的准确信息。

`runs/recal_file.log` 中保存的旧复核记录如下，和当前复算有轻微差异；论文写作以本报告和 raw JSON 的当前复算值为准，除非后续查明并记录代码版本差异。

```text
c85 train pass 0.930
c85 test pass 0.890
c90 train pass 0.943
c90 test pass 0.905
c95 train pass 0.953
c95 test pass 0.912
```

主协议为 `_file_c90`。对应 class band 与阈值摘要：

| class | band Hz | env_prom_min | env_prom_max | mcsa_min |
| --- | --- | --- | --- | --- |
| healthy | [200.0, 1200.0] | None | 6.693128771547791 | None |
| OR | [1800.0, 2800.0] | 1.2329265512714889 | None | 0.2895422349626697 |
| IR | [200.0, 1200.0] | 0.7020770997364655 | None | 0.24442873361698908 |

高风险项：固定硬频带 spectrum gate、单一 SK 最大共振带、单相 MCSA hard gate、9 维宏观统计 diversity embedding。

## 4. 生成池

| run dir | json | npy | accepted slots | acceptance |
| --- | --- | --- | --- | --- |
| pool_physics_file_k3 | 450 | 2470 | 355 | 0.7889 |
| pool_basic_file_k0 | 450 | 416 | 0 | 0.0 |
| pool_physics_k3_v1 | 900 | 3539 | 392 | 0.4356 |
| pool_basic_k0 | 600 | 599 | 0 | 0.0 |
| pilot_mimo_k2 | 12 | 49 | 7 | 0.5833 |
| pilot_mimo_k2b | 15 | 73 | 12 | 0.8 |
| pool_raw_k2 | 36 | 59 | 0 | 0.0 |

从正式 run 组装的论文候选池：

| pool | shape | class counts |
| --- | --- | --- |
| open_loop_basic | [416, 3, 2048] | {'healthy': 135, 'OR': 142, 'IR': 139} |
| open_loop_phys | [450, 3, 2048] | {'healthy': 150, 'OR': 150, 'IR': 150} |
| stats_only | [253, 3, 2048] | {'healthy': 83, 'OR': 114, 'IR': 56} |
| envelope_only | [442, 3, 2048] | {'healthy': 150, 'OR': 143, 'IR': 149} |
| breeze_k0 | [1173, 3, 2048] | {'healthy': 370, 'OR': 559, 'IR': 244} |
| breeze_k1 | [1333, 3, 2048] | {'healthy': 430, 'OR': 599, 'IR': 304} |
| breeze_k2 | [1461, 3, 2048] | {'healthy': 490, 'OR': 618, 'IR': 353} |
| breeze_k3 | [1547, 3, 2048] | {'healthy': 519, 'OR': 638, 'IR': 390} |

NPZ 池文件：

| npz | keys/shapes |
| --- | --- |
| pool_breeze_k3.npz | {'X': {'shape': [1547, 3, 2048], 'dtype': 'float32'}, 'y': {'shape': [1547], 'dtype': 'int64', 'counts': {'0': 519, '1': 638, '2': 390}, 'class_counts': {'healthy': 519, 'OR': 638, 'IR': 390}}} |
| breeze_ref_pool_v8.npz | {'X': {'shape': [1280, 3, 2048], 'dtype': 'float32'}, 'y': {'shape': [1280], 'dtype': 'int64', 'counts': {'0': 400, '1': 400, '2': 480}, 'class_counts': {'healthy': 400, 'OR': 400, 'IR': 480}}} |
| vae_fullcorpus_pool.npz | {'X': {'shape': [900, 3, 2048], 'dtype': 'float32'}, 'y': {'shape': [900], 'dtype': 'int64', 'counts': {'0': 300, '1': 300, '2': 300}, 'class_counts': {'healthy': 300, 'OR': 300, 'IR': 300}}} |
| gan_fullcorpus_pool.npz | {'X': {'shape': [900, 3, 2048], 'dtype': 'float32'}, 'y': {'shape': [900], 'dtype': 'int64', 'counts': {'0': 300, '1': 300, '2': 300}, 'class_counts': {'healthy': 300, 'OR': 300, 'IR': 300}}} |

正式可用：`pool_physics_file_k3`、`pool_basic_file_k0` 及由二者组装的 open-loop/stats/envelope/BREEZE pools。`pool_physics_k3_v1` 属旧架构池，当前不应混入主论文结果。

## 5. 结果表

| csv | rows | columns |
| --- | --- | --- |
| acceptance.csv | 4 | ['run', 'K', 'acceptance', 'mean_llm_calls', 'n_slots'] |
| downstream.csv | 288 | ['baseline', 'n_real', 'seed', 'n_syn', 'acc', 'f1'] |
| downstream_file.csv | 336 | ['baseline', 'n_real', 'seed', 'n_syn', 'acc', 'f1'] |
| pool_metrics.csv | 24 | ['pool', 'class', 'n', 'mmd2', 'nn_div', 'nn_div_real'] |
| significance.csv | 39 | ['n_real', 'baseline', 'breeze_mean', 'other_mean', 'delta', 'p_wilcoxon'] |

- `downstream_file.csv` baselines: `['breeze_k0', 'breeze_k1', 'breeze_k2', 'breeze_k3', 'envelope_only', 'gan', 'gan_fs', 'noise_aug', 'open_loop_basic', 'open_loop_phys', 'real_only', 'stats_only', 'vae', 'vae_fs']`
- n_real: `[10, 25, 50]`; seeds: `[0, 1, 2, 3, 4, 5, 6, 7]`
- expected rows: `336`; missing: `0`

| baseline | n_real | rows | mean acc | std acc | mean macro-F1 | std macro-F1 |
| --- | --- | --- | --- | --- | --- | --- |
| breeze_k0 | 10 | 8 | 0.7135 | 0.0427 | 0.7141 | 0.043 |
| breeze_k0 | 25 | 8 | 0.7999 | 0.0231 | 0.7994 | 0.0278 |
| breeze_k0 | 50 | 8 | 0.8324 | 0.0233 | 0.8334 | 0.0231 |
| breeze_k1 | 10 | 8 | 0.7327 | 0.061 | 0.735 | 0.0596 |
| breeze_k1 | 25 | 8 | 0.8002 | 0.0249 | 0.7994 | 0.0247 |
| breeze_k1 | 50 | 8 | 0.8224 | 0.0666 | 0.8211 | 0.0801 |
| breeze_k2 | 10 | 8 | 0.7196 | 0.0636 | 0.7187 | 0.073 |
| breeze_k2 | 25 | 8 | 0.7773 | 0.022 | 0.7783 | 0.0187 |
| breeze_k2 | 50 | 8 | 0.8381 | 0.0224 | 0.8402 | 0.0236 |
| breeze_k3 | 10 | 8 | 0.7283 | 0.0667 | 0.7304 | 0.0682 |
| breeze_k3 | 25 | 8 | 0.7844 | 0.0247 | 0.7853 | 0.0215 |
| breeze_k3 | 50 | 8 | 0.8317 | 0.0138 | 0.8336 | 0.0143 |
| envelope_only | 10 | 8 | 0.7964 | 0.0337 | 0.7991 | 0.0312 |
| envelope_only | 25 | 8 | 0.818 | 0.0267 | 0.8178 | 0.0292 |
| envelope_only | 50 | 8 | 0.8439 | 0.0238 | 0.8469 | 0.0234 |
| gan | 10 | 8 | 0.7179 | 0.0829 | 0.7155 | 0.0842 |
| gan | 25 | 8 | 0.7851 | 0.0544 | 0.7716 | 0.0583 |
| gan | 50 | 8 | 0.8484 | 0.0281 | 0.8492 | 0.0265 |
| gan_fs | 10 | 8 | 0.7109 | 0.0652 | 0.7012 | 0.0759 |
| gan_fs | 25 | 8 | 0.7554 | 0.0646 | 0.7377 | 0.0765 |
| gan_fs | 50 | 8 | 0.8454 | 0.0362 | 0.843 | 0.0388 |
| noise_aug | 10 | 8 | 0.6992 | 0.0544 | 0.7008 | 0.0587 |
| noise_aug | 25 | 8 | 0.8225 | 0.0508 | 0.8192 | 0.0544 |
| noise_aug | 50 | 8 | 0.8616 | 0.0235 | 0.8635 | 0.0233 |
| open_loop_basic | 10 | 8 | 0.3971 | 0.0744 | 0.2827 | 0.106 |
| open_loop_basic | 25 | 8 | 0.6522 | 0.0656 | 0.5934 | 0.0905 |
| open_loop_basic | 50 | 8 | 0.6415 | 0.0236 | 0.5862 | 0.0509 |
| open_loop_phys | 10 | 8 | 0.7834 | 0.0408 | 0.787 | 0.0411 |
| open_loop_phys | 25 | 8 | 0.8186 | 0.0221 | 0.8185 | 0.0254 |
| open_loop_phys | 50 | 8 | 0.8498 | 0.0219 | 0.8537 | 0.0218 |
| real_only | 10 | 8 | 0.6446 | 0.1085 | 0.6038 | 0.129 |
| real_only | 25 | 8 | 0.737 | 0.0374 | 0.7184 | 0.0426 |
| real_only | 50 | 8 | 0.7886 | 0.0195 | 0.7748 | 0.0252 |
| stats_only | 10 | 8 | 0.7196 | 0.0382 | 0.7192 | 0.0401 |
| stats_only | 25 | 8 | 0.7753 | 0.0371 | 0.7724 | 0.0385 |
| stats_only | 50 | 8 | 0.8268 | 0.0234 | 0.829 | 0.0234 |
| vae | 10 | 8 | 0.6821 | 0.0893 | 0.6641 | 0.1067 |
| vae | 25 | 8 | 0.7605 | 0.0317 | 0.7482 | 0.0422 |
| vae | 50 | 8 | 0.8314 | 0.0719 | 0.8277 | 0.0839 |
| vae_fs | 10 | 8 | 0.6298 | 0.0798 | 0.6047 | 0.1058 |
| vae_fs | 25 | 8 | 0.7547 | 0.0703 | 0.7397 | 0.0861 |
| vae_fs | 50 | 8 | 0.8104 | 0.0442 | 0.8079 | 0.0478 |

重要写作约束：当前完整主表里 BREEZE 相对 real-only 有稳定增益，但不是所有 n_real 下的全表最高；不能写成“最高准确率”除非后续实验支持。

Acceptance/cost 表：

| K | acceptance | mean LLM calls | slots |
| --- | --- | --- | --- |
| 0 | 0.5622222222222222 | 1.0 | 450 |
| 1 | 0.6555555555555556 | 1.4377777777777778 | 450 |
| 2 | 0.7333333333333333 | 1.7822222222222222 | 450 |
| 3 | 0.7888888888888889 | 2.048888888888889 | 450 |

显著性表预览（breeze_k3 对其他 baseline）：

| n_real | baseline | delta acc | p_wilcoxon |
| --- | --- | --- | --- |
| 10 | real_only | 0.08365 | 0.0234375 |
| 10 | noise_aug | 0.0291124999999999 | 0.4609375 |
| 10 | vae | 0.0462374999999999 | 0.3828125 |
| 10 | gan | 0.0103874999999999 | 1.0 |
| 10 | vae_fs | 0.0984874999999999 | 0.0546875 |
| 10 | gan_fs | 0.0173999999999999 | 0.7421875 |
| 10 | open_loop_basic | 0.3311999999999999 | 0.0078125 |
| 10 | open_loop_phys | -0.0550874999999999 | 0.078125 |
| 10 | stats_only | 0.0087124999999999 | 0.7421875 |
| 10 | envelope_only | -0.0681 | 0.015625 |
| 10 | breeze_k0 | 0.0148125 | 0.1796875 |
| 10 | breeze_k1 | -0.004425 | 1.0 |

## 6. 图表与论文草稿

- `paper/main.tex`：{'file': 'breeze/paper/main.tex', 'bytes': 18614, 'lines': 343, 'section_count': 7, 'has_todo_marker': True}
- `paper/main.pdf` exists：True

| figure | bytes |
| --- | --- |
| breeze/paper/figs/acceptance_k.pdf | 18714 |
| breeze/paper/figs/boxplots.pdf | 18659 |
| breeze/paper/figs/downstream_bars.pdf | 23071 |
| breeze/paper/figs/framework.pdf | 36245 |
| breeze/paper/figs/waveforms.pdf | 92956 |

## 7. 已完成、未完成与禁止写法

已完成可冻结：
- PU 主工况文件划分数据、c85/c90/c95 verifier、正式 LLM 闭环池、basic open-loop 池、Block 4 主表、Block 5 acceptance/pool/significance 表、主要 PDF 图。
- 本次快照过程中已重新运行 `figures.py` 和 `fig_framework.py`，五个 PDF 图均可由 `pdfinfo` 读取。

未完成或需复核：
- BREEZE-v2 高风险 gate 改进与离线重筛。
- 自建机床数据跨数据集实验。
- `downstream_file.csv` 未包含 per-class F1，若论文需要 IR 类 F1，必须补跑或修改训练输出。
- 四张数据图已由 `figures.py` 基于当前 CSV/NPZ 重跑；`framework.pdf` 是框架示意图，由 `fig_framework.py` 重跑，不依赖结果表。
- `paper/main.tex` 仍需按最终数据完整写作和逐数字溯源。

禁止写法：
- 禁止写 PU 原始数据只有 3 通道；只能写本项目选取并保留 3 路。
- 禁止把代码内部 X/Y/Z 写成 PU 三轴振动。
- 禁止写 BREEZE 在完整主表中全基线最高；当前数据不支持。
- 禁止把 `pool_physics_k3_v1` 旧池混入正式结论。
- 禁止把 verifier 阈值描述成用 test set 调过；当前协议是 train-only 校准。

机器可读原始统计：`reports/snapshot_raw_2026-07-04.json`
