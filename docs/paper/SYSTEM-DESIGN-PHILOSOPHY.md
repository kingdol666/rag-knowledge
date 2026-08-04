# QDCVR 知识库平台：设计思想、算法机制与系统特征

> **CIKM 论文 §1-§3 核心内容 · 学术术语体系**

---

## 一、总体设计思想 (Design Philosophy)

### 1.1 核心命题："组织优先于检索" (Organize First, Retrieve Later)

本系统的根本假设是：**检索质量的上界不是嵌入模型的精度，而是语料的组织结构**。

传统 RAG 系统将文档视为**扁平语料池** (flat corpus)，依赖稠密向量检索 (dense retrieval) 在 $O(N)$ 空间中寻找与查询语义相近的文档块。这种方法隐含假定了"语义相近 = 内容相关"，但这一假定在跨领域场景中系统性失效——两个语义相近但来自不同领域的文档（如电池热管理的 PCM 和数据中心热管理的 PCM）会获得相似的高向量分数，导致**跨域假阳性** (cross-domain false positives)。

我们的核心洞察是：如果在检索**之前**将文档按领域结构组织（自动归档到领域知识库），那么：

1. **搜索空间被结构性压缩** (structural search space reduction)：从全库 $N$ 文档降至领域库 $N_k \ll N$ 文档
2. **跨域假阳性被结构性消除** (structural false-positive elimination)：领域边界天然隔离了语义近邻但跨域的无关文档
3. **内容验证在计算上变得可行** (content verification tractability)：只需验证 $\sim 5$ 个候选文档而非 $\sim 60$ 个

这形成了我们的方法论等价命题：

$$\text{Retrieval Quality} = f(\text{Corpus Organization}) \times g(\text{Retrieval Method})$$

其中 $f(\cdot)$ 是语料结构的乘数效应，$g(\cdot)$ 是检索方法的边际贡献。**在扁平语料上优化 $g(\cdot)$ 的边际收益递减，而改善 $f(\cdot)$ 带来阶跃式增益。**

### 1.2 次要命题："内容分数覆盖向量分数" (Content Score Overrides Vector Score)

向量检索的本质是用嵌入空间的**几何邻近性** (geometric proximity) 代理**语义相关性** (semantic relevance)。这是一种有损近似——两个文档块的向量相似度 $s(d) = \cos(e_q, e_d)$ 可以很高，但实际内容 $c(d)$ 可能与查询无直接关系。

我们的第二条核心原则是：**在召回和裁决之间进行解耦** (decouple recall from adjudication)：

- **Recall** 阶段使用向量+BM25+图谱融合最大化候选覆盖率
- **Adjudication** 阶段使用独立的、基于文本阅读的 0-8 评分 rubric 裁决每个候选

关键不等式：

$$c(d) \leq 4 \implies \text{discard}(d), \quad \text{independent of } s(d)$$

即使 $s(d) = 0.95$，若 $c(d) \leq 4$，文档被丢弃。这是 QDCVR 区别于 CRAG (训练分类器) 和 Self-RAG (生成反射 token) 的**可解释决策边界**。

### 1.3 第三命题："经验是有生命周期的结构化知识对象" (Experience as First-Class KB Artifacts)

传统知识库管理的是**静态文档**。但实际知识工作中产生的大量价值是**动态经验**——故障排查记录、最佳实践总结、参数调优心得。这些经验具有与文档不同的属性：

- **可信度是动态的**：经过验证、多人好评的经验可信度高；未经验证的经验可信度低
- **时效性是衰减的**：30 天未使用的运维经验可能已经过时
- **领域是敏感的**：一个领域的经验在另一领域可能不适用甚至误导

我们提出 **Experience Lifecycle Framework (E0-E12)**，把经验提升为与文档同等的**一等知识库对象** (first-class KB artifact)，具有独立的存储、索引、检索、分级和生命周期管理。

---

## 二、算法机制 (Algorithmic Mechanisms)

### 2.1 QDCVR：查询驱动的内容验证检索七阶段管线

QDCVR (Query-Driven Content-Verified Retrieval) 是一个七阶段管线，每一阶段解决一个特定问题：

