# BREEZE 项目交接文档 / SOP

更新时间：2026-07-04（本机环境已布置，Block 4 主表、Block 5 指标、Block 6 图已补完；新增数据/通道与 verifier 风险快照）

## ★ 当前进度快照（最重要，先读这里）

已完成：
- Block 0-2：环境、PU 数据预处理、验证器（文件划分协议 c85/90/95 三套已校准，
  train 通过率 94.3% / test 90.5% @c90）。
- Block 3 全部完成：
  - `runs/pool_physics_file_k3/`：物理提示闭环生成，450 槽位全跑完，
    接受率 79%（healthy 83%，OR 87%，IR 67%）；轮数分布 1轮:253, 2轮:42,
    3轮:35, 4轮:25 → 说明闭环反馈有效（K 消融数据齐全）。
    认证池规模（含多种子扩增）：healthy 519 / OR 638 / IR 390
    （已缓存 `runs/pool_breeze_k3.npz`）。
  - `runs/pool_basic_file_k0/`：开环 basic prompt 450 槽位全跑完，
    认证通过率 0%（无物理指导的 LLM 无法通过验证器）→ 论文强对比点。
- 关键下游验证（8 seeds，n_real=10/25/50，文件划分）：
  - real_only: 0.678/0.741/0.790
  - + BREEZE 真实 LLM 池(k3): 0.736/0.777/0.820（+5.8/+3.6/+3.0 pt）
  - + BREEZE 参考配方池(v8 离线): 0.748/0.793/0.844
- Block 4 主表 `results/downstream_file.csv` 已补完：14 baselines × 3 n_real ×
  8 seeds = 336 行，missing=[]。均值（n_real=10/25/50）：
  - real_only: 0.645 / 0.737 / 0.789
  - noise_aug: 0.699 / 0.823 / 0.862
  - open_loop_phys: 0.783 / 0.819 / 0.850
  - envelope_only: 0.796 / 0.818 / 0.844
  - breeze_k0: 0.713 / 0.800 / 0.832
  - breeze_k1: 0.733 / 0.800 / 0.822
  - breeze_k2: 0.720 / 0.777 / 0.838
  - breeze_k3: 0.728 / 0.784 / 0.832
  ※ 当前完整主表中，breeze_k3 稳定提升 real_only，但不是全表最高；
  open_loop_phys/envelope_only/noise_aug 很强。若论文必须写“最高准确率”，
  需要把 BREEZE-family 物理验证变体作为主方法族，或继续做 BREEZE-v2
  使主方法真实超过这些强基线，不能只改措辞。
- Block 5 已补完：`results/acceptance.csv`, `pool_metrics.csv`,
  `significance.csv` 已生成。正式 K=3 接受率：K0 56.2%，K1 65.6%，
  K2 73.3%，K3 78.9%，mean LLM calls/window=2.05 @K3。
- Block 6 图已重跑：`paper/figs/waveforms.pdf`, `boxplots.pdf`,
  `acceptance_k.pdf`, `downstream_bars.pdf`。
- 机床私有数据已窗口化（proc/mt_*.npz，data_mt.py，文件划分 5 train/2 test）。

未完成（按 §5 SOP 顺序做）：
- 跨数据集（机床）实验、BREEZE-v2 高危 gate 改进与重筛实验、Block 7 论文正文、
  Block 8 终审。

## ★ 数据集、通道与鲁棒性快照（2026-07-04，避免误解）

### A. 当前主实验到底用了哪些数据与通道

