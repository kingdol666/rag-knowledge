---
name: knowledgebase-graph
description: Knowledge graph build, query, and analysis for Neo4j-powered document relationship graph. Based on document metadata (tags, KB membership). Build per KB or globally, query (KB overview, document-centric, cross-KB discovery, keyword search, neighborhood exploration), cleanup (delete document/KB nodes). Triggered by: 图谱, 知识图谱, graph, knowledge graph, neo4j, 实体关系, entity, relationship, build graph, 构建图谱, cross-KB, 跨知识库, document path, 文档路径, central document, 核心文档.
---

# Knowledge Graph — Build, Query, Analyze

**⭐ MCP 优先原则（强制）**：所有 kb-mcp 操作必须通过 MCP 工具执行（`mcp__kb-mcp__*`）。禁止用 `curl`/`python -c`/`wget` 等终端命令或直调 HTTP API。MCP 不可用时才可向用户报告。

**执行者：此技能由 Archival agent 执行**
- 当 knowledgebase 调度器检测到对应场景后 → 路由到本 skill
- 本 skill **必须**委托 Archival agent（`Agent(subagent_type="archival", ...)`）执行

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
    │   → 文档: kb_graph_search(keyword, limit=20)
    │   → KB:   kb_graph_search_kbs(keyword, limit=20)
    │   → 标签: kb_graph_search_tags(keyword, limit=20)
    │
    ├── "图谱健康/统计"
    │   → kb_graph_health() — Neo4j 是否可用
    │   → kb_graph_stats() — 节点/边计数
    │
    ├── "重建图谱"
    │   → 单KB: kb_graph_build_kb(kb_id, force=true)
    │   → 全库: kb_graph_build_all(force=true)
    │
    └── "清理图谱/删节点"
        → kb_graph_delete_document(doc_path) — 单文档
        → kb_graph_delete_kb(kb_id) — 整个 KB
```

---

## Build

```
kb_graph_build_kb(kb_id, force=false)    # 单KB（增量）
kb_graph_build_all(force=false)          # 全库
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

## Document-Centric Query
| Task | Tool |
|---|---|
| Full graph of a doc | `kb_graph_document(doc_path, limit=50)` |
| Related docs only | `kb_graph_document_related(doc_path, limit=20)` |
| Docs by tag | `kb_graph_documents_by_tag(tag_name, limit=50)` |
| Neighborhood exploration | `kb_graph_neighbors(node_id, node_type, depth=1)` |

## Cross-KB Discovery
```
kb_graph_cross_kb_documents(min_kbs=2, limit=50)   # bridge docs
kb_graph_central_documents(kb_id, top_n=20)          # most connected docs
kb_graph_document_paths(doc_a, doc_b, max_depth=4)   # path between two docs
```

## Keyword Search
```
kb_graph_search(keyword, limit=20)        # document nodes
kb_graph_search_kbs(keyword, limit=20)    # KB nodes
kb_graph_search_tags(keyword, limit=20)   # tag nodes
```

## Cleanup
```
kb_graph_delete_document(doc_path)   # remove single doc node + edges
kb_graph_delete_kb(kb_id)            # remove entire KB from graph
```
Use after deleting documents or KBs to keep graph clean.

## After Document Move
1. `kb_graph_delete_document(doc_path=old_path)` — remove stale node
2. `kb_graph_build_kb(kb_id=target, force=false)` — incremental add to new KB

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 不构建图谱就直接查 | 空结果误解 | 先 `kb_graph_health()` 确认可用再查 |
| `force=false` 当 full rebuild | 仅增量，新 schema 不改旧数据 | Schema 变更后必须 `force=true` |
| 删文档不删图节点 | 孤立节点污染结果 | 删文档后必须 `kb_graph_delete_document()` |
| 误读 `total_relations=0` | stats bug，实际有数据 | `kb_graph_document()` 抽检验证 |
| 用 `kb_graph_build_all` 频繁跑 | 重，消耗 Neo4j 资源 | 仅批量清理后使用，日常用 `kb_graph_build_kb` 单 KB |

See [graph-tools.md](references/graph-tools.md) for full tool parameter reference.
