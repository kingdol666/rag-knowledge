# 检索任务端到端真实测试报告（三通道 × 三模式 × 同题集）

- 生成时间: 2026-10-12 18:47:45 · commit `5f9faac` · 分支 feat/soul-persona-system
- 面板: 全部检索走**官方 harness 对外 API** `POST /api/claude/chat`（engine=claude, kbEnhanced=true），与外部调用方完全同构；工具门禁/MCP 挂载/Laya 判卷均为服务端行为
- 问题集: cm1（InstructDS 对话摘要, 金标 arXiv:2310.10981, 库=计算机与人工智能）· cm2（EHR 中风预测, 金标 arXiv:1904.11280, 库=生命科学与医学）· cm3（Herbert-Moulton collider, **域外题**, 应如实拒答）
- 三通道: ① harness API 流式（SSE 时间线, 逐工具耗时）· ② exp --chatmodes 非流式系统臂（`chatmodes-20261012T061102Z-5f9faac`）· ③ exp --retmodes 纯检索矩阵无 LLM（`run-20261012T062847Z-5f9faac`）

## 结论 TL;DR

- 通道1 门禁（拒答优先修正口径）**8/9**——唯一 FAIL 为 B×cm1 假拒答（详见「发现与根因」）；通道1 端到端均值：A=47.0s · B=142.2s · C=51.2s
- 通道2 门禁（修正口径）**8/9**——同样败于 B×cm1 假拒答（独立复现）；非流式均值：A=48.0s · B=66.4s · C=68.9s
- 通道3（纯检索, 无 LLM 回答）金标命中 **6/6**（三模式脚本臂 6/6 + baseline 6/6; 与 2026-09-26 基线对照: B 342/234s→25.0/10.2s, C 1152/1818s→37.3/33.7s）
- 三种模式检索流程与获取方式见「真实检索流程」一节（由 SSE 逐工具时间线还原, 非推断）。

## 通道 1：harness 对外 API（流式 SSE 时间线）

| 模式 | 题 | 预期 | 端到端s | 引擎报时长ms | turns | 成本$ | 工具序列 | 检索工具耗时s | 门 |
|---|---|---|---:|---:|---:|---:|---|---:|:--:|
| A | cm1 | found | 55.7 | 53923 | 6 | 0.2376 | EndConversation→kb_search_two_stage→kb_search_vector→kb_search_vector→kb_laya_judge | 17.9 | ✅ |
| A | cm2 | found | 48.8 | 47851 | 6 | 0.1930 | EndConversation→kb_search_two_stage→kb_search_vector→kb_laya_judge→kb_doc_read | 21.2 | ✅ |
| A | cm3 | refusal | 36.4 | 35562 | 5 | 0.1218 | ExitWorktree→kb_list→kb_search_two_stage→kb_search_vector | 3.6 | ✅ |
| B | cm1 | found | 353.5 | 352708 | 8 | 0.1784 | EndConversation→kb_list→kb_get_documents→kb_get_documents→kb_get_documents→kb_search_vector→kb_laya_judge | 319.5 | ❌ |
| B | cm2 | found | 43.2 | 42278 | 7 | 0.2501 | EndConversation→kb_list→kb_get_documents→kb_get_documents→kb_get_documents→kb_laya_judge | 13.2 | ✅ |
| B | cm3 | refusal | 29.9 | 29037 | 5 | 0.2001 | EndConversation→kb_list→kb_get_documents→kb_get_documents | 2.0 | ✅ |
| C | cm1 | found | 43.1 | 42207 | 6 | 0.2039 | EndConversation→kb_search_two_stage→kb_search_vector→kb_laya_judge→kb_doc_read | 11.7 | ✅ |
| C | cm2 | found | 45.6 | 44812 | 6 | 0.1936 | EndConversation→kb_search_two_stage→kb_search_vector→kb_laya_judge→kb_doc_read | 19.8 | ✅ |
| C | cm3 | refusal | 65.0 | 64245 | 6 | 0.1590 | EndConversation→kb_search_two_stage→kb_search_vector→kb_laya_judge→kb_list | 21.8 | ✅ |

