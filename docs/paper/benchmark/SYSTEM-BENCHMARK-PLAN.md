# QDCVR 知识库平台 — CIKM 2027 可发表级完整评测方案（v6.0 最终版）

> **本文是评测的唯一权威文档，取代之前所有版本（含 v5.0）。**
> **目标**: CIKM 2027 Full Research Paper §6 Experimental Evaluation
> **叙事定位**: _Organize First, Retrieve Later_ — 领域结构 + 内容验证 + 经验生命周期
> **差异化王牌**: content-overrides-vector 原则 + 经验生命周期 E0-E12 + 完整 KB 生命周期管理 + **五层数据一致性模型** + **冥想自动归纳** + **多格式解析质量**
> **必比对手**: CRAG, Self-RAG, MCP-Pyserini (RAGFlow/Dify 作为系统级对照)
> **版本**: v6.0 Final · **最后更新**: 2026-07-29
> **对齐系统**: RAG Knowledge Platform v2.3.0 · 71 MCP Tools · 14 Skills · 5-Layer Data Model

---

## 目录

- [0. 论文逻辑链：每个实验回答什么](#0-论文逻辑链)
- [1. 评测哲学与方法论](#1-评测哲学)
- [2. 基线系统选择与辩护](#2-基线系统)
- [3. 数据集与评测资源](#3-数据集)
- [4. 实验总览（18 实验 × 4 层评测金字塔）](#4-实验总览)
- [5. Layer 1 — 检索精度 (EXP-1~4, EXP-7~8, EXP-15)](#5-layer-1-检索精度)
- [6. Layer 2 — 功能正确性 (EXP-5~6, EXP-11, EXP-17)](#6-layer-2-功能正确性)
- [7. Layer 3 — 系统完整性 (EXP-9~10, EXP-12, EXP-16, EXP-18)](#7-layer-3-系统完整性)
- [8. Layer 0 — 数据基础层 (EXP-13~14)](#8-layer-0-数据基础层)
- [9. 综合评分与论文产出物映射](#9-综合评分)
- [10. 统计协议](#10-统计协议)
- [11. 审稿人预判防御矩阵](#11-防御矩阵)
- [12. 执行路线图与资源评估](#12-执行)
- [13. 结果输出规范](#13-输出规范)
- [14. 变更日志](#14-变更日志)

---

## 0. 论文逻辑链

```
┌──────────────────────────────────────────────────────────────────────┐
│ 每个实验必须对应论文逻辑链的一个环节，否则审稿人会问"这证明什么"         │
└──────────────────────────────────────────────────────────────────────┘

Foundation (Layer 0)
────────────────────
  EXP-13: 多格式解析质量 → 入库管线的可靠性基础
  EXP-14: 增量索引正确性 → 数据新鲜度和并发安全

Problem
───────
  RAG 系统在扁平语料上产生系统性跨域误召回
  (EXP-0: 实测 thermal management 污染 4 领域; FPR=0.60 Flat vs 0.00 Domain)

Insight
───────
  误召回根因不是嵌入模型差，而是语料缺乏领域结构
  + 向量相似度不等于内容相关性（向量分数欺骗性）

Claims
──────
  C1:  领域组织压缩搜索空间 → 高效              [EXP-1, EXP-3]
  C2:  领域边界消除跨域误召回 → 准确              [EXP-2]
  C3:  content-overrides-vector → 可信            [EXP-4]
  C4:  经验 E0-E12 加速运维检索                   [EXP-5]
  C5:  自动归档 A0-A9 准确可靠                    [EXP-6]
  C6:  QDCVR 在效率-精度联合指标上超越基线          [EXP-7, EXP-8]
  C7:  五层一致性模型保障数据可靠性                 [EXP-9]
  C8:  图谱桥接文档实现跨域知识发现                 [EXP-10]
  C9:  balance_kbs 防止大库霸权                    [EXP-11]
  C10: 递归层级结构正确反映嵌套 KB                 [EXP-12]
  C11: 冥想自动归纳持续生产高质量经验               [EXP-13] ⭐ NEW
  C12: MinerU 多格式解析达到可接受准确率             [EXP-14] ⭐ NEW
  C13: 增量索引维护入库后检索一致性                 [EXP-15] ⭐ NEW
  C14: 跨语言检索能力达标                          [EXP-16] ⭐ NEW
  C15: 标签生命周期管理有效                         [EXP-17] ⭐ NEW
  C16: 系统可线性扩展到大规模语料                   [EXP-18] ⭐ NEW

Comparison
──────────
  vs CRAG (后验证) / Self-RAG (反射token) / MCP-Pyserini (纯IR工具)
  vs RAGFlow / Dify / LightRAG (系统级对照)

Ablation
────────
  消融 10 个组件 (含增量索引 + 固定向量索引)

Result
──────
  论文 Table 1-14 + Figure 1-12
```

### 十六大核心声明（Claims）及其验证实验

| Claim | 声明内容 | 验证实验 | 如果成立，证明什么 |
|:-----:|---------|:-------:|-------------------|
| **C1** | 领域组织使搜索空间压缩 ≥1000×，P@5 不降 | EXP-1, EXP-3 | "组织优先"的效率价值 |
| **C2** | 领域边界消除跨域误召回，FPR 相对降低 ≥80% | EXP-2 | 结构解决了扁平 RAG 无法解决的跨域污染 |
| **C3** | content-overrides-vector 原则独立于向量分裁决 | EXP-4 | CRAG/Self-RAG 做不到的可解释裁决 |
| **C4** | 经验优先检索使运维查询的文档读取减少 ≥50% | EXP-5 | 经验的实用价值 |
| **C5** | 自动归档 Top-1 准确率 ≥80%，支撑结构可靠 | EXP-6 | 领域结构的前提条件成立 |
| **C6** | QDCVR 在效率-精度联合指标上超越 CRAG 和 Self-RAG | EXP-7, EXP-8 | 整体优势 |
| **C7** | 五层一致性模型确保文档删除后索引正确清理 | EXP-9 | 数据完整性（#1 数据损坏成因的防御） |
| **C8** | 图谱桥接文档发现跨域知识联系 | EXP-10 | Neo4j 图谱的实用价值 |
| **C9** | balance_kbs 多样性守卫防止大库检索霸权 | EXP-11 | 公平检索的工程保障 |
| **C10** | 递归层级正确计数嵌套 KB 文档 | EXP-12 | 层级结构模型的正确性 |
| **C11** ⭐ | 冥想自动归纳持续生产高质量经验（≥60% 可审批率） | EXP-13 | 经验知识库自我增长的自动化价值 |
| **C12** ⭐ | MinerU 解析在不同格式上达到可接受准确率（≥85% markdown fidelity） | EXP-14 | 入库管线可靠性基础 |
| **C13** ⭐ | 增量索引维护入库→检索一致性，无索引过期 | EXP-15 | 系统长期运行的数据可靠性 |
| **C14** ⭐ | 跨语言检索在中文查询上不弱于英文查询 | EXP-16 | 系统多语言能力 |
| **C15** ⭐ | 标签生命周期管理有效：自动去重、孤儿清理、标签检索 | EXP-17 | 标签系统的工程价值 |
| **C16** ⭐ | 系统吞吐和延迟可线性扩展到 10× 数据量 | EXP-18 | 大规模部署可行性 |

---

## 1. 评测哲学

### 1.1 四层评测金字塔（v6.0 扩展）

```
        ┌─────────────────────────┐
        │  Layer 3  System E2E    │  系统级端到端
        │  EXP-9~12, EXP-16, 18   │  一致性/图谱/层级/跨语言/扩展性
        ├─────────────────────────┤
        │  Layer 2  Functional    │  功能正确性
        │  EXP-5~6, EXP-11, 17    │  经验/归档/多样性/标签
        ├─────────────────────────┤
        │  Layer 1  Retrieval     │  检索精度
        │  EXP-1~4, EXP-7~8, 15   │  P@k/FPR/nDCG/MRR + 增量
        ├─────────────────────────┤
        │  Layer 0  Data Found.   │  数据基底层 ⭐ NEW
        │  EXP-13~14              │  解析质量 / 增量索引正确性
        └─────────────────────────┘
```

**Layer 0 是 v6.0 新增的基础层**：审稿人会问"你的检索好是因为解析做得好还是检索算法好？"
如果没有 Layer 0，我们无法区分 pipeline 效应的来源，消融实验也不完整。

### 1.2 与纯 IR 基准的本质区别

| | 纯 IR Benchmark | 本评测方案 |
|---|---|---|
| 视角 | 算法精度竞赛 | 系统功能完整性 + 数据一致性 + **数据质量** |
| 指标 | 单一 P@k, nDCG | 精度 + 效率 + 功能 + 可用性 + 一致性 + **解析质量** |
| 基线 | 仅检索方法 | 检索方法 + 完整系统 + 消融组件 |
| 数据 | 静态 benchmark | 动态：上传→解析→分类→检索→整理→经验→验证→**冥想** |
| 统计 | 通常是 | 必须（配对检验 + CI + 效应量 + Bonferroni） |
| **数据一致性** | 不测 | **5 层模型完整性验证（独有）** |
| **增量索引** | 不测 | **ADO 周期验证（独有）** |
| **解析质量** | 不测 | **多格式 fidelity 评测（独有）** |

---

## 2. 基线系统

### 2.1 基线选择矩阵

CIKM 审稿人会要求与**最相关已发表工作**对比，且基线必须**公平可复现**。

| 基线 | 类别 | 为什么必须比 | 如何实现公平对比 |
|------|:----:|-------------|----------------|
| **B1: Vector-only (BGE-M3)** | 检索方法 | 当前 RAG 主流 | 同一嵌入模型、同一查询、同一 top-k |
| **B2: BM25+Vector fusion** | 检索方法 | 混合检索标准 | 同一语料，线性融合 α=0.5 |
| **B3: Vec+Cross-Encoder Rerank** | 检索方法 | 强检索基线 | ms-marco-MiniLM CE 重排 |
| **B4: CRAG-style** ⭐ | 检索后验证 | **头号竞争** | 实现评估器→三档动作管线 |
| **B5: Self-RAG-style** ⭐ | 反射验证 | 内容验证对手 | 用 LLM 模拟 reflection token |
| **B6: MCP-Pyserini** | Agent IR | **必须引用+区分** | 调用其 MCP 工具做检索对比 |
| **B7: 两阶段搜索 (不含内容验证)** | 我们的系统消融 | 验证内容验证的独立贡献 | 同管线但跳过 Step 3 |
| **B8: Flat QDCVR (无 KB 选择)** | 我们的系统消融 | 验证 KB 选择的独立贡献 | 同管线但 kb_id="" |
| **S1: RAGFlow** | 知识库系统 | 系统级对照 | 同文档集，测入库→检索完整流程 |
| **S2: Dify** | 知识库平台 | 系统级对照 | 同文档集，测功能覆盖 |
| **S3: LightRAG** | 图增强 RAG | 图方法对照 | 同文档集，测图增强效果 |
| **P1: Unstructured.io** ⭐ | 解析基线 | 解析质量对照 | 同 PDF 集，测 markdown fidelity |
| **P2: LlamaParse** ⭐ | 解析基线 | 解析质量对照 | 同 PDF 集，测 table/formula |

### 2.3 对比公平性声明（论文必写）

> *"All baselines use the same document corpus, the same embedding model (BGE-M3, 1024-dim), and the same query set. Retrieval baselines (B1-B8) are implemented within the same infrastructure, varying only the retrieval strategy. System baselines (S1-S3) are tested with identical document sets. Parse baselines (P1-P2) are tested with identical PDF inputs. Any differences in preprocessing or chunking are documented and discussed."*

---

## 3. 数据集

### 3.1 评测数据集总览（v6.0 扩展）

| 数据集 | 来源 | 规模 | 用途 | 类型 |
|--------|------|:----:|------|:----:|
| **D1: arXiv-6D** | arXiv API | 60 篇 (6领域×10) | EXP-1,2,3,6,7,8,14 | 多领域科学论文 |
| **D2: MS MARCO dev** | MS MARCO | 6,980 查询 | EXP-1,3,7,16 | 标准检索 benchmark |
| **D3: BEIR-subset** | BEIR | NFCorpus+SciFact | EXP-1,7 | 标准 IR 零样本评测 |
| **D4: StackOverflow-QA** | SO Data Dump | 50 QA pairs | EXP-5 | 运维/故障型查询 |
| **D5: TechDocs-mixed** | ReadTheDocs+GitHub | 30 篇 (中英混合) | EXP-6,14 | 多语言文档 |
| **D6: 系统现有数据** | 13 KB × 154 docs | 13,709 chunks | EXP-2,4,8,9,10,11,12,15,18 | 跨域对抗+消融+一致性 |
| **D7: 对抗查询集** | 人工构造 | 15 条 | EXP-2 | 跨域对抗 |
| **D8: 图谱桥接文档** | Neo4j 现网 | 50 篇跨KB桥文档 | EXP-10 | 图谱验证 |
| **D9: Multi-format corpus** ⭐ | 构造 | 40 文件 (PDF/Word/Excel/Image) | EXP-14 | 解析质量 |
| **D10: Chat session DB** ⭐ | 系统收集 | 100+ 用户对话 | EXP-13 | 冥想输入源 |
| **D11: Chinese queries** ⭐ | 人工构造 | 30 中文查询 | EXP-16 | 跨语言能力 |
| **D12: Scalability corpus** ⭐ | 构造 | 10× 规模 (600 篇) | EXP-18 | 扩展性 |
| **D13: Tag benchmark** ⭐ | 构造 | 30 篇含标签 | EXP-17 | 标签评估 |

### 3.2 数据集使用矩阵（v6.0 扩展）

```
         D1  D2  D3  D4  D5  D6  D7  D8  D9 D10 D11 D12 D13
EXP-1     ✓   ✓   ✓
EXP-2     ✓                   ✓   ✓
EXP-3     ✓   ✓   ✓
EXP-4     ✓
EXP-5             ✓   ✓
EXP-6     ✓               ✓
EXP-7     ✓   ✓   ✓
EXP-8     ✓                   ✓
EXP-9                             ✓
EXP-10                            ✓   ✓
EXP-11                            ✓
EXP-12                            ✓
EXP-13                                        ✓
EXP-14    ✓               ✓       ✓   ✓
EXP-15                            ✓
EXP-16    ✓   ✓                               ✓
EXP-17                        ✓   ✓                       ✓
EXP-18                            ✓                   ✓
```

---

## 4. 实验总览

| 实验 | 标题 | Layer | Claim | 指标 | 数据集 |
|:----:|------|:-----:|:-----:|------|:-----:|
| EXP-0 | 系统基线 + 跨域污染实证 | — | Problem | 系统快照, FPR | D6 |
| EXP-1 | 检索精度主实验 | L1 | C1 | P@k, nDCG, MRR, MAP | D1,D2,D3 |
| EXP-2 | 跨域误召回消除 | L1 | C2 | FPR, KB Diversity | D1,D6,D7 |
| EXP-3 | 多基线全面对比 | L1 | C1,C6 | 全指标 vs 8 基线 | D1,D2,D3 |
| EXP-4 | Content-Overrides-Vector 实证 | L1 | C3 | FPPR, scatter | D1 |
| EXP-5 | 经验管道有效性 | L2 | C4 | docs_read, exp_hit_rate | D4,D5 |
| EXP-6 | 自动归档与知识组织 | L2 | C5 | Top-1 Acc, Tag quality | D1,D5 |
| EXP-7 | 效率与成本对比 | L1 | C6 | Latency breakdown, P@5/ms | D1,D2,D3 |
| EXP-8 | 消融实验 (10 组件) | L1 | C6 | ΔP@5 per component | D1,D6 |
| EXP-9 | 五层数据一致性验证 | L3 | C7 | 5-layer status (✓/✗) | D6 |
| EXP-10 | 图谱桥接文档评估 | L3 | C8 | Relevance, hit rate | D6,D8 |
| EXP-11 | balance_kbs 多样性守卫 | L2 | C9 | Shannon entropy, dominance | D6 |
| EXP-12 | 递归层级结构验证 | L3 | C10 | Count accuracy | D6 |
| **EXP-13** ⭐ | **冥想自动归纳质量** | **L0** | **C11** | **Approve rate, signal P/R** | **D6,D10** |
| **EXP-14** ⭐ | **多格式解析质量** | **L0** | **C12** | **MD fidelity, table acc** | **D1,D5,D9** |
| **EXP-15** ⭐ | **增量索引正确性** | **L1** | **C13** | **ADO cycle consistency** | **D6** |
| **EXP-16** ⭐ | **跨语言检索能力** | **L3** | **C14** | **ΔP@5(zh vs en)** | **D1,D2,D11** |
| **EXP-17** ⭐ | **标签管理生命周期** | **L2** | **C15** | **Tag P/R, dedup rate** | **D6,D13** |
| **EXP-18** ⭐ | **系统扩展性测试** | **L3** | **C16** | **Throughput, latency@scale** | **D6,D12** |

---

## 5. Layer 1 — 检索精度 (EXP-1~4, EXP-7~8, EXP-15)

### EXP-0: 系统状态基线 + 跨域污染实证

**对应论文**: §1 Introduction (Figure 1 的 failure case)
**目的**: (1) 建立当前系统状态基线 (2) 实证跨域污染问题存在
**这不是假设检验，而是问题陈述的证据。**

#### 协议

```
Step 1: 记录系统状态快照（当前真实数据）
  → KB 数量: 13
  → 文档总数: 154
  → Chunk 总数: 13,709 (16 collections)
  → 嵌入模型: BAAI/bge-m3, 1024-dim
  → 大库占比: 55.5% (高分子双向拉伸文献库, 7610 chunks)
  → 图谱节点: 179, 边: 2,502
  → 输出: benchmark/results/EXP-0-system-baseline.json

Step 2: 跨域污染实证（实测数据）
  查询 "thermal management" 平铺检索:
  → Flat (kb_id=""): 返回 Energy-Batteries + 高分子 + Materials-ML + Materials-Science (4 领域)
  → Domain (kb_id=Energy): 仅返回 Energy-Batteries (1 领域)
  → 量化: 跨域污染 FPR = 0.60 (Flat) vs 0.00 (Domain)

Step 3: 输出 Figure 1 数据
  → 跨域污染散点: 每个 (query, doc) 对的向量分 vs 所属 KB
```

#### 产出

| 指标 | 值 | 用途 |
|------|:--:|------|
| 系统 KB 数 | 13 | 系统规模 |
| 文档总数 | 154 | 语料规模 |
| Chunk 总数 | 13,709 | 检索基数 |
| 大库占比 | 55.5% (高分子 7610) | 大库主导证据 |
| 跨域污染率（Flat） | ~60% | 问题实证 |
| 领域隔离率（Domain） | 100% | 方案预期 |

---

### EXP-1: 检索精度主实验

**对应论文**: §6.2 Main Results (Table 1)
**假设 (H1)**: QDCVR Domain-organized 检索的 P@5 ≥ Vector-only Flat 检索，且 nDCG@5 显著更高。
**预注册**: H0: P@5(domain) = P@5(flat); H1: P@5(domain) > P@5(flat)

#### 数据集: D1 (arXiv-6D, 60 queries) + D2 (MS MARCO dev, 50 queries sampled) + D3 (BEIR NFCorpus+SciFact)

#### 协议

```
Stage A: 文档入库 (使用 D1 的 60 篇 arXiv papers)
  A1. 创建 6 个领域 KB (cs.AI, cs.CL, cs.CV, stat.ML, physics, q-bio)
  A2. 对每篇:
    → fs_upload_file → parse_doc → kb_doc_save_parsed → kb_index_document
  A3. 验证: kb_search_stats(kb_id) 确认 chunks > 0

Stage B: 构造查询集
  B1. 对 D1: 从每篇文档提取标题+摘要生成 3 类查询 (title/abstract/cross), 共 60 条
  B2. 对 D2: 随机采样 50 条 MS MARCO 查询
  B3. 对 D3: 使用 BEIR 原始查询
  B4. Ground Truth:
    - D1: 源文档 = 正例
    - D2/D3: 使用 BEIR/MSMARCO 官方 qrels

Stage C: 执行检索
  对每条查询执行 4 种方法:
  C1. Flat (B1): kb_search_vector(q, kb_id="", top_k=5)
  C2. Domain (ours): kb_list(lightweight=true) → 选库 → kb_search_vector(q, kb_id=selected, top_k=5)
  C3. BM25+Vec (B2): BM25 + 向量线性融合
  C4. Vec+CE (B3): 向量 top-20 → CE 重排 top-5

Stage D: 计算指标
  → P@1, P@3, P@5, R@5, nDCG@5, MRR, MAP
  → 候选文档数 (搜索空间)
  → 统计检验: 配对 t-test, p-value, Cohen's d, 95% bootstrap CI
```

#### 预期结果表 (Table 1)

| Method | P@1 | P@3 | P@5 | nDCG@5 | MRR | MAP | Candidates↓ |
|--------|:---:|:---:|:---:|:------:|:---:|:---:|:-----------:|
| B1: Vector-only (Flat) | — | — | — | — | — | — | ~13,709 |
| B2: BM25+Vector | — | — | — | — | — | — | ~13,709 |
| B3: Vec+CE Rerank | — | — | — | — | — | — | ~13,709 |
| **QDCVR Domain (ours)** | — | — | — | — | — | — | **~12** |
| *Δ vs B3* | | | | | | | **×1,142** |

**验收**: P@5(domain) ≥ P@5(flat) 且 搜索空间缩减 ≥ 100× (p < 0.05)

---

### EXP-2: 跨域误召回消除

**对应论文**: §6.3 Cross-Domain Robustness (Table 2, Figure 4)
**假设 (H2)**: QDCVR 的领域 KB 选择系统性消除跨域假阳性，FPR 显著低于 Flat 检索。

#### 数据集: D7 对抗查询集 (15 条) + D1 multi-domain queries + D6 现有跨域数据

#### 协议

```
Stage A: 对抗查询集 (D7)
  15 条查询，每条查询词跨 ≥2 领域但只有一个正确答案。
  例:
  - "reinforcement learning policy optimization" → correct: AI-ML-Research, distractor: Materials-ML
  - "thermal management cooling" → correct: Energy-Batteries, distractor: Materials-Science, 高分子

Stage B: 对每条查询执行
  B1. Flat: kb_search_vector(q, kb_id="", top_k=5)
  B2. Domain: kb_list(lightweight=true) → 选库 → kb_search_vector(q, kb_id=selected, top_k=5)
  B3. GroundTruth: kb_search_vector(q, kb_id=<correct_kb>, top_k=5)

Stage C: 度量
  → FPR = top-5 中来自非目标 KB 的文档数 / 5
  → KB Diversity (Shannon entropy): -Σ p_i·log₂(p_i)
  → Domain Selection Accuracy: Agent 选中正确 KB 的比例

Stage D: 跨域混淆矩阵
  → 哪些领域 pair 最容易混淆？
  → 例: Materials-ML ↔ AI-ML-Research 的混淆率
```

#### 预期结果表 (Table 2)

| Query Type | Flat FPR | Domain FPR | GT FPR | FPR Reduction |
|-----------|:--------:|:----------:|:------:|:-------------:|
| Adversarial (n=15) | 0.58 | **0.08** | 0.00 | **86.2%** |
| Multi-domain (n=20) | 0.42 | **0.05** | 0.00 | **88.1%** |
| Overall (n=35) | 0.49 | **0.06** | 0.00 | **87.8%** |

**验收**: FPR 相对降低 ≥ 80% (p < 0.001)

---

### EXP-3: 多基线全面对比

**对应论文**: §6.2 Main Results + §6.6 Comparison with Prior Systems
**目的**: 在一张表上展示 QDCVR 相对所有基线的优势。

#### 协议

```
Stage A: 检索方法对比 (B1-B8 vs Ours)
  → 使用 D1 + D2 统一评测
  → B4 (CRAG): 实现评估器→三档动作→如 Incorrect 则 cross-KB 扩展
  → B5 (Self-RAG): LLM 逐 chunk 输出 IS_REL/IS_SUP
  → B6 (MCP-Pyserini): 如其 MCP 可用则调用；否则用等价的 BM25+dense 实现 + 诚实声明
  → B7 (Two-stage without content verification): 我们的管线跳过 Step 3
  → B8 (Flat QDCVR without KB selection): 同管线但 kb_id="" 
  → 所有方法同嵌入、同 top-k、同查询

Stage B: 系统级对比 (S1-S3 vs Ours)
  → 对 30 篇 D1 文档:
    - 在各系统中创建 KB → 导入文档 → 执行同样 60 条查询 → 录 P@5
    - 记录操作步骤数作为"易用性"代理指标
  → 检查功能矩阵:
    | 功能 | RAGFlow | Dify | LightRAG | Ours |
    | 自动归档 | ✗ | ✗ | ✗ | ✓ |
    | 经验管理 | ✗ | ✗ | ✗ | ✓ |
    | 层次 KB | 部分 | ✗ | ✗ | ✓ |
    | 图谱桥接 | ✗ | ✗ | ✗ | ✓ |
    | 多样性守卫 | ✗ | ✗ | ✗ | ✓ |
    | 一致性模型 | ✗ | ✗ | ✗ | ✓ |
    | 冥想归纳 | ✗ | ✗ | ✗ | ✓ |
    | 标签管理 | ✗ | 部分 | ✗ | ✓ |
    | Agent 工具 | ✗ | 部分 | ✗ | 71 MCP |
```

#### 预期结果表 (Table 3 — 核心大表)

| Method | P@5 | nDCG@5 | FPR↓ | Latency(ms) | Search Space | 额外功能数 |
|--------|:---:|:------:|:----:|:----------:|:------------:|:----------:|
| B1: Vector-only | — | — | — | — | 13,709 | 0 |
| B2: BM25+Vector | — | — | — | — | 13,709 | 0 |
| B3: Vec+CE Rerank | — | — | — | — | 13,709 | 0 |
| B4: CRAG-style | — | — | — | — | 13,709 | 1 |
| B5: Self-RAG-style | — | — | — | — | 13,709 | 1 |
| B6: MCP-Pyserini | — | — | — | — | 13,709 | 1 |
| B7: Two-stage (no verify) | — | — | — | — | 13,709 | 0 |
| B8: QDCVR Flat (no KB sel) | — | — | — | — | 13,709 | 0 |
| **QDCVR (ours)** | — | — | — | — | **~12** | **9** |
| *Best baseline* | *best* | *best* | *best* | *best* | — | — |

---

### EXP-4: Content-Overrides-Vector 实证

**对应论文**: §6.4 Content Verification Analysis (Figure 5)
**假设 (H3)**: 存在高向量分(>0.6)低内容分(≤4)的文档被 QDCVR 正确丢弃，证明 C-over-V 原则有效。

#### 协议

```
Stage A: 对每条查询 (D1, 60 条)
  A1. 获取 Flat top-20 (向量分 >0.30)
  A2. 对每个候选: kb_doc_read(max_chars=3000) → 0-8 rubric 打分
  A3. 记录 (vector_score, content_score, 最终决策)

Stage B: 构建 Content-vs-Vector 散点图
  → 横轴: Vector Score [0,1]
  → 纵轴: Content Score [0,8]
  → 关键区域: 右下角 (v>0.6, c≤4) = QDCVR 正确截断的假阳性

Stage C: 量化 C-over-V 贡献
  → False Positive Prevention Rate (FPPR) 对比 CRAG 和 Self-RAG
```

#### 预期结果

| 场景 | 数量 | 说明 |
|------|:---:|------|
| 高向量 (>0.6) + 低内容 (≤4) | ~18% | QDCVR 正确截断 |
| 高向量 + 高内容 → Accept | ~65% | 正确通过 |
| 低向量 + 高内容 → Accept | ~5% | C-over-V 挽救 |

---

### EXP-7: 效率与成本对比

**对应论文**: §6.6 Efficiency Analysis (Table 7)
**目的**: 证明 QDCVR 的延迟是可接受的，且效率-精度联合指标优于基线。

#### 协议

```
Stage A: 延迟分解
  → Query Understanding (ms)
  → KB Selection (ms)
  → Two-Stage Recall (ms)
  → Content Verification (ms) ← 瓶颈
  → Confidence Tiering (ms)
  → Answer Synthesis (ms)

Stage B: 方法间延迟对比
  → B1 (Vector): 纯向量检索
  → B3 (Vec+CE): 向量 + Cross-Encoder 重排
  → B4 (CRAG): 评估器
  → QDCVR: 完整管线
```

#### 预期结果表 (Table 7)

| Stage | Latency (ms) | % of Total |
|-------|:------------:|:----------:|
| Query Understanding | — | —% |
| KB Selection | — | —% |
| Two-Stage Recall (BM25+Graph) | — | —% |
| Content Verification | — | —% |
| Confidence Tiering | — | —% |
| **Total** | — | **100%** |

| Method | Latency (ms) | P@5 | P@5/ms (×1000) |
|--------|:------------:|:---:|:--------------:|
| B1: Vector-only | — | — | — |
| B3: Vec+CE | — | — | — |
| B4: CRAG-style | — | — | — |
| **QDCVR** | — | — | — |

---

### EXP-8: 消融实验（增强版 — 10 个组件）

**对应论文**: §6.7 Ablation Study (Table 8, Figure 7)
**目的**: 证明每个组件有独立的、可测量的边际贡献。

#### 消融矩阵（v6.0 扩展）

| 变体 | 移除的组件 | 验证的 Claim | 预期 ΔP@5 | 预期 ΔFPR |
|------|-----------|:-----------:|:---------:|:---------:|
| QDCVR-full | — (完整系统) | baseline | 0.000 | 0.000 |
| −ContentVerify | 0-8 内容验证 (Step 3) | C3 | **−0.15** | **+0.28** |
| −Archiving | 自动归档 → 扁平 KB | C5, C1 | **−0.12** | **+0.22** |
| −DomainScope | KB 选择 → 全库检索 | C1, C2 | **−0.08** | **+0.18** |
| −QueryRewrite | 查询理解 (Step 0) | — | −0.03 | +0.02 |
| −Balance | balance_kbs 多样性守卫 | C9 | −0.02 | +0.01 |
| −Experience | 经验优先路由 | C4 | −0.01ˣ | — |
| −BlindSpot | 盲点声明 | — | — | — |
| **−RecursiveCount** | 递归文档计数 | C10 | **−0.04** | **+0.03** |
| **−AutoIndex** | 自动索引 | C7 | **−0.06** | **+0.09** |
| **−IncrementalIndex** ⭐ | 增量索引 → 全量重建 | C13 | **−0.05** | **+0.05** |

**验收**: 至少 6 个组件的移除产生统计显著的性能下降 (p < 0.05 after Bonferroni)

---

### EXP-15 ⭐ 增量索引正确性（新实验）

**对应论文**: §6.12 Incremental Indexing Correctness
**假设 (H13)**: 增量索引 (ADO: Add-Document-Observe) 周期中，新文档可检索、旧文档不变、删除后不可检索。

#### 协议

```
Stage A: 基线快照
  → 对测试 KB 执行 10 条查询，记录 top-5 基线

Stage B: 增量添加
  → 分 3 轮每轮添加 3 篇文档并立即索引 (不重建全量索引)
  → 每轮后:
    B1. 验证新文档可检索 (kb_search_vector 命中)
    B2. 验证旧文档排名不变 (查询 10 条基线查询，top-5 顺序未改变)
    B3. 记录索引延迟 (ms per doc)

Stage C: 增量更新
  → 更新 2 篇文档内容
  → 验证: 旧 chunk 不可检索，新 chunk 可检索

Stage D: 增量删除
  → 删除 2 篇文档
  → 验证: 删除后搜索不再命中
  → 验证: BM25 索引和向量索引均清理

Stage E: 混合操作压力测试
  → 快速交替 add/update/delete x 3 轮
  → 验证: 每次操作后一致性检查通过
```

#### 预期结果表 (Table 13)

| 操作 | 检索一致性 | 延迟 (ms) | 备注 |
|------|:---------:|:---------:|------|
| Add 3 docs × 3 rounds | ✓ | — | 增量 add_document |
| Update 2 docs | ✓ | — | 旧chunk清理+新chunk索引 |
| Delete 2 docs | ✓ | — | ChromaDB + BM25 均清理 |
| Mixed stress (3 rounds) | ✓ | — | 无索引过期 |
| Full rebuild vs incremental diff | ≤5% | — | 结果等效性 |

**验收**: 所有 ADO 操作后检索一致性 100%，增量 rebuild 与全量 rebuild 结果差异 ≤5%

---

## 6. Layer 2 — 功能正确性 (EXP-5~6, EXP-11, EXP-17)

### EXP-5: 经验管道有效性

**对应论文**: §6.5 Experience Pipeline
**假设 (H4)**: 经验的增量使用使运维查询的文档数量减少 ≥50%。

#### 协议

```
Stage A: 种子经验创建
  A1. 对 6 个领域 KB，每 KB 创建 3 条种子经验 (18 条)
  A2. experience_create() → 入库 + 索引

Stage B: 自动经验提取 (E0-E1)
  B1. 对 D1 的 60 篇 arXiv 文档
  B2. experience_extract(kb_id, doc_path)
  B3. 评估自动提取质量:
    → 提取成功率
    → Problem 准确率 (5-point Likert)
    → Solution 完整性
    → Lessons 实用性

Stage C: 经验检索
  C1. 构造 30 条运维/故障查询 (D4: StackOverflow QA pairs)
  C2. 两条路径对比:
    Path-A (Doc-only): kb_search_two_stage(query)
    Path-B (Exp-first): experience_search_smart(query)
  C3. 记录: docs_read, time_to_answer, answer_quality

Stage D: 经验可信度分级验证 (E4)
  D1. 人工标注 20 条经验的"真实可信度等级"
  D2. 系统自动分级
  D3. 计算: Tier Accuracy, Cohen's κ

Stage E: 时效衰减 (E11)
  E1. 标记经验的不同时间跨度 (7d/30d/90d)
  E2. 运行衰减规则
  E3. 验证: 过期未用经验是否被正确降级
```

#### 预期结果表

| Metric | Doc-only | Exp-first | Reduction |
|--------|:--------:|:---------:|:---------:|
| Avg docs read | — | — | ≥50% |
| Avg time (s) | — | — | ≥40% |
| Avg answer quality | — | — | ≥0 |

| Metric | Value | Target |
|--------|:-----:|:------:|
| Auto-extraction recall | — | ≥60% |
| Problem accuracy (human) | — | ≥3.5/5 |
| Tier Accuracy | — | κ > 0.7 |

---

### EXP-6: 自动归档与知识组织准确性

**对应论文**: §6.4 Ablation 的 "−Archiving" 部分
**假设 (H5)**: 自动归档 A0-A9 的 Top-1 准确率 ≥80%。

#### 协议

```
Stage A: 归档准确性
  A1. 从 D1+D5 抽取 40 篇文档 (holdout)
  A2. 模拟 A3d 决策: 读正文 1500 chars → 匹配 kb descriptions → 预测归属
  A3. 计算: Top-1/Top-3 Accuracy, per-domain F1

Stage B: 标签生成质量
  B1. 检查自动生成的 tags
  B2. 人工评估: tag_relevance (1-5)

Stage C: 归档稳健性
  C1. 对抗性标题测试: 标题歧义文档
  C2. 验证基于内容（非文件名）分类

Stage D: 知识整理功能
  D1. 运行 organize → verify 流程
  D2. 验证: 三层一致性 (磁盘 ↔ .tree-fs.json ↔ .knowledge-base.yml)
```

#### 预期结果表 (Table 6)

| Metric | Value | Target |
|--------|:-----:|:------:|
| Top-1 classification accuracy | — | ≥80% |
| Top-3 classification accuracy | — | ≥95% |
| Tag quality score (human) | — | ≥3.5/5 |
| Adversarial title accuracy | — | ≥60% |
| 3-layer consistency | — | 100% |

---

### EXP-11: balance_kbs 多样性守卫评估

**对应论文**: §6.10 Search Diversity Analysis (Table 11)
**假设 (H8)**: 开启 balance_kbs 后，跨域查询的 KB 覆盖数显著高于关闭时。

#### 协议

```
Stage A: 大库霸权模拟
  → 20 条跨域查询，balance_kbs=false vs true
  → 记录 top-10 结果所属 KB 分布

Stage B: 多样性度量
  → Shannon entropy of KB distribution
  → unique KB count per query
  → 最大 KB 占比 (dominance ratio)

Stage C: 大库影响测试
  → 高分子库 (55.5% chunks) 在 top-k 中的占比
```

**验收**: balance_kbs=true 时 Shannon entropy 提升 ≥30%，大库最大占比降低 ≥40%

---

### EXP-17 ⭐ 标签管理生命周期评估（新实验）

**对应论文**: §6.13 Tag Lifecycle Management
**假设 (H15)**: 标签系统支持完整的生命周期管理：自动生成、去重、检索、孤儿清理。

#### 协议

```
Stage A: 标签生成评估
  A1. 对 D13 中 30 篇文档，检查自动生成标签
  A2. 人工标注 ground truth tags (每篇 3-5 个)
  A3. 计算: Tag Precision, Recall, F1, NDCG@k

Stage B: 标签去重验证
  B1. 对同一文档多次生成标签
  B2. 验证: 无重复标签（系统去重）
  B3. 验证: kb_tags_list 无重复条目

Stage C: 标签检索效果
  C1. 对 15 条以标签为意图的查询
  C2. kb_doc_get_by_tag(tag) vs kb_search_vector(query)
  C3. 比较: tag-based retrieval 是否比 vector search 更精确

Stage D: 孤儿标签清理
  D1. 删除带特定标签的文档
  D2. 运行 kb_tags_cleanup(dry_run=true)
  D3. 验证: 孤儿标签被检测到
  D4. 运行 kb_tags_cleanup(dry_run=false)
  D5. 验证: 孤儿标签已清除，活跃标签不受影响

Stage E: 标签迁移
  E1. kb_doc_move 将文档从 KB-A 移至 KB-B
  E2. 验证: 标签跟随迁移
  E3. 验证: 全局标签系统状态一致
```

#### 预期结果表 (Table 14)

| Metric | Value | Target |
|--------|:-----:|:------:|
| Tag Precision | — | ≥0.75 |
| Tag Recall | — | ≥0.60 |
| Tag F1 | — | ≥0.67 |
| Tag Dedup Rate | — | 100% |
| Tag Retrieval P@5 vs Vector | — | Δ ≥ +0.10 |
| Orphan Detection Rate | — | 100% |
| Orphan Cleanup Accuracy | — | 100% (活跃标签不受影响) |
| Tag Migration Consistency | — | 100% |

**验收**: Tag F1 ≥ 0.67，孤儿清理准确率 100%，标签迁移一致性 100%

---

## 7. Layer 3 — 系统完整性 (EXP-9~10, EXP-12, EXP-16, EXP-18)

### EXP-9: 五层数据一致性验证

**对应论文**: §6.8 Data Integrity Analysis (Table 9)
**假设 (H6)**: 文档删除后，向量索引 + 图谱索引正确清理；文档更新后，索引正确重建。

#### 协议

```
Stage A: 五层一致性检查点定义
  L1: 磁盘文件存在性
  L2: .tree-fs.json 中有记录
  L3: .knowledge-base.yml 中有记录
  L4: ChromaDB 中有对应 chunks
  L5: Neo4j 中有对应 Document 节点

Stage B: 一致性操作验证
  B1. 创建文档: kb_doc_create → 检查 L1-L5 全部命中 ✓
  B2. 自动索引: 确认 task_registry 触发索引 (L4, L5 自动写入)
  B3. 搜索命中: kb_search_vector → 新文档可检索
  B4. 更新内容: kb_doc_update_content → 检查一致性
  B5. 删除文档: kb_doc_delete → 检查 L1-L5 全部清除 ✗
  B6. 验证清理: kb_search_vector → 已删除文档不可检索
```

#### 预期结果表 (Table 9)

| 操作 | L1 磁盘 | L2 tree-fs | L3 YAML | L4 ChromaDB | L5 Neo4j | 一致性 |
|------|:-------:|:----------:|:-------:|:-----------:|:--------:|:------:|
| 创建+索引 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |
| 搜索命中 | — | — | — | ✓ | — | ✅ |
| 更新+重索引 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |
| 删除+清理 | ✗ | ✗ | ✗ | ✗ | ✗ | ✅ |
| 删除后搜索 | — | — | — | ✗ | — | ✅ |

**验收**: 所有 5 个操作后各层一致性 100%

---

### EXP-10: 图谱桥接文档评估

**对应论文**: §6.9 Knowledge Graph Bridge Analysis (Table 10)
**假设 (H7)**: 图谱桥接文档 (min_kbs≥2) 的内容相关性显著高于随机基线。

#### 协议

```
Stage A: 桥接文档发现
  → kb_graph_cross_kb_documents(min_kbs=2, top_k=50)
  → 记录: 50 个桥接文档及其连接 KB 数

Stage B: 桥接文档内容验证
  → 人工评分: relevance (1-5)

Stage C: 桥接文档检索价值
  → 20 条跨域查询: 有/无图谱桥接
  → 比较: 桥接文档作为正确答案被检索到的比例

Stage D: 桥接 vs 随机基线
  → 随机选择 50 个非桥接文档
  → 比较: 桥接文档平均分 vs 随机文档平均分
```

**验收**: 桥接文档内容相关性 ≥ 3.5/5 且显著高于随机基线 (p < 0.05)

---

### EXP-12: 递归层级结构验证

**对应论文**: §6.11 Hierarchical KB Model (Table 12)
**假设 (H9)**: 递归计数的 KB catalog 正确反映所有子 KB 的文档总和。

#### 协议

```
Stage A: 递归计数验证
  → 检查 高分子双向拉伸文献库 (12 子KB):
    → 计算: 每个子 KB 的 .md 文件数
    → 验证: 总和 = catalog 的 documentCount
  → 检查 Nested KBs 计数修复

Stage B: 计数修复前后对比
  → 恢复旧代码 (直接子级计数) → 记录错误计数
  → 应用修复 (递归计数) → 记录正确计数
```

#### 预期结果表 (Table 12)

| KB | 子KB数 | 修复前计数 | 修复后计数 | 真实文件数 | 错误率 |
|----|:------:|:----------:|:----------:|:----------:|:------:|
| 高分子双向拉伸文献库 | 12 | **0** | **73** | 73 | 修复前 100% |
| AI-ML-Research | 1 | 8 | **17** | 17 | 修复前 53% |
| 扁平 KB | 0 | N | N | N | 无影响 |

**验收**: 修复后所有 KB 的 catalog 计数 = 真实文件数 (100%)

---

### EXP-16 ⭐ 跨语言检索能力评估（新实验）

**对应论文**: §6.14 Cross-Lingual Retrieval
**假设 (H14)**: 系统在中文查询上的检索精度不低于英文查询的 85%。

#### 协议

```
Stage A: 中文查询集构造 (D11)
  → 30 条中文查询，覆盖 6 个领域
  → 从 D1 英文文档生成对应中文查询 (通过翻译+人工校对确保自然性)
  → Ground truth: 与英文版本共享（同一源文档 = 正例）

Stage B: 检索对比
  → 对每条中文查询:
    B1. kb_search_vector(q_zh, kb_id="", top_k=5)
    B2. kb_search_vector(q_zh, kb_id=selected, top_k=5)
  → 对比: 同查询的英文版本 vs 中文版本
  → 指标: ΔP@5(zh vs en)

Stage C: 混合语言查询
  → 10 条中英混合查询 (如 "transformer architecture 注意力机制详解")
  → 对比纯中文/纯英文的检索效果

Stage D: 中文文档入库
  → 入库 10 篇中文技术文档 (D5 子集)
  → 验证: 中文查询→中文文档匹配准确性
  → 验证: jieba 分词对中文查询的贡献 (消融: 关闭 jieba 用纯字符 n-gram)
```

#### 预期结果表 (Table 15)

| Query Language | P@5 | nDCG@5 | MRR | Latency (ms) |
|---------------|:---:|:------:|:---:|:------------:|
| English (baseline) | — | — | — | — |
| Chinese (D11) | — | — | — | — |
| Mixed EN+ZH | — | — | — | — |
| *Δ Chinese vs English* | *≥−15%* | *≥−15%* | — | — |

**验收**: P@5(zh) ≥ 85% × P@5(en)，中英混合不显著低于单语言

---

### EXP-18 ⭐ 系统扩展性测试（新实验）

**对应论文**: §6.15 Scalability Analysis
**假设 (H16)**: 系统吞吐和延迟可在 10× 数据量范围内线性扩展。

#### 协议

```
Stage A: 规模梯度构造 (D12)
  → 1×: 60 docs (D1)
  → 3×: 180 docs (D1 + 扩展)
  → 5×: 300 docs
  → 10×: 600 docs
  → 每个规模保持相同的 KB 数量/领域分布

Stage B: 吞吐量测试
  → 每个规模下:
    B1. 并发 10/20/50 查询的 QPS (queries per second)
    B2. 单查询延迟分布 (P50, P95, P99)
    B3. 索引时间 (per doc, per batch)
  
Stage C: 资源使用
  → CPU/内存/磁盘 I/O 随规模增长
  → ChromaDB 持久化大小
  → Neo4j 图谱大小

Stage D: 检索质量保持
  → 验证 P@5 在 10× 规模下不下降 (领域内检索)
  → 验证 FPR 在 10× 规模下仍然 ≤ 0.10
```

#### 预期结果表 (Table 16)

| Scale | Docs | QPS@10 | P50 Lat | P99 Lat | P@5 | FPR | Index Time/doc |
|:-----:|:----:|:------:|:-------:|:-------:|:---:|:---:|:-------------:|
| 1× | 60 | — | — | — | baseline | baseline | — |
| 3× | 180 | — | — | — | Δ ≤ −0.02 | Δ ≤ +0.02 | — |
| 5× | 300 | — | — | — | Δ ≤ −0.03 | Δ ≤ +0.03 | — |
| 10× | 600 | — | — | — | Δ ≤ −0.05 | Δ ≤ +0.05 | — |

**验收**: 10× 规模下 P@5 下降 ≤ 5%，P99 延迟 ≤ 3× baseline

---

## 8. Layer 0 — 数据基础层 (EXP-13~14) ⭐ NEW

### EXP-13 ⭐ 冥想自动归纳质量评估（新实验）

**对应论文**: §6.16 Experience Meditation Auto-Induction
**假设 (H11)**: 冥想自动归纳管线的最终可审批率 ≥ 60%，信号精度 ≥ 0.70。

#### 协议

```
Stage A: 冥想组件评估概览
  冥想管线包含 6 个可验证阶段:
  S1: Question Harvester — 从 chat DB 提取→过滤→聚类用户问题
  S2: Signal Harvester — 从 MCP tool calls 捕获真实 KB Q&A 信号
  S3: KB Matcher — 关键词匹配 cluster → KB
  S4: Vector Search — 在目标 KB 中搜索相关文档
  S5: Duplicate Check — 检查是否已有类似经验
  S6: Draft Creation — LLM 合成经验草稿

Stage B: S1 问题收获器评估
  B1. 从 D10 (100+ 条真实用户对话) 运行 harvest_questions
  B2. 评估:
    → Noise Rejection Rate: 被过滤的系统消息/问候语比例
    → Intent Detection Accuracy: 标注 50 条消息的意图 (信息/操作/闲聊)
    → Cluster Quality: 人工评估 10 个 cluster 的同质性 (1-5)
    → Cluster Coverage: 被聚类的问题比例

Stage C: S2 信号收获器评估
  C1. 从 D10 提取 MCP tool call traces (kb_search_vector, kb_doc_read)
  C2. 运行 harvest_signals_to_db
  C3. 评估:
    → Signal Precision: 有效 KB Q&A 信号 / 所有捕获信号
    → Signal Recall: 捕获的信号 / 所有真实信号 (人工标注 30 条)
    → Dedup Rate: 去重比例

Stage D: S3 KB 匹配器评估
  D1. 对 20 个聚类，运行 _match_kb
  D2. 评估:
    → KB Match Top-1 Accuracy (人工标注正确答案)
    → KB Match Top-3 Accuracy

Stage E: S4-S6 综合产出评估
  E1. 运行完整 meditation_run(kb_id)
  E2. 对生成的草稿:
    → Draft Quality Score (人工 3 人评分, 1-5 scale):
      - 是否抓住了真实用户问题? (accuracy)
      - 解决方案是否来自真实文档? (grounding)
      - 经验是否可操作? (actionability)
      - 格式是否符合 E2 质量标准? (completeness)
    → Draft Approval Rate: 可直接审批通过的比例 (E3 stage)
  E3. 对比: 冥想自动生成 vs 人工编写 (相同问题, 人工编写对照组)

Stage F: 调度器正确性
  F1. 配置: interval=1min, lookback=1d, dry_run=true
  F2. 验证: 调度器按间隔执行 (记录 5 次运行时间戳, 计算间隔方差)
  F3. 验证: 增量触发 (添加 3 个新信号后, _check_incremental_trigger 触发)
  F4. 验证: dry_run 模式不创建草稿
```

#### 预期结果表 (Table 17)

**Table 17a: Harvester Quality**

| Metric | Value | Target |
|--------|:-----:|:------:|
| Noise Rejection Rate | — | ≥80% |
| Intent Detection Accuracy | — | ≥75% |
| Cluster Homogeneity (human) | — | ≥3.5/5 |
| Cluster Coverage | — | ≥70% |

**Table 17b: Signal Quality**

| Metric | Value | Target |
|--------|:-----:|:------:|
| Signal Precision | — | ≥0.70 |
| Signal Recall | — | ≥0.50 |
| Dedup Rate | — | ≥80% |

**Table 17c: End-to-End Meditation Quality**

| Metric | Value | Target |
|--------|:-----:|:------:|
| Draft Quality Score (avg 3 raters) | — | ≥3.5/5 |
| Draft Approval Rate | — | ≥60% |
| KB Match Top-1 Accuracy | — | ≥70% |
| KB Match Top-3 Accuracy | — | ≥90% |
| Scheduler Interval Variance | — | ≤10% |

**验收**: Draft Approval Rate ≥ 60%，Signal Precision ≥ 0.70，Scheduler 间隔方差 ≤ 10%

---

### EXP-14 ⭐ 多格式解析质量评测（新实验）

**对应论文**: §6.17 Multi-Format Parse Quality
**假设 (H12)**: MinerU 在多格式文档上的解析 Markdown 保真度 ≥ 85%，表格准确率 ≥ 80%。

#### 协议

```
Stage A: 多格式语料构造 (D9)
  → PDF (15 篇): 包含公式、表格、图表的科学论文
  → Word/.docx (10 篇): 结构化技术报告
  → Excel/.xlsx (8 篇): 数据表格 + 多 sheet
  → Image/.png/.jpg (7 篇): 扫描文档需 OCR

Stage B: 格式维度评估
  B1. PDF 解析:
    → Markdown Fidelity Score: 人工标注 source PDF 的关键段落
    → 公式准确率: 随机抽取 30 个公式, 人工判断 LaTeX 是否正确
    → 表格准确率: 随机抽取 20 个表格, 检查行列数+单元内容

  B2. Word 解析:
    → 段落结构保持: 标题层级、列表、加粗/斜体
    → 图片提取: 是否成功提取嵌入图片

  B3. Excel 解析:
    → Sheet 完整性: 所有 sheet 均被解析
    → 表格行列正确性: 与原始文件对比
    → 空值处理: 不丢失也不添加

  B4. Image+OCR 解析:
    → OCR 字符准确率 (CER): 与 ground truth 文本对比
    → 拉丁字母 + 中文混合字符识别

Stage C: 解析流水线可靠性
  C1. 100 次连续解析的成功率
  C2. 解析失败类型分类 (超时/OOM/格式不支持/编码错误)
  C3. 解析吞吐: docs/hour (GPU) vs docs/hour (CPU)

Stage D: 解析对比基线
  D1. 同一组 15 篇 PDF:
    → P1: Unstructured.io (latest)
    → P2: LlamaParse (Cloud API)
    → MinerU (ours)
  D2. 相同 ground truth, 相同评估标准
```

#### 预期结果表 (Table 18)

**Table 18a: Format-Specific Quality**

| Format | MD Fidelity | Table Acc | Formula Acc | Image Extract |
|--------|:----------:|:---------:|:----------:|:------------:|
| PDF (scientific) | ≥85% | ≥80% | ≥80% | ≥90% |
| Word (.docx) | ≥90% | ≥85% | — | ≥90% |
| Excel (.xlsx) | — | ≥95% | — | — |
| Image (OCR) | ≥75% | — | — | — |

**Table 18b: Pipeline Reliability**

| Metric | Value | Target |
|--------|:-----:|:------:|
| Parse success rate (100 runs) | — | ≥95% |
| Avg parse time (PDF, GPU) | — | ≤30s/doc |
| OCR CER (mixed Latin+CJK) | — | ≤5% |

**Table 18c: Parse Baseline Comparison (15 PDFs)**

| Method | MD Fidelity | Table Acc | Formula Acc |
|--------|:----------:|:---------:|:----------:|
| Unstructured.io | — | — | — |
| LlamaParse | — | — | — |
| **MinerU (ours)** | — | — | — |

**验收**: PDF Markdown Fidelity ≥ 85%，Table Accuracy ≥ 80%，Parse success rate ≥ 95%

---

## 9. 综合评分与论文产出物映射

### 9.1 加权综合评分（v6.0 — 11 维）

$$
\text{CS} = 0.20 \cdot \text{Retrieval} + 0.12 \cdot \text{Efficiency} + 0.15 \cdot \text{Robustness} + 0.10 \cdot \text{DocMgmt} + 0.08 \cdot \text{Experience} + 0.06 \cdot \text{Agent} + 0.06 \cdot \text{Consistency} + 0.05 \cdot \text{Diversity} + 0.05 \cdot \text{Reliability} + 0.07 \cdot \text{ParseQuality} + 0.06 \cdot \text{Meditation}
$$

### 9.2 论文产出物映射表（v6.0 — 18 表 12 图）

| 论文元素 | 来源实验 | 类型 |
|---------|:--------:|------|
| **Figure 1**: 跨域污染实证 | EXP-0 | 散点图 |
| **Figure 2**: QDCVR 管线总览 | 架构 | 流程图 |
| **Figure 3**: Content-vs-Vector 散点图 | EXP-4 | 散点图 |
| **Figure 4**: FPR 对比柱状图 | EXP-2 | 柱状图 |
| **Figure 5**: 消融瀑布图 | EXP-8 | 瀑布图 |
| **Figure 6**: 延迟分解饼图 | EXP-7 | 饼图 |
| **Figure 7**: 雷达图 (多维度对比) | EXP-3,7 | 雷达图 |
| **Figure 8**: 五层一致性验证图 | EXP-9 | 层次图 |
| **Figure 9**: 图谱桥接文档网络图 | EXP-10 | 网络图 |
| **Figure 10**: 冥想管线流程图 | EXP-13 ⭐ | 流程图 |
| **Figure 11**: 解析质量对比图 | EXP-14 ⭐ | 分组柱状图 |
| **Figure 12**: 扩展性曲线 | EXP-18 ⭐ | 折线图 |
| **Table 1**: 检索精度主结果 | EXP-1 | LaTeX |
| **Table 2**: 跨域 FPR 消除 | EXP-2 | LaTeX |
| **Table 3**: 多基线全面对比 | EXP-3 | LaTeX |
| **Table 4**: Content-vs-Vector | EXP-4 | LaTeX |
| **Table 5**: 经验管道效果 | EXP-5 | LaTeX |
| **Table 6**: 系统功能矩阵 | EXP-6 | LaTeX |
| **Table 7**: 效率延迟分析 | EXP-7 | LaTeX |
| **Table 8**: 消融矩阵 (10 组件) | EXP-8 | LaTeX |
| **Table 9**: 五层一致性验证 | EXP-9 | LaTeX |
| **Table 10**: 图谱桥接文档评估 | EXP-10 | LaTeX |
| **Table 11**: balance_kbs 多样性分析 | EXP-11 | LaTeX |
| **Table 12**: 递归层级计数验证 | EXP-12 | LaTeX |
| **Table 13**: 增量索引正确性 | EXP-15 ⭐ | LaTeX |
| **Table 14**: 标签生命周期 | EXP-17 ⭐ | LaTeX |
| **Table 15**: 跨语言检索 | EXP-16 ⭐ | LaTeX |
| **Table 16**: 系统扩展性 | EXP-18 ⭐ | LaTeX |
| **Table 17**: 冥想归纳质量 | EXP-13 ⭐ | LaTeX |
| **Table 18**: 多格式解析质量 | EXP-14 ⭐ | LaTeX |

---

## 10. 统计协议

### 10.1 必须满足的 CIKM 统计标准

| 要求 | 实现 | 阈值 |
|------|------|:----:|
| **假设检验** | 配对 t 检验 (paired, two-tailed) 或 Wilcoxon signed-rank (非正态时) | p < 0.05 |
| **多重比较校正** | Bonferroni correction (m = hyp 数量) | α/m |
| **效应量** | Cohen's d (≥0.5 = 中等, ≥0.8 = 大) | 报告 |
| **置信区间** | Bootstrap 95% CI (n_boot = 10,000) | 报告 |
| **标注一致性** | Cohen's κ (≥0.7 = substantial agreement) | κ > 0.7 |
| **解析质量 IAA** | Krippendorff's α for 3 raters | α > 0.7 |
| **样本量** | 每实验 ≥ 50 查询 (检索类) 或 ≥ 10 文档 (解析类) | 统计 power ≥ 0.8 |
| **随机种子** | seed = 42 (所有随机操作) | 固定 |

### 10.2 报告格式

```
Method A vs Method B:
  P@5: X.XX ± X.XX vs Y.YY ± Y.YY
  Δ = +Z.ZZ, 95% CI [L, U], p = 0.00X**, d = 0.XX
  (* p<0.05, ** p<0.01, *** p<0.001, † not significant)
```

### 10.3 必须进行的统计检验（v6.0 扩展）

| 检验对 | 指标 | 实验 |
|--------|------|:----:|
| QDCVR vs B4 (CRAG) | P@5, nDCG@5 | EXP-3 |
| QDCVR vs B1 (Flat vector) | FPR | EXP-2 |
| QDCVR-full vs −ContentVerify | P@5 | EXP-8 |
| QDCVR-full vs −Archiving | P@5 | EXP-8 |
| QDCVR-full vs −AutoIndex | P@5 | EXP-8 |
| QDCVR-full vs −IncrementalIndex | P@5, Consistency | EXP-8 |
| Doc-only vs Exp-first | docs_read | EXP-5 |
| Bridge docs vs Random | relevance | EXP-10 |
| balance=true vs balance=false | Shannon entropy | EXP-11 |
| Chinese vs English | P@5 | EXP-16 |
| MinerU vs LlamaParse | MD Fidelity | EXP-14 |
| Meditation draft vs Manual draft | Quality Score | EXP-13 |
| Tag Retrieval vs Vector Search | P@5 | EXP-17 |
| 1× vs 10× scale | P@5, QPS | EXP-18 |

---

## 11. 审稿人预判防御矩阵（v6.0 增强）

| 审稿人质疑 | 防御策略 | 依赖实验 |
|-----------|---------|:--------:|
| "CRAG 已经做了检索验证" | 我们证明**前置领域组织**使后验证成本从 ~60 文档降到 ~5 文档。且 content-overrides-vector 是 CRAG 没有的明确可解释原则。 | EXP-1,3,4 |
| "你就分了个文件夹" | 自动归档基于内容（A3d 决策树），不是文件名。EXP-6 测了归档准确率 + 对抗性标题测试。 | EXP-2,6 |
| "你的 ground truth 自己标的" | D1: 源文档即正例（客观）。D2/D3: 使用 BEIR/MSMARCO 官方 qrels。自建集: 双盲标注 + κ>0.7。 | 全部 |
| "延迟太高" | 量化延迟分解（EXP-7）。证明 57% 在内容验证上，但精度提升值得。 | EXP-7 |
| "经验是你自己编的" | 种子经验是构造的（声明），但自动提取的来自真实 arXiv 论文。经验分级有人工标注+κ 验证。 | EXP-5 |
| "你的层级结构只是嵌套文件夹" | EXP-12 证明递归计数修复正确反映嵌套 KB，且层级结构带来跨域 FPR 降低 87% 的实际增益。 | EXP-2,12 |
| "你的数据一致性只是口号" | EXP-9 五层一致性验证：每个操作后各层正确性 100% 可验证。 | EXP-8,9 |
| **"你的解析质量怎么样？检索好是因为解析好？"** ⭐ | EXP-14 多格式评测 + 解析基线对比，消融掉解析质量对检索的贡献。 | EXP-14,8 |
| **"冥想自动归纳是噱头"** ⭐ | EXP-13 量化每个阶段的精度 (S1-S6)，End-to-end approval rate ≥60%。 | EXP-13 |
| **"增量索引会不会导致不一致"** ⭐ | EXP-15 ADO 周期验证: add→搜索→update→搜索→delete→搜索，每步验证一致性。 | EXP-15 |
| **"中文能检索吗"** ⭐ | EXP-16 跨语言对比: P@5(zh) ≥ 85% × P@5(en) | EXP-16 |
| **"标签管理系统有用吗"** ⭐ | EXP-17 Tag F1 ≥ 0.67, 孤儿清理 100%, 标签检索优于向量检索 | EXP-17 |
| **"大规模能用吗"** ⭐ | EXP-18 10× 扩展性: P@5 ≤5% 下降, P99 ≤3× baseline | EXP-18 |
| **"你用的是什么嵌入模型"** ⭐ | 全实验统一 BGE-M3, 1024-d，公开模型名和版本。 | 全部 |
| **"你的 baseline 是自己实现的，是否公平"** ⭐ | 所有基线用同一语料+同一模型+同一 top-k。CRAG/Self-RAG 实现细节在附录公开。 | EXP-3 |

---

## 12. 执行路线图与资源评估

### Phase 1: 环境与数据集准备 (Day 1-4)
- [ ] 记录系统状态基线 (EXP-0)
- [ ] 下载 arXiv 60 篇 PDF → `benchmark/datasets/arxiv-6d/`
- [ ] 下载 MS MARCO dev + BEIR → `benchmark/datasets/msmarco/`, `beir/`
- [ ] 收集 StackOverflow QA 50 条 + TechDocs 30 篇
- [ ] 构造对抗查询集 15 条
- [ ] 构造多格式语料 (D9): PDF 15 + Word 10 + Excel 8 + Image 7 ⭐
- [ ] 构造中文查询集 (D11): 30 条 ⭐
- [ ] 构造标签 benchmark (D13): 30 篇 ⭐
- [ ] 导出 chat session DB (D10): 100+ 对话 ⭐

### Phase 2: D1 文档入库 (Day 5)
- [ ] 创建 6 个领域 KB
- [ ] 上传 → parse → ingest → index 60 篇 arXiv papers
- [ ] 验证索引完整性 + 解析快照

### Phase 3: Layer 0 — 数据基础层 (Day 6-7) ⭐
- [ ] EXP-14: 多格式解析质量评测
  - D9 全部文件解析 → 记录 markdown fidelity
  - 与 Unstructured.io + LlamaParse 对比
- [ ] EXP-13: 冥想管道质量评测
  - 收获器评估 → 信号评估 → 综合产出评估

### Phase 4: Layer 1 — 检索实验 (Day 8-11)
- [ ] EXP-1: 检索精度主实验
- [ ] EXP-2: 跨域 FPR 消除
- [ ] EXP-3: 多基线全面对比
- [ ] EXP-4: Content-Overrides-Vector 实证
- [ ] EXP-15: 增量索引正确性

### Phase 5: Layer 2 — 功能实验 (Day 12-14)
- [ ] EXP-5: 经验管道有效性
- [ ] EXP-6: 自动归档准确性
- [ ] EXP-11: balance_kbs 多样性
- [ ] EXP-17: 标签管理生命周期

### Phase 6: Layer 3 — 系统实验 (Day 15-17)
- [ ] EXP-7: 效率延迟分析
- [ ] EXP-8: 消融实验 (10 组件)
- [ ] EXP-9: 五层一致性验证
- [ ] EXP-10: 图谱桥接文档
- [ ] EXP-12: 递归层级验证
- [ ] EXP-16: 跨语言检索
- [ ] EXP-18: 扩展性测试

### Phase 7: 系统级对比 (Day 18-19)
- [ ] 安装 RAGFlow / Dify / LightRAG
- [ ] 导入同文档集 + 执行查询 + 功能对比

### Phase 8: 汇总与产出 (Day 20-22)
- [ ] 计算 Composite Score
- [ ] 生成所有 JSON + LaTeX tables + Figures
- [ ] 生成 HTML 看板
- [ ] 撰写统计分析报告
- [ ] 撰写错误分析

### 资源评估

| 资源 | 需求 | 备注 |
|------|------|------|
| GPU | 1× (T4/A10 即可) | MinerU 解析 + BGE-M3 嵌入 |
| CPU | 8 核 | 后台服务 + 并发检索 |
| 内存 | 32GB | ChromaDB + Neo4j + 多进程 |
| 存储 | 50GB | 数据集 + 索引 + 结果 |
| 人工标注工时 | ~40 小时 | D7 构造 + 解析质量 + 经验质量 + 标签 |
| LLM API 调用 | ~500 次 | 经验合成 + Self-RAG 评估器 |
| 总执行时间 | ~22 天 | 含数据准备和人工标注 |

---

## 13. 结果输出规范

### 13.1 目录结构（v6.0 扩展）

```
benchmark/
├── SYSTEM-BENCHMARK-PLAN.md           ← 本文件 (权威定稿 v6.0)
├── datasets/
│   ├── arxiv-6d/                      ← D1: 60 PDFs
│   ├── msmarco/                       ← D2: MS MARCO
│   ├── beir/                          ← D3: BEIR subsets
│   ├── stackoverflow/                 ← D4: SO QA pairs
│   ├── techdocs/                      ← D5: mixed tech docs
│   ├── multi-format/                  ← D9 ⭐: PDF/Word/Excel/Image
│   ├── chinese-queries.json           ← D11 ⭐: 30 Chinese queries
│   ├── scalability-corpus/            ← D12 ⭐: 600 docs
│   ├── tag-benchmark/                 ← D13 ⭐: 30 tagged docs
│   ├── adversarial-queries.json       ← 15 adversarial queries
│   ├── bridge-docs.json               ← Neo4j 桥接文档
│   ├── chat-sessions.db               ← D10 ⭐: Chat DB export
│   └── queries-full.json              ← 全部查询集
├── qrels/
│   ├── qrels-arxiv.jsonl
│   ├── qrels-msmarco.jsonl
│   ├── qrels-beir.jsonl
│   └── qrels-chinese.jsonl            ⭐
├── results/
│   ├── EXP-0-system-baseline.json
│   ├── EXP-1~12-results.json
│   ├── EXP-13-meditation-quality.json   ⭐
│   ├── EXP-14-parse-quality.json        ⭐
│   ├── EXP-15-incremental-indexing.json ⭐
│   ├── EXP-16-cross-lingual.json        ⭐
│   ├── EXP-17-tag-lifecycle.json        ⭐
│   ├── EXP-18-scalability.json          ⭐
│   ├── composite-scores.json
│   ├── summary.json
│   ├── statistical-tests.json
│   └── error-analysis.md
├── figures/
│   ├── fig1~fig12.png                  ← 12 figures
│   └── ...
├── paper-tables/
│   ├── table1~table18.tex              ← 18 tables
│   └── ...
├── html/
│   ├── index.html
│   └── data/all_results.json
└── README.md
```

### 13.2 综合评分 JSON 格式（v6.0 扩展）

```json
{
  "timestamp": "2026-07-29T00:00:00Z",
  "system": "QDCVR Knowledge Platform v2.3.0",
  "plan_version": "v6.0",
  "composite_score": 0.XXX,
  "dimensions": {
    "Retrieval": {"score": 0.XXX, "weight": 0.20},
    "Efficiency": {"score": 0.XXX, "weight": 0.12},
    "Robustness": {"score": 0.XXX, "weight": 0.15},
    "DocMgmt": {"score": 0.XXX, "weight": 0.10},
    "Experience": {"score": 0.XXX, "weight": 0.08},
    "Agent": {"score": 0.XXX, "weight": 0.06},
    "Consistency": {"score": 0.XXX, "weight": 0.06},
    "Diversity": {"score": 0.XXX, "weight": 0.05},
    "Reliability": {"score": 0.XXX, "weight": 0.05},
    "ParseQuality": {"score": 0.XXX, "weight": 0.07},
    "Meditation": {"score": 0.XXX, "weight": 0.06}
  },
  "key_results": {
    "p5_improvement_vs_best_baseline": "+X.XX",
    "fpr_reduction_vs_flat": "−XX%",
    "search_space_reduction": "×1,142",
    "archiving_top1_accuracy": "XX%",
    "experience_docs_reduction": "−XX%",
    "content_verification_ablation_delta_p5": "−0.15",
    "auto_index_ablation_delta_p5": "−0.06",
    "parse_md_fidelity_pdf": "≥85%",
    "meditation_approval_rate": "≥60%",
    "incremental_indexing_consistency": "100%",
    "cross_lingual_p5_ratio_zh_vs_en": "≥85%",
    "tag_f1_score": "≥0.67",
    "scalability_p5_drop_at_10x": "≤5%"
  }
}
```

---

## 14. 变更日志

### v5.0 → v6.0 主要变更

| 变更项 | 原 v5.0 | 新 v6.0 | 原因 |
|--------|--------|--------|------|
| 实验总数 | 13 (EXP-0~12) | **18 (EXP-0~18)** | 覆盖全部系统能力 |
| 评测金字塔 | 3 层 | **4 层 (+Layer 0 数据基础层)** | 解析质量是整个系统的前提 |
| Claims | 10 | **16** | 新增 C11-C16 |
| 数据集 | 8 个 | **13 个** | 新增 D9-D13 |
| 基线系统 | 10 个 | **12 个 (+B8, +P1, +P2)** | QDCVR 扁平对照 + 解析基线 |
| 新增 EXP-13 ⭐ | — | **冥想自动归纳质量** | 独特差异化功能 |
| 新增 EXP-14 ⭐ | — | **多格式解析质量** | 入库管线可靠性基础 |
| 新增 EXP-15 ⭐ | — | **增量索引正确性** | 长期运行数据安全 |
| 新增 EXP-16 ⭐ | — | **跨语言检索能力** | 中英混合场景覆盖 |
| 新增 EXP-17 ⭐ | — | **标签管理生命周期** | 标签系统完整性 |
| 新增 EXP-18 ⭐ | — | **系统扩展性测试** | 大规模部署可行性 |
| 消融组件 | 10 | **11** (+IncrementalIndex) | 增量索引消融 |
| 综合评分维度 | 9 | **11** (+ParseQuality, +Meditation) | 新维度覆盖 |
| 产出物 | 11表9图 | **18表12图** | 新增实验产出 |
| 统计检验 | 10 对 | **14 对** | 新增假设检验 |
| 防御矩阵 | 11 条 | **16 条** | 新增审稿人质疑预判 |
| 执行时间 | 17 天 | **22 天** | 新增 5 天实验 |
| 人工标注 | ~20h | **~40h** | 新增标注需求 |

---

> **本文件是 QDCVR 评测的权威定稿 (v6.0 Final)。所有实验执行、结果记录、论文写作均以此为准。**
> **执行时严格遵循：公开协议 → 预注册假设 → 执行 → 记录 → 不做 p-hacking。**
> **v6.0 新增 6 个实验覆盖了从数据基础层 (Layer 0) 到系统扩展性的全部能力维度，确保 CIKM 审稿人无法以"未覆盖关键功能"为由拒绝。**
