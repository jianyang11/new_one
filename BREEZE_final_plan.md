# BREEZE 论文最终方案：方向确定、参考论文、写作方法与分块执行计划

> 前置论文：MechaForge: A Multi-Strategy Time-Series Synthesis Framework for Intelligent Fault Diagnosis（Appl. Sci. 2026）
> 目标：中科院一区 SCI；生成数据但**不训练任何生成模型**；框架名 BREEZE

---

## 一、方向分析（有哪些可选方向）

结合 MechaForge 留下的缺口（Basic LLM 合成信号 RMS/peak/std 偏大、kurtosis 近高斯而真实故障信号高冲击、未验证包络谱/故障频带一致性、生成后只有格式检查没有物理质检、论文自己在 limitation 中明确写了"post-generation acceptance filtering... not part of the present pipeline"），以及 2024–2026 文献格局，可行方向共 7 条：

| # | 方向 | 免训练程度 | 即插即用性 | 创新性 | 可实现性 | 与 MechaForge 差异 | 审稿风险 | 结论 |
|---|---|---|---|---|---|---|---|---|
| A | **闭环物理验证 + 约束反馈重采样**（verifier-guided constrained resampling） | ★★★★★ 完全免训练 | ★★★★★ 可包裹任意生成器 | ★★★★☆ | ★★★★★ | 大（open-loop→closed-loop） | 低 | **主线** |
| B | BREEZE-score 入池筛选/排序（只筛不反馈） | ★★★★★ | ★★★★★ | ★★★☆☆ | ★★★★★ | 中 | 中（易被说成后处理） | 并入 A 作为 ablation |
| C | 统一物理可行域形式化（admissibility constraints F_m） | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ | 大 | 低 | **并入主线**（提供理论骨架） |
| D | LLM 信号生成物理可信度评测协议/基准 | ★★★★★ | ★★★★★ | ★★★☆☆ | ★★★★★ | 中 | 中（单独发不够硬） | 作为实验贡献并入 |
| E | 振动 + MCSA 多传感器一致性验证 | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★☆☆ | 大 | 中 | 作为增强模块（可选约束） |
| F | 更复杂 prompt / LLM self-refine 自评 | ★★★★★ | ★★★★☆ | ★★☆☆☆ | ★★★★☆ | 小 | 高（无新意） | 不做主线，作对照 baseline |
| G | 训练 physics-informed diffusion / 微调 LLM | ★☆☆☆☆ 需训练 | ★★☆☆☆ | ★★★★★ | ★★☆☆☆ | 大 | 高（算力+偏离免训练要求） | 排除 |

### 最终选定方向（最免训练、最即插即用）

**主线 = A + C + D（E 作为可选增强，B 作为消融变体）：**

> **BREEZE：一个 training-free、即插即用（plug-and-play）的闭环物理验证与证书化入池框架 —— 把任意 LLM 信号生成器包裹在"物理可行域定义 → 确定性物理验证 → 结构化约束报告 → 反馈重采样 → 证书化入池"的推理期闭环中。**

为什么这条最优：
1. **零训练**：验证器全部由信号处理（Welch PSD、Hilbert 包络、包络谱峰检测）+ 轴承运动学（BPFO/BPFI/BSF/FTF）+ 真实训练集鲁棒统计（分位数边界）构成，无任何可学习参数。
2. **真正即插即用**：BREEZE 是 wrapper，生成器可以是 Qwen3-Max、GPT、DeepSeek，甚至 GAN/diffusion——"generator-agnostic" 是审稿人无法否认的卖点。
3. **与文献缝隙精准对齐**：2025–2026 的竞争工作（BearGen/AEI 2026、物理约束 GAN/MST 2025、HAWAN-PIR 2025、Physics-Informed Diffusion）全部走"训练新生成器 + 物理损失"路线；**推理期免训练的物理验证-反馈闭环还没人在轴承信号合成里系统做过**。ChatTS/Self-Refine 证明闭环反馈范式成立，但反馈来自 LLM 自评而非确定性物理验证器——这正是 BREEZE 的区分点。
4. **与 MechaForge 完美衔接不冲突**：MechaForge 证明 LLM 合成信号有诊断价值并在 limitation 中亲自点名"post-generation acceptance filtering"是 open limitation；BREEZE 就是回答这个 open limitation 的论文。