## 真实检索流程（逐工具还原自 SSE 时间线）

### A × cm1（wall 55.7s, 门 ✅）

工具调用时序（含入参摘要与每工具耗时）：

- `t+   3.9s → t+   3.9s` (  0.0s) **EndConversation**  `{"message": "placeholder"}`
- `t+  13.9s → t+  14.8s` (  0.9s) **mcp__kb-mcp__kb_search_two_stage**  `{"query": "InstructDS query-based dialogue summarization instruction tuning data synthesis", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "slim": true, "top_k": 30, "stage2_top_k": 5}`
- `t+  13.9s → t+  14.9s` (  1.0s) **mcp__kb-mcp__kb_search_vector**  `{"query": "InstructDS: query-based dialogue summarization instruction tuning dataset generation", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "slim": true, "top_k": 30}`
- `t+  13.9s → t+  14.9s` (  1.0s) **mcp__kb-mcp__kb_search_vector**  `{"query": "high-quality dialogue summary generation query-based LLM synthetic data pipeline", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "slim": true, "top_k": 30}`
- `t+  20.6s → t+  35.6s` ( 15.0s) **mcp__kb-mcp__kb_laya_judge**  `{"query": "How does InstructDS synthesize high-quality query-based dialogue summarization (QDS) triples? Three-step pipeline: summary-anchored query generation, query filtering, query-based summary generation; quality sc`

> 回答摘录（前 420 字）: The evidence pack gives a complete, direct answer. **结论：InstructDS 通过一个"三步式"综合管线从已有的"对话–摘要"对中自动合成高质量的查询对话摘要（QDS）三元组**——核心是借用通用大语言模型的"条件式问题生成 + 问答"能力（受 Self-Instruct 启发），从而绕开昂贵的人工标注。  ## 三步综合管线（论文 §3.2）  论文第一作者表述为：*"we propose a three-step approach to synthesize high-quality query-based summarization triples. This process involves summary-anchored query generation, query filtering and query-based summary generation."*…

### A × cm2（wall 48.8s, 门 ✅）

工具调用时序（含入参摘要与每工具耗时）：

- `t+   2.9s → t+   2.9s` (  0.0s) **EndConversation**  `{"message": "noop"}`
- `t+  10.0s → t+  10.9s` (  0.9s) **mcp__kb-mcp__kb_search_two_stage**  `{"query": "stroke prediction electronic health records machine learning risk factors", "kb_id": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28", "slim": true, "stage2_top_k": 5, "stage1_top_k": 20}`
- `t+  10.1s → t+  10.9s` (  0.8s) **mcp__kb-mcp__kb_search_vector**  `{"query": "中风 卒中 风险预测 电子健康记录 机器学习 危险因素", "kb_id": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28", "slim": true, "top_k": 15}`
- `t+  19.0s → t+  28.6s` (  9.6s) **mcp__kb-mcp__kb_laya_judge**  `{"query": "Which risk factors for stroke prediction are identified from electronic health records, and what is their impact? machine learning methods used", "documents": "[{\"kb_id\":\"b28f0a25-1e1d-40ad-96b8-61bd2b093a2`
- `t+  19.0s → t+  28.9s` (  9.9s) **mcp__kb-mcp__kb_doc_read**  `{"doc_path": "生命科学与医学/clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md", "kb_id": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28", "max_chars": 14000}`

> 回答摘录（前 420 字）: # 结论  库内已有直接对口的证据：**Nwosu et al.《Predicting Stroke from Electronic Health Records》** 是唯一一篇直接命中该主题的文献，它用 29,072 条 EHR 记录系统分析了中风风险因素并基准测试了 ML 算法——结论是**高血压（hypertension）、心脏病（heart disease）、年龄、平均血糖水平、BMI、吸烟状况、婚姻状况是主要风险因素，且这些特征彼此弱相关（不应做特征降维），全部 10 个特征都应用于建模**。  ## 关键风险因素及影响  | 风险因素（EHR 属性） | 影响 | |---|---| | 高血压 hypertension | 明确列为中风主因之一（binary 1/0） | | 心脏病 heart disease | 明确列为中风主因之一（binary 1/0） | | 年龄 age | 对前两个主成分**贡献最高…