1. **PU / Paderborn 主实验数据**
   - 主工况：`N09_M07_F10`。
   - 轴承：healthy `K001-K005`；OR `KA04/KA15/KA16/KA22/KA30`；
     IR `KI04/KI14/KI16/KI17/KI18/KI21`。注意：IR 包含 `KI17`。
   - 当前 `proc/*.npz` 中每个 PU window 形状为 `(3, 2048)`。
   - 当前项目实际使用的 3 路通道是：
     ```text
     ch0 = vibration_1      -> 振动/加速度，代码内简称 X
     ch1 = phase_current_1  -> 电机相电流 1，代码内简称 Y
     ch2 = phase_current_2  -> 电机相电流 2，代码内简称 Z
     ```
   - **重要：这里的 X/Y/Z 只是 verifier 内部短名，不是三轴振动。**
     `Z` 在 PU 主实验里是第二相电流，不是 Z 轴加速度。
   - 为什么只选这 3 路作为主实验：
     - 与当前 renderer/verifier 的物理假设一致：1 路机械振动 + 2 路电机相电流。
     - envelope/BPFO/BPFI gate 用振动通道；MCSA gate 用电流通道，能构成
       机械-电气一致性验证。
     - 3 通道窗口能控制 LLM recipe 复杂度和下游 CNN 输入维度，避免把未建模的辅助
       测量混入 verifier。
     - 当前 `proc` 就是按这 3 路预处理的，所有已完成实验均依赖这个协议。
   - **PU 原始数据一共多少通道：当前附件没有 PU 原始 `.mat`，只能确认本项目保留了
     以上 3 路，不能在论文里写“PU 原始数据只有 3 通道”。** `data.py` 会从原始
     `.mat` 的 `Y[i]["Name"]` 中只抽取 `CHANNELS` 列表内的 3 路；如果原始 `.mat`
     还有其它传感器/辅助测量，当前预处理会忽略。要给出“PU 原始全通道数”，必须
     重新下载一个原始 `.mat` 并枚举所有 `Y[i]["Name"]`。

2. **私有机床数据**
   - 原始 CSV 表头为：
     ```text
     X, Y, Z, Current
     ```
   - 当前 window 形状为 `(4, 2048)`：
     ```text
     ch0 = X       -> X 向振动/加速度
     ch1 = Y       -> Y 向振动/加速度
     ch2 = Z       -> Z 向振动/加速度
     ch3 = Current -> 单路电流
     ```
   - `mt_train_1/2/3.npz` 与 `mt_test_1/2/3.npz` 已存在。
   - **私有数据不能直接复用 PU verifier。** PU verifier 假设 `(振动, 电流1, 电流2)`；
     私有数据是 `(三轴振动, 单电流)`。跨数据集时需要单独的 channel schema：
     三轴振动 gate 应作用于 X/Y/Z 或三轴合成量 `sqrt(X^2+Y^2+Z^2)`，MCSA 只能作用于
     `Current`，且没有两相电流空间矢量。

### B. 当前物理验证是否鲁棒

已比较扎实的部分：
- sanity gate：shape、finite、非恒定、重复行检查。
- train-only quantile calibration：阈值只来自 train split，不碰 test。
- 文件划分协议：每个轴承前 80% 文件 train，后 20% test。
- envelope fault-frequency gate：BPFO/BPFI 来自 6203 轴承运动学，N09 工况
  `fr=15Hz, BPFO=46.06Hz, BPFI=73.94Hz`。
- 约束反馈闭环：失败项会转成定量反馈给 LLM，而不是后处理修波形。

仍是高危、需要 BREEZE-v2 处理的部分：
1. spectrum hard bands 太刚性。
2. resonance band 单一 SK 最大值选择不够稳健。
3. MCSA 没充分利用两相电流，且应先验证电流边带可靠性。
4. diversity embedding 只用 9 个宏观统计量，太粗。
5. PU 的 X/Y/Z 命名误导，容易把电流通道误解成空间轴。
6. 私有数据 4 通道，不能直接复用 PU verifier。

## ★ 高危问题的理解与建议实验路线（先离线重筛，再决定是否重跑 LLM）

### 1. Spectrum Gate：固定硬频带过刚性

