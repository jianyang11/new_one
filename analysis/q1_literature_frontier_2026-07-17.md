# BREEZE 一区提升：2026-07-17 文献前沿与研究差距审计

## 1. 审计范围与证据规则

本报告服务于 `breeze_full-2` 的一区水平提升，不把搜索摘要、未来日期论文、未核验引用或本地历史结果当作已证实事实。检索截止时间为 2026-07-17 Asia/Shanghai。方法、数据集、结论和出版状态优先从期刊出版页、正式会议 proceedings、JMLR 等一手页面核验。预印本只用于发现方向，不能单独支撑“已形成领域共识”或“首次提出”的主张。

本轮检索聚焦五个问题：

1. LLM 直接或间接生成时序/机械信号的最新路线；
2. 轴承与旋转机械数据增强中扩散模型和物理先验的最新强基线；
3. 生成后筛选、可接受性控制和有限样本风险保证；
4. 跨工况、少样本和物理可解释诊断的评测门槛；
5. BREEZE 当前“固定生成池 + 单一 CNN + 训练集分位 gate”证据链相对前沿的真实差距。

## 2. 已核验的前沿工作

| 工作 | 出版状态与一手来源 | 方法核心 | 评测范围/主张边界 | 对 BREEZE 的直接含义 |
|---|---|---|---|---|
| BearGen | *Advanced Engineering Informatics*, 2026, DOI [10.1016/j.aei.2026.104400](https://doi.org/10.1016/j.aei.2026.104400) | LLM 生成信号描述，再以描述条件化扩散模型生成轴承信号；包含本地化 LLM 蒸馏 | 8 个公开轴承数据集；质量、少样本、严重不平衡和成本 | “LLM + 轴承合成”本身已不是创新；一区实验广度和强生成基线门槛显著提高 |
| SDForger | NeurIPS 2025 正式论文，[proceedings](https://proceedings.neurips.cc/paper_files/paper/2025/hash/70fb27f33beefef137e09bbd875c28ad-Abstract-Conference.html) | 将多元时序编码为紧凑文本表示，低成本微调自回归 LLM 后生成并解码 | 多领域数据；相似性和下游预测双轨评价 | “免训练”需与少量微调 LLM 的质量/成本正面对照；文本化时序生成不能被 Related Work 略过 |
| SCOPE-Gen | ICLR 2025 正式论文，[proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c2a96d676ac2716615bf1ab7edd3f3d3-Abstract-Conference.html) | 对黑盒生成器候选集做顺序贪心过滤，并以共形方法控制集合中至少含一个可接受样本的概率 | 自然语言和分子图；保证针对其定义的 admissibility | “生成后筛选 + 可接受性”已有严格统计路线。BREEZE 不能把经验分位过滤本身写成充分创新，必须明确保证对象、交换性条件和不可保证部分 |
| CAP | JMLR 2025, [paper page](https://www.jmlr.org/papers/v26/24-0452.html) | Calibration after Adaptive Pick，在在线选择后控制 false coverage-statement rate | 有限样本、分布无关；同时讨论分布漂移下的长期控制 | 闭环反馈会产生自适应选择，若声称风险控制，必须处理“先选择再报告”的统计口径，不能直接套普通窗口分位数 |
| Physics-informed diffusion augmentation | *Journal of Vibration and Control*, 2026, DOI [10.1177/10775463261455715](https://doi.org/10.1177/10775463261455715) | 多尺度小波先验、时序注意力和非对称 U-Net 融入扩散生成 | 两个轴承试验平台；物理保真和下游诊断 | BREEZE 的物理证据必须包含 gate 未直接优化的独立诊断，并与训练式物理扩散做公平对照 |
| DDPM-LFR | *Mechanical Systems and Signal Processing*, 2025, DOI [10.1016/j.ymssp.2025.113170](https://doi.org/10.1016/j.ymssp.2025.113170) | 局部特征细化、classifier-free guidance、动态 EMA 的一维扩散生成 | 直升机尾传动数据和 CWRU；质量、多样性、分类和泛化 | 简化 DDPM 只能作为基础基线，不能代表当前最强扩散路线；正式稿需披露与 DDPM-LFR 等方法的可比边界 |
| CFGDMHD | *Reliability Engineering & System Safety*, 2025, DOI [10.1016/j.ress.2024.110567](https://doi.org/10.1016/j.ress.2024.110567) | classifier-free guidance、混合/多样性损失与参数迁移 | 轴承少样本生成；强调多类和多样性 | 必须把生成模型的训练数据边界、迁移数据和类条件预算统一后再比较，不能用弱训练配置衬托 BREEZE |
| DiffUCD | *Measurement*, 2025, DOI [10.1016/j.measurement.2024.115951](https://doi.org/10.1016/j.measurement.2024.115951) | condition-guided diffusion 生成未知工况信号，并用无监督聚类过滤 | SDUST 与 PU；MMD、GAN-train/test 和跨工况 | “跨工况 + 生成后过滤”已有直接竞争者。BREEZE 的 CWRU load transfer 与 PU LOCO 失败必须完整保留，并增加真正独立的工况/实体协议 |
| PI-SSDG | *Information Sciences*, 2026, DOI [10.1016/j.ins.2026.123252](https://doi.org/10.1016/j.ins.2026.123252) | 物理一致性与不确定性感知的半监督域泛化 | 有限标注、无目标域训练的跨工况轴承诊断 | 一区审稿人会要求区分“生成增强”与“直接域泛化”收益；至少需要一个非生成跨工况强基线 |
| PFA-Net | *Scientific Reports*, 2026, DOI [10.1038/s41598-026-61244-9](https://doi.org/10.1038/s41598-026-61244-9) | 傅里叶/Hilbert 物理特征解耦、注意力和动态联合损失 | 强噪声、可解释轴承诊断 | 下游不能只依赖紧凑 CNN；至少要验证物理增强诊断器或现代时序骨干下的排序是否稳定 |
| Bearing RUL conformal calibration | PHM Europe 2026, DOI [10.36001/phme.2026.v9i1.4902](https://doi.org/10.36001/phme.2026.v9i1.4902) | 物理约束 RUL + MC dropout + 后验共形区间 | XJTU-SY 退化轨迹；保证是边际覆盖，不是逐轨迹条件覆盖 | 旋转机械领域已经开始要求“物理一致 + 不确定性校准”。BREEZE 可引入源组级校准，但必须准确限定为真实源组覆盖/拒绝风险，不得称为物理真值保证 |

## 3. 截止 2026-07-17 的方向判断

### 3.1 领域进展

第一，生成器侧已经从 GAN/VAE 进入条件扩散、物理先验扩散、描述条件化扩散和 LLM 微调时序生成并存的阶段。BearGen 在八个轴承数据集上把 LLM 语义描述与扩散生成结合，说明“LLM 能帮助信号合成”已被高水平期刊直接覆盖。BREEZE 的差异不应继续表述为“首次把 LLM 用于轴承信号”，而应集中在不训练目标生成器时，如何以可审计、可校准、无波形修补的方式控制显式配方生成。

第二，过滤侧已从经验阈值走向风险控制。SCOPE-Gen 对生成候选集合给出共形可接受性控制，CAP 进一步说明自适应选择后的统计报告需要单独处理。因此，BREEZE 当前按窗口估计多个分位 gate、再在一个固定池上报告接受率的做法不足以支撑“一般可靠性保证”。可行的升级不是更复杂的阈值拼接，而是源组独立的联合 nonconformity、明确交换性假设、对真实源组拒绝率的有限样本界，以及对闭环选择过程的独立审计。

第三，跨工况已成为必测维度。DiffUCD 和 PI-SSDG 都直接处理未知/变化工况。BREEZE 当前 CWRU load transfer 为正、PU LOCO 为负，这组结果有价值，但它证明的是不同协议下的边界，不是普遍跨工况能力。一区版本需要把工况、实体、文件三层分组写进数据合同，并至少建立一个训练阶段完全不读目标工况的正式协议。

第四，评价从“单个分类器精度”扩展到质量、效用、多样性、成本、隐私/记忆和不确定性。当前稿件已经补了物理距离、精确复制和相关性审计，这是良好基础；仍缺多个诊断骨干、多个独立生成池，以及把 pool-to-pool 方差纳入统计单位的推断。

### 3.2 BREEZE 仍然成立的独特资产

1. LLM 输出的是显式、可归档的物理配方，确定性 renderer 才生成波形；责任边界比端到端生成器清楚。
2. 失败候选被拒绝或反馈重采样，不通过局部波形修补进入训练池，符合可追溯性要求。
3. PU、CWRU、Berkeley 已有冻结数据、配方、gate 记录、统计表和失败链，能支持方法升级后的回放对照。
4. 当前稿件诚实保留 PU LOCO 六轮失败、Berkeley 规则收敛和单池推断边界，为新的预注册实验提供可信起点。

### 3.3 当前稿件距一区水平的硬差距

| 差距 | 当前证据 | 一区最低修复要求 |
|---|---|---|
| 创新定位 | training-free + deterministic admission，但经验 gate 与筛选已有强邻近工作 | 源组独立联合校准、明确有限样本风险对象、闭环自适应选择审计；不夸大为物理真值 |
| 强生成基线 | TimeGAN/DDPM 正式运行未完成；当前实现和协议仍需文献忠实性审计 | 至少一个忠实 GAN/TimeGAN 和一个忠实一维扩散基线；训练预算、数据、调参、失败次数全部披露 |
| LLM 必要性 | 主要对照是 rule、random、noise | 加入 train-stat estimator 与同配方空间的黑盒优化器；在相同 proposal/renderer/verifier 预算下隔离 LLM 贡献 |
| 分类器依赖 | 一个紧凑 1-D CNN | CNN、ResNet1D/InceptionTime/TCN 中至少三种，再加 MiniROCKET 或等价非深度强基线；排序需跨骨干稳定 |
| 推断单位 | 多训练 seed 围绕一个固定池 | 至少 10 个独立生成池；pool 为一级统计单位，训练 seed 嵌套其中；报告 pool-level CI/置换检验 |
| 校准与泄漏 | 训练集内分位数，历史协议不统一 | source/entity/regime 明确分组；reference/calibration/test 三分；测试源在校准、生成、调参阶段不可访问 |
| 独立物理诊断 | 部分指标与 gate 共用定义 | 至少一个 gate 未使用的留出物理指标族；grouped two-sample 与记忆审计；保留不利结果 |
| 可复现发布 | PU 可复放，CWRU/Berkeley 主波形池仍在 ignored runs | 建立 checksum release manifest；关键池、配方、renderer seed、gate report 可从公开包复放 |
| 存储与运行工程 | 项目约 51 GB；长基线日志为空且已停在 3 个 seed | 降至不高于 47 GB 工作水位；每 60 秒心跳、原子 checkpoint、任务分片、严格合并与断点续跑 |

## 4. 推荐的创新主线

建议将升级方法暂称为 **BREEZE-RC**（Risk-Calibrated BREEZE），直到实验通过再决定是否改正式题目。它不是在现有 gate 上增加一个“共形”标签，而是重构证据合同：

1. `Layer 0`：格式、长度、采样率、通道、非有限值和哈希合法性；
2. `Layer 1`：按独立 `source_id` 将 outer-train 划为 reference/calibration，形成源均衡的联合 generic nonconformity；
3. `Layer 2`：设备无关的时域、归一化谱形、多通道结构和 leave-one-source-out 多样性；
4. `Layer 3`：元数据门控的 bearing/milling physics plugin，状态严格为 `pass/fail/unavailable`；
5. `Risk certificate`：只对声明交换性范围内的真实源组拒绝风险/覆盖作有限样本陈述；不把该保证扩张为合成信号物理真值；
6. `Independent diagnostic ledger`：用 gate 未直接使用的指标、grouped two-sample、复制/相关性和跨工况结果检验证书外有效性；
7. `Hierarchical utility ledger`：独立生成池为一级重复，few-shot 抽样和分类器初始化为池内重复。

该主线相对现有文献的潜在贡献在于：把显式 LLM 配方、确定性物理 renderer、源组级风险校准、无修补闭环和层级效用推断放进同一可复放流程。是否能写成“首个”必须在投稿前再做一次系统检索，当前报告不作首次性断言。

## 5. 不可使用的论证捷径

- 不以更多窗口代替独立 source group 来制造共形样本量。
- 不把 verifier 通过率解释为物理正确率。
- 不把训练 seed 数量解释为独立生成池数量。
- 不把简化 DDPM/TimeGAN 标成当前 SOTA。
- 不因为训练时间长而减少正式 epoch、数据量或不报告失败 run。
- 不把 CWRU 同一试验台/同一轴承结构的文件划分写成跨机器或跨实体泛化。
- 不删除 PU LOCO 负结果，不通过改阈值恢复失败 pool。
- 不用 t-SNE/UMAP 的视觉分离代替统计距离或下游效用。
- 不在作者元数据、API provider seed、缺失机械元数据上做猜测。

## 6. 文献检索后续维护

每次正式方法冻结前执行一次增量检索，记录检索日期、查询式、来源、纳入/排除理由和 DOI。2026-07-17 之后在线优先发表但尚未正式编目的论文只进入候选表；只有核验正文/补充材料中的数据划分、基线配置和指标后，才进入论文 Related Work 或实验参数依据。