核心命题（一句话）：
> LLM 生成的信号并不天然物理可信；BREEZE 在不训练任何模型的前提下，通过物理可行域约束采样与证书化入池，控制"哪些合成样本被允许进入训练集"。

---

## 二、最具参考性的论文

### 2.1 首选写作范文（最能参考写法的 1 篇）

**BearGen: LLM-guided signal generation framework for bearing fault diagnosis**, *Advanced Engineering Informatics*, 2026, DOI: 10.1016/j.aei.2026.104400（中科院一区）

理由——它是与 BREEZE 题材最近（LLM + 轴承信号生成 + 下游诊断）且刚发表在一区的论文，其写法值得逐节模仿：
- **Introduction 套路**：数据稀缺 → 现有生成方法缺陷（GAN 模式崩塌等）→ LLM 机遇 → 现有 LLM 方法的具体缺口 → 三条贡献。BREEZE 只需把"缺口"换成"open-loop 无物理验证"。
- **实验规模标杆**：8 个公开轴承数据集、FID/KID 生成质量指标 + 下游分类双轨评价、类不平衡与少样本工业场景模拟。这告诉你一区对实验广度的期待（BREEZE 至少 2–3 个数据集 + 双轨指标）。
- **"质量评价 + 下游效用分离"的叙事**：BearGen 单独验证了描述的 reliability——BREEZE 同样要把 physical fidelity 与 diagnostic utility 分开成两组结果。

### 2.2 方法与定位参考（按用途分类）

**(a) 免训练 LLM 时序生成范式（证明赛道热度）**
- SDForger（NeurIPS 2025, IBM）：LLM 生成多元时序，低成本、few-sample——引作生成器侧最新范式。
- ChatTS（2025）：时序-语言模态对齐问题——支撑"LLM 数值文本生成脆弱、需要外部验证"的动机。

**(b) 闭环反馈范式（BREEZE 的算法学基础）**
- Self-Refine: Iterative Refinement with Self-Feedback（NeurIPS 2023）——引作推理期反馈闭环范式；明确区分：BREEZE 反馈来自**外部确定性物理验证器**而非 LLM 自评。
- LLM rejection sampling / verifier-guided generation 类工作（如 best-of-n with verifiers）——支撑"约束采样"形式化。

**(c) 物理验证器的信号处理依据（一区硬度来源）**
- Antoni & Randall, "The spectral kurtosis: application to the vibratory surveillance and diagnostics of rotating machines", *MSSP* 2006 —— 谱峭度/共振带选择的经典依据（MechaForge 已引，继续用）。
- Randall & Antoni, "Rolling element bearing diagnostics—A tutorial", *MSSP* 2011 —— 包络分析、BPFO/BPFI 检测的标准流程，是 verifier 每个 gate 的权威出处。

**(d) 竞争对手（Related Work 中"训练式物理约束生成"一节）**
- 时频物理引导多模态 GAN（*Meas. Sci. Technol.* 2025, DOI: 10.1088/1361-6501/ae1a04）：把衰减冲击响应、转速调制写成可微约束 + 用 DTW/包络谱偏差/统计相似度做多维评估——**它的评估指标可直接借为 BREEZE 的 verifier 指标，但它需要训练 GAN，正好反衬 BREEZE 免训练**。
- HAWAN-PIR（*Automation* 2025）：提出 CMSQI 合成质量指数（判别分数+物理保真+类平衡）——引作"合成质量指数"先例，指出其仍绑定训练式 GAN。
- 深度特征增强 GAN + automatic data filter（*MSSP* 2022, DOI: 10.1016/j.ymssp.2021.108139 一类）：训练式框架里内嵌数据过滤器——引作"入池过滤"先例，指出其过滤器是学习式判别器而非确定性物理验证。
- Physics-Informed Diffusion Models（2024–2025）：物理残差进训练目标——反衬免训练路线。

**(e) LLM + 轴承诊断（说明领域正在拥抱 LLM）**
- Tao et al., "LLM-based framework for bearing fault diagnosis", *MSSP* 2024 (112127)；BearLLM；FD-LLM；DiagLLM (*Sci. China Inf. Sci.* 2025)；T2MFDF (*IEEE TIM* 2025)。