当前逻辑：对振动 Welch PSD 用固定频带
`0-250, 250-500, 500-1000, ..., 3000-4000Hz` 计算能量比例：
```text
E_b = integral_b Pxx(f) df / integral_all Pxx(f) df
```
并要求 `E_b` 落在 train quantile 区间内。

问题本质：如果真实合理频峰跨在 250/500/1000Hz 等边界附近，小频移会让相邻两个
`E_b` 剧烈跳变，导致合理样本被错误 reject。

建议多尝试：
- v2-spectrum-A：重叠三角滤波器组。用平滑权重 `w_k(f)`：
  ```text
  E_k = integral Pxx(f) w_k(f) df / integral Pxx(f) df
  ```
  频峰跨边界时能量平滑转移。
- v2-spectrum-B：PSD Wasserstein/EMD 距离。把归一化 PSD 当频率分布：
  ```text
  p(f)=Pxx(f)/integral Pxx(f)df
  W1(p,q)=integral |CDF_p(f)-CDF_q(f)| df
  ```
  小频移只产生小距离，不会硬跳变。
- v2-spectrum-C：多尺度频带，保留当前 8 band，同时加 500/1000/2000Hz 宽带统计；
  只有多尺度一致偏离时才判异常。

### 2. Resonance Band：单一 spectral-kurtosis 最大带不够稳健

当前逻辑：在真实 fault train windows 上，以 1000Hz 宽度滑窗找 mean spectral kurtosis
最大的 band，作为 `B_y`。注意：`B_y` 不是由 LLM 样本决定，所以 LLM 生成的 3500Hz
噪点不会反过来改变 `B_y`；真正风险是 train split 中的偶发瞬态会让单一 SK 最大值偏置。

建议多尝试：
- v2-resonance-A：robust SK，用 median/trimmed mean 替代 mean，降低偶发尖峰影响。
- v2-resonance-B：SK + envelope evidence 联合打分：
  ```text
  Score(B)=robust_SK(B)+lambda*Prom_fault(B)-eta*BetweenBearingVar(B)
  ```
  只选“高 SK 且能在 BPFO/BPFI 显示包络证据、跨训练轴承稳定”的 band。
- v2-resonance-C：top-multi-band。保留 train-calibrated 的 2-3 个稳定共振带；
  候选样本在任一 train-supported band 上通过 envelope/energy 即可。不是放宽，
  而是把单点最大改成训练集支持的多模态共振。

### 3. MCSA：两相电流没有充分利用，且电流边带可靠性要先校准

当前逻辑：只在 `phase_current_1` 上估计供电基频 `fe`，检查 `fe ± BPFO/BPFI` 的
sideband prominence，并与 train quantile 阈值比较。

问题本质：电流故障边带通常很弱，单相电流容易因相位、噪声、PWM/逆变器干扰而不稳定。
如果把它当 hard gate，可能误杀本来振动证据充分的真实故障样本。

比较权威、科学的改法：
- 使用两相电流的空间矢量/Clarke 表示，这是电机电流分析中的标准思想，不是拍脑袋。
  对 PU 的两相电流 `i_a=phase_current_1, i_b=phase_current_2`，可在平衡三相假设下：
  ```text
  i_c = -(i_a+i_b)
  i_alpha = i_a
  i_beta  = (i_a + 2*i_b)/sqrt(3)
  S_i(f) = S_alpha(f) + S_beta(f)
  ```
  然后在 `S_i(f)` 上检测 `fe ± f_fault`。
- v2-mcsa-A：单相 Y、单相 Z、两相 vector-current 三种 MCSA score 都算，比较 train split
  上 fault-vs-healthy 分离度，选最可靠的作为 gate。
- v2-mcsa-B：可靠性校准。若 train split 中某工况/类别的电流边带与 healthy 不可分，
  MCSA 不作为 hard admission gate，而作为 certificate score/report。这个是
  sensor-reliability calibration，不是后处理补丁。
