---
name: knowledgebase-graph
description: >
  Knowledge graph build, query, and analysis for the Neo4j-powered graph
  database. Build graphs per KB or globally, discover cross-KB entity
  bridges, find entity paths, identify central entities, query doc-centric
  graphs, and explore entity neighborhoods. Triggered by: "图谱", "知识图谱",
  "graph", "knowledge graph", "KB graph", "neo4j", "实体关系", "entity",
  "relationship", "build graph", "构建图谱", "cross-KB entities",
  "跨知识库实体", "entity path", "实体路径", "central entities",
  "中心实体", "graph overview", "图谱概览", "图谱构建", "重建图谱",
  "graph for document", "文档图谱", anything referencing Neo4j or graph
  construction.
---

# Knowledge Graph — Build, Query & Analyze

## ⚡ 路由规则

当命中任何图谱触发词时，委托 **Archival** subagent 执行本技能。

**路由 prompt 示例：**
```
Agent(
  subagent_type="archival",
  prompt="[Detected scenario: Graph] <操作详情>"
)
```

**多场景混合作业时**，Graph 操作放在 Ingest/Manage 之后（先确认文档入库，再构建图谱）。

---

## G1 — 构建知识图谱（核心）

### G1a — 构建单 KB 图谱

用 MCP 工具在单 KB 上构建：

```
# 单 KB 构建（增量：跳过已有 graph_index 的文档）
kb_graph_build_kb(kb_id, force=false)

# 单 KB 构建（强制重建：清空该 KB 的图谱节点再重建）
kb_graph_build_kb(kb_id, force=true)
```

**MCP 工具不存在时**（MCP server 未热重载）直接调用后端 API：
```
POST /api/v1/graph/build-kb  {"kb_id": "...", "force": false}
```

### G1b — 全库批量构建

```
# 增量构建（推荐，跳过已有 graph_index 的文档）
kb_graph_build_all(force=false)

# 强制重建（清空全部图谱再重建）
kb_graph_build_all(force=true)
```

**MCP 工具不存在时：**
```
POST /api/v1/graph/build-all  {"force": false}
```

### G1c — 单文档索引（向量+图谱）

```
POST /api/v1/search/index-document
{"kb_id": "...", "doc_path": "...", "doc_name": "...", "description": "..."}
```
或 MCP `kb_index_document` 工具（已有，会同时构建向量+图谱）。

---

## G2 — 查询知识图谱

### G2a — 文档图谱视图（按文档查图谱）

查看一个文档的实体、实体间共现关系、以及该文档实体在其他文档中的出现：

```
# MCP 工具
kb_graph_document(doc_path, limit=50)

# 直接 API
GET /api/v1/graph/document?doc_path=...&limit=50
```

**返回结构：**
```
{
  entities: [{name, type, mentions, source_kbs, doc_freq}],
  relations: [{head, tail, relation, weight}],
  cross_doc_links: [{entity, other_doc, other_kb}],
  entity_count, relation_count, cross_doc_count
}
```

### G2b — KB 图谱概览

```
kb_graph_kb_overview(kb_id)
GET /api/v1/graph/kb-overview?kb_id=...
```

**返回结构：**
```
{
  docs: [{gid, name, entity_count, mentions}],
  top_entities: [{name, type, doc_freq, mentions}],
  cross_kb_bridges: [{name, type, source_kbs, mentions}],
  doc_count, entity_count
}
```

### G2c — 实体搜索与邻居

```
kb_graph_search(keyword, limit=20)
GET /api/v1/graph/search?keyword=...&limit=20

kb_graph_neighbors(entity_name, depth=1)
GET /api/v1/graph/neighbors?entity_name=...&depth=...
```

### G2d — 统计与健康

```
kb_graph_stats()
GET /api/v1/graph/stats

kb_graph_health()  → 检查 Neo4j 是否可用
GET /api/v1/graph/health
```

---

## G3 — 跨 KB 分析

