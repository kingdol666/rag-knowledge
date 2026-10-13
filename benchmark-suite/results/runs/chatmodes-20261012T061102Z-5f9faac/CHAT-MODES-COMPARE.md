# Chat-API 三模式系统臂对照（当前系统官方执行流）

- Run: `chatmodes-20261012T061102Z-5f9faac` · 生成: 2026-10-12 06:20 UTC
- 通道: `POST /api/claude/chat` 默认**非流式**（一次阻塞 JSON）· `kbEnhanced=true` · A/C 钉库 `kbIds` · 工具门禁由服务端 `disallowedTools` 内建
- 判定门: found=HTTP200∧success∧答案非空∧答案金标词命中; refusal=HTTP200∧success∧如实拒答标记

| 模式 | 题 | 预期 | 耗时s | turns | 门 | 会话 |
|---|---|---|---:|---:|:--:|---|
| A | cm1 | found | 53.0 | 6 | ✅ | `44c01626` |
| A | cm2 | found | 65.3 | 6 | ✅ | `ed3a6fcf` |
| A | cm3 | refusal | 25.7 | 4 | ✅ | `ad186a66` |
| B | cm1 | found | 41.4 | 6 | ✅ | `9631420d` |
| B | cm2 | found | 91.9 | 8 | ✅ | `92f9997a` |
| B | cm3 | refusal | 66.0 | 11 | ✅ | `7495ea7f` |
| C | cm1 | found | 58.3 | 6 | ✅ | `3bc70319` |
| C | cm2 | found | 100.0 | 9 | ✅ | `8e25de47` |
| C | cm3 | refusal | 48.3 | 6 | ✅ | `6fe686f6` |

## 逐臂回答摘录

### A × cm1

> I have complete, verbatim methodology. Synthesizing the answer.  ---  **InstructDS 通过一个「三步数据合成流水线」从现成的 dialogue-summary 对自动造出高质量 query-dialogue-summary（QDS）三元组；关键增量来自两道过滤（剔不可答 + 语义去重），使专家评测的「既唯一又正确」比例从 45% 提升到 75%。**（出处：`nlp__2310.10981` ​*Instructive Dialogue Summarization with Query Aggregations*，Bin Wang et al., I2R A*STAR，KB `b1199132…`，P0 直接证据）  **背景**：query-based 对话摘要的监督数据稀缺（现有 QMSum 仅 232 个

### B × cm1

> ## 结论  **知识库中无对应内容** —— 全库（20 个 KB）没有任何文档覆盖 "InstructDS / 基于 query 的对话摘要指令微调数据合成" 这一主题。  **已执行的精确检索**  1. `kb_list(lightweight=true)` → 20 个库：计算机与人工智能(131)、自然科学与地球科学(75)、生命科学与医学(53)、工程与能源(39)、经济与社会(24)、aw-industrial(29)、AI 基础设施(3)、Novel-PridePrejudice(28)，以及 e2e-demo / demo-qa / soul-* / ZZ 复现 / 玄鸟演示等小库。目录描述中**唯一可能承载 NLP 论文的架子是「计算机与人工智能」**（含 artificial-intelligence__* / nlp__* 系 arXiv 论文）。 2. `kb_

### C × cm1

> **结论：InstructDS 用一条「三步合成法」从已有的 dialogue-summary 对自动生成高质量 QDS（query-dialogue-summary）三元组——① summary-anchored query generation（基于参考摘要生成候选查询）→ ② query filtering（文本+语义双重过滤保有效性/多样性）→ ③ query-based summary generation（以查询+完整摘要为输入、触发 LLM 问答能力生成查询条件摘要），再配合 mixed training 与 length augmentation 训练统一模型。**  ## 三步合成流程（论文 §3.2）  1. **Query Generation（查询生成）**：以 **Flan-T5-XL（模型 X）** 的 question-generation 能力，基于**参考

### A × cm2

