# Chat-API 三模式系统臂对照（当前系统官方执行流）

- Run: `chatmodes-20260930T143945Z-3ec2174` · 生成: 2026-09-30 14:59 UTC
- 通道: `POST /api/claude/chat` 默认**非流式**（一次阻塞 JSON）· `kbEnhanced=true` · A/C 钉库 `kbIds` · 工具门禁由服务端 `disallowedTools` 内建
- 判定门: found=HTTP200∧success∧答案非空∧答案金标词命中; refusal=HTTP200∧success∧如实拒答标记

| 模式 | 题 | 预期 | 耗时s | turns | 门 | 会话 |
|---|---|---|---:|---:|:--:|---|
| A | cm1 | found | 85.5 | 6 | ✅ | `95fa4615` |
| A | cm2 | found | 83.6 | 5 | ✅ | `752be0a4` |
| A | cm3 | refusal | 76.1 | 5 | ✅ | `207d4b01` |
| B | cm1 | found | 196.9 | 17 | ✅ | `41a81273` |
| B | cm2 | found | 142.2 | 9 | ✅ | `f13eff08` |
| B | cm3 | refusal | 316.0 | 19 | ✅ | `9b1cc3a7` |
| C | cm1 | found | 99.1 | 7 | ✅ | `fa2a7c7a` |
| C | cm2 | found | 89.9 | 8 | ✅ | `50d0ac49` |
| C | cm3 | refusal | 72.0 | 5 | ✅ | `a09ff7a4` |

## 逐臂回答摘录

### A × cm1

> **InstructDS 通过「三步合成法」从既有对话-摘要对自动构造查询-对话-摘要（QDS）三元组：摘要锚定的查询生成 → 查询过滤 → 查询式摘要生成，全程利用 LLM 的问题生成与问答能力，将人工标注降到最低，质量分从 45% 提升到 75%。**（P0 直接证据，来源：`nlp__2310.10981__instructive-dialogue-summarization-with-quer` (part 1 of 4)，SAMSum 专题库）  具体流程（§3.2 Synthesize QDS Triples）：  1. **摘要锚定的查询生成**：用在 Quoref、MC-TACO、CosmosQA 等问题上生成数据上训练过的 Flan-T5-XL（"model X"），基于参考摘要（而非冗长对话）生成候选问题——每个实例生成 5 个候选 query，以获得多样性。  2. 

### B × cm1

