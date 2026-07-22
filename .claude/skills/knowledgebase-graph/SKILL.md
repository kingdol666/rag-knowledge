---
name: knowledgebase-graph
description: Knowledge graph build, query, and analysis for Neo4j-powered document relationship graph. Based on document metadata (tags, KB membership). Build per KB or globally, query (KB overview, document-centric, cross-KB discovery, keyword search, neighborhood exploration), cleanup (delete document/KB nodes). Triggered by: 图谱, 知识图谱, graph, knowledge graph, neo4j, 实体关系, entity, relationship, build graph, 构建图谱, cross-KB, 跨知识库, document path, 文档路径, central document, 核心文档.
---

# Knowledge Graph — Build, Query, Analyze

**⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型）+ [MCP 优先原则](../knowledgebase/references/skill-trigger-contract.md#第五条mcp-优先原则)（禁止 terminal/HTTP 绕过）

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

Graph nodes: `Document`, `KnowledgeBase`, `Tag`. Edges: `BELONGS_TO`, `HAS_SUBKB`, `HAS_TAG`, `RELATED_TO`.

---

## 思维框架：先想清楚要查什么 ⭐

```
[用户需求] → [查询类型] → [选工具] → [构建/查询/清理]
```

| 用户说 | 本质需求 | 选哪个流 |
|--------|---------|---------|
| "这个KB的图谱怎么样" | 概览 | KB Overview |
| "这篇文档和什么相关" | 文档关系 | Document-Centric |
| "有没有跨库桥梁文档" | 跨库发现 | Cross-KB Discovery |
| "帮我查图谱节点" | 关键词 | Keyword Search |
| "重建图谱" | 构建 | Build |
| "删了文档，图谱不干净" | 清理 | Cleanup |

---

## 查询决策树

```
用户想查什么？
    │
    ├── "这个KB的整体概况"
    │   → kb_graph_kb_overview(kb_id)
    │      （doc_count, sub-KBs, tag distribution, top central docs）
    │
    ├── "这篇文档关联了什么"
    │   → 全部信息: kb_graph_document(doc_path, limit=50)
    │   → 仅相关文档: kb_graph_document_related(doc_path, limit=20)
    │
    ├── "跨KB桥梁文档"
    │   → kb_graph_cross_kb_documents(min_kbs=2, limit=50)
    │
    ├── "核心文档/中心文档"
    │   → kb_graph_central_documents(kb_id, top_n=20)
    │
    ├── "两篇文档之间的路径"
    │   → kb_graph_document_paths(doc_a, doc_b, max_depth=4)
    │
    ├── "按标签查文档"
    │   → kb_graph_documents_by_tag(tag_name, limit=50)
    │
    ├── "关键词搜"
    │   → kb_graph_search(keyword, node_type="all", limit=20)
    │     (node_type: all/document/kb/tag — all 合并三类结果)
    │
    ├── "图谱健康/统计"
    │   → kb_graph_health() — Neo4j 是否可用
    │   → kb_graph_stats() — 节点/边计数
    │
    ├── "重建图谱"
    │   → kb_graph_build(kb_id="", force=true)
    │     (空 kb_id=全库；指定 kb_id=单KB)
    │
    └── "清理图谱/删节点"
        → kb_graph_delete_document(doc_path) — 单文档
        → kb_graph_delete_kb(kb_id) — 整个 KB
```

---

## Build

```
kb_graph_build(kb_id="", force=false)    # 空 kb_id=全库；指定 kb_id=单KB（增量）
```
- `force=false`: 跳过已索引文档（快）
- `force=true`: 完全重建（schema变更/清理后使用）

### 构建后验证
第一次 build 或 force rebuild 后，务必验证：
```
kb_graph_stats()       # 对比 node/edge 数是否合理
kb_graph_kb_overview(kb_id)  # doc_count 是否匹配实际文档数
```
如出现 `total_relations` 为 0 但 doc_count 正常 → 图谱实际已写入，stats 有 bug（用 `kb_graph_document()` 抽检确认）。

---

## Global Stats
```
kb_graph_stats()      # node/edge counts, relationship distribution
kb_graph_health()     # Neo4j availability check
```

## KB Overview
`kb_graph_kb_overview(kb_id)` — doc count, sub-KBs, tag distribution, related KBs, top central docs.

> **已知显示限制**：`related_kbs[].name` 和 `sub_kbs[].name` 返回 **UUID** 而非可读名称。用 `kb_catalog()` 回查 UUID→名称映射。

## Document-Centric Query
| Task | Tool |
|---|---|
| Full graph of a doc | `kb_graph_document(doc_path, limit=50)` |
| Related docs only | `kb_graph_document_related(doc_path, limit=20)` |
| Docs by tag | `kb_graph_documents_by_tag(tag_name, limit=50)` |
| Neighborhood exploration | `kb_graph_neighbors(node_id, node_type, depth=1)` |

> **路径格式**：`kb_graph_*` 工具用**正斜杠**路径（如 `Energy-Batteries/lithium-ion-design.md`）。`kb_get_documents` 在 Windows 返回**反斜杠**路径（如 `Energy-Batteries\lithium-ion-design.md`）。跨工具传参时统一转正斜杠。

## Cross-KB Discovery
```
kb_graph_cross_kb_documents(min_kbs=2, limit=50)   # bridge docs
kb_graph_central_documents(kb_id, top_n=20)          # most connected docs
kb_graph_document_paths(doc_a, doc_b, max_depth=4)   # path between two docs
```

## Keyword Search
```
kb_graph_search(keyword, node_type="all", limit=20)
# node_type: "all"（默认，合并 document+kb+tag 三类结果）/ "document" / "kb" / "tag"
# Returns: {documents:[...], kbs:[...], tags:[...], counts:{documents, kbs, tags}}
```
- `node_type="all"` returns all three node types in one call (documents/kbs/tags arrays).
- For precision, use a specific `node_type` ("document"/"kb"/"tag") to get only that type.

## Cleanup
```
kb_graph_delete_document(doc_path)   # remove single doc node + edges
kb_graph_delete_kb(kb_id)            # remove entire KB from graph
```
Use after deleting documents or KBs to keep graph clean.

## After Document Move
1. `kb_graph_delete_document(doc_path=old_path)` — remove stale node
2. `kb_graph_build(kb_id=target, force=false)` — incremental add to new KB

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 不构建图谱就直接查 | 空结果误解 | 先 `kb_graph_health()` 确认可用再查 |
| `force=false` 当 full rebuild | 仅增量，新 schema 不改旧数据 | Schema 变更后必须 `force=true` |
| 删文档不删图节点 | 孤立节点污染结果 | 删文档后必须 `kb_graph_delete_document()` |
| 误读 `total_relations=0` | stats bug，实际有数据 | `kb_graph_document()` 抽检验证 |
| 用 `kb_graph_build()`（空 kb_id=全库）频繁跑 | 重，消耗 Neo4j 资源 | 仅批量清理后用全库；日常用 `kb_graph_build(kb_id=...)` 单 KB |

See [graph-tools.md](references/graph-tools.md) for full tool parameter reference.
