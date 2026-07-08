---
name: knowledgebase-search-enterprise
description: >
  企业级多策略内容优先检索。从 knowledgebase-search 自动升级：
  标签锚定+描述智能+BM25 三道门产出候选 <3 篇，或来自 <2 个 KB，
  或用户明确要求 "全库搜索" / "全面"。
  并行 3 路（标签扩展 + BM25 + 向量）召回，交叉验证去重，
  短内容过滤，内容重排，融合呈现。
  Triggered by: 全库搜索, 所有KB, 跨知识库, 跨库, 联表, 宏观,
  cross-KB, all KBs, enterprise search, 全局搜索, 全面的, thorough search, comprehensive.
---

# Enterprise Content-First Multi-Strategy Retrieval

## 触发条件

从 `knowledgebase-search` 自动升级，当以下任一满足：
- 标签+描述+BM25 三道门合计候选 <3 篇
- 确认的 P0/P1 文档来自 <2 个 KB（跨库盲区）
- 用户明确要求 "全库搜索" / "全面" / "所有知识库"

## 核心原则

与 `knowledgebase-search` 一致：**内容是唯一真相**。
向量仅作为 3 条召回路径之一，最终仍由 Agent 读内容裁决。

## Phase 1 — 并行 3 路召回 (同时发起)

### Path A: 标签扩展 (Agentic)
```
kb_tags_list() → 扩大标签匹配范围（放宽到上位/关联标签）
kb_doc_get_by_tag(tag, kb_id="")  ← 对每个扩展标签跨库搜索
```
比标准搜索的标签匹配更宽松：包含上位概念和关联领域。
例: 标准 → `pva` + `mechanical-properties`
    扩展 → 加上 `polymer` + `film` + `tensile-testing`

### Path B: BM25 关键词 (精确匹配)
```
kb_search_two_stage(query, kb_id="", stage1_top_k=20, stage2_top_k=0)
```
只取 Stage 1 BM25 结果，跳过向量阶段。

### Path C: 向量语义 (纯语义)
```
kb_search_vector(query, kb_id="", top_k=5)
```
纯向量跨库搜索。注意：结果仅作候选，不直接采纳。

## Phase 2 — 交叉验证 + 去重

合并 3 路结果，按 doc_path 去重，记录每篇文档的命中路径:

| 命中模式 | 置信度 | 层级 |
|----------|:---:|------|
| A+B+C 三路命中 | ★★★★★ | P0 候选 |
| B+C 两路命中 | ★★★★ | P0 候选 |
| A+B 两路命中 | ★★★★ | P0 候选 |
| A+C 两路命中 | ★★★ | P1 候选 |
| A 仅标签 | ★★ | P1 候选 (需内容验证) |
| B 仅 BM25 | ★★ | P1 候选 (需内容验证) |
| C 仅向量 | ★ | P2 候选 (严格验证) |

## Phase 3 — 短内容过滤

对去重后的候选，检查 BM25/向量返回的 chunk 内容:
- chunk <50 字符 → 标记 `short_content_warning`，降级到 P2
- 某文档 >50% 的命中 chunk 是短内容 → 整篇文档降级一档
- **例外**: 如果同一文档有其他 P0/P1 命中，短内容 chunk 不影响该文档层级

## Phase 4 — 内容裁决 (核心步骤，与标准搜索一致)

对全部候选（去重后 ≤12 篇），逐篇读真实内容:

```
kb_doc_read(kb_id, doc_path, max_chars=3000)
```

**Agent 内容评分 (0-8)**:

| 维度 | 分值 | 标准 |
|------|:---:|------|
| 主题相关性 | 0-3 | 内容是否关于查询主题 |
| 场景匹配度 | 0-3 | 内容是否直接回答查询问题 |
| 答案潜力 | 0-2 | 是否包含可用数据/方法/结论 |

| 总分 | 判定 | 动作 |
|:---:|------|------|
| 6-8 | 确认 | P0 — 直接用于答案 |
| 5 | 可用 | P1 — 补充信息 |
| ≤4 | 丢弃 | 不呈现 |

**内容裁决规则**:
1. 向量 score 0.9 但内容不回答问题 → **丢弃** (向量不可靠)
2. BM25 score 高但内容跑题 → **丢弃** (关键词巧合)
3. 标签命中但内容与标签不符 → **丢弃** (标签不准)
4. 短内容 (<200 字符) → 降一档
5. **Agent 最终判断优先于任何分数** — 人类阅读理解 > 余弦距离

## Phase 5 — 图谱扩展 (可选，当确认 P0 文档 <3 篇)

```
# 对已确认的 P0 文档，查图谱关联
kb_graph_document_related(doc_path)  ← 发现关联文档
kb_graph_central_documents(kb_id)    ← 找核心/综述文档
kb_graph_cross_kb_documents(min_kbs=2) ← 跨库桥接文档
```

图谱新发现的文档 → 进入 Phase 4 内容裁决（不跳过）。

## Phase 6 — 融合呈现

```
## 全库检索结果

### 检索路径
查询: "{user_query}"
3 路并行: 标签扩展({a}篇) + BM25({b}篇) + 向量({c}篇)
去重后: {total} 篇候选
内容裁决: {k0} 篇 P0, {k1} 篇 P1, {k2} 篇丢弃

### 答案
{基于 P0/P1 文档内容综合的回答}

### 来源文档 (按置信度排序)
1. **[{doc_name}]** (P0, 三路命中) — {相关性说明}
   路径: {doc_path} | KB: {kb_name}
   内容要点: {关键信息}
2. **[{doc_name}]** (P1, BM25+向量) — {相关性说明}
   ...

### 置信度
{High/Medium/Low} — {原因}

### 盲区
{知识库未覆盖的方面}
```
