# MCP Graph Tools Reference

14 `kb_graph_*` MCP tools organized by category. All tools are available on the `kb-mcp` server and callable directly via MCP -- no raw API calls needed.

---

## Query (7 tools)

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `kb_graph_search` | `keyword`, `node_type="all"`, `limit=20` | Unified graph node search. `node_type`: `"all"` (default — merges document+kb+tag results), `"document"`, `"kb"`, or `"tag"` |
| `kb_graph_document` | `doc_path`, `limit=50` | Full graph view of a document: its tags, related documents, and cross-KB connections |
| `kb_graph_document_related` | `doc_path`, `limit=20` | Related documents for a given document (by shared tags, same KB, vector similarity) |
| `kb_graph_documents_by_tag` | `tag_name`, `limit=50` | Find all documents tagged with a specific tag |
| `kb_graph_kb_overview` | `kb_id` | KB-level graph overview: doc count, sub-KBs, tag distribution, related KBs, top documents by centrality |
| `kb_graph_neighbors` | `node_id`, `node_type`, `depth=1` | Get neighbor subgraph around a document, KB, or tag node |
| `kb_graph_cross_kb_documents` | `min_kbs=2`, `limit=50` | Discover bridge documents connected to multiple KBs via shared tags |

---

## Stats (2 tools)

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `kb_graph_stats` | _(none)_ | Global graph statistics: node count, edge count, relationship type distribution |
| `kb_graph_health` | _(none)_ | Check whether the Neo4j database is available and responsive |

---

## Path Analysis (2 tools)

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `kb_graph_central_documents` | `kb_id`, `top_n=20` | Identify the most connected documents in a KB (sorted by `RELATED_TO` edge count) |
| `kb_graph_document_paths` | `doc_a`, `doc_b`, `max_depth=4` | Find the connection chain between two documents through the graph |

---

## Build (1 tool)

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `kb_graph_build` | `kb_id=""`, `force=false` | Build/rebuild graph. Empty `kb_id` = all KBs; specific `kb_id` = single KB (incremental when `force=false`, full rebuild when `force=true`) |

---

## Cleanup (2 tools)

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `kb_graph_delete_document` | `doc_path` | Remove a single document node and its relationships from the graph |
| `kb_graph_delete_kb` | `kb_id` | Remove all nodes and relationships belonging to a KB |

---

## Notes

- **Graph v4 metadata model**: nodes are `Document` (keyed by `graph_doc_id = "doc::path/to/doc.md"`), `KnowledgeBase` (keyed by `kb_id`), and `Tag` (keyed by `name`). Edges are `BELONGS_TO`, `HAS_SUBKB`, `HAS_TAG`, and `RELATED_TO`.
- **Automatic relationships**: three paths establish `RELATED_TO` edges -- shared tags (`shared_tag`), vector similarity (`vector_similar`, weight = cosine similarity), and agent judgment (`continuation`/`implementation`, weight 1.0-1.5).
- **Incremental vs force**: `force=false` skips already-indexed documents (fast); `force=true` clears and rebuilds (slow but thorough -- use after schema upgrades).
- **No NER parsing**: the v4 graph builds relationships from document **metadata** (tags, KB membership), not content entity extraction.
- **Graph index is written back** to `.knowledge-base.yml` automatically after build (symmetric with `vector_index`).
- **After moving documents**: delete the document graph node (`kb_graph_delete_document`) and rebuild the KB (`kb_graph_build(kb_id=...)`) for incremental update.
- **Unified search/build**: `kb_graph_search` merges the former `kb_graph_search`/`_kbs`/`_tags` trio via `node_type`; `kb_graph_build` merges the former `kb_graph_build_kb`/`_all` pair via optional `kb_id`.
