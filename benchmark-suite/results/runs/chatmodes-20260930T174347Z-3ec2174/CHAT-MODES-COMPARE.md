# Chat-API 三模式系统臂对照（当前系统官方执行流）

- Run: `chatmodes-20260930T174347Z-3ec2174` · 生成: 2026-09-30 17:48 UTC
- 通道: `POST /api/claude/chat` 默认**非流式**（一次阻塞 JSON）· `kbEnhanced=true` · A/C 钉库 `kbIds` · 工具门禁由服务端 `disallowedTools` 内建
- 判定门: found=HTTP200∧success∧答案非空∧答案金标词命中; refusal=HTTP200∧success∧如实拒答标记

| 模式 | 题 | 预期 | 耗时s | turns | 门 | 会话 |
|---|---|---|---:|---:|:--:|---|
| A | cm1 | found | 38.8 | 5 | ✅ | `d9f58ae7` |
| A | cm2 | found | 32.4 | 5 | ✅ | `c15e0127` |
| A | cm3 | refusal | 23.0 | 7 | ✅ | `07d62c23` |
| B | cm1 | found | 44.0 | 11 | ✅ | `3f3b5671` |
| B | cm2 | found | 31.7 | 6 | ✅ | `ebaced88` |
| B | cm3 | refusal | 33.9 | 7 | ✅ | `33188ecf` |
| C | cm1 | found | 28.8 | 5 | ✅ | `ed7ac9b3` |
| C | cm2 | found | 38.2 | 8 | ✅ | `8953ad59` |
| C | cm3 | refusal | 12.2 | 5 | ✅ | `10139351` |

## 逐臂回答摘录

### A × cm1

> **结论：InstructDS 用「摘要锚定」的三步合成流水线，从已有的「对话-摘要」对中自动造出高质量的 query-dialogue-summary（QDS）三元组，借助大语言模型（Flan-T5-XL）的提问与问答能力，把人类参与降到最低。**  出处：`计算机与人工智能/nlp__2310.10981__instructive-dialogue-summarization-with-quer (part 1 of 4).md`（论文 *Instructive Dialogue Summarization with Query Aggregations*，Wang, Liu, Chen；KB `b1199132-…`）。证据强度 **P0**（论文原文直接陈述，判定全部命中，score 0.75–0.95）。  ## 三步合成流程（§3.2 Synthesize QDS Triple

### B × cm1

> I have everything needed.  ## 结论  InstructDS 通过一条**三步合成流水线**从现成的 dialogue–summary 对中自动合成高质量的"查询–对话–摘要"(QDS) 三元组，核心是**以参考摘要为锚**、用 LLM 的问答能力反推查询与答案，再用双重过滤保质量。  **三步合成（论文 §3.2）** 1. **Query Generation（摘要锚定查询生成）**：用 Flan-T5-XL（记为 model X）基于**完整参考摘要**生成 5 个候选查询——因为摘要是对话的凝练版，比直接从对话提问更可靠、覆盖更多话轮。 2. **Filtering（查询过滤）**——两道：    - **文本过滤**：把 model X 当二分类器判断查询"可回答性"，剔除 *What will / How would* 这类无法无幻觉回答的查询，**

### C × cm1

> The evidence pack directly and fully answers the question. Synthesizing now.  **结论：InstructDS 通过一条三步"总结锚定"的合成流水线（summary-anchored QDS triple synthesis）批量生成高质量的 query-based 对话摘要指令数据——先由大模型从参考摘要反向生成候选 query，再经"文本可答性 + 语义去重"双重过滤，最后以 query+摘要为输入触发 LLM 问答能力生成 query-based 摘要，从而在几乎零人工标注下把三元组质量从 45% 提升到 75%。**  ## 合成流程（三步）  出处：*Instructive Dialogue Summarization with Query Aggregations*（nlp__2310.10981，KB

### A × cm2

> The evidence is complete and directly on-point. Here is the answer.  ---  **结论：** 知识库中有一篇与该问题完全对应的核心文献，其结论是——高血压、糖尿病、心脏病是中风的主要风险因素；而在 EHR 心电图（patient-attribute）特征上做系统分析后发现，各特征之间相关性低（前两个主成分仅解释 31.4% 方差），因此**不能靠降维删特征，10 个患者属性须全部保留**；在三种经典 ML 算法中，**多层感知机（神经网络）表现最佳，准确率 75.02%**（决策树 74.31%、随机森林 74.53%）。  ### 关键风险因素及其影响（P0 直接证据）  来源：*Predicting Stroke from Electronic Health Records*（Nwosu, Dev, Bhardwaj

### B × cm2

> The evidence gate confirms the exact document (1 doc with yes, 8/8 segments survive, top score 0.89). I have the full evidence pack; synthesizing now.  ---  **结论：知识库中确实收录了直接对应的文献——"Predicting Stroke from Electronic Health Records"（生命科学与医学库），它用 PCA + 决策树/随机森林/神经网络系统分析了 EHR 各风险因素对卒中的影响，并给出基准精度。**  **出处**：`clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md`（KB：生命科学与医学；作者 N

### C × cm2

> I now have complete evidence.  **结论：本库中能直接回答该问题的核心文献是 Nwosu 等人的《Predicting Stroke from Electronic Health Records》（临床医学库 / b28f0a25…），其结论为——高血压、糖尿病（高血糖）与心脏病是中风的主要风险因素；10 项 EHR 患者属性彼此相关性低、不可降维，全部保留作特征；在高度不平衡数据（29072 条中仅 548 条中风）经随机下采样后，前馈多层感知机（神经网络）取得最佳准确率 75.02%，决策树 74.31%、随机森林 74.53%。**  **关键风险因素与影响**（出处：clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md）  - **三大主要风险因素*

### A × cm3

> **结论：在指定知识库中未找到任何关于 "Herbert-Moulton collider benchmark" 或粒子物理探测器漂移量化的内容——该库不含此主题的证据，无法回答。**  **检索事实（仅陈述，不推测库内容）**  对指定库 `b1199132-e4d4-4305-8c2e-82dc1753b0ba`（"计算机与人工智能"，内容为 CS/AI/机器人/数据库/NLP 论文）：  | 检索 | 结果 | |---|---| | `kb_search_two_stage`（"Herbert-Moulton collider benchmark detector drift quantification"） | 20 候选，全部为 SLAM/Gaussian Splatting、数据库查询优化、BERT、神经网络精神分裂综述等，无一篇涉及粒子物理；stage2 命中分数最高者也仅

### B × cm3

> The engine's only survivor is a gravitational-wave interferometer paper (high-frequency response functions) — it matched on generic "detector/response" vocabulary, not on collider benchmarks. No particle-physics/collider content exists.  ---  **The knowledge base contains no content on the "Herbert-Moulton collider benchmark" or on particle-physics detector drift — this is an honest NOT_FOUND, not

### C × cm3

> **结论：在该知识库中未找到任何关于 "Herbert-Moulton collider benchmark" 或粒子物理实验中探测器漂移（detector drift）量化的内容。**  **检索事实（可核验）：**  1. **检索库**：`b1199132-e4d4-4305-8c2e-82dc1753b0ba`（"计算机与人工智能"，131 篇文档）。这是个**计算机科学与 AI** 库（算法、NLP/LLM、视觉、机器人感知、数据系统、语音、社会计算），与粒子物理无关。  2. **已执行的检索与命中**：    - `kb_search_two_stage`（query: "Herbert-Moulton collider benchmark detector drift particle physics"）→ 20 个候选，命中项全部是无关文档（GPT-3 few-shot 