### A × cm3（wall 36.4s, 门 ✅）

工具调用时序（含入参摘要与每工具耗时）：

- `t+   2.9s → t+   2.9s` (  0.0s) **ExitWorktree**  `{"action": "keep"}`
- `t+  10.7s → t+  11.3s` (  0.6s) **mcp__kb-mcp__kb_list**  `{"lightweight": true}`
- `t+  10.7s → t+  12.1s` (  1.4s) **mcp__kb-mcp__kb_search_two_stage**  `{"query": "Herbert-Moulton collider benchmark detector drift", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "slim": true, "top_k": 20, "stage1_top_k": 30}`
- `t+  10.7s → t+  12.3s` (  1.6s) **mcp__kb-mcp__kb_search_vector**  `{"query": "Herbert-Moulton benchmark quantify detector drift particle physics", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "slim": true, "top_k": 20}`

> 回答摘录（前 420 字）: **结论：在这批知识库中未找到任何关于 "Herbert-Moulton collider benchmark" 的内容——该概念在本库不存在，无法说明它如何量化粒子物理实验中的探测器漂移。**  ## 检索事实（只报告，不推测）  **检索范围** - 指定库：`b1199132-e4d4-4305-8c2e-82dc1753b0ba` — **计算机与人工智能**（Computer science and AI: algorithms, NLP/LLM, vision, robotics perception, data systems, speech, social computing），131 篇文档。  **已执行的检索** 1. `kb_search_two_stage(kb_id=b1199132…, query="Herbert-Moulton collider benchmark detector drift"…

### B × cm1（wall 353.5s, 门 ❌）

工具调用时序（含入参摘要与每工具耗时）：

- `t+   4.9s → t+   4.9s` (  0.0s) **EndConversation**  `{"message": "placeholder"}`
- `t+   7.9s → t+   8.5s` (  0.6s) **mcp__kb-mcp__kb_list**  `{"lightweight": true}`
- `t+  15.3s → t+  15.6s` (  0.3s) **mcp__kb-mcp__kb_get_documents**  `{"kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "lightweight": true}`
- `t+  15.3s → t+  16.2s` (  0.9s) **mcp__kb-mcp__kb_get_documents**  `{"kb_id": "455137b4-a0be-46ed-acf5-d8b475dc5d70", "lightweight": true}`
- `t+  15.3s → t+  16.8s` (  1.5s) **mcp__kb-mcp__kb_get_documents**  `{"kb_id": "09b2102e-7dd2-4f4e-afe0-13b40c9b1463", "lightweight": true}`
- `t+  21.5s → t+ 321.5s` (300.0s) **mcp__kb-mcp__kb_search_vector**  `{"query": "InstructDS query-based dialogue summarization instruction tuning", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "top_k": 5}`
- `t+ 325.6s → t+ 341.8s` ( 16.2s) **mcp__kb-mcp__kb_laya_judge**  `{"query": "How does InstructDS generate high-quality query-based dialogue summaries (dialogue summarization instruction tuning data synthesis)?", "documents": "[{\"kb_id\":\"b1199132-e4d4-4305-8c2e-82dc1753b0ba\",\"doc_p`

> 回答摘录（前 420 字）: The engine's "evidence" criterion is passing near-every segment regardless of topical relevance (Hanabi MARL doc scored 0.63–0.89 on a dialogue-summarization question) — a known weak-signal pathology, not a real match. I'll rely on the description layer, which is unambiguous here, rather than body reads.  I have enough to answer honestly.  **结论：知识库中没有覆盖 InstructDS / query-based 对话摘要指令数据合成的内容——未能找到任何相关文档。**  检索过程（全库目录…

