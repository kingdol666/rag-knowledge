---
name: knowledgebase-graph
description: >
  Knowledge graph build, query, and analysis for the Neo4j-powered document
  relationship graph. Based on document metadata (tags, KB membership) not NER
  entity extraction. Build graphs per KB or globally, discover cross-KB document
  bridges, find document paths, identify central documents, explore graph
  neighborhoods. Triggered by: "图谱", "知识图谱", "graph", "knowledge graph",
  "KB graph", "neo4j", "实体关系", "entity", "relationship", "build graph",
  "构建图谱", "cross-KB", "跨知识库", "document path", "文档路径",
  "central document", "核心文档", "graph overview", "图谱概览", "图谱构建",
  "重建图谱", "graph for document", "文档图谱", anything referencing Neo4j or
  graph construction.
---

# Knowledge Graph — Document Relationship Graph (v3)

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

## 核心概念变更（v4 — 基于 metadata 的关系图谱）

图谱不再解析文档内容中的命名实体，而是基于文档入库时的**元数据**建立关系。
v4 升级：引入`kb_graph_central_documents`、`kb_graph_neighbors`、`kb_graph_cross_kb_documents`
等新工具，并在检索中集成图谱扩展（search Step 4.5）。

| 节点 | 主键 | 说明 |
|------|------|------|
| `Document` | `graph_doc_id = "doc::path/to/doc.md"` | 文档 |
| `KnowledgeBase` | `kb_id` | 知识库 |
| `Tag` | `name` | 标签 |

| 关系 | 说明 |
|------|------|
| `BELONGS_TO` | 文档所属 KB |
| `HAS_SUBKB` | KB 层级 |
| `HAS_TAG` | 文档/KB 拥有标签 |
| `RELATED_TO` | 文档间/KB间关联（基于同KB/共享标签/向量相似） |

文档间关联自动建立的三条路径：
1. **共享标签** → reason="shared_tag", weight=共享标签数
2. **向量相似** → reason="vector_similar", weight=余弦相似度
3. **Agent 判断** → reason="continuation"/"implementation"等, weight=1.0~1.5

---

## G1 — 构建知识图谱（核心）

### G1a — 构建单 KB 图谱

```
# 单 KB 构建（增量：跳过已有 graph_index 的文档）
kb_graph_build_kb(kb_id, force=false)

# 单 KB 构建（强制重建：清空该 KB 的图谱节点再重建）
kb_graph_build_kb(kb_id, force=true)
```

**MCP 工具不存在时**直接调用后端 API：
```
POST /api/v1/graph/build-kb  {"kb_id": "...", "force": false}
```

### G1b — 全库批量构建

```
# 增量构建（推荐）
kb_graph_build_all(force=false)

# 强制重建
kb_graph_build_all(force=true)
```

### G1c — 单文档索引（向量+图谱联动）

入库/解析时自动触发：
```
# 首选：MCP 工具（向量索引 + 图谱构建同时完成）
kb_index_document(kb_id, doc_path, doc_name="", description="", tags=[])

# 备用：原始 API
POST /api/v1/search/index-document
{"kb_id": "...", "doc_path": "...", "doc_name": "...", "description": "...", "tags": [...]}
```

---

## G2 — 查询知识图谱

### G2a — 文档图谱视图

查看一个文档的标签、关联文档、跨 KB 连接：

```
kb_graph_document(doc_path, limit=50)
```

**返回结构：**
```json
{
  "document": {"graph_doc_id", "path", "name", "kb_id", "description"},
  "tags": ["标签1", "标签2"],
  "related_documents": [{"path", "name", "kb_id", "reason", "weight"}],
  "cross_kb_links": [{"path", "name", "kb_id", "reason", "weight"}]
}
```

### G2b — KB 图谱概览

```
kb_graph_kb_overview(kb_id)
```

**返回结构：**
```json
{
  "doc_count": 10,
  "sub_kbs": [],
  "tag_distribution": [{"tag": "故障诊断", "doc_count": 5}],
  "related_kbs": [{"kb_id": "...", "shared_tags": 3}],
  "top_docs": [{"name": "...", "path": "...", "degree": 5, "total_weight": 10.5}]
}
```