### 2.3 目标期刊（按冲刺顺序）

1. **Mechanical Systems and Signal Processing (MSSP)** —— 一区 Top。要求：物理验证器必须硬（包络谱、谱峭度带选择、order-domain），跨工况实验、统计显著性。
2. **Advanced Engineering Informatics (AEI)** —— 一区，BearGen 就在这里，编辑对 LLM+工业信息学接受度高。**推荐首投**。
3. **Reliability Engineering & System Safety (RESS)** —— 一区，可把"证书化入池 = 合成数据可靠性保证"往可靠性叙事上靠。
4. 备选二区：EAAI、ESWA、KBS、Measurement。

---

## 三、BREEZE 论文怎么写（方法 + 结构）

### 3.1 题目（首选）

> **BREEZE: A Training-Free Closed-Loop Physics-Verification Framework for Certified Admission of LLM-Generated Bearing Fault Signals**

Acronym 展开：**B**oundary-**R**estricted **E**nergy-**E**nvelope **Z**ero-shot **E**valuation with closed-loop feedback。

### 3.2 方法（Method 章的四个模块）

```text
real training seed pool + metadata (class, channel, speed, load)
        ↓
[固定 LLM 生成器 G]  ←──────────────┐
        ↓                            │ 结构化约束报告
[M1 格式/合法性解析器]                │ (constraint report)
        ↓                            │
[M2 物理验证器 → 可行域 F_m 判定] ────┘ 不可行时反馈重采样（≤K 轮）
        ↓ 可行
[M3 多样性/非复制守门]
        ↓
[M4 证书化入池：accepted pool + physics certificate]
```

**M1 解析与合法性 gate**：长度、通道数、NaN/Inf、重复行、采样率与元数据齐全。

**M2 物理验证器（核心，全部免训练）**，可行域 F_m = {x | c_i(x,m) ≤ τ_i}：
- *Boundary-Restricted 统计边界*：按类别×通道×工况从真实训练集用 median/IQR 或分位数估计 mean/std/RMS/peak/crest/kurtosis/skewness 区间；阈值由训练集覆盖率（90–95% 真实窗口通过）确定，不用测试集、不按最终准确率调参。
- *Energy / fault-band gate*：Welch PSD；总能量与通道能量比；BPFO/BPFI 频带能量占比；共振带能量；带宽 = max(FFT 分辨率, 转速波动容差, 传感器容差)，转速变化大时转 order-domain。
- *Envelope-spectrum gate*（与 MechaForge 拉开差距的关键）：带通至共振区（可用谱峭度选带）→ Hilbert 包络 → 平方包络谱 → 检查 BPFO/BPFI/BSF/FTF 及前 2–3 阶谐波的 peak proximity error、prominence、harmonic consistency；内圈故障额外检查转频调制边带。
- *（可选）MCSA sideband gate*：电流通道 f_e ± m·f_fault 边带、Y/Z 相干性；不要求 X 与 Y/Z 高相关。

**M3 多样性守门**：nearest-neighbor distance（防复制 seed）、MMD/DTW/ACF distance（防塌缩）、acceptance–diversity curve。

**M4 反馈重采样 + 证书**：失败项→结构化约束报告（量化的违反幅度 + 可执行的再生成指令，非"make it more physical"）；闭环轮数 K∈{0,1,2,3} 作为实验变量；每样本记录 sample_id/prompt_hash/round_id/verifier_scores/fail_reasons/accepted，天然支持断点续跑；被接受样本附 physics certificate（各 gate 得分向量）。**明确禁止波形局部修补（no post-hoc repair）**——不可行就拒绝，这是防"后处理补丁"质疑的关键立场。

### 3.3 贡献三条（按一区写法）

1. A **training-free, generator-agnostic closed-loop quality-control framework**：用确定性物理验证器 + verifier-guided constrained resampling 包裹现成 LLM 生成器，不训练新生成模型、不修补波形。
2. A **bearing-physics verifier for synthetic-signal admission**：自适应统计边界 + 能量一致性 + 包络谱故障频率对齐 + 故障频带保持 +（可选）MCSA 边带一致性，全部阈值来自训练集鲁棒统计。
3. A **physical-fidelity-aware synthetic-pool protocol**：把物理保真与诊断效用分离评价，报告接受率、重采样成本、多样性与种子级稳健性。