### B × cm2（wall 43.2s, 门 ✅）

工具调用时序（含入参摘要与每工具耗时）：

- `t+   3.4s → t+   3.4s` (  0.0s) **EndConversation**  `{"message": "test"}`
- `t+   6.9s → t+   7.5s` (  0.6s) **mcp__kb-mcp__kb_list**  `{"lightweight": true}`
- `t+  14.3s → t+  14.9s` (  0.6s) **mcp__kb-mcp__kb_get_documents**  `{"kb_id": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28", "lightweight": true}`
- `t+  14.3s → t+  15.4s` (  1.1s) **mcp__kb-mcp__kb_get_documents**  `{"kb_id": "455137b4-a0be-46ed-acf5-d8b475dc5d70", "lightweight": true}`
- `t+  14.3s → t+  16.1s` (  1.8s) **mcp__kb-mcp__kb_get_documents**  `{"kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "lightweight": true}`
- `t+  23.3s → t+  32.4s` (  9.1s) **mcp__kb-mcp__kb_laya_judge**  `{"query": "基于电子健康记录(EHR)数据用机器学习算法预测中风/卒中风险：关键风险因素及其影响分析", "documents": "[{\"kb_id\":\"b28f0a25-1e1d-40ad-96b8-61bd2b093a28\",\"doc_path\":\"生命科学与医学\\\\clinical-medicine__1904.11280__predicting-stroke-from-electronic-heal`

> 回答摘录（前 420 字）: **结论：知识库中确有一篇完全对口的一手文献——《Predicting Stroke from Electronic Health Records》(arXiv:1904.11280)，其核心发现是：单一风险因素中高血压、心脏病、糖尿病最为关键，但 PCA 显示"年龄 + 婚姻状态"对主成分贡献最大、"居住类型几乎无贡献"，且 10 个患者属性整体不高度相关、不应做特征约简；三种机器学习算法精度接近，多层感知机(MLP)最高 75.02%。**  **证据基础(P0 强，Laya 引擎 8/8 段全部存活，最高分 0.94)** - 来源库：《生命科学与医学》KB (`b28f0a25-1e1d-40ad-96b8-61bd2b093a28`) - 文献：`clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md`（Nwosu, …

### B × cm3（wall 29.9s, 门 ✅）

工具调用时序（含入参摘要与每工具耗时）：

- `t+   3.8s → t+   3.8s` (  0.0s) **EndConversation**  `{"message": "Placeholder"}`
- `t+   5.3s → t+   5.9s` (  0.6s) **mcp__kb-mcp__kb_list**  `{"lightweight": true}`
- `t+  11.5s → t+  12.1s` (  0.6s) **mcp__kb-mcp__kb_get_documents**  `{"kb_id": "1e6199ea-f380-44e2-94fc-d431f0f9bb6b", "lightweight": true}`
- `t+  11.6s → t+  12.4s` (  0.8s) **mcp__kb-mcp__kb_get_documents**  `{"kb_id": "455137b4-a0be-46ed-acf5-d8b475dc5d70", "lightweight": true}`

> 回答摘录（前 420 字）: **知识库中无对应内容**——没有任何库或文档描述 "Herbert-Moulton collider benchmark" 或其在粒子物理中量化探测器漂移(detector drift)的方法。  **检索过程（一轮，按目录层 + 描述层判定）**  1. `kb_list(lightweight=true)`：20 个库，逐一核对名称/描述，唯一可能覆盖「物理/粒子物理」领域的书架是 **自然科学与地球科学**（"physics, quantum, climate, astronomy, chemistry, ocean, seismology"）。 2. `kb_get_documents(lightweight=true)` 描述层扫描：    - **自然科学与地球科学**（75 文档全量描述）：内容集中在量子错误缓解(NISQ/QEM)、量子纠错码、行星/恒星天文巡天(CoRoT、DES、甲醇多波束)、气候降水与 M…