> **InstructDS synthesizes high-quality query-based summaries via a three-step pipeline that turns ordinary dialogue–summary pairs into query–dialogue–summary (QDS) triples: summary-anchored query generation, query filtering, and query-based summary generation.** (Source: *Instructive Dialogue Summarization with Query Aggregations* (Wang, Liu, Chen, A\*STAR I2R), KB「计算机与人工智能」, parts 1/4 — P0 strong,

### C × cm1

> **结论：InstructDS 靠“三步法”从已有的 dialogue-summary 对合成 query-dialogue-summary（QDS）三元组——摘要锚定的问题生成 + 双重问题过滤 + 基于查询的摘要生成，人工几乎不介入。**（出处：KB `b1199132`，《InstructDS: Instructive Dialogue Summarization with Query-based Data Synthesis》(arXiv 2310.10981)，Part 1，§3.2；laya 判定 2/2 文档幸存，P0 直接证据）  三步细节：  1. **Summary-anchored query generation（摘要锚定的问题生成）**    用 Flan-T5-XL（已在 Quoref、MC-TACO、CosmosQA 等问题生成数据上训练）作为生成模型 X，对

### A × cm2

> **结论：EHR 中风预测的关键风险因素是高血压、心脏病、高血糖、年龄（及 BMI、吸烟等生活方式属性），且各因素间相关性低——降维会损失信息，全部特征保留时多层感知机（MLP）表现最佳（准确率 75.02%）。**  依据库内唯一高相关文献（P0 直接证据，Laya 证据门 8/8 段全部幸存）：  **文献**：《Predicting Stroke from Electronic Health Records》（Nwosu、Dev 等，arXiv:1904.11280），生命科学与医学 KB。  **关键发现（原文引用）**  1. **风险因素集合**：数据集为 29,072 条患者 EHR（Kaggle/McKinsey），10 个输入属性——性别、年龄、高血压、心脏病、婚况、工作类型、居住地（城乡）、平均血糖水平、BMI、吸烟状态。文献指出 "high blood pressur

### B × cm2

> **结论：知识库中唯一直接对口的文献（《Predicting Stroke from Electronic Health Records》，Nwosu et al., arXiv 1904.11280，存于「生命科学与医学」库）表明：基于 29,072 条 EHR 记录，年龄与婚姻状态是对预测贡献最大的因素，居住类型几乎无贡献；算法性能上多层感知机最优（75.02%），三种经典算法差异很小。**  **要点与关键引文**（均逐字出自该文档）：  1. **数据**：McKinsey 医疗黑客松数据集（Kaggle 公开），"29072 patient's information with 12 attributes"，10 个输入特征为性别、年龄、高血压、心脏病、婚姻状态、工作类型、居住类型（urban/rural）、平均血糖、BMI、吸烟状态。 2. **关键风险因素**：既往研究确认 

### C × cm2

> **结论：库内证据（P0 级直接命中）显示，基于 EHR 的机器学习中风风险预测中，关键风险因素为高血压、糖尿病（高血糖）与心脏病这三大主因，且年龄是属性中贡献最大的因素之一；模型基准上 MLP 神经网络以 75.02% 准确率最优。**  核心证据来自《Predicting Stroke from Electronic Health Records》（Nwosu et al., arXiv:1904.11280，生命科学与医学 KB，laya 判定 19/19 段幸存，P0 直接证据）：  **1. 关键风险因素及影响** - 原文引言明确："Studies in healthcare like [6]-[8] have identified **high blood pressure, diabetes and heart disease** as major risk factors

### A × cm3

> **库中没有关于该主题的任何内容，无法回答此问题。**  检索事实如下（指定库 `b1199132-e4d4-4305-8c2e-82dc1753b0ba`）：  1. `kb_search_two_stage`（查询："Herbert-Moulton collider benchmark detector drift particle physics"）：Stage1 召回 20 个候选、Stage2 返回 5 条，全部来自计算机科学/AI 文献（GPT-3 Few-Shot Learners、MCGS-SLAM 多相机SLAM、Bitvector 查询优化等），无任何粒子物理相关命中。 2. `kb_search_vector`（中英混合查询："粒子物理 对撞机 探测器漂移 基准测试…"）：返回 15 条，最高分 0.5408，命中均为数据库查询优化、SLAM、NLP 基准文档。 3.

### B × cm3

> **结论：知识库中不存在任何与 "Herbert-Moulton collider benchmark" 或粒子物理对撞机探测器漂移量化相关的内容，无法从库内给出该问题的答案。**  检索过程与证据：  1. **目录层扫描（全库 19 个 KB）**：无任何库的描述涉及粒子物理/对撞机。物理领域唯一覆盖库是「自然科学与地球科学」（75 篇），逐篇描述核对后确认内容为：量子计算与纠错（NISQ 基准、QEM 等）、气候、天文、化学、引力波、地震学——没有一篇是对撞机实验。  2. **laya 引擎证据判决**（候选 31 段，幸存 21 段）：幸存片段全部来自最接近的候选——Corda《Moriond 07 proceedings》（`gravitational-physics__0706.3294`，自然科学与地球科学库），但该文讨论的是**引力波激光干涉仪（VIRGO/LIGO/GE

### C × cm3

> **结论：该问题无法从指定知识库得到回答——库中不存在任何关于 "Herbert-Moulton collider benchmark" 或粒子物理探测器漂移的内容，我拒绝编造。**  已执行的检索事实：  1. **`kb_search_two_stage`**（英文原问题，pinned KB `b1199132-e4d4-4305-8c2e-82dc1753b0ba`）：Stage1 召回 20 个候选、Stage2 返回 5 条——命中的全部是计算机/AI 文档（GPT-3 few-shot learners、MCGS-SLAM 多相机SLAM、Bitvector 查询优化），匹配的只是 "benchmark" / "experiment" 等泛化词，无一涉及对撞机或探测器。 2. **`kb_search_vector`**（中文变体「探测器漂移 量化 对撞机 实验 benchma