**措辞红线**：写 "BREEZE controls which generated samples are admitted into the training pool"。

### 3.4 章节结构（对齐 BearGen/MSSP 式写法）

1. Introduction（1.5 页）：数据稀缺 → LLM 合成潜力（引 MechaForge/SDForger/BearGen）→ open-loop 物理可信缺口 → BREEZE 定位 → 三贡献。
2. Related Work（1.5 页）：① 故障诊断合成数据（GAN/VAE/diffusion/物理约束训练式）② LLM 时序生成 ③ 推理期反馈与验证范式 ④ 轴承物理验证信号处理。
3. Problem Formulation（0.5–1 页）：固定生成器、可行域 F_m、certified admission、training-free 边界。
4. BREEZE Method（3–4 页）：四模块 + 算法伪代码 + 复杂度/成本分析。
5. Experimental Setup（2 页）：数据集（Paderborn 主 + CWRU/KAIST 泛化）、group split、baselines、指标、实现细节。
6. Results（4–5 页）：物理一致性 → 下游分类 → 消融 → K 轮成本/接受率权衡 → 案例研究（一条被拒样本的约束报告全过程图）。
7. Discussion（1 页）：为什么不训练生成器、失败模式、阈值敏感性、跨工况限制。
8. Conclusion。

### 3.5 实验设计要点

- **Baselines（11 个）**：Real-only；MechaForge Basic LLM open-loop；Physics-Guided prompt open-loop；随机噪声增强；VAE；GAN；stats-only filter；envelope-only filter；LLM self-refine（无外部验证器，对应方向 F）；BREEZE-no-feedback（只筛选）；BREEZE-full。
- **物理指标**：RMS/peak/std/kurtosis 分布差；fault-band energy ratio error；envelope peak proximity/prominence/harmonic consistency；MCSA sideband score；多样性（NN distance、MMD、DTW、ACF）；acceptance rate 与重采样成本。
- **下游指标**：Accuracy、macro-F1、per-class F1（单独强调内圈故障 F1——MechaForge 最弱类）；5–10 seeds 给均值±std+置信区间；paired Wilcoxon（非正态）/paired t-test。
- **划分**：所有阈值只从 train split 估计；test set 完全隔离；加 cross-speed/cross-load split（Paderborn 补齐 N09_M07_F10 以外工况）；CWRU 或 KAIST 作外部泛化。
- **消融**：去掉每个 gate；no-feedback；自然语言反馈 vs 结构化约束报告；K=0/1/2/3；1/3/5/10-shot；synthetic pool size 小/中/大。

### 3.6 摘要骨架（可直接扩写）

> Fault data scarcity limits intelligent bearing diagnosis, and LLMs have recently been shown to generate diagnostically useful time-series augmentations. However, existing physics-guided prompting remains open-loop: physical priors are described in prompts, but generated signals are rarely verified against bearing kinematics, envelope spectra, or fault-band consistency before entering the training pool. This paper proposes BREEZE, a training-free, generator-agnostic closed-loop framework... [验证器构成] ... Failed generations are converted into structured constraint reports for verifier-guided resampling; only feasible samples are admitted with physics certificates, without post-hoc waveform repair. Experiments on [datasets] show...

### 3.7 审稿风险与防御（写作时预埋）

| 质疑 | 防御 |
|---|---|
| 只是后处理筛选 | 定位为 constrained sampling + certified admission；闭环反馈+可行域形式化+证书是算法贡献；training-free 是优势不是缺陷 |
| 阈值人为调参 | 全部来自训练集分位数；附敏感性分析（覆盖率 85/90/95%） |
| 下游提升来自选择偏差 | 报告 acceptance rate、多样性、NN distance；acceptance–diversity curve |
| 物理更真 ≠ 分类更好 | 主动把两者分离评价，作为论文亮点讨论 |
| 跨工况不足 | cross-speed/load split + 外部数据集；不夸大声明 |

---

## 四、所需资源

