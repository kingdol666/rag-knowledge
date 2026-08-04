# 论文写作框架（CIKM Full Paper 格式）

> **目标会议**: CIKM 2027 Full Research Paper (备选: SIGIR 2027 AP Track / KBS 期刊)
> **格式**: ACM `sigconf` 双栏 · 10pt Times Roman · 正文 ≤ 10页 · 参考文献不计
> **最后更新**: 2026-07-24

---

## 📋 论文元数据

### 推荐标题（三选一）

| # | 标题 | 风格 |
|---|------|------|
| **1 ⭐** | **QDCVR: Query-Driven Content-Verified Retrieval for Agentic Knowledge Bases** | 方法名 + 场景，最学术 |
| 2 | Beyond Vector Similarity: Content-Verified Retrieval for Trustworthy RAG | 问题导向，吸引眼球 |
| 3 | An Agentic Knowledge Base Platform with Content-Verified Retrieval and Experience Lifecycle | 全系统叙事 |

### 作者信息
```
[Author Name(s)]
[Affiliation]
[email]
```

### CCS Concepts（ACM 分类）
```
- Information systems → Information retrieval → Retrieval tasks and goals → Question answering
- Information systems → Information retrieval → Specialized information retrieval → ...
- Computing methodologies → Artificial intelligence → Natural language processing → Information extraction
- Human-centered computing → Collaborative and social computing → ...
```

### Keywords (5-8个)
```
Retrieval-Augmented Generation; Content Verification; Knowledge Management;
Agent Systems; Model Context Protocol; Experience Lifecycle; Semantic Search
```

---

## 📝 Abstract（150-200词）

### 草稿

> Retrieval-Augmented Generation (RAG) systems increasingly rely on dense vector
> similarity for document retrieval, yet high cosine similarity does not guarantee
> content relevance—a fundamental limitation that introduces false positives
> and erodes user trust. We present **QDCVR** (Query-Driven Content-Verified
> Retrieval), a multi-stage retrieval methodology that decouples *recall*
> (vector + BM25 fusion) from *relevance judgment* (independent content scoring).
> QDCVR introduces three key innovations: (1) a **0–8 content verification
> scoring rubric** that reads candidate documents and independently judges
> relevance, applying the principle *"content score overrides vector score"*;
> (2) an **adaptive query understanding layer** that classifies query intent
> (factual, procedural, troubleshooting, comparative) and adjusts thresholds
> accordingly; and (3) a **P0/P1/P2 credibility tier model** for an integrated
> *experience library* that manages structured operational knowledge through a
> 13-stage lifecycle (E0–E12) with temporal decay. We implement QDCVR within
> an agentic knowledge base platform exposing 76 Model Context Protocol (MCP)
> tools and 14 agent skills. Evaluation on [N] queries across [M] knowledge
> bases demonstrates that QDCVR achieves [X]% precision@5 and [Y]% reduction
> in false-positive retrieval compared to vector-only baselines, while the
> experience credibility model achieves [Z]% accuracy in tier assignment.
> The system is open-source and deployed in production across [domain] domains.

### Abstract 写作要点

| 要素 | 对应内容 | 字数分配 |
|------|---------|---------|
| **问题** | 向量相似 ≠ 内容相关 | ~30词 |
| **方法** | QDCVR 三大创新 | ~70词 |
| **系统** | 91 MCP + 17 skills 的平台 | ~30词 |
| **结果** | 精度提升 + 误召回下降的数字 | ~40词 |
| **意义** | 开源 + 实际部署 | ~20词 |

---

## 📑 正文结构（10页分配）

```
┌─────────────────────────────────────────────┐
│  Section 1: Introduction          ~1.5 page  │
│  Section 2: Related Work           ~1.0 page  │
│  Section 3: Problem & Background   ~0.8 page  │
│  Section 4: QDCVR Methodology      ~2.5 pages │ ← 核心
│  Section 5: Experience Lifecycle   ~1.2 pages │ ← 核心
│  Section 6: System Implementation  ~0.8 page  │
│  Section 7: Evaluation             ~2.0 pages │
│  Section 8: Discussion & Threats   ~0.5 page  │
│  Section 9: Conclusion             ~0.3 page  │
│  References                        不计页数    │
└─────────────────────────────────────────────┘
```

---

## Section 1 — Introduction（~1.5页）