- v2-mcsa-C：用 sideband-to-carrier 或 dB 比值，而不是只用局部 prominence；
  同时报告 `20log10(A_sideband/A_fe)`，便于和 MCSA 文献对齐。

### 4. Diversity Filter：9 维宏观统计太粗

当前逻辑：每通道 `rms/kurtosis/crest`，共 9 维，按 real-real 最近邻距离 1% 分位数过滤
过近合成样本。

问题本质：RMS/kurtosis/crest 不能区分冲击时序、包络谱结构、相位和故障频率形态。
两个时域波形可能看起来完全不同，但这 9 个数一样；也可能宏观数不同但物理上重复。

建议多尝试：
- v2-div-A：扩展物理嵌入：
  ```text
  time stats: rms, peak, std, kurtosis, skewness, crest
  spectrum: soft-band energy 或 PSD Wasserstein coordinates
  envelope: BPFO/BPFI prominence, 2nd harmonic, IR sidebands BPFI±fr
  current: vector-current sideband score
  timing: envelope autocorrelation near 1/BPFO or 1/BPFI
  ```
- v2-div-B：两级 diversity。先按物理 embedding 过滤，再按 waveform/PSD 距离二次去重。
- v2-div-C：按类别自适应阈值，仍使用 real-real NN 距离分位数，避免手写 magic number。

### 5. 执行策略

不要先重跑 LLM。优先利用 `runs/pool_physics_file_k3/` 中已经保存的 round 样本做离线重筛：
1. 小样本：每类 10 slots 离线重筛，检查 pass/reject 原因和 pool 规模。
2. 中样本：每类 50 slots，跑 downstream 2 seeds 快速看趋势。
3. 全量：450 slots 全部重筛，缓存 `pool_breeze_v2_*.npz`，再跑完整 8 seeds。
4. 只有当离线重筛证明 v2 gate 确实提升或解释力更强时，再考虑重新调用 LLM。
5. 所有长任务必须断点续跑：每个 v2 配置单独输出 json/csv/npz，已有结果跳过。

## 0. 一句话概述
BREEZE = training-free、generator-agnostic 的闭环物理验证 + 约束反馈重采样框架：
LLM 生成"参数配方"（JSON）→ 确定性渲染器合成轴承振动+电流信号 → 物理验证器
（M1-M5 gate）判定 → 不通过则把违规转成自然语言反馈给 LLM 迭代（K 轮）→
通过的样本带证书入池 → 用于少样本故障诊断的数据增强。
目标：SCI 一区（首选 Advanced Engineering Informatics，对齐 BearGen 结构）。

## 1. 目录结构（当前本机项目根 `breeze_full-2/breeze/`；远端原根为 `/home/ubuntu/breeze/`）

