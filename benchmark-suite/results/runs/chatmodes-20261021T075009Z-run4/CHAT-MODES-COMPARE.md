# Chat-API 三模式系统臂对照（当前系统官方执行流）

- Run: `chatmodes-20261021T075009Z-run4` · 生成: 2026-10-21 08:19 UTC
- 通道: `POST /api/claude/chat` 默认**非流式**（一次阻塞 JSON）· `kbEnhanced=true` · A/C 钉库 `kbIds` · 工具门禁由服务端 `disallowedTools` 内建
- 判定门: found=HTTP200∧success∧答案非空∧答案金标词命中; refusal=HTTP200∧success∧如实拒答标记

| 模式 | 题 | 预期 | 耗时s | turns | 门 | 会话 |
|---|---|---|---:|---:|:--:|---|
| A | cm1 | found | 182.9 | 4 | ✅ | `9a3b9e1c` |
| A | cm2 | found | 208.2 | 6 | ✅ | `b2fbacd4` |
| A | cm3 | refusal | 217.7 | 7 | ✅ | `e19de410` |
| B | cm1 | found | 335.1 | 11 | ✅ | `0d522d7b` |
| B | cm2 | found | 242.5 | 6 | ✅ | `e71fd266` |
| B | cm3 | refusal | 172.0 | 8 | ✅ | `8b701a3b` |
| C | cm1 | found | 104.0 | 4 | ✅ | `787f4b5f` |
| C | cm2 | found | 222.4 | 9 | ❌ | `d292758d` |
| C | cm3 | refusal | 100.5 | 6 | ✅ | `3164e637` |

## 逐臂回答摘录

### A × cm1

> **InstructDS 的高质量 query-based 摘要数据，不是靠人工标注，而是用“摘要锚定”的三步合成流水线从已有 dialogue-summary pair 中反向生成 QDS（query-dialogue-summary）三元组**，再与通用摘要、长度感知指令混合训练 Flan-T5-XL。  **三步合成（论文 §3.2）**  1. **Summary-anchored query generation（摘要锚定的问题生成）**    受 Self-Instruct 启发，“leverage the conditional question generation and answering ability of general large language models”。用 Flan-T5-XL（文中称 model X，曾在 Quoref / MC-TACO / Co

### B × cm1

> **结论：InstructDS 用「摘要锚定查询生成 → 双重过滤 → 基于查询生成摘要」三步合成 query-对话-摘要三元组 (QDS)，以 Flan-T5-XL 生成查询、再用摘要（而非原始对话）作为答案生成源，从而在几乎无人工标注下获得高质量指令微调数据。**  **三步合成管线（论文 §3.2，part 1 of 4）**  1. **摘要锚定查询生成**：借鉴 Self-Instruct，利用通用 LLM 的条件提问能力；具体用 Flan-T5-XL（文中称 model X，已 Quoref/MC-TACO/CosmosQA 等提问数据训练）**基于参考摘要**为每个对话-摘要对生成 **5 个候选查询**（模板见 Table 7）。 2. **查询过滤（两道）**：    - **文本过滤**：以 model X 作二分类器判定"可回答性"，剔除无幻觉不可确答的查询（如 "W

### C × cm1

> **结论：InstructDS 不依赖人工标注，而是用「总结锚定」的三步法（总结锚定式查询生成 → 查询过滤 → 基于查询的总结生成）从既有 dialogue-summary 对中自动合成 QDS（query-dialogue-summary）三元组，再用这些高质量三元组 + 长度感知增强对 Flan-T5-XL 做指令微调（LoRA），从而生成高质量、可跟随查询指令的对话摘要。**  **一、数据合成三步（§3.2, part 1）** 1. **Query Generation（总结锚定）**：以 LLM 从**完整参考总结**出发，为每个实例用 Table 7 模板生成 **5 条候选查询**，所用模型 X = **Flan-T5-XL**（其在 Quoref / MC-TACO / CosmosQA 等问句生成数据上训练过）。 2. **Filtering**：双重过滤保证"可答性

### A × cm2