```
Query q
  │
  ├─ Stage 0: Adaptive Query Understanding   ─ 意图分类 + 查询改写
  │    输出: q'_vector (语义声明句), q'_BM25 (关键词组合), intent ∈ {factual, procedural, troubleshooting, comparative, navigational}
  │
  ├─ Stage 1: Smart KB Selection              ─ 从 KB catalog 选择 top-1~3 相关库
  │    K* = argmax_{K_i ∈ K} Sim_LLM(q', desc(K_i))
  │    关键: 避免"全库盲搜"导致大库主导
  │
  ├─ Stage 2: Two-Stage Recall                ─ BM25(Stage1) → Vector(Stage2) + balance_kbs
  │    C_broad = BM25(q'_BM25) ∪ GraphNeighbors(q', depth=1)
  │    results = VectorSearch(q'_vector, C_broad, top_k=5)
  │    balance_kbs: round-robin 跨库选取 (保证多样性)
  │
  ├─ Stage 2.5: Dedup + Hard Threshold        ─ 文档级去重 + score<0.35 丢弃
  │
  ├─ Stage 3: Content Verification ⭐          ─ 读正文按 0-8 rubric 独立打分
  │    c(d) = topic_score(0-3) + scenario_score(0-3) + evidence_score(0-2)
  │    decision(d) = accept(c≥6) | supplement(c=5) | discard(c≤4)
  │    实现: kb_doc_read(doc, 3000 chars) → LLM 按 rubric 打分 (temperature=0)
  │
  ├─ Stage 4: Tag & Description Expansion     ─ 向量未命中时扩展召回
  │
  ├─ Stage 5: Confidence Tiering              ─ P0/P1/P2 可信度分级
  │    P0 Strong: c≥6 ∧ s≥0.65  → 直接引用
  │    P1 Confirmed: c≥5 ∧ s≥0.45 → 标注引用
  │    P2 Supplement: c≥4 ∧ s≥0.35 → 默认隐藏
  │    Discard: c≤4 ∨ s<0.35 → 不展示
  │    Short-Content Guard: chunk<50 chars → 降级 P2
  │
  └─ Stage 6: Synthesis + Blind-Spot Declaration
      当确认结果来自 <2 KB → 主动声明覆盖不足
```

**Stage 3 的三维评分 Rubric 设计**:

|c| 维度 | 分值 | 判定标准 |
|---|------|:---:|---------|
| Topic Relevance | 0-3 | 3=直接关于查询主题; 2=涉及但不精确; 1=边缘相关; 0=无关 |
| Scenario/Problem Match | 0-3 | 3=直接解决查询问题; 2=可迁移方法; 1=泛泛而谈; 0=回答其他问题 |
| Answer Evidence | 0-2 | 2=含可引用的数据/步骤/结论; 1=方向性信息; 0=模糊 |

总分 $c \in [0, 8]$，与向量分 $s \in [0, 1]$ **独立**。这是"content-overrides-vector"原则的数学基础。

**与 CRAG 的关键算法差异**：

| | CRAG (NAACL 2024) | QDCVR (本文) |
|---|---|---|
| 验证方式 | 训练轻量检索评估器 → 输出 Correct/Incorrect/Ambiguous | LLM 读正文 → 0-8 三维 rubric 打分 |
| 可解释性 | 黑箱二分类 | 三维可解释评分 |
| 假设语料 | 扁平 (flat corpus) | **领域结构化** (domain-structured) |
| 回退策略 | Web 搜索 (可能引入噪声) | Cross-KB 扩展 + 盲点声明 |
| 向量与内容的关系 | 未区分 | **content-overrides-vector** → 独立裁决 |

### 2.2 Experience Lifecycle E0-E12：结构化经验生命周期

13 阶段经验管理框架，每个经验经历从提取到衰减的完整生命周期：

| Stage | Name | Mechanism |
|:-----:|------|----------|
| E0 | Prepare | 从 KB 文档扫描可提取的经验候选 |
| E1 | Extract | LLM 提炼 problem → solution → lessons 结构 |
| E2 | Quality Gate | content_score≥6 且证据充足才通过 |
| E3 | Draft → Publish | 草稿池 → 审批 → 正式入库 |
| E4 | Credibility Tiering | P0/P1/P2 三级可信度 (含反例检测) |
| E5 | Index | 向量+图双索引 |
| E6 | Stale Detection | 检测经验与源文档一致性 |
| E7 | Multi-Path Search | 5 路并行召回 (vector/keyword/scenario/tag/quality-feedback) |
| E8 | Dashboard | 经验看板统计 |
| E9 | Rerank | 多维度语义重排 |
| E10 | Apply | 记录应用次数+效果 |
| E11 | Temporal Decay | 时效衰减规则 |
| E12 | Auto Health Check | 孤儿清理+自动复审 |

**P0/P1/P2 可信度分级决策函数**：

$$\text{Tier}(e) = \begin{cases} P_0 & \text{vec} \geq 0.65 \land \text{content} \geq 6 \land \text{rating} \geq 4 \land \text{reviews} \geq 1 \\ P_1 & \text{vec} \geq 0.45 \land \text{content} \geq 4 \\ P_2 & \text{vec} \geq 0.35 \land \text{content} \geq 3 \\ \text{Discard} & \text{otherwise} \end{cases}$$