| 资源 | 说明 | 成本 |
|---|---|---|
| 数据 | Paderborn（已有）、CWRU（免费下载）、KAIST/SEU（免费） | 0 |
| LLM API | Qwen3-Max（与 MechaForge 一致）；估算：~10 类 × ~500 样本 × 平均 2 轮 ≈ 1–2 万次调用 | 约 ¥500–2000（按 token 计） |
| 算力 | 仅下游 CNN 训练（复用 MechaForge 的 CNN），单卡（甚至 CPU/消费级 GPU）即可；verifier 纯 CPU | 已有即可 |
| 软件 | Python + numpy/scipy（Welch、Hilbert）+ PyTorch + MechaForge 现有代码 | 0 |
| 前置资产 | MechaForge 代码、prompt、Paderborn 划分、CNN 训练脚本 | 已有 |

**无需任何生成模型训练算力——这是本方案的资源优势。**

## 五、用时估算

| 阶段 | 内容 | 用时（全职人力/AI 并行可压缩） |
|---|---|---|
| P1 | 验证器 v0 实现 + 小样本跑通（先 20–50 样本反复测试） | 1.5 周 |
| P2 | 闭环反馈 + 断点续跑 + 全量生成（K=0..3） | 1.5 周 |
| P3 | 下游训练 + 全部 baselines + 多 seed | 2 周 |
| P4 | 消融 + 跨工况 + 外部数据集 | 2 周 |
| P5 | 图表 + 统计检验 | 1 周 |
| **实验合计** | | **约 8 周（多 AI 并行可压至 4–5 周）** |
| W1 | Method + Problem Formulation 初稿 | 1 周（可与 P3 并行） |
| W2 | Intro + Related Work | 0.5 周 |
| W3 | Experiments + Results + Discussion | 1.5 周 |
| W4 | 摘要/结论/润色/格式/图美化 | 1 周 |
| **写作合计** | | **约 4 周（与实验并行，净增 2–3 周）** |
| **总计** | 投稿就绪 | **约 10–11 周；多 AI 并行约 7–8 周** |

---

## 六、分块执行计划（可直接分配给其他 AI）

每块含【输入 / 任务 / 输出 / 验收标准 / 预计用时 / 依赖】，块间接口用文件约定，可并行。

### Block 1：数据与基础设施（AI-1）
- 输入：Paderborn 原始数据、MechaForge 划分代码。
- 任务：整理 group split（bearing ID 级）；补齐多 speed/load 工况；下载并预处理 CWRU/KAIST；写统一数据加载接口 `dataset.py`；实现断点续跑日志 schema（sample_id, label, seed_id, prompt_hash, round_id, verifier_scores, fail_reasons, action, accepted, output_path）。
- 输出：`data/` 目录 + `splits.json` + `dataset.py` + `runlog_schema.md`。
- 验收：train/test 无泄漏（bearing ID 不重叠）；三数据集加载单测通过。
- 用时：4–5 天。无依赖。

### Block 2：物理验证器（AI-2，核心块）
- 输入：Block 1 的 train split；轴承几何参数（BPFO/BPFI 公式）。
- 任务：实现 M1 解析 gate；统计边界 gate（分位数阈值，覆盖率 90–95% 可配）；Welch PSD 能量/fault-band gate；谱峭度选带 + Hilbert 包络谱 gate（BPFO/BPFI/BSF/FTF + 谐波峰检测）；MCSA gate；多样性守门（NN/MMD/DTW/ACF）；输出结构化约束报告 JSON。
- 输出：`verifier/` 包 + 单测 + `verifier_report_spec.md`。
- 验收：在真实 train 窗口上通过率≈设定覆盖率；能抓出 MechaForge 已知问题（对其公开合成样本，RMS/kurtosis/包络 gate 必须报警）；每个 gate 有独立开关（供消融）。
- 用时：1.5–2 周。依赖 Block 1 的 train split（可先用旧划分并行开发）。

### Block 3：闭环生成管线（AI-3）
- 输入：MechaForge prompt 与 API 代码；Block 2 的 verifier 接口。
- 任务：封装 LLM 生成器（Qwen3-Max，参数与 MechaForge 一致以保可比性）；实现约束报告→再生成指令模板；K 轮闭环控制（K=0/1/2/3 可配）；并行调用 + 限速 + 断点续跑；先 20–50 样本小规模跑通迭代，确认接受率与报告质量后再全量。
- 输出：`pipeline/` + 全量 synthetic pools（每个 K、每个 track 一个 pool）+ 运行日志。
- 验收：小样本演示中至少 1 个失败样本经反馈后转为可行；全量运行可从中断点恢复；每 pool 附接受率/成本统计。
- 用时：1.5–2 周。依赖 Block 2。