> **结论：** 在该库中，唯一直接对口的文献是 Nwosu 等人的《Predicting Stroke from Electronic Health Records》（arXiv:1904.11280）。该文给出的核心答案是：**高血压、糖尿病、心脏病是文献公认的卒中主要风险因素**；但在该电子健康记录（EHR）数据上，PCA 分析表明 10 个患者属性彼此**并不高度相关**，所以不能对特征空间做压缩，全部特征都必须保留；在此前提下，神经网络（MLP）的预测准确率最高，为 **75.02%**，决策树为 74.31%、随机森林为 74.53%，三者性能相近（P0 直接证据）。  **数据与特征（P0）** - 数据集：McKinsey 医疗黑客松发布、Kaggle 公开的 EHR 数据，共 **29,072 名患者、12 个属性**；剔除患者ID后，共 10 个输入变量：性别、年龄、高血

### B × cm2

> **结论：知识库中有一篇直接命中的文献可以回答这个问题：基于 EHR 数据的卒中预测应当使用全部 10 个患者属性进行建模，因为特征之间并不高度相关，强行用 PCA 降维会损失信息；在因素影响方面，年龄与婚姻状态对主成分贡献最大，居住类型几乎零贡献，而三类经典分类器的基准准确率仅在 74.31%–75.02% 之间（神经网络最优）。**  **出处**：生命科学与医学库（`b28f0a25-1e1d-40ad-96b8-61bd2b093a28`）→《Predicting Stroke from Electronic Health Records》（arXiv 1904.11280；Nwosu, Dev, Bhardwaj, Veeravalli, Deepu John）。**可信度 P0（强）**：描述层的表述与问题精确匹配，Laya 证据门控的 8/8 个段落全部存活，最高分 0.93

### C × cm2

> **结论：** 在本库中，与该问题直接对应的核心文献只有一篇，即 Nwosu 等人的《Predicting Stroke from Electronic Health Records》。该文基于 29,072 条 EHR 记录，用 PCA 分析风险因素之间的相关性，并以神经网络模型取得最佳指标（75.02%，决策树 74.31%、随机森林 74.53%）；由于 10 个患者属性彼此相关性低，无法压缩特征空间，必须全部输入模型。  ### 一、关键风险因素（来自文献的直接证据，可信级别 P0） - **公认的主要危险因素**：作者引证此前的研究，“Studies in healthcare like [6]-[8] have identified **high blood pressure, diabetes and heart disease** as major risk factors

### A × cm3

> **结论：指定的「计算机与人工智能」知识库（b1199132-e4d4-4305-8c2e-82dc1753b0ba）中不存在任何关于 “Herbert-Moulton collider benchmark” 或粒子物理探测器漂移的材料，该问题在库内无证据可答。**  **检索事实**  | 检索 | 参数 | 结果 | |---|---|---| | `kb_search_two_stage` | “Herbert-Moulton collider benchmark detector drift particle physics”，stage1=20/stage2=5，slim | 20 个候选，全部为 CS/AI 论文（GPT-3 few-shot、SLAM、bitvector 查询优化等）；最高 stage2 分数 7.64 的是 GPT-3 附录 G，与题意无关 | | `kb_

### B × cm3

> **知识库中没有任何关于 "Herbert-Moulton collider benchmark" 或对撞机探测器漂移量化的内容——这是一个未收录的（很可能是虚构/不存在的）基准名，无法作答。**  检索路径与实测结果（全库逐级检索，只读）：  1. **`kb_list(lightweight=true)`** — 21 个库。唯一覆盖物理学的库是「自然科学与地球科学」（75 文档）；另有泛化库 `demo-qa-20260927`（description 明示 "random real-world content"），按规则一并抽查。 2. **描述层全量扫描**：    - 「自然科学与地球科学」两页共 75 条描述全部过目 — 主题分布为：量子计算/量子纠错/QEM、气候科学、天文学（CoRoT、DES、甲醇巡天、系外行星人口统计）、地震学、海洋学、化学、数学（随机 PDE 控制）

### C × cm3

> **该库中不存在关于 “Herbert-Moulton collider benchmark” 的任何内容 —— 未找到相关证据，且该名称在库内无任何字面或语义匹配；无法据此回答其如何量化粒子物理实验中的探测器漂移。**  ## 检索事实  **检索库**：`计算机与人工智能`（kb_id `b1199132-e4d4-4305-8c2e-82dc1753b0ba`），共 **131 篇文档 / 9 个主题分组**。  **已执行的三次检索及命中情况**：  | 检索 | 参数 | 命中 | 结果性质 | |---|---|---|---| | `kb_search_two_stage` | query="Herbert-Moulton collider benchmark detector drift"，top_k=20 | 20 条候选（stage2 返回 5） | 全部为**关键词/