### C × cm1（wall 43.1s, 门 ✅）

工具调用时序（含入参摘要与每工具耗时）：

- `t+   3.2s → t+   3.2s` (  0.0s) **EndConversation**  `{"temporary": "placeholder"}`
- `t+   8.5s → t+   9.4s` (  0.9s) **mcp__kb-mcp__kb_search_two_stage**  `{"query": "InstructDS query-based dialogue summarization data synthesis instruction tuning", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "slim": true, "stage1_top_k": 20, "stage2_top_k": 5}`
- `t+   8.6s → t+   9.5s` (  0.9s) **mcp__kb-mcp__kb_search_vector**  `{"query": "InstructDS dialogue summarization query-based summary generation", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "slim": true, "top_k": 20}`
- `t+  12.9s → t+  22.5s` (  9.6s) **mcp__kb-mcp__kb_laya_judge**  `{"query": "How does InstructDS synthesize high-quality query-based dialogue summarization data? three-step approach summary-anchored query generation, filtering, query-based summary generation", "documents": "[{\"kb_id\"`
- `t+  25.9s → t+  26.2s` (  0.3s) **mcp__kb-mcp__kb_doc_read**  `{"doc_path": "计算机与人工智能/nlp__2310.10981__instructive-dialogue-summarization-with-quer (part 1 of 4).md", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "offset": 0, "limit": 120}`

> 回答摘录（前 420 字）: I have everything needed.  **InstructDS 通过「三步合成 + 二重过滤」自动生成高质量 query-based 对话摘要三元组（QDS triple），核心是借 LLM 的问答能力把已有的 dialogue-summary 对扩增成 query-dialogue-summary 三元组。**  **三步合成流程**（§3.2 "Synthesize QDS Triples"，`nlp__2310.10981` part 1，KB `b1199132`）：  1. **摘要锚定的查询生成（Summary-anchored Query Generation）**：用 **Flan-T5-XL（model X）** 的问题生成能力，基于**参考摘要**（而非对话本身）为每个实例生成 **5 个候选查询**，利用其泛化到叙述性文本的能力保证多样性。  2. **查询过滤（Filtering and …

### C × cm2（wall 45.6s, 门 ✅）

工具调用时序（含入参摘要与每工具耗时）：

- `t+   3.2s → t+   3.2s` (  0.0s) **EndConversation**  `{"message": "x"}`
- `t+   9.7s → t+  10.5s` (  0.8s) **mcp__kb-mcp__kb_search_two_stage**  `{"query": "machine learning stroke prediction electronic health records risk factors", "kb_id": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28", "stage1_top_k": 20, "stage2_top_k": 6, "slim": true}`
- `t+   9.7s → t+  10.6s` (  0.9s) **mcp__kb-mcp__kb_search_vector**  `{"query": "stroke prediction EHR machine learning key risk factors hypertension glucose BMI", "kb_id": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28", "top_k": 15, "slim": true}`
- `t+  17.1s → t+  26.0s` (  8.9s) **mcp__kb-mcp__kb_laya_judge**  `{"criterion": "evidence", "documents": "[{\"kb_id\":\"b28f0a25-1e1d-40ad-96b8-61bd2b093a28\",\"doc_path\":\"生命科学与医学/clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md\"}]", "query": "stroke pr`
- `t+  17.1s → t+  26.3s` (  9.2s) **mcp__kb-mcp__kb_doc_read**  `{"doc_path": "生命科学与医学/clinical-medicine__1904.11280__predicting-stroke-from-electronic-health-rec.md", "kb_id": "b28f0a25-1e1d-40ad-96b8-61bd2b093a28", "max_chars": 16000}`

> 回答摘录（前 420 字）: **结论：该库对此主题的覆盖以单篇论文《Predicting Stroke from Electronic Health Records》(clinical-medicine__1904.11280) 为核心（P0 直接证据）**——它用 ML 在 EHR 上做卒中预测，明确给出了关键风险因素、特征分析方法和三种算法的基准精度。  **关键风险因素（该文明确列出）** - **三大主要风险因素**：高血压（high blood pressure / hypertension）、糖尿病（diabetes）、心脏病（heart disease）——"Studies in healthcare like [6]-[8] have identified high blood pressure, diabetes and heart disease as major risk factors responsible for stroke …

