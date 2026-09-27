# Mode B v2（新契约：Jev yes 全收，无 rubric/无剪枝）— Q2 回答

**Query**: 基于电子健康记录（EHR）数据用机器学习算法预测中风/卒中风险：关键风险因素及其影响分析（L1 保留：生命科学与医学）

## Search Paths
L0 目录 11 KBs → L1 保留 1 shelf → L2 53 条文档描述 → L3 全部可信 → L4 重叠排序全读 11 篇（42 篇 unscanned 如实报告，部分扫描）→ L5 真实 Laya（laya_sdk, criterion=evidence, threshold 0.5）：**79/79 段打分 → 77 段判 yes 全部保留（5+ 篇文档，0.575–0.978）** → L5.5 聚合（证据包 40k 字符）→ L6 直接从全幸存集作答。耗时 **3.9 min**（与 v1 持平）。

## Answer（直接回答）
金标论文（Nwosu et al., *Predicting Stroke from EHR*，8 段全幸存）给出：**年龄与婚姻状态对前两个主成分贡献最高；居住类型几乎无贡献**（PCA 双标图原文可引：*patient's residence type has no contribution… age and marital status have the highest contribution*）。主成分结构：PC1 对峙吸烟状态与其余属性；PC2 分离医疗特征（血糖/BMI/高血压/心脏病）与生活方式（年龄/婚姻/工作类型）；前两主成分分不开卒中标签簇，需更高维特征。基准：1000 次随机下采样实验，**前馈 MLP 最佳准确率 75.02%**，决策树≈随机森林。

## Knowledge Enhancement（全幸存集附加知识）
同批保留的 77 段中还有 69 段来自同库临床 ML 研究，按契约全部交付：

- **sci2cl（29 段，最高 0.978）**：单细胞数据整合方法——同库高分邻居，跨任务参考。
- **continuous-time probabilistic models（17 段）**：临床事件流的连续时间概率建模——EHR 时序建模的进阶路线。
- **clinical drug representations（15 段）**：临床药物表示学习——EHR 特征工程的药物侧补充。
- **lung cancer profiling（8 段）**：EHR 用于癌症分型的同类方法论，可与 stroke 管线互相印证。

## Sources（全部 Jev yes）
- [0.978] sci2cl (part 3) · [0.921] stroke 论文 future-work 段 · [0.9] stroke 相关工作段 · [0.88] stroke 标题/摘要段 · [0.817] **stroke PCA 段（答案核心）** · [0.805] stroke 讨论 · [0.719] **stroke 基准段（75.02%）** 等 5+ 文档 77 段，逐段含行号/Jev 分溯源（见 modeB-q2-v2.json）

## Confidence
覆盖型置信：金标 8 段全幸存（含 PCA 与基准两个答案核心段，v1 曾被相对线压低的段此次无一丢失）；同域 4 篇 69 段增强材料一并保留；无引擎错误。

## Blind Spots (Cross-Library Perspective)
- 42/53 篇未读（预算封顶，部分扫描）。
- 幸存集内同库临床干扰/增强比约 9:1（69 vs 8 段）——新契约下它们是"知识增强"而非噪声，但若任务只允许引用答案文档，需使用方按 doc_path 自行过滤（数据都在，未丢弃）。
