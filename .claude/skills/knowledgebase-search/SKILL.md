---
name: knowledgebase-search
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
2. **分层扫描（Hierarchical KB Awareness）**：优先扫描子 KB 的精确 description，再逐步上溯到父KB。子 KB 描述比父 KB 更聚焦子领域，Agent 更容易判断精确匹配。
3. **轻量优先**：检索初期用 catalog 工具（仅 id+description），不加载 file_size/tags/vector_index 等污染 context。
4. **内容验证**：候选确认后必须 `kb_doc_read` 读真实内容片段，验证真满足场景。不满足就丢弃。
5. **经验优先 + 严格**：操作/故障类问题先查经验；经验严格相关度（≥0.55），灰区抑制，**宁可不给也不要错给**。
6. **诚实标注盲区**：知识库没有就坦率说，不硬凑。

---

## 自适应深度

| 深度 | 典型场景 | 流程 |
|------|---------|------|
| **L1 浅层** | 事实性快速查找（1-2 KB） | 分层 Catalog 判断 → 读内容 → 答 |
| **L2 标准** | 知识问答（2-3 KB） | 分层 Catalog → Doc Catalog → 向量确认 → 内容验证 → 答 |
| **L3 深度** | 对比/综合分析（3-5 KB） | 完整流程 + 多 KB 交叉 + 跨库升级 |
| **L4 探索** | 跨域探索 | 全库 catalog + 经验 global + 企业级 3 路召回 |

---

## 完整检索流程（7 步，分层 KB 感知）

### Step 0 — 意图识别

读懂用户问题，分类：
- **操作/故障/排查类**（"怎么处理""以前遇到""排查""诊断"）→ **经验优先路径**
- **知识/原理/对比类**（"什么是""原理""对比""方法"）→ **文档优先路径**
- **混合** → 经验优先 + 文档补充

**识别子领域关键词**：如"磨煤机故障预警" → 父域=Energy/Power，子域=coal-mill-fault-prediction。

### Step 1 — 分层 KB Catalog 扫描（子 KB 优先）📍 起点

> 这是分层 KB 设计的核心优势：子 KB 的 description 比父 KB **精确 10 倍**。

```
kb_catalog()  →  [{kb_id, name, description, doc_count}]
fs_get_tree(include_files=False, max_depth=2)  → 了解层级结构（可选）
```

**扫描策略：**

1. **先扫所有 KB，区分父/子**：
   - `kb_catalog()` 返回所有 KB 的扁平列表
   - 通过 `parent_id` 字段不同（如果没有暴露，则从 `name` 的连字符结构推断）
   - **子 KB** 的 name 通常含父前缀（如 `Thermal-Power-Coal-Mill` 可能是子）

2. **子 KB 优先匹配**：
   - 对每个可能与问题相关的 KB，检查 name/description 是否含精确子域关键词
   - **子 KB 命中比父 KB 命中更重要**——子 KB 说"煤磨机故障预警"比父 KB 说"火电"精确得多
   - 先读子 KB description，再读父 KB

3. **Agent 判断维度**：

| 维度 | 判断 |
|------|------|
| description 语义 | KB 描述的领域/设备/场景是否与问题匹配？ |
| 子 KB 级别 | 凡是有子 KB 的父 KB，以子 KB 精确度优先 |
| doc_count | 0 文档的 KB 立刻排除 |
| 语言匹配 | 问题语言与 KB 描述是否一致？ |

**输出候选 KB**（带相关性理由 + ★评级 + 层级标注）：
```
| KB | 层级 | 相关性 | 理由 |
|----|------|--------|------|
| Thermal-Power-Coal-Mill | 子KB | ★★★ | description 含"煤磨机/CNN-LSTM/故障预警"直接匹配 |
| Thermal-Power-Monitoring | 父KB | ★★☆ | description 含"火电"大类匹配，但子KB更精确 |
| Wind-Power-Fault-Diagnostics | 父KB | ★☆☆ | 风电不匹配当前"煤磨机"查询 |
```

### Step 2 — Doc Catalog 扫描（子 KB 内）

对每个候选子 KB（或父 KB 中无子 KB 时）：
```
kb_doc_catalog(kb_id)  →  [{doc_path, name, description}]
```

**Agent 读每篇 doc 的 description 判断**：
- 设备/方法/场景是否一致？
- 如果文档在子 KB 中，子 KB 本身已经做了领域过滤，这一步只需要判断文档粒度

**输出候选 doc**（带评分 + 依据）：
```
| 文档 | Agent评分 | 理由 |
|------|----------|------|
| CNN-LSTM-coal-mill-fault.md | 9/10 | description 明确"煤磨机堵煤/提前315min"双匹配 |
| transformer-oil-DGA.md | 2/10 | 主题是变压器油，非煤磨机 → 丢弃。虽然在同父KB但不同子KB |
```

> **分层优势体现**：如果 KB 组织得好，Step 1 的精确子 KB 命中 + Step 2 的文档筛选，通常能在 Step 3 之前就锁定目标。

### Step 3 — 经验优先检索（仅操作/故障类问题）

对候选 KB（含父 KB 及其子 KB），先查经验：

