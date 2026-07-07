---
name: knowledgebase-graph
description: Knowledge graph build, query, and analysis for the Neo4j-powered document relationship graph. Based on document metadata (tags, KB membership) not NER entity extraction. Build graphs per KB or globally, discover cross-KB document bridges, find document paths, identify central documents, explore graph neighborhoods. Triggered by: "图谱", "知识图谱", "graph", "knowledge graph", "KB graph", "neo4j", "实体关系", "entity", "relationship", "build graph", "构建图谱", "cross-KB", "跨知识库", "document path", "文档路径", "central document", "核心文档", "graph overview", "图谱概览", "图谱构建", "重建图谱", "graph for document", "文档图谱", anything referencing Neo4j or graph construction.
---

# Knowledge Graph — Document Relationship Network (v4)

## Core Concept
Nodes: Document | KnowledgeBase | Tag
Relations: BELONGS_TO | HAS_SUBKB | HAS_TAG | RELATED_TO
Auto-built paths: shared_tag (strongest), vector_similar, agent_judged
No NER — relationship graph based on metadata only.

## G1 — Build
- Single KB: `kb_graph_build_kb(kb_id, force=false)` — incremental; `force=true` — full rebuild
- All KBs: `kb_graph_build_all(force=false)`
- Single doc: auto-triggered on parse/index. Manual: `kb_index_document(kb_id, doc_path)`

See [references/graph-tools.md](references/graph-tools.md) for complete tool signatures.

## G2 — Query

| Task | Tool |
|---|---|
| Doc's graph view (tags + related docs + cross-KB) | `kb_graph_document(doc_path)` |
| Doc's related docs | `kb_graph_document_related(doc_path)` |
| KB overview + tag distribution + top docs | `kb_graph_kb_overview(kb_id)` |
| Cross-KB bridge docs | `kb_graph_cross_kb_documents(min_kbs=2)` |
| Doc-to-doc shortest path | `kb_graph_document_paths(doc_a, doc_b)` |
| KB central documents | `kb_graph_central_documents(kb_id)` |
| Subgraph from node | `kb_graph_neighbors(node_id, node_type, depth)` |
| Search nodes by keyword | `kb_graph_search` / `kb_graph_search_kbs` / `kb_graph_search_tags` |
| Find docs by tag | `kb_graph_documents_by_tag(tag_name)` |

## G3 — Stats & Health
- `kb_graph_stats()` — node/edge counts, relation distribution
- `kb_graph_health()` — Neo4j connectivity check

## G4 — Cleanup
- `kb_graph_delete_document(doc_path)` — remove doc from graph
- `kb_graph_delete_kb(kb_id)` — remove entire KB from graph

## Integration Points
- **Search Step 4.5**: `kb_graph_document_related` to expand candidates, `kb_graph_central_documents` for hub docs
- **Organize O14**: Check `kb_graph_kb_overview` doc_count vs kb_get_documents. If low, `kb_graph_build_kb(kb_id, force=true)`
- **Verify V5**: Include `kb_graph_health` + `kb_graph_stats` in scorecard

## Notes
- Graph build is fast (metadata only, no content reading)
- Incremental (force=false) skips already-indexed docs. Full rebuild (force=true) is thorough.
- After doc move: `kb_graph_delete_document(old_path)` then `kb_graph_build_kb(target_kb, force=false)`
- cross-KB bridges are auto-discovered via shared tags