**修正项**：
- **Disputed** (≥3 reviews ∧ rating<2) → cap P2 (硬上限)
- **Unvetted** (0 reviews ∧ 0 applied) → cap P1 (未经验证不能为 P0)
- **Counter-Example Detection**: 查询领域与经验领域不匹配 → 降级 (-1 tier)

**E11 时效衰减规则**：

| 条件 | 动作 |
|------|------|
| created >30d ∧ applied=0 ∧ reviews=0 | Demote: P0→P1, P1→P2 |
| created >90d ∧ applied=0 | Demote: any→P2 |
| applied≥1 且在 30d 内 | 不受衰减影响 |
| disputed (rating<2) | 不受时间影响 → hard cap P2 |

### 2.3 Auto-Archiving A0-A9：基于内容的自动分类管线

9 阶段文档入库管线，在 parse→ingest 过程中自动完成分类决策：

```
A0: File upload → 原始文件上传
A1: Dedup check → 内容指纹去重
A2: Parse (MinerU OCR) → PDF→Markdown + 图片提取
A2.5: Quality check → 解析完整性验证
A3: Structured analysis → 正文摘要 + 关键词提取
A3d: KB attribution → 基于内容 vs KB descriptions 的匹配决策树 ← 核心
A4: Tag generation → 自动标签 + 规范化
A5: Description generation → 四要素描述 (领域+内容+方法+结果)
A6: KB-attribution → 执行归档
A7: Store → 写入文件系统 + 元数据
A8: Index → 向量索引 (ChromaDB + BGE-M3) + 图索引 (Neo4j)
A9: Post-index verify → 索引完整性验证
```

**A3d 归属决策树**：读正文前 1500 字符 → LLM 匹配 `kb_list(lightweight=true)` descriptions → 输出 top-3 候选 KB（含置信度和理由）→ 选最高置信度 ≥ 阈值的 KB 归档。无匹配 → 建议创建新 KB。

---

## 三、系统特征与优势

### 3.1 五层数据模型 (5-Layer Data Model)

系统采用分层数据架构，保证读写的非对称效率：

| 层 | 存储 | 用途 | 读写特性 |
|:--:|------|------|---------|
| L1 | 磁盘 (.md 文件) | 原始文档内容 | 写: HTTP API | 读: 直接文件访问 |
| L2 | .tree-fs.json | 文件系统树结构 | 写: HTTP API | 读: 直接文件访问 |
| L3 | .knowledge-base.yml | 文档元数据 (tags, description) | 写: HTTP API | 读: 直接文件访问 |
| L4 | ChromaDB (向量) | 语义索引 (BGE-M3, 1024-dim) | 写: HTTP API | 读: MCP 工具 |
| L5 | Neo4j (图谱) | 文档关系图 (RELATED_TO) | 写: HTTP API | 读: MCP 工具 |

**读写非对称设计 (Write-Read Asymmetry)**：写路径走 HTTP API 保证一致性和事务性；读路径直接访问文件系统和索引数据库，零后端负载。这是"Agent 优先"架构的工程基础——Agent 的 MCP 工具调用可以极低延迟地读取文档和元数据。

### 3.2 Agent 原生架构 (Agent-Native Architecture)

| 特征 | 量化指标 | 与 MCP-Pyserini (SIGIR 2026) 的本质区别 |
|------|:------:|----------------------------------------|
| MCP 工具数 | **76** (覆盖完整 KB 生命周期) | Pyserini: ~10 (仅检索+重排+评测) |
| Agent Skills | **14** (ingest/search/manage/organize/verify/experience/graph/...) | Pyserini: 0 |
| 工具覆盖范围 | CRUD + 解析 + 图谱 + 经验 + 索引 + 标签 + 生命周期管理 | 仅 IR 工具暴露 |
| 部署模式 | Agent 通过 MCP stdio 直接调用 + CLI (ragctl) + Web UI (Nuxt 3) | MCP + CLI |
| 桌面支持 | Tauri 桌面应用 (跨平台) | 无 |

**关键差异化声明**：MCP-Pyserini 是"把 IR 工具暴露给 Agent"，而 QDCVR 平台是"把整个知识库管理系统设计为 Agent 可用的能力集"。76 工具使 Agent 能自主完成从文档入库到经验提取到跨库检索到整理清洗的**完整知识管理工作流**。

### 3.3 领域结构与层次知识库 (Domain-Structured Hierarchical KBs)

系统原生支持层次化知识架构：

