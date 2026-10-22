# Chat-API 三模式系统臂对照（当前系统官方执行流）

- Run: `chatmodes-20261021T051709Z-a8273b5` · 生成: 2026-10-21 05:42 UTC
- 通道: `POST /api/claude/chat` 默认**非流式**（一次阻塞 JSON）· `kbEnhanced=true` · A/C 钉库 `kbIds` · 工具门禁由服务端 `disallowedTools` 内建
- 判定门: found=HTTP200∧success∧答案非空∧答案金标词命中; refusal=HTTP200∧success∧如实拒答标记

| 模式 | 题 | 预期 | 耗时s | turns | 门 | 会话 |
|---|---|---|---:|---:|:--:|---|
| A | cm1 | found | 163.3 | 4 | ❌ | `bb543e6f` |
| A | cm2 | found | 129.3 | 4 | ✅ | `2a5a7a69` |
| A | cm3 | refusal | 200.5 | 7 | ✅ | `b90e7b03` |
| B | cm1 | found | 188.6 | 7 | ✅ | `2a43bcc4` |
| B | cm2 | found | 178.5 | 8 | ✅ | `9b2d3ed2` |
| B | cm3 | refusal | 192.6 | 12 | ✅ | `23bc1a1d` |
| C | cm1 | found | 130.0 | 5 | ✅ | `31097470` |
| C | cm2 | found | 167.0 | 7 | ✅ | `6997cec1` |
| C | cm3 | refusal | 181.0 | 7 | ✅ | `faa3310a` |

## 逐臂回答摘录

### A × cm1

> **InstructDS 通过一套“以摘要为锚”的三步合成流程，从现有的对话—摘要数据对中自动生成查询—对话—摘要（QDS）三元组，并且只靠约 1.3 个新三元组/对话就显著提升了查询式对话摘要质量。** 该方法的思路受 Self-Instruct 启发，目的是解决指令式对话摘要中监督数据稀缺的问题。  ### 三步合成流程（论文 §3.2）  **① 查询生成（Query Generation）** “为了覆盖多种潜在查询，我们利用大语言模型的问句生成能力生成多个候选查询。具体来说，我们使用 Flan-T5-XL……对于每个实例，我们使用表 7 中的模板生成 5 个候选查询。”关键在于**以参考摘要作为锚点**（“summary-anchored”），并不以对话本身作为锚点。  **② 查询过滤（Query Filtering）** - **基于文本的过滤**：把 Flan-T5-XL 

### B × cm1

> **InstructDS 生成高质量 query 型对话摘要数据的关键在于三步合成流程：以已有摘要为锚点生成查询、用文本与语义双重过滤提质、再由摘要而非对话生成基于查询的摘要，三步合起来把三元组质量从 45% 提升到 75%。**  ## 三步合成流水线（论文 §3.2）  1. **摘要锚定查询生成（summary-anchored query generation）**    用 **Flan-T5-XL**（论文称 model X，训练过 Quoref、MC-TACO、CosmosQA 等问答生成数据）针对每条已有的「对话–摘要」对生成 **5 个候选查询**。模板为："Generate an answerable and specific question based on the following context. Context: ${Summary}"——锚定在**完整摘要

### C × cm1

> **结论：InstructDS 不在“对话→摘要”上直接合成指令数据，而是以已有摘要为锚（summary-anchored），把问答式（dialogue-summary pair）数据三步合成成「查询-对话-摘要」(QDS) 三元组——先让 LLM 从完整摘要生成多条候选查询，再经可回答性+语义去重两道过滤，最后用「查询+完整摘要」生成查询式摘要。**  ## 三步合成流水线（论文 §3.2）  **① Query Generation（摘要锚定的查询生成）** 利用 Flan-T5-XL（文中称 model X，训练时见过 Quoref / MC-TACO / CosmosQA 等问答生成数据）的提问能力，**对每条摘要生成 5 条候选查询**，以保证查询多样性。关键设计是查询从**已在手的人工摘要**出发，而非从对话中凭空抽取——这样查询天然有答案、不依赖新标注。  **② Filte

### A × cm2