### 1.1 开篇：问题陈述

**Para 1 — 场景与重要性**（~4句）

RAG 系统已成为 LLM 获取外部知识的主流方案。然而，现有 RAG 管线几乎全部依赖稠密向量检索（dense retrieval）作为文档召回的核心机制。虽然向量相似度能高效捕获语义近邻，但它**无法保证召回的文档真正包含回答用户查询所需的内容**。

**Para 2 — 具体问题**（~5句）

我们观察到三个系统性问题：
1. **向量误召回 (Vector False Positive)** — 向量 cos 相似度 0.9 的文档可能内容完全答非所问。例如查"PET薄膜双向拉伸"返回了"PP材料"文献（二者共享"聚合物薄膜"语义空间）。
2. **跨库噪声 (Cross-KB Noise)** — 多知识库场景下大库（文档多的库）主导检索结果，淹没小库的相关文档。
3. **可信度缺失 (Trust Gap)** — 缺乏分级信任机制：哪些检索结果可以直接引用，哪些需要人工核实。

**Para 3 — 现有方案的不足**（~3句）

现有方案要么依赖后处理的 reranker（如 Cross-Encoder），成本高且不可解释；要么用 LLM 做 final answer check（如 FLARE），延迟大且不透明。缺乏一种**在检索阶段就完成内容级验证**的轻量、可解释方法。

**Para 4 — 我们的方案**（~4句）

本文提出 QDCVR，核心原则：**"Vectors are fast. Content is accurate."**（向量快召回，内容真裁决）。QDCVR 将检索分为召回阶段（向量+BM25）和裁决阶段（独立内容评分），以 0–8 分制直接读取候选文档正文进行验证，内容分 < 阈值的文档被丢弃，即使向量分再高。

**Para 5 — 贡献清单**（~4句）

本文贡献：
- **C1**: 提出 QDCVR — 一种内容验证驱动的 RAG 检索方法，包含自适应查询理解和七步管线。
- **C2**: 提出经验可信度模型（P0/P1/P2 三级 + E0-E12 生命周期 + 时效衰减），首个面向 Agent 知识库的经验管理框架。
- **C3**: 实现一个 Agent 优先的知识库平台（91 MCP 工具 + 17 技能），开源并实际部署。
- **C4**: 在 [N] 个查询上评估 QDCVR，相比向量基线提升 precision@5 达 [X]%。

### 1.2 配图计划

| 图编号 | 内容 | 类型 |
|--------|------|------|
| **Figure 1** | 问题示意：向量高分但内容不相关的典型案例 | 示意图 |
| **Figure 2** | QDCVR 七步管线总览 | 流程图 |

---

## Section 2 — Related Work（~1页）

### 2.1 Dense Retrieval in RAG（~0.3页）

- DPR (Karpukhin et al., 2020) — 双编码器稠密检索
- Contriever (Izacard et al., 2022) — 无监督对比检索
- BGE-M3 (Chen et al., 2024) — 多语言多功能嵌入（本系统所用）
- **差距**: 这些工作优化召回质量，但不验证召回结果的内容相关性

### 2.2 Retrieval Verification & Reranking（~0.3页）

- Cross-Encoder Rerankers (Nogueira & Cho, 2019)
- FLARE (Jiang et al., 2023) — LLM 实时判断检索质量
- Self-RAG (Asai et al., 2023) — 训练 LLM 自我判断检索必要性
- **差距**: 这些方法要么是黑箱 LLM 判断（不可解释），要么是独立 reranker（增加管线复杂度）。QDCVR 将验证嵌入检索管线，以可解释的 0–8 分制完成。

### 2.3 Knowledge Management Systems（~0.2页）

- Confluence / Notion AI / Glean — 商业 KB 系统
- GraphRAG (Microsoft, 2024) — 图增强 RAG
- LightRAG / RAGFlow — 开源 RAG 框架
- **差距**: 这些系统关注检索+生成管线，缺乏**结构化经验管理和可信度分级**。本系统的经验库 E0-E12 生命周期是首创。

### 2.4 Agent & Tool-Use Paradigms（~0.2页）

- ReAct (Yao et al., 2022) — 推理+行动框架
- Toolformer (Schick et al., 2023)
- Model Context Protocol (Anthropic, 2024) — 工具调用标准
- **差距**: 本系统将 MCP 工具设计为知识库的原生接口（76 工具），实现 Agent 优先的架构。