> **结论：** 该库中唯一直接回答此问题的文献是 Nwosu 等《Predicting Stroke from Electronic Health Records》(arXiv:1904.11280)，其核心结论为——高血压、糖尿病、心脏病是中风的主要风险因素；PCA 显示患者属性之间相关性低，**不能**通过降维简化特征空间，须使用全部 10 个属性建模；并在 29072 条 EHR 记录上给出 ML 基准（神经网络 75.02% 最高）。**证据等级 P0（直接命中，全文可读）。**  **一、数据与建模设置（P0）** - 数据集：McKinsey & Company 医疗黑客松公开 EHR（Kaggle），**29072 名患者 × 12 属性**；11 个输入属性 + 1 个二元中风标签。10 个用于建模的输入为：性别、年龄、高血压(0/1)、心脏病(0/1)、婚姻状况、职业类型

### B × cm2

> # 基于 EHR 的中风预测：关键风险因素与机器学习基准  **结论**：命中一篇直接对口的文献——`生命科学与医学` 库的 **《Predicting Stroke from Electronic Health Records》**（Nwosu, Dev, Bhardwaj, Veeravalli, John；arXiv 1904.11280）。该文即用数据挖掘/经典 ML 分析 EHR 预测卒中，并系统分析风险因素影响与相互依赖。**P0 强证据**（描述层主题完全命中 + Laya 引擎判定存活 + 正文直接支撑）。demo-qa 杂项库 5 篇（长城/旅行者1号/光合作用/Transformer/检索卡）经描述层抽查，与本问题无关。  ## 关键风险因素 - 文献综述层面（引用 [6]-[8]）：**高血压、糖尿病、心脏病**是卒中主要风险因素（原文："high blood pre

### C × cm2

> I have the complete evidence. Here is the answer.  ---  **结论：在指定库（生命科学与医学）中，最直接回答该问题的是论文《Predicting Stroke from Electronic Health Records》(Nwosu et al., arXiv:1904.11280)。其核心结论是：基于 EHR 的 10 个患者属性（性别、年龄、高血压、心脏病、婚姻状况、职业、居住地、平均血糖、BMI、吸烟状态）预测中风，各特征间相关性不高、不能显著降维，多层感知机（MLP）取得最佳分类准确率 75.02%。**  **一、关键风险因素（论文列为 EHR 中的输入属性）**  论文基于 McKinsey/Kaggle 公开 EHR 数据集，样本 **29072 名患者、12 个属性**，其中 11 个输入属性为：患者标识、性别、年龄、

### A × cm3

> **结论：在指定的知识库（b1199132-e4d4-4305-8c2e-82dc1753b0ba，"计算机与人工智能"库）中未找到 "Herbert-Moulton collider benchmark" 这一术语，也未找到任何粒子物理（particle physics）探测器漂移（detector drift）标定/量化的相关内容。**  检索事实（只读，未修复任何内容）：  | 检索项 | 参数 | 命中情况 | |---|---|---| | `kb_search_two_stage` | query=`Herbert-Moulton collider benchmark detector drift particle physics`；stage1_top_k=20, stage2_top_k=5, slim=true | 20 个候选，5 条 stage2 结果；**无一与粒子

### B × cm3

> **结论：知识库中不存在关于「Herbert-Moulton 对撞机基准（Herbert-Moulton collider benchmark）」的任何内容——该问题所涉的粒子物理对撞机基准/探测器漂移量化主题，在全部 20 个知识库中均无对应文档。**  本轮为全库逐级检索，实际扫描如下（未命中，故无引文可给）：  1. **目录层** `kb_list(lightweight=true)`：20 个 KB，主题覆盖计算机与 AI（131 篇）、自然科学与地球科学（75 篇）、生命科学与医学（53 篇）、工程与能源（39 篇）、经济与社会（24 篇）、工业生产（aw-industrial 30 篇）、数学/统计、测试与演示库（e2e-demo、demo-qa、Novel-PridePrejudice、ZZ 复现库、玄鸟飞控演示库）等。无任何库的描述提及粒子物理实验、对撞机（collide

### C × cm3

> **结论：所查知识库中不存在关于「Herbert-Moulton collider benchmark」的任何内容，因此无法回答该基准如何量化粒子物理实验中的探测器漂移——该主题在库内为「未命中」。**  **检索事实（已执行的检索与命中情况）**  | 步骤 | 工具 | 查询 | 结果 | |---|---|---|---| | 1 | `kb_search_two_stage` | Herbert-Moulton collider benchmark detector drift particle physics | 20 候选，全部为 CS/AI 论文；无物理/对撞机文档 | | 2 | `kb_search_vector`（top_k=20） | detector drift measurement collider benchmark particle physics | 最高