```
breeze/
├── HANDOVER.md              # 本文档
├── .venv-breeze/            # 本机 Python 虚拟环境（不要用 tsfm）
├── ../proc/                 # 本机预处理窗口 npz（PU + mt，config.py 会自动识别）
├── data/                    # Paderborn(PU) 原始数据（远端有；本机附件未带原始 .mat）
├── data_mt/                 # 机床私有数据 CSV（X,Y,Z,Current；1_/2_/3_ 为三类）
├── runs/                    # 所有实验输出（验证器 json、生成池、日志）
│   ├── verifier_N09_M07_F10_file_c{85,90,95}.json  # 文件划分协议验证器（当前主用）
│   ├── pool_physics_file_k3/   # ★正式 LLM 闭环生成池（K=3, 150槽/类, 已完成）
│   ├── breeze_ref_pool_v8.npz  # 离线参考配方池（v8, 下游验证用）
│   ├── vae_fullcorpus_pool.npz / gan_fullcorpus_pool.npz  # 深度生成基线池
│   └── *.log                # 各种实验日志（downstream_check_v5..v8 等）
├── results/                 # 导出 CSV（论文表格数据）
├── paper/main.tex           # LaTeX 论文（AEI 格式骨架已有）
└── src/
    ├── config.py            # ★全局配置：FS=8k, WIN=2048, 类别/轴承划分、
    │                        #   LLM_BASE_URL/LLM_MODEL/LLM_MIN_INTERVAL（限速）
    ├── data.py              # PU 下载/解析/降采样/窗口化;
    │                        #   load_file_split(split,cond) = ★主划分协议
    ├── data_mt.py           # 机床数据窗口化 (mt_{split}_{cls}.npz) + load_mt
    ├── verifier/
    │   ├── features.py      # 时域统计/PSD/包络谱等特征
    │   └── verifier.py      # BreezeVerifier: M1 sanity, M2 boundary(分位数),
    │                        #   M3 diversity, M4 envelope(运动学), M5 spectral shape
    ├── renderer.py          # 确定性渲染器: recipe JSON → 3ch 信号
    │                        #   (成分正弦+随机瞬态+周期冲击+频段噪声+均衡化)
    ├── llm.py               # LLM client(限速锁, 2.2s/请求) + prompt + 配方解析
    ├── pipeline.py          # ★闭环生成主脚本（断点续跑：已存 json 的槽位跳过）
    ├── pools.py             # 从 run 目录组装各基线池(open_loop/stats_only/breeze_k*)
    ├── train.py             # SimpleCNN 下游训练/评估 (--split file|bearing)
    ├── models.py            # VAE/GAN 基线生成器
    ├── metrics.py           # MMD/多样性/统计检验
    ├── figures.py fig_framework.py  # 图表
    └── raw_pipeline.py      # MechaForge 风格原始数值 LLM 生成器（演示 generator-agnostic）
```

## 2. 关键协议与结论（勿改，论文数字依据）

- **主评估协议 = 文件划分**：每个轴承按测量文件时间序，前 80% 文件 → train，
  后 20% → test（`load_file_split`）。原因：原按轴承划分时测试轴承 KA30/KI21
  即使全真实数据训练也 0% 准确率（损伤机理不同），增强实验无提升空间。
- **验证器**：runs/verifier_*_file_c90.json 为主（c85/c95 做敏感性）。
  train 通过率 94.3%，test 90.5%。
- **渲染器均衡化**（renderer.py 最近改动）：按 band_weights 做温和逐频段 EQ
  （增益 0.7-1.4 截断）+ target_rms 归一。参考配方通过率 20% → 70%。
- **下游离线验证（8 seeds, 参考配方池 v8, cap=200 合成/类）**：
  n_real=10/25/50: real_only 0.678/0.741/0.790 → +BREEZE 0.748/0.793/0.844。
  这是 v8 参考配方池的开发检查结果，不等同于完整主表结论。
- **LLM 生成实测**（mimo API, K=2 pilot）：接受率 80%（prompt 修正后）。
  正式 K=3 全量池接受率 78.9%。
- 电流通道物理：近纯正弦 kurtosis≈1.505, crest≈1.49；振动 kurtosis 故障类需 >3.6。
- 当前 `verifier_N09_M07_F10_file_c90.json` 的故障共振带：OR 1800-2800 Hz；
  IR 200-1200 Hz；healthy 200-1200 Hz。早期 prompt hint 中出现过
  OR 600-1100 / IR 3000-3600Hz，那是生成提示经验，不是当前 c90 verifier 的最终 band。
- 运动学（6203, fr=15Hz）：BPFO=46.1, BPFI=73.9, BSF=30.5, FTF=5.8 Hz。

## 3. LLM API（★注意额度）

- 当前：`https://fufu.iqach.top/v1`，model `mimo-v2.5`，key 只放环境变量
  `DASHSCOPE_API_KEY`，不要写进论文/日志。**限速：串行 + ≥2.2s/请求**
  （llm.py 里全局锁强制，勿提高并发）。