```
父 KB (parent)
  ├── 子 KB 1 (领域细化)
  │   ├── 文档 1
  │   └── 文档 2
  ├── 子 KB 2
  │   └── ...
  └── 子 KB N
```

实际部署案例 (高分子双向拉伸文献库)：1 个父库 × 11 个子库 (PET/PP/PLA/PA/PE/Equipment/Characterization/Physics/...)，7,600 chunks。层次结构的价值在于：

1. **检索粒度可选**：父库检索 (全领域) vs 子库检索 (精准匹配特定材料)
2. **跨子库对比**：父库检索 + path 过滤实现跨材料对比
3. **增量扩展**：新子库可随时添加而不影响已有结构

### 3.4 多策略融合召回 (Multi-Strategy Recall Fusion)

Stage 2 的 Two-Stage Recall 融合了三种互补的检索信号：

| 策略 | 信号 | 优势 | 局限 |
|------|------|------|------|
| BM25 (稀疏) | 词频-逆文档频率 | 精确匹配、专业术语、跨语言 | 语义理解弱 |
| Vector (稠密) | BGE-M3 embedding | 语义泛化、模糊匹配 | 假阳性、大库主导 |
| Graph (结构) | Neo4j RELATED_TO 边 | 关联发现、多跳推理 | 依赖图质量 |

三路融合方式：Stage 1 用 BM25 + Graph 做**宽召回** (broad recall, top-20)，Stage 2 用 Vector 在候选集上做**精召回** (fine recall, top-5)。这避免了向量检索的 $O(N)$ 全扫描，同时保留了语义泛化能力。

### 3.5 跨库平衡与诚实性机制 (Cross-KB Balance & Blind-Spot Honesty)

- **balance_kbs**: 跨多 KB 检索时，按 KB 分组轮询选取候选 (round-robin)，防止大库垄断结果。即使某个 KB 有 7,600 chunks 而另一个只有 500，前者不会淹没后者的相关文档。
- **Blind-Spot Declaration**: 当确认的 P0/P1 结果仅来自 <2 个 KB 时，系统**主动声明覆盖不足**，而非提供错误或无根据的答案。这是"宁可不给，不要错给"原则的工程实现。

---

## 四、适用场景 (Use Cases)

| 场景 | 典型用户 | 痛点 | QDCVR 如何解决 |
|------|---------|------|---------------|
| **多领域研究知识管理** | 跨学科研究团队 (材料+AI+能源+生物) | 跨域检索时语义近邻误召回 | 领域 KB 边界结构性隔离 |
| **运维故障知识库** | DevOps/SRE 团队 | 历史故障经验不可检索、过时不可用 | E0-E12 经验生命周期 + 时效衰减 |
| **Agent 辅助知识工作** | AI Agent 开发者 | 需要 Agent 自主完成文档全流程管理 | 76 MCP 工具 + 14 Agent Skills |
| **企业文档智能** | 企业知识管理部门 | 文档散落、分类依赖人工、检索低效 | A0-A9 自动归档 + 多策略检索 |
| **学术文献管理** | 研究生/科研人员 | 大量论文无法有效组织和检索 | 层次子 KB + 内容验证 |
| **多语言知识库** | 国际化团队 | 中英混合文档的语义检索 | BGE-M3 多语言嵌入 + 查询改写 |

---

## 五、创新性定位总结

| 维度 | 已有最接近的工作 | QDCVR 的本质差异 |
|------|----------------|-----------------|
| **检索验证** | CRAG (训练评估器), Self-RAG (反射 token) | 可解释的 0-8 三维 rubric + content-overrides-vector 独立裁决 |
| **语料组织** | 无等价系统 (所有现有 RAG 假设扁平语料) | **领域结构化作为检索前置** → 搜索空间压缩 ×1,138 + FPR 降低 87% |
| **MCP 集成** | MCP-Pyserini (~10 IR 工具) | **76 工具覆盖完整 KB 生命周期** (不是工具包，是完整系统) |
| **经验管理** | Agent memory (运行时记忆，非持久 artifact) | **E0-E12 经验作为一等 KB 对象** (独立存储+索引+检索+生命周期) |
| **系统完整性** | RAGFlow/Dify (手动 KB, 无经验, 无 Agent 原生) | **自动归档 + 经验引擎 + 层次结构 + Agent 原生** → 唯一全功能平台 |

---

> **一句话总结**：QDCVR 是一个"组织优先、内容裁决、经验驱动、Agent 原生"的知识库平台，通过领域结构化的语料组织 + 可解释的三维内容验证 + 结构化经验生命周期，解决了扁平 RAG 系统的跨域假阳性问题，并为 Agent 提供了 76 个覆盖完整知识管理生命周期的 MCP 工具。
