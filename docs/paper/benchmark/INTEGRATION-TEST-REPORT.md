# QDCVR Skill Integration Test Report

**Date**: 2026-07-29 05:27 UTC
**Scenarios**: 8/8 completed
**Skills Tested**: 13/14 (init, update not applicable in running system)

## 1. Scenario Results

| Scenario | Status | Steps | Key Findings |
|----------|--------|:-----:|-------------|
| S1 | ? | ? | All 8 steps passed. Full ingest pipeline works end-to-end: KB listing, document creation with auto-indexing, explicit in |
| S2 | success | ? | {'scenario': 'S2', 'title': 'Cross-Domain FPR + Multi-Baseline Retrieval Test', 'timestamp': '2026-07-29T00:00:00Z', 'me |
| S3 | PASS_WITH_FINDINGS | ? | {'scenario': 'S3-KB-Organize-Verify', 'description': 'KB Organize + Verify Flow Test — full health audit of E2E-Integrat |
| S4 | ALL_PASSED | ? | {'scenario': 'S4', 'title': 'Batch Operations + Tag Lifecycle Test', 'timestamp': '2026-07-29T05:19:49.000Z', 'completio |
| S5 | success | ? | {'total_steps': 8, 'passed': 8, 'failed': 0} |
| S6 | PASS | ? | {'scenario': 'S6_CrossLingual_GraphBridge', 'timestamp': '2026-07-29T00:00:00Z', 'status': 'PASS', 'steps': {'step1_cros |
| S7 | ? | ? | {'overall_status': 'PASS', 'layers_verified': ['L1', 'L2', 'L3', 'L4'], 'notes': 'L4 vector index retains stale entries  |
| S8 | ? | ? | {'total_steps': 9, 'success': 8, 'no_results_expected': 1, 'chain_integrity': 'intact', 'skills_tested': 8, 'key_finding |

## 2. Skill Coverage Matrix

| Skill | Scenarios | Result |
|-------|-----------|--------|
| knowledgebase (dispatcher) | S1, S2, S3, S4, S5, S6, S7, S8 | PASS |
| knowledgebase-batch | S4 | PASS |
| knowledgebase-experience | S5, S8 | PASS |
| knowledgebase-experience-summarize | S5 | PASS |
| knowledgebase-graph | S6, S8 | PASS |
| knowledgebase-ingest | S1, S4, S8 | PASS |
| knowledgebase-init | N/A | NOT TESTED (lifecycle skill) |
| knowledgebase-list | S3, S8 | PASS |
| knowledgebase-manage | S4, S7 | PASS |
| knowledgebase-organize | S3, S8 | PASS |
| knowledgebase-search | S1, S2, S6, S8 | PASS |
| knowledgebase-search-enterprise | S2, S6 | PASS |
| knowledgebase-update | N/A | NOT TESTED (lifecycle skill) |
| knowledgebase-verify | S3, S8 | PASS |

## 3. Bug Discoveries

| Bug | Found In | Severity | Description | Workaround |
|-----|----------|:--------:|-------------|-----------|
| L4 ChromaDB stale entries | S7 | HIGH | Document deletion does not clean ChromaDB collection entries; orphan chunks accumulate | kb_cleanup_orphan_collections needed after deletes |
| Orphan vector collections | S3 | HIGH | 42 orphan chunks in E2E-Integration-Test KB due to split collections | kb_cleanup_orphan_collections(dry_run=false) |
| Graph node double-extension bug | S3 | MEDIUM | Graph nodes created with '.md.md' extension | Fix graph_doc_id normalization |
| Missing graph index for CRUD docs | S3 | MEDIUM | Explicit kb_graph_build needed after kb_doc_create | Auto-trigger graph build on doc create |
| kb_id filter leak | S2 | MEDIUM | Domain-scoped search leaks results from RAG-Research sub-KB | Fix KB hierarchy collection resolution |
| Tags not auto-registered globally | S4 | LOW | kb_doc_create tags do not appear in kb_tags_list until explicitly updated | Fix tag propagation on doc create |

## 4. Key Metrics

- S2 Cross-domain FPR: Flat **0.333** -> Domain **0.033** (90% reduction)
- S5 Experience hit rate: macro-avg **0.667** (content scoring effective)
- S6 Cross-lingual retrieval: **2/3 rank-1**, all queries found correct KB
- S7 Five-layer consistency: CREATE **5/5**, UPDATE **5/5**, DELETE **4/5** (L4 stale)
- S3 Health score: **87/115** (75.7%) for E2E-Integration-Test
- S1 Full ingest pipeline: **8/8 steps passed**
- S8 Chained workflow: **8 skills validated**, chain integrity intact

## 5. Bug Severity Breakdown

- HIGH: 2 — Orphan chunks, stale vector entries
- MEDIUM: 3 — Graph indexing gaps, tag propagation, KB hierarchy leaks
- LOW: 1 — Tag auto-registration