### C × cm3（wall 65.0s, 门 ✅）

工具调用时序（含入参摘要与每工具耗时）：

- `t+   7.4s → t+   7.4s` (  0.0s) **EndConversation**  `{"reason": "This is a test/demonstration of the EndConversation tool."}`
- `t+  21.1s → t+  21.9s` (  0.8s) **mcp__kb-mcp__kb_search_two_stage**  `{"query": "Herbert-Moulton collider benchmark detector drift particle physics", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "slim": true, "top_k": 15}`
- `t+  21.1s → t+  22.0s` (  0.9s) **mcp__kb-mcp__kb_search_vector**  `{"query": "Herbert-Moulton collider benchmark quantify detector drift", "kb_id": "b1199132-e4d4-4305-8c2e-82dc1753b0ba", "slim": true, "top_k": 15}`
- `t+  32.7s → t+  42.5s` (  9.8s) **mcp__kb-mcp__kb_laya_judge**  `{"query": "Herbert-Moulton collider benchmark quantify detector drift in particle physics experiments", "documents": "[{\"kb_id\":\"b1199132-e4d4-4305-8c2e-82dc1753b0ba\",\"doc_path\":\"计算机与人工智能/robotics__2509.14191__mcg`
- `t+  32.8s → t+  43.1s` ( 10.3s) **mcp__kb-mcp__kb_list**  `{"lightweight": true}`

> 回答摘录（前 420 字）: **结论：该知识库中不存在 "Herbert-Moulton collider benchmark"，也无法回答它如何量化粒子物理实验中的探测器漂移 —— 检索范围内无任何匹配证据（honest not-found）。**  **已执行的检索与事实**  | 检索 | 范围 | 命中 | |---|---|---| | `kb_search_two_stage`（slim） | pinned KB `b1199132`（计算机与人工智能） | 20 候选，无一篇涉及粒子物理/对撞机 | | `kb_search_vector`（slim, top_k=15） | 同上 | 15 命中，最高分 0.500 — 仅为 SLAM "drift" 语义近邻 | | `kb_laya_judge`（evidence 模式） | 4 篇候选正文判定 | 36 段评分，4 篇"有幸存段"，但**无一段**与 Herbert-Moulton /…

## 通道 2：exp --chatmodes（同题非流式系统臂, 门禁实验）

- Run: `chatmodes-20261012T061102Z-5f9faac` · 判定门: found=HTTP200∧success∧答案非空∧金标词命中; refusal=HTTP200∧success∧如实拒答

| 模式 | 题 | 预期 | 耗时s | turns | 成本$ | 门 |
|---|---|---|---:|---:|---:|:--:|
| A | cm1 | found | 53.0 | 6 | 0.2088 | ✅ |
| A | cm2 | found | 65.3 | 6 | 0.2344 | ✅ |
| A | cm3 | refusal | 25.7 | 4 | 0.1034 | ✅ |
| B | cm1 | found | 41.4 | 6 | 0.1669 | ❌ |
| B | cm2 | found | 91.9 | 8 | 0.3023 | ✅ |
| B | cm3 | refusal | 66.0 | 11 | 0.4305 | ✅ |
| C | cm1 | found | 58.3 | 6 | 0.2097 | ✅ |
| C | cm2 | found | 100.0 | 9 | 0.2853 | ✅ |
| C | cm3 | refusal | 48.3 | 6 | 0.1606 | ✅ |

## 通道 3：exp --retmodes（同题纯检索矩阵, 无 LLM 回答）

