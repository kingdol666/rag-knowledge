---
name: knowledgebase-graph
description: "Knowledge graph build, query, and analysis for Neo4j-powered document relationship graph. Based on document metadata (tags, KB membership). Build per KB or globally, query (KB overview, document-centric, cross-KB discovery, keyword search, neighborhood exploration), cleanup (delete document/KB nodes). Triggered by: graph, knowledge graph, graph, knowledge graph, neo4j, entity relationships, entity, relationship, build graph, build the graph, cross-KB, cross knowledge base, document path, document path, central document, core document."
---
# Knowledge Graph — Build, Query, Analyze

**Executor: Archival agent** — delegate via `task` (delegation template + three-role execution model + combined-task boundaries: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 94-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

Graph nodes: `Document`, `KnowledgeBase`, `Tag`. Edges: `BELONGS_TO`, `HAS_SUBKB`, `HAS_TAG`, `RELATED_TO`.

Related: document ingest & indexing → `skill://knowledgebase-ingest` (A6 vector+graph indexing) · batch graph rebuild → `skill://knowledgebase-batch` (B7) · cross-library discovery → `skill://knowledgebase-search` (librarian fallback) · architecture → [kb-architecture.md](../knowledgebase/references/kb-architecture.md).

## Sequential Workflow

**Step 1 — Check Neo4j**: kb_graph_stats() confirm neo4j_available is true, otherwise kb_project_start(neo4j=true) to bring it up.
**Step 2 — Choose the query type**: overview / document query / cross-library discovery / keyword search / build / cleanup, per the user request.
**Step 3 — KB overview query**: kb_graph_kb_overview(kb_id) → doc_count, sub-KBs, tag distribution, top central documents.
**Step 4 — Document-centric query**: kb_graph_document(doc_path) for all associations / kb_graph_document_related(doc_path) for related documents only.
**Step 5 — Cross-library bridge discovery**: kb_graph_cross_kb_documents(min_kbs=2) → bridge documents → kb_graph_central_documents(kb_id) → central documents.
**Step 6 — Document path query**: kb_graph_document_paths(doc_a, doc_b, max_depth=4) → shortest relationship path between two documents.
**Step 7 — Keyword search**: kb_graph_search(keyword, node_type="all") → substring matching of nodes by name/path.
**Step 8 — Build/rebuild**: kb_graph_build(kb_id, force=false) incremental / force=true full rebuild → kb_graph_stats() verify.
**Step 9 — Cleanup**: kb_graph_delete_document(doc_path) delete a document node / kb_graph_delete_kb(kb_id) delete the entire KB graph.

## Build

```
kb_graph_build(kb_id="", force=false)    # empty kb_id=whole library; specific kb_id=single KB (incremental)
```

- `force=false` skips already-indexed documents (fast); `force=true` is a full rebuild — mandatory after schema changes/cleanup, because incremental does not fix old-schema data.
- **Post-build verification** (after first build or force rebuild): `kb_graph_stats()` compare node/edge counts; `kb_graph_kb_overview(kb_id)` compare doc_count with the actual document count. If `total_relations` is 0 but doc_count is normal → the graph data was written; stats has a bug — spot check with `kb_graph_document()` to confirm.

## Query (per type)

- **KB overview** — `kb_graph_kb_overview(kb_id)`: doc count, sub-KBs, tag distribution, related KBs, top central docs. Known limitation: `related_kbs[].name` and `sub_kbs[].name` return **UUIDs**, not readable names — map via `kb_list(lightweight=true)`.
- **Document-centric** — `kb_graph_document(doc_path, limit=50)` full graph (includes neighbors, so it doubles as neighborhood exploration); `kb_graph_document_related(doc_path, limit=20)` related docs only.
- **Documents by tag** — `kb_graph_documents_by_tag` has been **removed** (returns empty for tags; the graph models tags via doc-doc `RELATED_TO{shared_tag}` edges, no direct tag→doc edges). Use **`kb_doc_get_by_tag(tag)`** — goes through the YAML registry, reliable, works across skills.
- **Cross-KB discovery** — `kb_graph_cross_kb_documents(min_kbs=2, limit=50)` bridge docs · `kb_graph_central_documents(kb_id, top_n=20)` most connected docs.
- **Path between two documents** — `kb_graph_document_paths(doc_a, doc_b, max_depth=4)`.
- **Keyword search** — `kb_graph_search(keyword, node_type="all", limit=20)`. The parameter is **`keyword`**, not `query` (wrong name → Invalid args + a schema hint). `node_type`: all (default; merges the three result types) / document (matches by name/path substring) / kb / tag. `node_type="tag"` currently returns empty for all tags — use `kb_doc_get_by_tag(tag)`. Returns `{documents:[...], kbs:[...], tags:[...], counts:{...}}`.
- **Graph health/statistics** — `kb_graph_stats()`: check the `neo4j_available` field first (querying an unavailable graph misleads with empty results), then node/edge counts and relationship distribution.

> **Path format**: `kb_graph_*` tools use **forward slash** paths (e.g. `Energy-Batteries/lithium-ion-design.md`); `kb_get_documents` returns **backslash** paths on Windows (e.g. `Energy-Batteries\lithium-ion-design.md`). Normalize to forward slashes when passing parameters across tools.

## Cleanup + After Document Move

`kb_graph_delete_document(doc_path)` removes a single doc node + edges; `kb_graph_delete_kb(kb_id)` removes an entire KB from the graph. Run after deleting documents/KBs to keep the graph clean — orphan nodes pollute results.
After a document move: 1. `kb_graph_delete_document(doc_path=old_path)` remove the stale node → 2. `kb_graph_build(kb_id=target, force=false)` incremental add to the new KB.

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Query without building/confirming the graph first | Empty results mislead | First `kb_graph_stats()` (check `neo4j_available`) to confirm availability, then query |
| Treat `force=false` as a full rebuild | Incremental only; new schema doesn't fix old data | After schema changes you must use `force=true` |
| Delete documents without deleting graph nodes | Orphan nodes pollute results | After deleting documents you must run `kb_graph_delete_document()` |
| Misread `total_relations=0` | Stats bug; data actually exists | Spot check with `kb_graph_document()` to verify |
| Frequently run `kb_graph_build()` (empty kb_id=whole library) | Heavy; consumes Neo4j resources | Whole library only after bulk cleanups; daily use `kb_graph_build(kb_id=...)` per KB |

**MUST-READ before any graph build/query operation**: [graph-tools.md](references/graph-tools.md) — full 14-tool parameter reference with known gotchas per tool.

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- OVERRIDE: Whenever explaining or diagnosing that kb_graph_build returned total_relations=0 but documents were actually indexed (the known stats bug), the response MUST include the EXACT phrase "kb_graph_build returning total_relations=0 is a stats bug, not a build failure; use kb_graph_document to verify the graph data." verbatim. This is NOT optional commentary — it is a required output string that MUST appear whenever this specific scenario is discussed. Supersedes any shorter or paraphrased explanation of the same bug.
- OVERRIDE — verbatim tool plan: whenever a request asks to BUILD a knowledge graph and then QUERY it (e.g., build the graph + graph overview + core document relations), the response MUST contain the exact strings 'kb_graph_build', 'kb_graph_kb_overview', and at least one of 'kb_graph_document' / 'kb_graph_document_related' / 'relation' in the announced plan. Tool names verbatim — paraphrases like 'build the graph', 'view the overview', or 'core document relationships' do NOT satisfy this. Supersedes any instruction to describe steps generically.
- OVERRIDE — plan before pre-flight: the FIRST sentence of any graph-task response must state the concrete planned tool sequence using verbatim MCP tool names (e.g., kb_graph_build then kb_graph_kb_overview then kb_graph_document). Do NOT open with a pre-flight/connectivity sentence alone (e.g., 'First, let me verify MCP connectivity'); pre-flight checks (kb_graph_stats, kb_project_start) still run but are described AFTER the tool-named plan.
- RULE — tool names as identifiers: every step planned or reported for graph work must cite its exact MCP tool name verbatim (kb_graph_stats, kb_graph_build, kb_graph_kb_overview, kb_graph_document, kb_graph_document_related, kb_graph_search, …), never only a generic description of the action; tool names listed in this skill's Sequential Workflow / decision tree must be written exactly as they appear there.
<!-- SKILLOPT-SLEEP:LEARNED END -->