- 节流规则：max_tokens=900、重试 3 次、一个配方渲染多种子扩增（1 配方→最多 5 个
  认证样本，不耗 API）、断点续跑（重复运行同一命令自动跳过已完成槽位）。
- 预算：正式池（K=3 physics 450 槽 + K=0 basic 450 槽）约 1200-1500 次调用。

## 4. 常用命令（本机用 `.venv-breeze/bin/python`；长任务 nohup 后台 + tail 日志）

```bash
cd "/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze"
export DASHSCOPE_API_KEY="..."

# 正式闭环生成（断点续跑，重复执行安全）
nohup .venv-breeze/bin/python src/pipeline.py --k 3 --n 150 \
  --out runs/pool_physics_file_k3 --workers 2 > runs/pool_physics_file_k3.log 2>&1 &

# 开环基线（basic prompt, K=0）
nohup .venv-breeze/bin/python src/pipeline.py --k 0 --n 150 --prompt basic \
  --out runs/pool_basic_file_k0 --workers 2 > runs/pool_basic_file_k0.log 2>&1 &

# 组装池: python -c 'from pools import build_pool; ...' (mode=breeze/k, open_loop_*)
# 下游主表: .venv-breeze/bin/python src/train.py --split file ...（详见 train.py argparse）
```

## 5. 剩余工作 SOP（按序）

1. ~~等 pool_physics_file_k3 跑完~~ 已完成（450/450，接受率 79%）。
2. ~~跑 pool_basic_file_k0~~ 已完成（450/450，认证通过率 0% = 开环对比点）。
3. ~~Block 4 主表~~ 已完成。复核/续跑命令：
   ```bash
   nohup .venv-breeze/bin/python src/train.py --split file --seeds 8 --n_real 10 25 50 \
     --baselines all > runs/block4_main.log 2>&1 &
   ```
   自动跳过 results/downstream_file.csv 已有的行。
4. ~~Block 5~~ 已完成：metrics.py 算 MMD/多样性 + Wilcoxon 显著性。
   覆盖率 c85/c90/c95 的主表敏感性仍可作为后续补充。
5. **BREEZE-v2 高危 gate 改进**：先用现有 `pool_physics_file_k3` 离线重筛，
   不急着重跑 LLM；按上文 v2-spectrum/resonance/mcsa/diversity 方案小样本→中样本→全量。
6. **跨数据集实验**：机床数据（data_mt.py 已窗口化）上重新校准验证器
   （只用通用 gate，不用轴承运动学 gate），证明即插即用。
7. ~~Block 6 图表~~ 已重跑：figures.py（波形/包络谱、boxplots、接受率 vs K、主表柱状）。
8. **Block 7 论文**：paper/main.tex 填入结果；结构对齐 BearGen
   （Intro/Related/Method(M1-M5+闭环)/Experiments/Ablation/Conclusion）。
9. **Block 8 终审**：数字与 results/*.csv 一一对应、拼写、图注、附录。

## 6. 注意事项 / 坑

- 不要用 bearing 划分做主表（KA30/KI21 无法学习，见 §2）。
- pipeline.py 的 verifier 文件名带 `_file_`（文件划分校准），别加载旧的
  verifier_N09_M07_F10_c90.json（那是 bearing 划分版）。
- runs/pool_physics_k3_v1（旧架构池）已废弃，勿混用。
- CNN 训练在 CPU 上一次 fit 约几十秒；主表已补完，复跑全表仍建议用 nohup。
- LLM 输出偶有非 JSON → parse_recipe 返回 None 自动反馈重试，属正常。
- 每类池样本量：认证池按 cap=200/类混入效果最好（v8 实验）。
- 论文卖点排序：①下游准确率提升(硬指标) ②零训练/即插即用 ③闭环反馈可量化
  ④证书化+覆盖率保证 ⑤跨数据集/双生成器通用性。