| 方法 | q1 耗时 | q2 耗时 | q1 金标 | q2 金标 | q1 docs | q2 docs |
|---|---:|---:|:--:|:--:|---:|---:|
| mode_A | 25.0s | 22.7s | ✅ | ✅ | 18 | 18 |
| mode_B | 25.0s | 10.2s | ✅ | ✅ | 23 | 11 |
| mode_C | 37.3s | 33.7s | ✅ | ✅ | 12 | 12 |
| bm25 | 0.0s | 0.0s | ✅ | ✅ | 10 | 10 |
| vector | 0.1s | 0.1s | ✅ | ✅ | 1 | 3 |
| rrf | 0.0s | 0.0s | ✅ | ✅ | 10 | 10 |


### 检索类 baseline（bm25 / vector / rrf, 同题对照）

| baseline | 题 | 耗时s | 金标 |
|---|---|---:|:--:|
| bm25 | q1 | ≈0（本地） | ✅ |
| bm25 | q2 | ≈0（本地） | ✅ |
| vector | q1 | 0.1 | ✅ |
| vector | q2 | 0.1 | ✅ |
| rrf | q1 | ≈0（本地） | ✅ |
| rrf | q2 | ≈0（本地） | ✅ |

## 论文支撑数据（可直接引用）

| 数据点 | A 钉库向量 | B 全库逐级 | C 混合 | 来源 |
|---|---|---|---|---|
| 端到端耗时均值 (s, 非流式) | 48.0 | 66.4 | 68.9 | 通道2 exp --chatmodes |
| turns 均值 | 5.3 | 8.3 | 7.0 | 通道2 |
| 成本均值 ($/题) | 0.182 | 0.300 | 0.219 | 通道2 |
| 端到端耗时均值 (s, 流式) | 47.0 | 142.2 | 51.2 | 通道1 |
| 检索工具耗时均值 (s) | 14.2 | 111.6 | 17.8 | 通道1 |
| 门禁通过(修正后) | 3/3 | 2/3 | 3/3 | 通道2 |

> 历史对照（2026-09-26 基线, 纯检索层, q1/q2）: A 13.3/7.4s · B 342/234s · C 1152/1818s；经 09-28 图书管理员七层瘦身与判卷契约改造后, 当前检索层耗时见通道 3。

## 发现与根因（本轮测试的真实产出）

### 发现 1：模式 B 在 cm1 上三连失败（假拒答 ×2 + 超时挂起 ×1）——系统性缺陷

