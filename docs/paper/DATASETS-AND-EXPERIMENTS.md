# 数据集与实验设计报告 —— 基于已发表论文的实证分析

> **生成**: 2026-09-09 · 方法：对 reference/ 全部 9 篇 PDF 的实验章节做全文提取分析
>（脚本产物 `tmp/paper_exp_extract.txt`），并联网核对 FlashRAG 数据集体系现状。
> **回答三个问题**: ① 已发表论文的数据从哪来 ② 哪些公开数据集能直接适配本系统 ③ 实验章节怎么写。

---

## 一、已发表论文的数据从哪来（实证画像）

| 论文 | 数据集 | 数据来源与规模 | 指标 | 关键实验组织 |
|---|---|---|---|---|
| **CRAG** (NAACL'24) | PopQA / Biography / PubHealth / Arc-Challenge | 4 个**公开 QA 集**，按生成形式分组：短生成/长生成/判断/选择；检索评估器用 PopQA 自带 golden wiki title 当相关性标签微调 | Acc、FactScore；**检索评估器单独报准确率（Table 4: T5-based 84.3 vs ChatGPT 58.0）** | ① 主表(基于不同底座 LLM) ② 与 Self-RAG 直接对比 ③ 逐动作消融 ④ **评估器本身单独成为一张表** |
| **Self-RAG** (ICLR'24) | PopQA / TriviaQA / Bio / PubHealth / ARC + KILT(NQ, WoW, FEVER) + ASQA | 全部公开；reflection token 标签由 GPT-4 生成（silver data） | Acc、FactScore、Rouge-L、MAUVE、**引用精度(str-em)**；检索频率-精度曲线 | 按任务形式分 4 组各一个 RQ；消融 3 数据集；人工评测 S&P |
| **Adaptive-RAG** (NAACL'24) | 单跳: SQuAD/NQ/TriviaQA；多跳: MuSiQue/HotpotQA/2Wiki | 语料 = **Wikipedia 预处理版（Karpukhin 2020 / Trivedi 2022）**；query-complexity 标注**无现成集 → 从 6 个集采样 400 条自动标注(silver)** | F1/EM/Acc + **Time/Query 效率曲线 (Fig.5)** | 复杂度分类准确率表 → 总体 QA 表 → 效率-效果权衡图 |
| **GraphRAG** (2024) | **自建**: Podcast + News(MultiHop-RAG) | **LLM persona 生成语料特定查询**（先让 LLM 推断潜在用户与用例再出题） | comprehensiveness / diversity（**win-rate 人工 pairwise 评**） | 全局意义生成任务；chunk size 消融 |
| **HiRAG** (EMNLP'25) | HotpotQA / 2Wiki + UltraDomain 4 集 | 公开；**客观+主观双轨**：EM/F1 客观表 + win-rate 主观表 | EM、F1、win-rate | 主表基线含 NaiveRAG/GraphRAG/LightRAG/fastgraphrag |
| **AgenticRAG** (2026) | **BRIGHT / WixQA / FinanceBench** | 按"**现实企业场景**"选集：长 PDF 手册(均 143 页/117K token)、企业 wiki、金融 | Recall@1、factuality、answer correctness | benchmark 统计表放附录 B；强调与 oracle 接近程度 |
| **DeepRead** (2026) | FinanceBench / QASPER / SyllabusQA / **ContextBench(自建)** | **自建集人工标注 94 篇**，附录 A.2 详述标注流程（先给 golden examples 再标注） | Acc（vs Search-o1 baselines） | 4 benchmarks × 主表；检索 recall vs accuracy 关系图 |
| **MCP-Pyserini** (SIGIR'26) | 预建索引 + relevance judgments | 资源论文：工具+评测一体化 | 检索指标 | Demo 场景 + artifact |

### 提炼出的五条铁律（审稿人默认预期）

1. **数据集全部来自公开 benchmark + 可选的自建集**；自建集必须：人工标注、附录给统计表（文档数/token 数/查询分布）、说明标注流程与一致性
2. **按任务形式分组选数据集**（短/长/判断/选择——CRAG；单跳/多跳——Adaptive-RAG），每组一个 RQ 一张表
3. **指标与任务严格绑定**：QA=EM/F1/Acc；检索=Recall@k/nDCG@k/P@k；长文=FactScore/Rouge/MAUVE；主观对比=win-rate
4. **评估器/验证模块单独评测**（CRAG Table 4）——本系统 QDCVR 内容验证的直接对应写法
5. **效率必须报**：time-per-query vs 性能的权衡曲线（Adaptive-RAG Fig.5 是范本）

---

## 二、可直接适配本系统的公开数据集（含具体接入方式）

### 2.1 首选通道：FlashRAG 数据集体系（最短路径）⭐

`huggingface.co/datasets/RUC-NLPIR/FlashRAG_datasets` 已成为 RAG 论文事实标准（GraphRAG-Router、
PIKE-RAG、Search-R1 等均用），**预处理好的评测集 + 对应 Wikipedia 语料一条龙**：

| 数据集 | 任务 | Test 规模 | 对本系统的适配方式 |
|---|---|---|---|
| **PopQA** | 单跳事实（长尾实体） | 14,267 | ① 检索质量主实验 ② **挑长尾实体子集构造"检索无益"样本 → 评测 QDCVR 拒答/盲点声明（PopQA 自带 golden wiki title = 现成相关性标签）** |
| **HotpotQA** | 2 跳，带句级 supporting facts | 7,405 dev | **按 supporting docs 的主题标题拆入不同 KB → 天然强制跨库检索**，直接测 KB 路由(Smart KB Selection)与 balance_kbs |
| **2WikiMultiHopQA** | 2-3 跳，带推理类型标注(comparison/inference/compositional/bridge) | 12,576 dev | comparison 类问题 = 两实体各在一库 → 跨库对比推理；推理类型 → 分难度报告 |
| **MuSiQue** | 2-4 跳组合推理 | 2,417 dev | 高难度多跳，压测两阶段召回 |
| **NQ / TriviaQA** | 单跳通用 | 3,610 / 11,313 | 与 Self-RAG/CRAG 直接可比的通用集 |
| **Bamboogle** | 多跳难题 | 125 | 小而难的抽查集 |

**多 KB 改造方法**（本系统独特实验设计，写进论文的 setup）：
把 FlashRAG 语料按 Wikipedia 页面主题（或 HotpotQA supporting docs 标题聚类）拆分为 **8–12 个主题 KB**，
每个问题 golden docs 分布在 1–4 个 KB → 这就是"多知识库检索"的公开可复现版本。
**没有任何已发表工作这样评过 KB 路由——这是本系统独有实验维度。**

### 2.2 备选/补充数据集

| 数据集 | 用途 | 备注 |
|---|---|---|
| **BRIGHT** (Su 2024) | 企业长文档检索（Recall@1） | AgenticRAG 用过；长 PDF 手册场景与 MinerU 管线契合；如需"企业级"叙事可选 |
| **PubHealth / FEVER** | 判断题/事实核查 | 与内容验证的 Correct/Incorrect 语义同源，CRAG/Self-RAG 都用了 |
| **FinanceBench / QASPER** | 长文档金融/学术 QA | DeepRead 用过；可选 |
| **CRAG KDD Cup 2024 数据集** | 网页检索增强生成（Meta 官方） | 若强调 corrective 检索对比可用 |

### 2.3 自建领域集（Track 2，DeepRead ContextBench 是先例）

用本系统真实 47 KB（材料/能源/AI…）人工标注 40–100 查询（五类：事实/推理/跨库/意图干扰/**盲点**）。
DeepRead 自建 ContextBench（94 篇人工标注）发表于顶会 → **自建集规模不用大，标注流程规范即可**。
盲点类样本没有任何公开集提供 → 这是自建集存在的理由，也是独家指标 FPR 的 ground truth。

---

## 三、两轨实验设计（论文 Evaluation 的骨架）

**Track 1 公开可比轨**（证明方法有效，给审稿人对比锚点）：
- 数据：PopQA(2k 子样本) + HotpotQA(1k) + 2Wiki(1k) + MuSiQue(500) —— FlashRAG 版本
- 拆库：按主题聚成 8–12 KB
- 指标：检索 P@5/R@5/nDCG@5 + **FPR** + 端到端 EM/F1/Acc + 盲点正确声明率
- Baselines（8 个）：BM25 / BGE-M3 向量 / BM25+Vec / Vec+CE-Rerank / RAG-Fusion /
  NaiveRAG / **CRAG 式 corrective**（retrieval evaluator + 纠正动作）/ **Self-RAG 式 LLM 自评**
- LLM：deepseek-v4-pro（omp 通道）+ 可选 GPT-4o-mini 对照列

**Track 2 领域自建轨**（证明实用价值，差异化叙事）：
- 数据：Dataset C(领域查询) + D(经验) + E(端到端)，按 BENCHMARK-TEST-PLAN v3.0
- 指标：经验分级 κ、时效衰减 F1、任务成功率、时延
- 消融在 Track 2 做：−Content Verify / −KB Selection / −balance_kbs / −经验路由

---

## 四、实验章节写法模板（对齐 CRAG/Self-RAG 的段落级规范）

```
6.1 Research Questions          RQ1-6 表（继承 CIKM-WRITING-FRAMEWORK）
6.2 Datasets & Setup
    - 数据集统计表（Table: 名称/任务/#Query/#Docs/#KB/平均token）← 仿 AgenticRAG 附录B
    - 语料说明: FlashRAG 预处理 Wikipedia + 拆库方法一段 ← 仿 Adaptive-RAG 语料来源段
    - Baselines 一句话逐个 + 底座 LLM 版本
6.3 Main Results (Table 2)
    - 行=8 方法, 列=P@5/R@5/nDCG@5/FPR/EM; 最好值加粗, 次优下划线, † 表显著
    - 正文三句法: ①总体谁赢多少 ②哪类问题赢最多(multi-hop/跨库) ③为什么(归因到机制)
6.4 Content Verifier Evaluation (Table 3)   ← 直接对标 CRAG Table 4
    - 把 0-8 rubric 当分类器: Correct/Incorrect/Ambiguous 三分类准确率 vs ChatGPT zero-shot
6.5 Ablation (Table 4)          逐模块移除, Δ 列
6.6 Efficiency (Fig)            time-per-query vs 质量(含/不含内容验证)  ← 仿 Adaptive-RAG Fig.5
6.7 Experience & Blind-spot (Table 5)   κ / 衰减 F1 / 拒答率
6.8 Case Study                  真实盲点拒答案例(双拉薄膜 435s 拒答现成)
```

**写作红线**（从 PDF 提取中看到的共同点）：
- 每张表正文都必须被三句话解释，不允许"表已自明"
- 消融必须回答"哪个模块贡献最大 + 为什么"
- 所有数字 5 次运行均值，配对 t 检验 †
- Limitations 段固定三选：LLM 打分延迟、标注规模、E0-E12 长期效果待验证

---

## 五、执行清单（立即开始）

1. **本周**：`pip install flashrag`（或直接下 FlashRAG_datasets 的 4 个评测 jsonl），写
   `benchmark-web/backend/load_flashrag.py` → 按主题拆库脚本 `split_corpus_to_kbs.py`
2. **下周**：8 个 baseline 在 PopQA 2k 子样本上跑通（baselines.py 已有骨架）
3. **并行**：Dataset C 领域查询标注启动（3 人 × 1 周 × 40 条初版）
4. **月底检查点**：Track 1 主表初版数字 → 决定是否冲 SIGIR 2027 AP（2027-01 截稿）或稳 CIKM 2027
