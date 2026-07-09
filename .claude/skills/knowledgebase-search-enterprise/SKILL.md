---
name: knowledgebase-search-enterprise
description: >
  企业级多策略向量优先检索。从 knowledgebase-search 自动升级：
  向量+标签+描述三道门产出确认 P0/P1 文档来自 <2 个 KB，
  或用户明确要求 "全库搜索" / "全面"。
  并行 3 路（向量 + 标签扩展 + BM25）召回，交叉验证去重，
  内容裁决，融合呈现。
  Triggered by: 全库搜索, 所有KB, 跨知识库, 跨库, 联表, 宏观,
  cross-KB, all KBs, enterprise search, 全局搜索, 全面的, thorough search, comprehensive.
---

# Enterprise Vector-First Multi-Strategy Retrieval

## 触发条件

从 `knowledgebase-search` 自动升级，当以下任一满足：
- 确认的 P0/P1 文档来自 <2 个 KB（跨库盲区）
- 向量+标签+描述三道门合计确认 <2 篇
- 用户明确要求 "全库搜索" / "全面" / "所有知识库"

## 核心原则

与 `knowledgebase-search` 一致：**向量负责快，内容负责准**。
多路并行召回，内容统一裁决。

## Phase 1 — 并行 3 路召回 (同时发起)

### Path A: 向量扩展 (扩大召回范围)
```
# 放宽 top_k，增加召回量
kb_search_two_stage(query, kb_id="", stage1_top_k=30, stage2_top_k=10)
```

### Path B: 标签扩展 (Agentic)
```
kb_tags_list() → 扩大标签匹配范围（放宽到上位/关联标签）
kb_doc_get_by_tag(tag, kb_id="")  ← 对每个扩展标签跨库搜索
```
比标准搜索的标签匹配更宽松：包含上位概念和关联领域。

### Path C: BM25 纯关键词
```
# 只取 BM25 结果
kb_search_two_stage(query, kb_id="", stage1_top_k=25, stage2_top_k=0)
```

## Phase 2 — 交叉验证 + 去重

合并 3 路结果，按 doc_path 去重，记录每篇文档的命中路径:

| 命中模式 | 置信度 | 层级 |
|----------|:---:|------|
| A+B+C 三路命中 | ★★★★★ | P0 候选 |
| A+B 两路命中 | ★★★★ | P0 候选 |
| B+C 两路命中 | ★★★★ | P0 候选 |
| A+C 两路命中 | ★★★ | P1 候选 |
| A 仅向量 | ★★ | P1 候选 (需内容验证) |
| B 仅标签 | ★★ | P1 候选 (需内容验证) |
| C 仅 BM25 | ★ | P2 候选 (严格验证) |

## Phase 3 — 内容裁决 (核心步骤)

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
1. 向量 score 0.9 但内容不回答问题 → **丢弃**
2. BM25 score 高但内容跑题 → **丢弃**
3. 标签命中但内容与标签不符 → **丢弃**
4. 短内容 (<200 字符) → 降一档
5. **Agent 最终判断优先于任何分数**

## Phase 4 — 图谱扩展 (可选，当确认 P0 <3 篇)

```
kb_graph_document_related(doc_path)  ← 发现关联文档
kb_graph_central_documents(kb_id)    ← 找核心/综述文档
kb_graph_cross_kb_documents(min_kbs=2) ← 跨库桥接文档
```

图谱新发现的文档 → 进入 Phase 3 内容裁决（不跳过）。

## Phase 5 — 融合呈现

```
## 全库检索结果

### 检索路径
查询: "{user_query}"
3 路并行: 向量扩展({a}篇) + 标签扩展({b}篇) + BM25({c}篇)
去重后: {total} 篇候选
内容裁决: {k0} 篇 P0, {k1} 篇 P1, {k2} 篇丢弃

### 答案
{基于 P0/P1 文档内容综合的回答}

### 来源文档 (按置信度排序)
1. **[{doc_name}]** (P0, 三路命中, 内容score={score}) — {相关性说明}
   路径: {doc_path} | KB: {kb_name}
   内容要点: {关键信息}
2. ...

### 置信度
{High/Medium/Low} — {原因}

### 盲区
{知识库未覆盖的方面}
```