### G3a — 跨 KB 桥梁实体

发现连接多个知识库的实体：同一实体出现在多个 KB 的文档中。

```
kb_graph_cross_kb_entities(min_kbs=2, limit=50)
GET /api/v1/graph/cross-kb-entities?min_kbs=2&limit=50
```

**Agent 解读：** 桥梁实体是跨 KB 连接的骨干。
- 例："华北电力大学"出现在 Thermal-Power-Monitoring + Wind-Power-Fault-Diagnostics → 这两个 KB 研究电力系统
- 通过桥梁实体可发现隐藏的领域关联

### G3b — 实体路径

发现两个实体之间如何通过共现关系链相连：

```
kb_graph_entity_paths(entity_a, entity_b, max_depth=4)
GET /api/v1/graph/entity-paths?entity_a=...&entity_b=...&max_depth=4
```

**用于：** 探索知识图谱中实体间的间接关系。

---

## G4 — 中心度分析

### G4a — KB 内中心实体

找出一个 KB 中出现文档最多的实体（文档连接数排序）：

```
kb_graph_central_entities(kb_id, top_n=20)
GET /api/v1/graph/central-entities?kb_id=...&top_n=20
```

**用于：** 理解 KB 的核心主题——中心实体通常是该 KB 的主要话题。

### G4b — 图谱统计

```
GET /api/v1/graph/stats
→ {node_count, edge_count, doc_count, kb_count, type_distribution}
```

---

## G5 — 图谱清理

### G5a — 单文档清理

删除某文档的图谱数据（共享实体保留，只移除该文档贡献）：

```
# MCP 工具（若可用）
kb_graph_delete_document(doc_path)

# 直接 API
DELETE /api/v1/graph/document?doc_path=...
```

### G5b — KB 级清理

删除整个 KB 的图谱数据（跨 KB 共享实体保留，仅移除该 KB 贡献）：

```
kb_graph_delete_kb(kb_id)
DELETE /api/v1/graph/kb/{kb_id}
```

---

## Agent 判断指引

### 在检索流程中使用图谱

在 `knowledgebase-search` 的 Step 2.5（Catalog 后，向量确认前）插入图谱查询：

```
# 如果检索的问题包含命名实体（人名/组织/地点）：
q_entities = NER(query)  ← 调 knowledgebase-search 已有的 NER
if q_entities:
    for ent in q_entities:
        kb_graph_search(ent.text)     → 寻找匹配实体
        kb_graph_documents_by_entity  → 找到含该实体的文档（潜在候选）
```

### 在 Organize 中使用图谱

```
# O2 阶段检查 KB 的图谱覆盖率：
kb_graph_kb_overview(kb_id)
→ 实体数量少表示文档多为英文（中文 NER 看不到英文实体）
  → 或文档内容薄弱
```

### 在 Verify 中使用图谱

```
# V2 检查每个文档是否有 graph_index
for each document:
    check doc has graph_index field
    if missing: note as graph not built
```

---

## ⚠️ 注意事项

1. **MCP 工具可用性**：MCP server 是长驻进程，新增的 `kb_graph_*` 工具需重启 MCP server 方可调用。
   在 MCP 工具不可用时，直接调后端 API（`POST /api/v1/graph/...`）。
2. **英文文档**：知识图谱自动按语言选择 NER 模型——中文用 `ckiplab/bert-base-chinese-ner`（BIOES），
   英文用 `dslim/bert-base-NER`（BIO, PER/ORG/LOC/MISC）。英文实体也可被图谱检索到。
3. **增量 vs 强制**：`force=false` 跳过已索引文档（快）；`force=true` 清空重建（慢但彻底）。
4. **graph_index**：构建完成后自动写回 `.knowledge-base.yml`（与 vector_index 对称），无需手动写入。
5. **跨 KB 桥接**：实体跨 KB 合并通过 Neo4j MERGE (name, type) 自动实现，`kb_graph_cross_kb_entities` 可发现。
