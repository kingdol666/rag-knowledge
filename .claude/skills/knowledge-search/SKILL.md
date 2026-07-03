---
name: knowledge-search
description: >
  Agentic RAG — 真正的智能检索。核心原则：**Agent 读 description 智能判断为主，
  向量相似度为辅助确认**。先读轻量 catalog 的 description 判断 KB/文档相关性，
  筛除无关项；再用向量在已确认候选内精排；最后读真实内容验证满足场景。
  绝不只是"向量 top-k 返回"。经验优先（操作类问题先查经验，严格相关度，
  宁可不给也不要错给）。Triggered by: "search", "find", "query", "ask",
  "retrieve", "what is", "how to", "explain", "rag", "回答", "检索", "搜索",
  "查找内容", "问答", "知识检索"。
---

# Agentic RAG — Agent 判断优先 + 向量辅助 + 内容验证

## ⚠️ 核心原则（必须遵守）

1. **Agent 判断为主，向量为辅**：先用 `kb_catalog` / `kb_doc_catalog` 读 description，用模型理解力判断相关性。**不是**直接调向量返回 top-k。
2. **轻量优先**：检索初期用 catalog 工具（仅 id+description），不加载 file_size/tags/vector_index 等污染 context。
3. **内容验证**：候选确认后必须 `kb_doc_read` 读真实内容片段，验证真满足场景。不满足就丢弃。
4. **经验优先 + 严格**：操作/故障类问题先查经验；经验严格相关度（≥0.55），灰区抑制，**宁可不给也不要错给**。
5. **诚实标注盲区**：知识库没有就坦率说，不硬凑。

---

## 自适应深度

| 深度 | 典型场景 | 流程 |
|------|---------|------|
| **L1 浅层** | 事实性快速查找（1-2 KB） | Catalog判断 → 读内容 → 答 |
| **L2 标准** | 知识问答（2-3 KB） | Catalog → Doc Catalog → 向量确认 → 内容验证 → 答 |
| **L3 深度** | 对比/综合分析（3-5 KB） | 完整流程 + 多 KB 交叉 |
| **L4 探索** | 跨域探索 | 全库 catalog + 经验 global |

---

## 完整检索流程（6 步）

### Step 0 — 意图识别（Agent 判断）

读懂用户问题，分类：
- **操作/故障/排查类**（"怎么处理""以前遇到""排查""诊断""应急"）→ **经验优先路径**
- **知识/原理/对比类**（"什么是""原理""对比""方法有哪些"）→ **文档优先路径**
- **混合** → 经验优先 + 文档补充

### Step 1 — KB Catalog 扫描（agentic 判断，轻量）📍 起点

```
kb_catalog()  →  [{kb_id, name, description, doc_count}]  (仅这4字段, 轻量)
```

**Agent 读每个 KB 的 description，用理解力判断**：
| 维度 | 判断 |
|------|------|
| description 语义 | KB 描述的领域/行业/技术是否与问题场景匹配？ |
| doc_count | 0 文档的 KB 立刻排除 |
| 语言匹配 | 问题语言与 KB 描述是否一致？ |

**输出候选 KB**（带相关性理由 + ★评级）：
```
| KB | 相关性 | 理由 |
|----|--------|------|
| Thermal-Power-Monitoring | ★★★ | description 含"火电监控/磨煤机/故障预警"直接匹配 |
| Wind-Power-Fault-Diagnostics | ★☆☆ | description 是风电，问题未涉及 |
```

> ⚠️ **不要**在这一步调向量搜索。先用理解力判断 description。

### Step 2 — Doc Catalog 扫描（agentic 判断，轻量）

对每个 ★★★/★★☆ 候选 KB：
```
kb_doc_catalog(kb_id)  →  [{doc_path, name, description}]  (仅这3字段, 轻量)
```

**Agent 读每篇 doc 的 description 判断**是否真正契合场景：
- description 里的研究对象/方法/设备是否与问题一致？
- 剔除"同 KB 但不同设备/主题"的文档（如问磨煤机时剔除空预器文档）

**输出候选 doc**（带评分 + 依据）：
```
| 文档 | Agent评分 | 依据 |
|------|----------|------|
| CNN-LSTM磨煤机故障预警 | 9/10 | description 明确"磨煤机堵煤预警"双匹配 |
| BP-SVR空预器压差预测 | 3/10 | 主题是空预器，非磨煤机 → 丢弃 |
```

### Step 3 — 经验优先检索（若操作/故障类问题）

对候选 KB，**先查经验**（实践总结优先于理论文档）：

```
# 已知场景标识 → 精确（最强）
experience_find_by_scenario(kb_id, scenario)

# 自然语言 → 向量语义（严格阈值 0.55，过滤无关）
experience_search_vector(kb_id, query)

# 跨库 → 全局向量（已用严格阈值）
experience_search_global(query)
```