> **结论：在这批文献中，唯一直接回答“EHR + 机器学习预测卒中 + 关键风险因素影响”的是 Nwosu 等 *Predicting Stroke from Electronic Health Records*（arXiv 1904.11280）：它确认高血压、糖尿病/血糖、心脏病是文献公认的三大风险因素，并用 PCA 证明这 10 个 EHR 属性彼此低相关（前两个主成分仅解释 31.4% 方差），因此**不能删减特征**；基准模型上 MLP 最优，但准确率仅约 75%，说明仅靠结构化 EHR 属性的可分离性有限。**  ### 一、数据与特征（P0 直接证据） - 数据来自 McKinsey 医疗黑客松发布、经 Kaggle 公开的 EHR 集：**29,072 名患者、12 个属性**。 - 11 个输入属性：患者 ID、性别、年龄、高血压 0/1、心脏病 0/1、婚姻状态、职业类

### B × cm2

> **结论：知识库里只有一篇直接对口文献，其核心结论是：在 EHR 卒中预测中，10 个患者属性（年龄、婚姻状态、吸烟、平均血糖、BMI、高血压、心脏病、性别、职业、居住类型）彼此相关性低，不能削减特征；最佳基准模型是前馈多层感知机（MLP），1000 次重复实验平均准确率 75.02%（决策树 74.31%、随机森林 74.53%）。**  ## 一、数据与任务设定 - 数据源：McKinsey & Company 医疗黑客松发布、Kaggle 的公开 EHR 数据集，**29,072 名患者、12 个属性**；11 个输入属性含患者 ID、性别、年龄、高血压 0/1、心脏病 0/1、婚姻状态、职业类型、居住地类型（城/乡）、平均血糖水平、BMI、吸烟状态，第 12 个为卒中 0/1 因变量；建模时剔除患者 ID，留 10 个输入变量。 - 原文引述：*"The dataset conta

### C × cm2

> **结论：** 在库内检索到的文献中，唯一直接回答该问题的是 Nwosu et al.《Predicting Stroke from Electronic Health Records》（arXiv 1904.11280）：该研究用 EHR 的 10 个患者属性预测卒中，三种分类器中多层感知机（神经网络）表现最好，1000 次重复实验平均准确率为 **75.02%**，随机森林为 **74.53%**，决策树为 **74.31%**；三个模型性能显著重叠（[P0 直接证据]）。  **1. 研究设置（引文）** - 数据：McKinsey 通过 Kaggle 发布的 EHR 数据集，**29072 条记录、12 个属性**；删除患者 ID 后，剩 **10 个输入特征**，外加 1 个二值卒中标签。 - 类别极度不平衡：**“Out of 29072 medical records, on

### A × cm3

> **Conclusion: The knowledge base contains no evidence for a "Herbert-Moulton collider benchmark" or any method for quantifying detector drift in particle-physics experiments — the premise cannot be substantiated from the corpus, and it is not found in KB (honest not-found).**  **What I searched**  | Search | Scope | Result | |---|---|---| | `kb_search_two_stage` "Herbert-Moulton collider benchmark

### B × cm3

> **结论：本知识库中没有任何关于「Herbert-Moulton 对撞机基准」或粒子物理实验中探测器漂移量化的内容；因此判定为 NOT_FOUND，不能作答。**  **检索过程（全库逐级检索，只读）**  1. `kb_list(lightweight=true, parent_id="__root__")` — 共 21 个顶层库，逐一比对目录描述，没有发现任何库覆盖「粒子物理 / 加速器 / 对撞机 / 探测器校准」领域：    - 唯一物理相关库「自然科学与地球科学」（75 篇）：描述范围为 physics / quantum / climate / astronomy / chemistry / ocean / seismology，**不含粒子物理或加速器**。    - 「工程与能源」（39 篇）：power systems / battery materials / con

### C × cm3

> **结论：本知识库中没有关于 “Herbert-Moulton collider benchmark” 的任何内容，因此无法说明它如何量化探测器漂移；该检索结果为零命中，而且这个基准的名称本身在库中无法核实（库内既无该基准，也无任何对撞机探测器漂移或刻度漂移的方法学文献）。**  ### 已执行的检索（均为 MCP 只读工具）  **主库 `计算机与人工智能`（b1199132…，131 篇）** - `kb_search_two_stage("detector drift particle physics collider benchmark")` → stage1 候选 20 / stage2 命中 5，最高向量分 0.547；命中的文档全部是 GPT-3 少样本学习（测试集污染分析）、BERT 微调、语音韵律边界检测、MLP-SLAM 等，与粒子物理无关。 - 另用 `kb_sear

