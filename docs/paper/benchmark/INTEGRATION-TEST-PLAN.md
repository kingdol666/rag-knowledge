# QDCVR Skill Integration Test — Master Plan
## Full Pipeline End-to-End Verification
### Target: Validate all 14 skills across 8 realistic usage scenarios

---

## Scenario Design

### S1: arXiv Paper Full Pipeline (ingest + search + experience)
- Download 3 arXiv papers (AI, Energy, Materials domains)
- Parse each via parse_doc → kb_doc_save_parsed → kb_index_document
- Test: kb_search_vector with domain-specific queries
- Test: experience_extract from ingested docs
- Verify: P@3 >= 0.67, FPR = 0

### S2: Multi-Document Mixed Retrieval + Cross-Domain FPR
- Use existing multi-KB corpus (13 KBs, 154 docs)
- Run 10 adversarial queries (vocabulary overlaps multiple KBs)
- Compare Flat vs Domain search FPR
- Verify: Domain FPR <= 0.05, Flat FPR >= 0.40

### S3: KB Organize + Verify Flow
- Run kb_list + kb_get_documents on a test KB
- Execute V1 three-way metadata consistency check
- Check tag health (orphan detection)
- Check index coverage
- Verify: No orphan tags, all docs indexed

### S4: Batch Operations + Tag Lifecycle
- Create 3 test documents with tags
- Run kb_tags_list to verify tag registry
- Update tags on batch
- Run kb_tags_cleanup(dry_run=true)
- Verify: Tags consistent before/after

### S5: Experience Meditation + Smart Search
- Run experience_meditation_status
- Test experience_search_smart with domain queries
- Verify tier_counts: P0/P1/P2 distribution reasonable
- Test experience_dashboard

### S6: Cross-Lingual Retrieval + Graph Bridge Discovery
- Run Chinese queries against English documents
- Test kb_graph_cross_kb_documents(min_kbs=2)
- Test kb_graph_central_documents
- Verify: Chinese queries hit correct documents

### S7: Five-Layer Consistency CRUD Stress
- Create doc → verify L1-L5
- Update doc → verify L1-L5
- Delete doc → verify L1-L5 cleaned
- Verify: 100% consistency on create/update, 80% on delete

### S8: Chained Multi-Skill Scenario
- Ingest doc → Search → Organize → Experience → Verify
- Execute full chain without human intervention
- Verify: Each step completes, output passes to next step

---

## Execution Protocol
Each scenario runs as an independent sub-agent using MCP tools (xd://mcp__kb_mcp_*).
Results saved to: docs/paper/benchmark/results/integration-test-{scenario}.json