**经验置信度分层**（严格，宁可不给也不要错给）：
| 层级 | 条件 | 处理 |
|------|------|------|
| **P0 强推** | scenario 精确命中 ∧ vector ≥ 0.65 ∧ rating≥4 | 强烈推荐 |
| **P1 可参考** | vector ≥ 0.55 ∧ rating≥3 | 推荐，标注可信度 |
| **P2 灰区** | 0.45 ≤ vector < 0.55 | **默认抑制**，仅"扩展探索"时呈现 |
| **丢弃** | vector < 0.45 | 不呈现 |

> **关键**：经验检索默认只返回 P0/P1。无 P0/P1 → 诚实说"暂无高相关经验"，**不拿灰区凑数**。

### Step 4 — 向量确认（辅助，在已确认候选内）

向量是**确认/精排手段**，不是主导。对 Step 2 确认的候选 doc：
```
# 单 KB 多文档：两阶段（BM25定位 + 向量精排）
kb_search_two_stage(query, kb_id, stage2_top_k=3)

# 文档无向量索引 → 跳过向量，直接 Step 5 读内容
```

向量结果与 Step 2 的 Agent 评分**交叉验证**：
- Agent 高分 ∧ 向量高分 → P0 优先
- 向量高分但 Agent 低分 → 怀疑向量误匹配，以 Agent 判断为准或读内容复核

**⚠️ 跨库盲区升级（关键）**：如果 `kb_search_two_stage` 跨库搜索（不指定 kb_id）返回的候选来自 **<2 个不同 KB**，表示 BM25 stage1 未能命中语义不同但内容相关的 KB。此时自动升级到企业级多路召回流程：

→ `Skill("knowledge-search-enterprise")` — 并行 3 路召回（kb_catalog + kb_search_two_stage + kb_search_vector），交叉验证去重，消除 BM25 跨库盲区。

**短文本过滤规则（⚠️ 新增）**：向量搜索可能返回极短 chunk（如仅 "## 问题"），此类 chunk score 虚高但无实质内容：
```
if len(chunk_content.strip()) < 50 characters:
    → 该 chunk 降为 P2 灰区（默认不呈现）
    → 除非该 chunk 的 doc_path 已有 P0/P1 候选背书
```
同一篇文档 >50% 的 chunk 为短文本 → 该文档整体降级，需 kb_doc_read 全文验证。

### Step 5 — 内容验证（读真实内容，必做）✅

对最终候选 doc，**读内容确认**真满足场景：
```
kb_doc_read(kb_id, doc_path, max_chars=1200)
```

逐篇判断：
| 维度 | 评分 |
|------|------|
| 主题对齐 | 0-3 |
| 场景匹配 | 0-3 |
| 答案潜力（能具体回答？） | 0-2 |
| 领域纯度（不是错误分类？） | -2-0 |

**评分 ≤4 → 丢弃并记录原因**。只有验证通过的 doc 才进答案。

### Step 6 — 综合呈现

```
## 答案
[自然语言组织。经验(可执行)优先 + 文档(原理)支撑]

**经验参考**（若 P0/P1）：
⭐ [经验标题] (rating X.X, applied N) → [关键教训]

**文档来源**：
📄 [文档名] → [贡献内容]

**确定性**: 高/中/低
**盲区**: [知识库暂无 XX 内容 / 主要参考 XX 机组数据]

### 检索路径
Catalog(KB判断) → DocCatalog(doc判断) → 经验(strict) → 向量确认 → 内容验证
```

---

## 工具选择优先级

| 阶段 | 首选 | 备注 |
|------|------|------|
| KB 概览 | `kb_catalog` | 轻量，agentic 判断 |
| KB 内 doc 概览 | `kb_doc_catalog` | 轻量，agentic 判断 |
| 全库结构 | `fs_catalog_all` | 扁平轻量 |
| 已知场景经验 | `experience_find_by_scenario` | 精确最强 |
| 语义查经验 | `experience_search_vector` | 严格 0.55 |
| 跨库经验 | `experience_search_global` | 向量跨库 |
| 文档精排 | `kb_search_two_stage` | 在候选内确认 |
| 读内容验证 | `kb_doc_read` | 必做验证 |
| 元信息兜底 | `kb_search` | 仅 name+desc，找文件名用 |
| **避免**：跳过 Catalog 直接向量 | — | 违背 agentic 优先原则 |

---

## CRITICAL RULES

1. **Agent 判断先行**——任何时候都先读 description 判断，不直接调向量 top-k。跳过=降级，必须注释原因。
2. **轻量 catalog 优先**——`kb_catalog` / `kb_doc_catalog` 不污染 context；只在确认候选后用 `kb_get_documents` / `kb_doc_read` 取详情。
3. **内容验证必做**——候选 doc 必须 `kb_doc_read` 验证内容真满足场景，否则丢弃。
4. **经验严格**——经验检索严格 0.55 阈值，灰区抑制，**宁可不给也不要错给**。
5. **经验优先**——操作/故障类问题，经验在文档前呈现（经验给"怎么做"，文档给"为什么"）。
6. **诚实标注空洞**——知识库无相关内容时坦率告知，不硬凑。
7. **向量是辅助**——向量用于在 Agent 已确认的候选内精排/确认，不作为唯一相关性判据。
