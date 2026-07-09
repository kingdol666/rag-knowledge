---
name: knowledgebase-graph
description: Knowledge graph build, query, and analysis for the Neo4j-powered document relationship graph. Based on document metadata (tags, KB membership) not NER entity extraction. Build graphs per KB or globally, discover cross-KB document bridges, find document paths, identify central documents, explore graph neighborhoods. Triggered by: 图谱, 知识图谱, graph, knowledge graph, KB graph, neo4j, 实体关系, entity, relationship, build graph, 构建图谱, cross-KB, 跨知识库, document path, 文档路径, central document, 核心文档, graph overview, 图谱概览, 图谱构建, 重建图谱, graph for document, 文档图谱, anything referencing Neo4j or graph construction.
---

# Knowledge Graph — Build, Query, Analyze

Graph nodes: `Document`, `KnowledgeBase`, `Tag`. Edges: `BELONGS_TO`, `HAS_SUBKB`, `HAS_TAG`, `RELATED_TO`.

## Build
```
kb_graph_build_kb(kb_id, force=false)    # single KB (incremental)
kb_graph_build_all(force=false)          # all KBs
```
- `force=false`: skip already-indexed docs (fast)
- `force=true`: full rebuild (use after schema changes or cleanup)

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

See [graph-tools.md](references/graph-tools.md) for full tool parameter reference.
