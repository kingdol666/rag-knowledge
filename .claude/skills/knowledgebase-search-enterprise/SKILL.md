---
name: knowledgebase-search-enterprise
description: Enterprise-grade multi-strategy retrieval. Auto-upgrade from knowledgebase-search when standard Agentic RAG fails to cover sufficient candidates: cross-KB candidates from <2 different KBs, stage1 hits <3, or user requests "all KBs" or "comprehensive". Parallel 3-path recall (Agentic + BM25->vector + pure vector) with cross-validation, short content filtering, content rerank, and fused presentation. Triggered by: 全库搜索, 所有KB, 跨知识库, 跨库, 联表, 宏观, cross-KB, all KBs, enterprise search, 全局搜索, 全面的, thorough search, comprehensive.
---

# Enterprise Multi-Strategy Retrieval

Auto-upgrade from `knowledgebase-search` when:
- Cross-KB candidates from <2 different KBs (BM25 blind spot)
- stage1 hits < 3 (keyword coverage insufficient)
- User explicitly requests "all KBs" / "comprehensive"

## Phase 1 — Parallel 3-Path Recall (run concurrently)
- **Path A (Agentic)**: `kb_catalog()` → Agent reads descriptions, rates KBs
- **Path B (BM25→vector)**: `kb_search_two_stage(query, kb_id="", stage2_top_k=3)`
- **Path C (Pure vector semantic)**: `kb_search_vector(query, kb_id="", top_k=5)`

## Phase 2 — Cross-Validate + Dedup
Merge 3 paths into unified candidate list, dedup by doc_path.

| Hit pattern | Confidence | Tier |
|---|---|---|
| A+B+C | ★★★★★ | P0 |
| B+C | ★★★★ | P0 |
| A+B | ★★★★ | P0 |
| A+C | ★★★ | P1 |
| A only | ★★ | P1 (theory-only, needs verify) |
| C only | ★ | P2 (semantic-only, strict verify) |

## Phase 3 — Short Content Filter
Chunk <50 chars → suppress to P2. Doc with >50% short chunks → downgrade.

## Phase 4 — Content Rerank
kb_doc_read each candidate (max_chars=1500). Score 0-8 (topic 0-3, scenario 0-3, answer potential 0-2). ≤4 discard, 5=P1, ≥6=P0.

## Phase 5 — Fused Presentation
Source docs + hit pattern + confidence + blind spots declaration.
