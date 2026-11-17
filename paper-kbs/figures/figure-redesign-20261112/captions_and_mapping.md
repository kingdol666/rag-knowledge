# Figure A — HMRS system design overview

**Caption draft:** HMRS separates three management objects from the services that operate on them. Collections, documents and segments are maintained over shared files, registries, search indices and a navigation graph. Browser/Web and Agent/CLI entry points reach the Nuxt/MCP/FastAPI boundaries; the catalogue-first path is optional and narrows from collection descriptions to a scored segment. Graph state supports navigation, not evidence; indexing, graph build and Laya judging are separate or optional operations.

**Source mapping:** `web/server/services/tree-file-system-service.ts` (disk/tree/YAML state); `backend/app/services/vector_service.py` (Chroma/BGE-M3); `backend/app/services/keyword_index_service.py` (BM25); `backend/app/services/graph_service.py` (Neo4j KB/document/tag navigation); `web/server/services/kb-search-service.ts` (catalogue/document reads); `backend/app/api/routes/search.py` and `graph.py` (search/index/graph APIs); `kb-mcp/server.py` (MCP orchestration).

# Figure B — HMRS ingest-to-evidence lifecycle

**Caption draft:** The workflow distinguishes knowledge creation from question answering. Source files are parsed and checked, structurally split and enriched, routed by an agent using parsed content, saved to files and registries, and indexed or probed according to the entry point. A query selects a pinned or all-library workflow, gathers catalogue/BM25/vector/graph candidates, and may invoke the Laya judge. The terminal states separate supported evidence, a completed scoped search without support, and an execution failure; a threshold score is not proof of support.

**Source mapping:** `backend/app/api/routes/parse.py` and `kb-mcp/server.py` parse/task registry; `web/server/api/parse/save-parsed-files.post.ts` save-only behavior; `web/server/api/kb/documents/create.post.ts` structure-aware split; `backend/app/services/two_stage_search_service.py` BM25/graph expansion/candidate-scoped vector stage; `kb-mcp/server.py` optional post-save indexing and Laya/graph tools; `web/server/api/kb/agent/chat.post.ts` external agent surface.

# Figure C — Latest content-layer results

**Caption draft:** Frozen 11 November content-layer results on 72 gold questions. Points show gold-string containment with Wilson 95% intervals; direct labels give the exact hit count. A0h reaches 52/72, compared with 37/72 for A0 and 46/72 for precise per-document PD. The A0h–PD difference is directional but not significant (7:1, exact McNemar p=0.0703). Auxiliary panels show mean tool calls and trace-recorded text volume per question; trace bytes may overlap and are not model-token counts. Gold-string containment is a retrieval proxy, not answer correctness.

**Data provenance:** `review/experiment-redesign-20261101/artifacts/final_bench/s6_stats.json` for rates, Wilson intervals, and averages; `s4_traces_final.json` for per-question calls/bytes and independent assertions. The auxiliary `final_bench/viz/chart1_gold_rate.png` and `chart3_bytes_time.png` were not used because they use a 76-row denominator/rounded display values rather than authoritative gold-only n=72 statistics.