### Block 4：下游训练与 baselines（AI-4）
- 输入：MechaForge CNN 代码；Block 1 数据接口；Block 3 的 pools。
- 任务：复现 Real-only / Basic LLM / Physics-Guided / 噪声 / VAE / GAN baselines；跑 BREEZE 各变体；5–10 seeds；cross-speed/load 与外部数据集实验；1/3/5/10-shot 与 pool size 扫描。
- 输出：`results/` 全部 CSV（每行：setting, seed, acc, macro-F1, per-class F1）。
- 验收：Real-only 与 MechaForge 报告数值可复现（±1%）；所有 setting 有 ≥5 seeds。
- 用时：2 周（GPU 上可并行多 setting）。依赖 Block 3。

### Block 5：物理指标评测与统计分析（AI-5）
- 输入：Block 3 pools + Block 2 verifier + Block 4 results。
- 任务：计算全部物理一致性指标与多样性指标；acceptance–diversity curve；K 轮 quality-gain/cost 曲线；Wilcoxon/t-test + 置信区间；阈值覆盖率敏感性分析。
- 输出：`analysis/` 统计表 + 显著性标注。
- 验收：每个主结论有 p 值支撑；敏感性分析覆盖 85/90/95%。
- 用时：1 周。依赖 Block 3、4。

### Block 6：图表制作（AI-6）
- 输入：Block 5 分析结果。
- 任务：框架总览图（对齐 BearGen 风格）；verifier 流程图；真实 vs 合成 vs BREEZE 接受样本的时域/包络谱对比图；箱线图（RMS/kurtosis 分布）；acceptance–diversity 与 K-cost 曲线；混淆矩阵；一条被拒样本的约束报告案例图。
- 输出：`figures/`（PDF/SVG，期刊双栏规格）。
- 验收：全部图 300dpi+，字号统一，可直接进 LaTeX。
- 用时：1 周。依赖 Block 5。

### Block 7：写作（AI-7，可与 Block 4–6 并行启动）
- 输入：本方案文档；BearGen 全文（写法范文）；MechaForge 全文；Block 5/6 产出。
- 任务：按 3.4 章节结构写作；Method 先行（不依赖实验结果）；Related Work 引用第二节文献清单（2025–2026 前沿 + 经典信号处理）；Results 按"物理一致性→下游效用→消融→成本"顺序；预埋 3.7 防御表的讨论。
- 输出：LaTeX 全稿（目标期刊模板：AEI/Elsevier 或 MSSP）。
- 验收：结构完整、贡献三条与实验一一对应、每个数字可溯源到 results CSV。
- 用时：4 周（滚动进行）。Method/Intro 无依赖，Results 依赖 Block 5/6。

### Block 8：终审与投稿（人工 + AI-8）
- 任务：交叉核对数字、查重、语言润色、cover letter、highlights、图形摘要、按最新中科院分区确认期刊、准备 supplementary（约束报告示例、全部 prompt、运行日志规范）。
- 用时：1 周。依赖全部。

**并行调度建议**：第 1–2 周 Block 1+2 并行（Block 7 的 Intro/Related Work/Method 同步动笔）；第 3–4 周 Block 3；第 5–6 周 Block 4+5；第 7 周 Block 6 + Results 写作；第 8 周 Block 8。**总计约 8 周投稿就绪。**

---

## 七、执行提醒（给各 AI 的统一注意事项）

1. 全部 Python 通过指定 anaconda 环境运行；长任务不设短 timeout。
2. 批量任务一律"少样本跑通 → 再全量"，并带断点续跑。
3. 参数选择必须有依据（阈值=训练集覆盖率、带宽=分辨率/转速容差公式、K 由成本-收益曲线定），不许拍脑袋。
4. 不接受数据编造：所有报告数字必须来自实际运行产出的 CSV/日志。
5. 阈值与任何筛选决策严禁接触 test set。