- 通道1 B×cm1：353.5s 后**假拒答**（声称“未找到任何 InstructDS 相关文档”），其中 `kb_search_vector` 兜底调用挂起 **300.0s**（恰为 MCP 300s 超时, kb-mcp SSE 事件循环僵死的已知病理形态）；
- 通道2 B×cm1（独立会话, 非流式）：41.4s 同样**假拒答**——系统性复现, 非偶发；
- 第三次确认试验（`extra_B-cm1_confirm3.json`）：600s 客户端超时, 卡点为 t+371.8s 的 `kb_search_vector` 触发 `permission_request` 事件后无人审批（流式挂起）。
- **根因（实测定位，2026-10-12 会话转录取证）**：`kb_get_documents(lightweight)` 对 131 文档书架返回 **74.9KB** 的 catalog（MCP 同形实测 72.0KB）——**超过引擎工具输出预算**，引擎将完整输出落盘、仅向模型透传 **2KB 预览**（转录原文：`<persisted-output> Output too large (74.9KB). Full output saved to: …tool-results\call_083862a61d774ca7985b9caf.txt  Preview (first 2KB)`），模型实际只看到约 2–3 个文档的预览 → 判定“无 InstructDS 内容”。金标条目本身在完整清单中（描述明写 “InstructDS：将指令微调引入对话摘要…”）；对照组 B×cm2 成功 = 53 文档书架返回 33.1KB（<预算, 正常透传；75 文档书架 46.7KB 亦然）。**机制本质：面向 LLM 的工具返回大小预算是一层隐藏的检索依赖——平台最大书架静默超限。**
- **✅ 已修复（2026-10-13）**：kb-mcp 服务端三层改造——① `kb_get_documents` 预算门（每页硬上限 ~28K chars，超限自动切页 + `truncated="budget_guard"` + `has_more`，超预算返回**永远无法到达引擎**）+ `view="groups"` 书架分组图（131 docs → 571 chars）+ `group=` 定向过滤；② `kb_list(parent_id=…)` 逐级下钻过滤（`__root__`→根库、`<kb_id>`→仅直接子库，一级一级看描述）；③ `enumerate_scan.py` 机侧跟随分页（131 篇全覆盖不缩水）。librarian/hybrid/batch/list 四个 skill 契约同步改为"机械层召回 + agent 只看最想看的目录"。**验证**：11/11 行为断言全过（4 页分页各 ≤23.1K chars、131 篇无重无漏、page_size=200 请求被钳到 43）；逐级阶梯实跑 cm1 描述层字节 **6,689 vs 旧 73,742 chars**（-91%）；`enumerate_scan` 55.3s 全 131 篇扫描金标 3/4 part 命中；**端到端复跑原失败臂 B×cm1 → 门禁 PASS**（53.5s、9 turns、金标命中、refusal=false，`benchmark-suite/results/runs/chatmodes-fixverify-20261013/arm_B-cm1.json`）。
- **对照**：通道3 的脚本化图书管理员（词法扫描+字典序拼包）在同题上 25.0s/10.2s 双金标命中——描述层扫描需要**机械化 assist** 而非裸 LLM 注意力，这是论文“逐级检索 + 判卷引擎”叙事的直接证据。
- **判卷门修正**：原 marker 门被问题回显欺骗（拒答文本含 “InstructDS” 即命中），已在 `chat_mode_arms.py` 改为**拒答优先**判定（found 题答案构成拒答即 FAIL），本报告全部门禁按修正口径重算。

### 发现 2：vector baseline 默认指向空库

- `--retmodes` 的 vector/rrf baseline 默认查 `Corpus-Chunks800`，该库在早前 reset 后为空（0 命中）；首次运行 10/12 金标，vector 两题 ❌ 0 docs。以 `RAG_BENCH_VECTOR_KB=""`（跨库口径）重跑后 **12/12 全命中**（vector 对两题均为 rank-1, 分数 0.756/0.842）。报告引用重跑 run。

### 发现 3：其余 16/18 个 chat 臂全绿且行为正确

- A/C 车道 6 题 found 全部金标命中并给出带引文的正确回答（如 A×cm2 答出 29,072 条 EHR 记录、高血压/心脏病/年龄/BMI 等风险因素清单；C×cm1 答出 Flan-T5-XL 三步合成管线）；
- 三车道对域外题 cm3 全部**如实拒答**且检索轨迹合规（宽网→判卷→目录核查后才下结论）；弃答延迟 A=36.4s / B=29.9s / C=65.0s。

## 模式机制说明

- **模式 A**: 钉库向量快车道 (kbEnhanced=true + kbIds=[目标库], 服务端放开向量/判卷工具)
- **模式 B**: 全库逐级检索 (kbEnhanced=true + kbIds=[], 向量工具被服务端门禁抑制, 图书管理员 spine: 目录→书架→文档)
- **模式 C**: 混合检索 (钉库 + 混合检索指令后缀: 宽网 two_stage/vector + kb_laya_judge 判卷, 证据不足再逐级兜底)

## 证据文件

- 通道1: `review/retrieval-e2e-20261012/c1_*.json`（含完整 SSE timeline 与工具 span）+ `channel1_summary.json`
- 通道2: `benchmark-suite/results/runs/chatmodes-20261012T061102Z-5f9faac/`（arm_*.json + chatmodes.json + CHAT-MODES-COMPARE.md）
- 通道3: `benchmark-suite/results/runs/run-20261012T062847Z-5f9faac/`（RETRIEVAL-COMPARE.md + 逐臂 JSON）
- 本报告: `review/retrieval-e2e-20261012/REPORT.md` + `REPORT.html`