### Related Work 表格

| System | Dense Ret. | Content Verify | KB Mgmt | Agent-Native | Open Source |
|--------|:---------:|:-------------:|:-------:|:------------:|:-----------:|
| DPR/DANCE | ✓ | ✗ | ✗ | ✗ | ✓ |
| RAG (Lewis+) | ✓ | ✗ | ✗ | ✗ | ✓ |
| GraphRAG | ✓ | ✗ | partial | ✗ | ✓ |
| Self-RAG | ✓ | LLM | ✗ | ✗ | ✓ |
| **Ours (QDCVR)** | **✓** | **✓ (0-8)** | **✓** | **✓ (MCP)** | **✓** |

---

## Section 3 — Problem Formulation & Background（~0.8页）

### 3.1 问题定义

给定：
- 一组知识库 $\mathcal{K} = \{K_1, K_2, \ldots, K_m\}$，每个 $K_i$ 含文档集 $\{d_1, \ldots, d_{n_i}\}$
- 用户查询 $q$（自然语言）

目标：返回一个有序结果集 $R = \{(d_j, s_j, c_j, t_j)\}$，其中：
- $s_j$: 向量相似度分数
- $c_j \in [0, 8]$: **内容验证分数**（QDCVR 核心创新）
- $t_j \in \{P_0, P_1, P_2\}$: 可信度分级

### 3.2 形式化：为什么内容验证是必要的

**定理（非正式）**: 向量相似度 $s$ 与内容相关性 $r$ 之间存在系统性偏差。设文档嵌入为 $\phi(d)$，查询嵌入为 $\phi(q)$，则：
$$s = \cos(\phi(q), \phi(d)) = \frac{\phi(q) \cdot \phi(d)}{\|\phi(q)\| \|\phi(d)\|}$$

当查询和文档处于同一语义子空间但描述不同实体时（如"battery thermal management" vs "data center thermal management"），$s$ 可以很高但 $r$ 很低。**QDCVR 通过独立内容评分 $c$ 截断这种假阳性。**

### 3.3 设计约束

| 约束 | QDCVR 设计选择 |
|------|---------------|
| 可解释性 | 0-8 分制 + 分维度评分（主题/场景/证据） |
| 低延迟 | 只对 top-5 候选执行内容验证 |
| 跨语言 | 查询改写 + 多语言嵌入（BGE-M3） |
| 诚实性 | 盲点声明机制（无命中则诚实声明） |

---

## Section 4 — QDCVR Methodology（~2.5页）⭐核心

### 4.1 管线总览

```
Query q
  │
  ├─ Step 0: Query Understanding & Rewrite ────────── 改写为检索友好形态
  │
  ├─ Step 1: Smart KB Selection ────────────────────── 从 KB catalog 选 top-1~3 相关库
  │
  ├─ Step 2: Two-Stage Recall ──────────────────────── BM25(Stage1) → Vector(Stage2) + balance_kbs
  │
  ├─ Step 2.5: Document-Level Dedup + Hard Threshold ── 去重 + score<0.35 丢弃
  │
  ├─ Step 3: Content Verification ⭐ ──────────────── kb_doc_read + 0-8 打分（核心裁决）
  │     └─ Fast Exit: content≥6 → 直接回答
  │
  ├─ Step 4: Tag & Description Expansion ───────────── 向量未命中时扩展召回
  │
  ├─ Step 5: Confidence Rating ─────────────────────── P0/P1/P2 分级
  │
  └─ Step 6: Synthesized Answer + Blind-Spot Declaration
```

### 4.2 Step 0 — Query Understanding Layer

#### 4.2a Intent Classification

| Intent Type | Signal | Threshold Strategy | Example |
|-------------|--------|-------------------|---------|
| Factual | "what is", "定义" | vector-only, high threshold (0.45) | "什么是双向拉伸" |
| Procedural | "how to", "怎么做" | vector + tag expansion | "如何设置拉伸比" |
| Troubleshooting | "error", "失败" | **experience-first** | "检索报错 ConnectionError" |
| Comparative | "A vs B", "区别" | multi-entity parallel recall | "PET vs PP 拉伸性能" |
| Navigational | "where is", "有没有" | catalog description match | "有没有相变材料的文献" |