### G2c — 搜索

```
# 搜索文档节点
kb_graph_search(keyword, limit=20)

# 搜索 KB 节点
kb_graph_search_kbs(keyword, limit=20)

# 搜索标签节点
kb_graph_search_tags(keyword, limit=20)
```
```

### G2d — 邻居子图

```
# 文档邻居（展示该文档在图谱中的关联网络）
kb_graph_neighbors(node_id="doc::path/to/doc.md", node_type="document", depth=1)

# KB 邻居
kb_graph_neighbors(node_id="kb-uuid", node_type="kb", depth=1)

# 标签邻居
kb_graph_neighbors(node_id="标签名", node_type="tag", depth=1)
```

### G2e — 按标签查文档 / 查关联文档

```
# 按标签查找文档
kb_graph_documents_by_tag(tag_name="故障诊断", limit=50)

# 查某文档的关联文档
kb_graph_document_related(doc_path="kb/doc.md", limit=20)
```

### G2f — 统计与健康

```
kb_graph_stats()    → 全局统计：节点数、边数、关联类型分布
kb_graph_health()   → 检查 Neo4j 是否可用
```

---

## G3 — 跨 KB 分析

### G3a — 跨 KB 桥梁文档

发现连接多个知识库的文档（通过共享标签关联到多个 KB）：

```
kb_graph_cross_kb_documents(min_kbs=2, limit=50)
GET /api/v1/graph/cross-kb-documents?min_kbs=2&limit=50
```

### G3b — 文档路径

发现两个文档之间如何通过关联链相连：

```
kb_graph_document_paths(doc_a="kb1/doc1.md", doc_b="kb2/doc2.md", max_depth=4)
GET /api/v1/graph/document-paths?doc_a=...&doc_b=...&max_depth=4
```

---

## G4 — 中心度分析

### G4a — KB 内中心文档

找出一个 KB 中关联度最高的文档（按 RELATED_TO 连接数排序）：

```
kb_graph_central_documents(kb_id, top_n=20)
GET /api/v1/graph/central-documents?kb_id=...&top_n=20
```

---

## G5 — 图谱清理

### G5a — 单文档清理

```
# MCP 工具
kb_graph_delete_document(doc_path)

# 直接 API
DELETE /api/v1/graph/document?doc_path=...
```

### G5b — KB 级清理

```
kb_graph_delete_kb(kb_id)
DELETE /api/v1/graph/kb/{kb_id}
```

---

## Agent 判断指引

### 在检索流程中使用图谱

在 `knowledgebase-search` 的 Step 2.5 插入图谱查询：
```
# 查询该 KB 的所有文档在图谱中的关联网络
kb_graph_kb_overview(kb_id)
→ 发现与该文档关联的其他文档（跨 KB 文档可能涉及不同领域）

# 查某文档的关联文档（两阶段检索 Stage 1 扩展）
kb_graph_document_related(doc_path)
→ 共享标签和同 KB 的关联文档作为候选
```

### 在 Organize 中使用图谱

```
# O2 阶段检查 KB 的图谱覆盖率：
kb_graph_kb_overview(kb_id)
→ 关联文档数量少表示文档间缺乏共享标签
→ 建议 O8 标签规范化后用 force=true 重建图谱
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

1. **MCP 工具已全部可用**：17 个 `kb_graph_*` MCP 工具已部署在 kb-mcp server，**不需要重启**即可直接调用。
   优先使用 MCP 工具，原生 API 作为备用。
2. **图谱构建极快**：v4 仅读 `.knowledge-base.yml` 的 metadata（不读文档内容），即使有大量文档也能秒级构建。
3. **增量 vs 强制**：`force=false` 跳过已索引文档（快）；`force=true` 清空重建（慢但彻底，适合 schema 升级后）。
4. **graph_index 写回**：构建完成后自动写回 `.knowledge-base.yml`（与 vector_index 对称），无需手动写入。
5. **跨 KB 关联**：通过共享标签自动建立，`kb_graph_cross_kb_documents` 可发现桥梁文档。
6. **文档移动后需要重建图谱**：`kb_graph_delete_document(old_path)` 再 `kb_graph_build_kb(kb_id, force=false)` 增量更新。