```
# 子KB已知场景 → 精确（最强）
experience_find_by_scenario(kb_id, scenario)

# 自然语言 → 向量语义（严格阈值 0.55）
experience_search_vector(kb_id, query)

# 跨库 → 全局向量
experience_search_global(query)
```

**经验置信度分层**：
| 层级 | 条件 | 处理 |
|------|------|------|
| **P0 强推** | scenario 精确命中 ∧ vector ≥ 0.65 ∧ rating≥4 | 强烈推荐 |
| **P1 可参考** | vector ≥ 0.55 ∧ rating≥3 | 推荐，标注可信度 |
| **P2 灰区** | 0.45 ≤ vector < 0.55 | **默认抑制**，仅"扩展探索"时呈现 |
| **丢弃** | vector < 0.45 或不同设备/场景 | 不呈现 |

无 P0/P1 → 诚实说"暂无高相关经验"，不拿灰区凑数。

### Step 4 — 向量确认（辅助，在已确认候选内）

对 Step 2 确认的候选文档，用向量精排：

```
# 单 KB 多文档：两阶段（BM25 定位 + 向量精排）
kb_search_two_stage(query, kb_id, stage2_top_k=3)

# 文档无向量索引 → 跳过向量，直接 Step 5 读内容
```

**交叉验证**向量结果与 Agent 评分：
- Step 2 高分 ∧ 向量高分 → P0 优先
- 向量高分但 Step 2 低分 → 怀疑向量误匹配，以 Agent 判断为准或读内容复核

**跨库盲区升级**：如果 `kb_search_two_stage` 跨库候选来自 **<2 个不同 KB** → 自动升级到企业级。

**短文本过滤规则**：
```
if len(chunk_content.strip()) < 50 characters:
    → 降为 P2 灰区（默认不呈现）
    → 除非该 chunk 的 doc_path 已有 P0/P1 候选背书
```
同一篇文档 >50% 的 chunk 为短文本 → 该文档整体降级。

### Step 5 — 子 KB 回溯（备用）

**仅在 Step 2 发现候选文档极少时执行：**

如果当前候选不足，检查父 KB 中其他子 KB 的文档：
```
# 获取所有同父 KB 的子 KB
# 对每个同父子 KB 的文档做快速筛选
```

为什么需要：跨子 KB 的相似主题可能分布在不同的子 KB 中。例如"振动分析"可能出现在 Steam-Turbine-Monitoring 和 Wind-Turbine-Gearbox 两个子 KB 中。这一步在需要横向比较时很关键。

### Step 6 — 内容验证（读真实内容，必做）✅

对最终候选文档，读内容确认真满足场景：
```
kb_doc_read(kb_id, doc_path, max_chars=1200)
```

逐篇判断：
| 维度 | 评分 |
|------|------|
| 主题对齐（与 KB 描述一致？） | 0-3 |
| 场景匹配 | 0-3 |
| 答案潜力 | 0-2 |
| 领域纯度 | -2-0 |

**评分 ≤4 → 丢弃并记录原因。** 只有验证通过的才进答案。

### Step 7 — 综合呈现

```
## 答案
[自然语言组织。经验(可执行)优先 + 文档(原理)支撑]

**层级检索路径**：
子KB识别(catalog层次匹配) → 子KB内doc筛选 → 经验确认(严格) → 向量精排 → 内容验证

**经验参考**（若 P0/P1）：
⭐ [经验标题] (rating X.X) → [关键教训]

**文档来源**：
📄 [子KB > 文档名] → [贡献内容]

**确定性**: 高/中/低
**盲区**: [知识库暂无 XX 内容 / 主要参考 XX 机组数据]
```

---

## 工具选择优先级

| 阶段 | 首选 | 备注 |
|------|------|------|
| 全库概览 | `kb_catalog` | 轻量。区分父/子KB，子KB description 更精确 |
| KB 层级 | `fs_get_tree` | 可选。了解 parent_id 关系 |
| 子KB 概览 | `kb_doc_catalog` | 在子KB内扫描doc |
| 同父跨子KB | `fs_get_children(parent_id)` | 获取同一父下的所有子KB |
| 已知场景经验 | `experience_find_by_scenario` | 精确最强 |
| 语义查经验 | `experience_search_vector` | 严格 0.55 |
| 文档精排 | `kb_search_two_stage` | 在候选内确认 |
| 读内容验证 | `kb_doc_read` | **必做** |
| **避免**：跳过 Catalog 直接向量 | — | 违背 agentic 优先 + 分层 KB 设计 |

---

## CRITICAL RULES

1. **Agent 判断先行**——先读 description 判断，不直接调向量 top-k。
2. **子 KB 优先**——同领域内，子 KB 的精确 description 比父 KB 的宽泛 description 更值得关注。
3. **分层扫描**——先子后父，子 KB 命中即锁定，父 KB 作为兜底。
4. **内容验证必做**——候选文档必须 `kb_doc_read` 验证真满足场景，否则丢弃。
5. **经验严格**——严格 0.55 阈值，宁可不给也不要错给。
6. **诚实标注空洞**——知识库无相关内容时坦率告知，不硬凑。
7. **向量是辅助**——向量用于在 Agent 已确认的候选内精排，不作为唯一相关性判据。