#### 4.2b Query Rewrite

口语查询 → **声明句 + 关键词组合**：
$$q' = \text{rewrite}(q) = f_{\text{LLM}}(q, \text{intent}, \text{context})$$

产出两个变体：
- $q'_{\text{vector}}$ — 面向向量检索的语义完整声明句
- $q'_{\text{BM25}}$ — 面向 BM25 的关键词组合

### 4.3 Step 1 — Smart KB Selection

$$K_{\text{selected}} = \arg\max_{K_i \in \mathcal{K}} \text{Sim}_{\text{desc}}(q', \text{desc}(K_i))$$

使用 `kb_list(lightweight=true)` 获取所有 KB 的轻量元数据（仅 name + description + doc_count），由 Agent/LLM 判断 top-1~3 个相关 KB。

**关键创新**: 避免"全库盲搜"导致大库主导。实测：跨 12 KB 盲搜时，11 文档的大库（Materials-ML）返回了 80% 的结果，淹没小库相关文档。

### 4.4 Step 2 — Two-Stage Recall with Balance

#### Stage 1: Broad Search (BM25 + Graph Neighbor Expansion)

$$C_{\text{broad}} = \text{BM25}(q'_{\text{BM25}}, \text{all\_docs}) \cup \text{GraphNeighbors}(q', \text{depth}=1)$$

- BM25 候选文档数：$|C_{\text{broad}}| \leq \text{stage1\_top\_k}$ (默认 20)
- 图谱邻居扩展：利用 Neo4j 的 RELATED_TO 边发现语义关联文档

#### Stage 2: Fine Vector Search (within candidate docs)

$$\text{results} = \text{VectorSearch}(q'_{\text{vector}}, C_{\text{broad}}, \text{top\_k}=5)$$

仅在 Stage 1 候选文档的向量集合内搜索，而非全库。这避免了向量检索的 $O(N)$ 全扫描。

#### balance_kbs — 跨库多样性保证

当跨多个 KB 检索时，按 KB 分组轮询选取候选（round-robin），确保每个 KB 至少贡献 1 个候选：

```python
# 伪代码
groups = group_by_kb(candidates)
result = []
while len(result) < top_k and any(group for group in groups.values()):
    for kb_id in sorted(groups, key=lambda k: len(groups[k]), reverse=True):
        if groups[kb_id]:
            result.append(groups[kb_id].pop(0))
```

### 4.5 Step 3 — Content Verification ⭐（核心创新）

#### 4.5a 0-8 Scoring Rubric

| Dimension | Score Range | Criteria |
|-----------|:-----------:|----------|
| **Topic Relevance** | 0-3 | 3=directly about query subject; 2=touches subject; 1=tangentially related; 0=irrelevant |
| **Scenario/Problem Match** | 0-3 | 3=directly solves the query's problem; 2=transferable method; 1=generic mention; 0=answers different question |
| **Answer Evidence** | 0-2 | 2=contains specific data/steps/conclusions to cite; 1=directional info; 0=vague |

$$c = \text{topic\_score} + \text{scenario\_score} + \text{evidence\_score} \in [0, 8]$$

#### 4.5b The Content-Override Principle

$$\text{decision}(d) = \begin{cases} \text{accept} & \text{if } c(d) \geq 6 \\ \text{supplement} & \text{if } c(d) = 5 \\ \text{discard} & \text{if } c(d) \leq 4 \end{cases}$$

**核心论点**: $c(d)$ 独立于向量分 $s(d)$。即使 $s(d) = 0.95$，若 $c(d) \leq 4$ 则丢弃。

#### 4.5c Implementation: Reading-based Verification

内容验证通过 `kb_doc_read(doc_path, max_chars=3000)` 读取候选文档正文，由 LLM/Agent 依据 rubric 打分。这是**基于文本阅读的验证**，而非基于嵌入相似度的估计。

### 4.6 Step 5 — Confidence Tiering

| Tier | Condition | Presentation |
|------|-----------|-------------|
| **P0 Strong** | content≥6 ∧ vector≥0.65 | Directly cite as answer |
| **P1 Confirmed** | content≥5 ∧ vector≥0.45 | Cite with annotation |
| **P2 Supplement** | content≥4 ∧ vector≥0.35 | Hidden by default, expand on request |
| **Discard** | content≤4 OR vector<0.35 | Never presented |

#### 4.6a Short-Content Guard

向量搜索可能返回极短 chunk（如 "## 问题" 两个字）却因向量维度集中获得高分：
- chunk < 50 chars → 降级 P2
- 文档 >50% 的 chunk 都是短 chunk → 整文档降级

### 4.7 Blind-Spot Declaration

当跨库检索确认的 P0/P1 结果来自 <2 个 KB 时，系统**主动声明盲点**，而非掩盖覆盖不足。这是"宁可不给，不要错给"原则的体现。

### 配图计划

| 图编号 | 内容 | 类型 |
|--------|------|------|
| **Figure 3** | QDCVR 详细管线（含每步输入输出） | 流程图 |
| **Figure 4** | 0-8 评分 rubric 示意图 | 表格/图 |
| **Figure 5** | 内容覆盖原则：向量分 vs 内容分散点图 | 散点图 |

---

## Section 5 — Experience Lifecycle Framework（~1.2页）⭐核心

### 5.1 Motivation

文档是**静态知识**，而实际运维/操作中产生的**经验**（problem→solution→lessons）是动态的、可复用的。现有 KB 系统没有管理经验的机制。我们提出**经验库 (Experience Library)**。

### 5.2 E0-E12 Lifecycle

| Stage | Name | Description |
|-------|------|-------------|
| **E0** | Prepare | Identify target KB + collect source material |
| **E1** | Heuristic Extract | Rule-based candidate extraction from documents |
| **E2** | Quality Gate | LLM-refined draft must pass golden standard |
| **E3** | Draft Pool | Human-in-the-loop: approve / reject / refine |
| **E4** | Experience-First Retrieval | P0/P1/P2 tiered search, intent-adaptive |
| **E5** | Application Tracking | Record when/where/how an experience was applied |
| **E6** | Stale Detection | Check consistency with related documents |
| **E7** | Review & Rating | Peer review with 0-5 rating |
| **E8** | Dashboard | Aggregate statistics + health metrics |
| **E9** | Semantic Rerank | Multi-dimensional relevance reranking |
| **E10** | Cross-KB Search | QDCVR pipeline for experiences (isomorphic with docs) |
| **E11** | Credibility Decay | Periodic degradation of stale/disputed experiences |
| **E12** | Auto Health Check | Automated cleanup of orphans + re-verify |

### 5.3 P0/P1/P2 Credibility Model

$$\text{Tier}(e) = \begin{cases} P_0 & \text{if } \text{vector}(e) \geq 0.65 \wedge \text{content}(e) \geq 6 \wedge \text{rating}(e) \geq 4 \wedge \text{reviews}(e) \geq 1 \\ P_1 & \text{if } \text{vector}(e) \geq 0.45 \wedge \text{content}(e) \geq 4 \\ P_2 & \text{if } \text{vector}(e) \geq 0.35 \wedge \text{content}(e) \geq 3 \\ \text{Discard} & \text{otherwise} \end{cases}$$

**修正项 (Modifiers)**:
- **Disputed**: ≥3 reviews ∧ rating<2.0 → 降级至 P2
- **Unvetted**: 0 reviews ∧ 0 applied → 封顶 P1
- **Counter-Example Penalty**: 领域不匹配（共享通用词但关键领域词不同）→ 降分

### 5.4 Temporal Decay (E11)

| Decay Rule | Condition | Effect |
|-----------|-----------|--------|
| stale_unverified | age>30d ∧ applied_count=0 | Flagged, demoted in search |
| disputed | ≥3 reviews ∧ rating<2.0 | Hard cap P2 |
| fully_unvetted | 0 reviews ∧ 0 applied | Hard cap P1 |

### 5.5 Multi-Path Experience Retrieval (E4 + E9)

5 路并行召回 + 融合去重：
```
Path A: Vector semantic recall (existing)
Path B: Keyword metadata recall (title/problem/solution/tags)
Path C: Scenario exact match (new) — match experience.scenario field
Path D: Tag-path recall (new) — domain_tokens ∩ experience.tags
Path E: Quality feedback recall (new) — applied_count≥2 ∧ rating≥4 bonus
```

---

## Section 6 — System Implementation（~0.8页）

### 6.1 Architecture Overview

```
┌─────────────────────────────────────────┐
│  User Interfaces (4)                     │
│  Claude Code (NL) · CLI · MCP · Web UI   │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  kb-mcp Server (Python/FastMCP)          │
│  91 MCP Tools — KB CRUD, Search,         │
│  Graph, Experience, Parse, Lifecycle     │
└──────┬───────────┬──────────────────────┘
       │ HTTP      │ Direct File Read
       ▼           ▼
┌──────────────┐  ┌─────────────────────────┐
│  FastAPI      │  │  Storage Layer           │
│  Backend      │  │  .tree-fs.json           │
│  + MinerU OCR │  │  .knowledge-base.yml     │
│  + Vector     │  │  ChromaDB (BGE-M3)       │
│  + Graph      │  │  Neo4j                   │
└──────────────┘  └─────────────────────────┘
```

### 6.2 Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, ChromaDB, Neo4j 5.20 |
| Embedding | BGE-M3 (1024-dim), sentence-transformers |
| OCR/Parse | MinerU (PDF/Word/Excel/PPT/Image → Markdown) |
| MCP | Python FastMCP, httpx |
| Frontend | TypeScript, Nuxt 3, Ant Design Vue |
| CLI | Node.js, js-yaml |
| Desktop | Rust, Tauri v2 |

### 6.3 Write-Read Asymmetry

**设计原则**: 写操作通过 HTTP API（保证一致性），读操作直接文件访问（零后端负载）。

### 6.4 Five-Layer Data Model

| Layer | Content | Format |
|-------|---------|--------|
| L1 Raw | Original documents | PDF/DOCX/XLSX/PNG |
| L2 Parsed | Markdown + images | .md |
| L3 Vector | Chunked embeddings | ChromaDB collections |
| L4 Graph | Entity/relation nodes | Neo4j |
| L5 Experience | Structured lessons | YAML + Markdown |

---

## Section 7 — Evaluation（~2页）

> ⭐ **详细评测方案见 [EVALUATION-DESIGN.md](./EVALUATION-DESIGN.md)**

### 7.1 Research Questions

| RQ | Question | Metric |
|----|----------|--------|
| **RQ1** | QDCVR 的内容验证是否降低了向量误召回？ | Precision@k, False-Positive Rate |
| **RQ2** | 内容覆盖原则（content > vector）的效果？ | Precision gain vs vector-only |
| **RQ3** | balance_kbs 是否改善了跨库多样性？ | KB diversity (Shannon entropy) |
| **RQ4** | 经验可信度模型的分级是否准确？ | Tier assignment accuracy |
| **RQ5** | 经验时效衰减是否有效？ | Stale detection F1 |
| **RQ6** | Agent 优先架构的任务完成率？ | Task completion rate |

### 7.2 Datasets

- **Doc-IR**: 构建评测集 — 从现有 12 KB / [N] 文档中，人工标注 [M] 个查询的 ground-truth 相关文档
- **Experience-IR**: 从现有 [14+] 条经验中，人工标注 [K] 个故障/运维查询的 ground-truth 经验
- **Baselines**: 向量-only (BGE-M3), BM25, BM25+Vector fusion, RAG-Fusion, Cohere Rerank

### 7.3 Metrics

| Metric | Formula | 用于 |
|--------|---------|------|
| Precision@k | $\frac{|\text{relevant} \cap \text{retrieved}_k|}{k}$ | RQ1, RQ2 |
| Recall@k | $\frac{|\text{relevant} \cap \text{retrieved}_k|}{|\text{relevant}|}$ | RQ1 |
| nDCG@k | 位置加权的相关性 | RQ1, RQ4 |
| FPR | $\frac{|\text{false positives}|}{|\text{retrieved}|}$ | RQ1 |
| KB Shannon Entropy | $-\sum_i p_i \log p_i$ (跨库结果分布) | RQ3 |

### 7.4 Results Table (预期)

| Method | P@5 | Recall@5 | nDCG@5 | FPR↓ |
|--------|:---:|:--------:|:------:|:----:|
| BM25 only | [0.45] | [0.38] | [0.42] | [0.35] |
| Vector only (BGE-M3) | [0.62] | [0.55] | [0.58] | [0.28] |
| BM25 + Vector fusion | [0.68] | [0.61] | [0.65] | [0.22] |
| Vector + Reranker (CE) | [0.75] | [0.68] | [0.72] | [0.18] |
| **QDCVR (ours)** | **[0.85]** | **[0.72]** | **[0.82]** | **[0.08]** |

### 7.5 Ablation Study

| Variant | P@5 | Δ vs Full |
|---------|:---:|:---------:|
| QDCVR full | [0.85] | — |
| − Content Verification | [0.62] | −0.23 |
| − Query Rewrite (Step 0) | [0.78] | −0.07 |
| − balance_kbs | [0.80] | −0.05 |
| − KB Selection (Step 1) | [0.74] | −0.11 |
| − Short-content Guard | [0.82] | −0.03 |

---

## Section 8 — Discussion & Threats to Validity（~0.5页）

### 8.1 Limitations

- 内容验证依赖 LLM 打分，引入一定延迟（~2-5s per query for top-5 candidates）
- 评测集规模有限（人工标注成本高）
- 经验系统的 E0-E12 生命周期需要较长时间验证实际效果

### 8.2 Threats to Validity

| 类型 | 威胁 | 缓解 |
|------|------|------|
| **Construct** | 0-8 评分主观性 | 3 名标注者交叉标注，Cohen's κ > 0.7 |
| **Internal** | LLM 打分偏差 | 使用 temperature=0 + 多次采样取均值 |
| **External** | 单一领域验证 | 扩展到 ML 研究 + 高分子材料两个领域 |

---

## Section 9 — Conclusion（~0.3页）

总结 QDCVR 的三大贡献（内容验证、经验生命周期、Agent 优先架构），强调"content > vector"原则对可信 RAG 的意义。展望：多模态内容验证、自动化评测集构建、跨语言经验迁移。

---

## 📚 参考文献计划（~30-40篇）

### 必引文献

**RAG / Retrieval:**
- Lewis et al. (2020). RAG. NeurIPS.
- Karpukhin et al. (2020). DPR. EMNLP.
- Gao et al. (2023). Retrieval-Augmented Generation for LLMs: A Survey.
- Izacard et al. (2022). Contriever. NeurIPS.
- Chen et al. (2024). BGE-M3. arXiv.

**Reranking / Verification:**
- Nogueira & Cho (2019). Passage Reranking with BERT. arXiv.
- Asai et al. (2023). Self-RAG. arXiv.
- Jiang et al. (2023). FLARE. arXiv.
- Glass et al. (2022). Re2G. Findings of EMNLP.

**Knowledge Management:**
- Edge et al. (2024). GraphRAG. arXiv (Microsoft).

**Agent / Tool Use:**
- Yao et al. (2022). ReAct. arXiv.
- Schick et al. (2023). Toolformer. NeurIPS.
- Anthropic (2024). Model Context Protocol. Specification.

**Hybrid Search:**
- Robertson & Zaragoza (2009). The Probabilistic Relevance Framework: BM25 and Beyond.
- Luan et al. (2021). Sparse, Dense, and Attentional Representations for Text Retrieval. TACL.

**Systems:**
- Johnson et al. (2019). Billion-scale similarity search with GPUs. IEEE TVCG. (FAISS)
- Pan et al. (2024). Unifying Large Language Models and Knowledge Graphs: A Roadmap. IEEE TKDE.

---

## 📐 排版规范（ACM sigconf）

```latex
\documentclass[sigconf, review]{acmart}  % review = 匿名版
\usepackage{booktabs, graphicx, subcaption, amsmath}

% 双栏 · 10pt · Times Roman
% 正文 ≤ 10 pages (不含 references)
% 匿名提交: \settopmatter{printacmref=false}
% 审稿期间: \acmConference[CIKM '27]{...}{2027}{...}
```

### 图表规范
- 所有图用 `\includegraphics` 嵌入，分辨率 ≥ 300dpi
- 表格用 `booktabs`（`\toprule`, `\midrule`, `\bottomrule`）
- 彩色图确保黑白可读
- 所有图表需有 caption 和可在正文中引用

### 写作风格检查清单
- [ ] 每个声明都有引用或实验支撑
- [ ] 没有 "obviously", "simply", "trivially" 等空洞词
- [ ] 每个图/表在正文中被引用 ("as shown in Figure 3")
- [ ] Related Work 不遗漏竞争对手
- [ ] Limitations 诚实披露
- [ ] Abstract 不超过 200 词
- [ ] References 格式统一 (ACM Reference Format)
