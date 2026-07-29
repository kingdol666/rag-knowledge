# QA Test Report — Search (QDCVR) 模块

**Agent**: SkillSearch  
**Date**: 2026-07-29  
**KB**: QA-SKILL-SEARCH-6xxvmv (a46f12c0-9649-47e1-828d-1e7aad3eca0f)  
**Status**: 11/11 steps completed ✓

---

## Test Results

| # | Step | Tool | PASS/FAIL | Details | Regression |
|---|---|---|---|---|---|
| 1 | backend_status → healthy | backend_status | **PASS** | `status: healthy`, MinerU available, backend 8765 | — |
| 2 | kb_create | kb_create | **PASS** | KB created with UUID a46f12c0 | — |
| 3 | Dok×5 + index | kb_doc_create + kb_batch_index | **PASS** | 5 docs (Transformer/Adam/RAG/KG/VectorDB), 33 total chunks, all indexed | BUG2: collection=`kb_a46f12c0-...` (UUID-based) ✓ |
| 4 | BUG7回归: nonexistent query | kb_search_two_stage(q="zzunique_nonexistent_7777777", top_k=2) | **FAIL** | stage1.candidate_count=0, stage2.source="keyword". **应为 "vector"** 非 "keyword" | BUG7 **unfixed** |
| 5 | BUG6回归: limit check | kb_search_two_stage(q="深度学习", top_k=2) | **PASS** | stage2 结果数=2，≤2 ✓ | BUG6 单候选场景已修复 |
| 6 | 语义相关性TOP1 | kb_search_vector(q="注意力机制") | **PASS** | TOP1: Transformer自注意力机制 (score 0.718) ✓ | — |
| 7 | BM25→Vector 两阶段 | kb_search_two_stage(q="优化算法", top_k=3) | **PARTIAL** | stage1=Adam+VectorDB→stage2 6结果(per-candidate 3). 流程通但top_k为per-candidate非全局 | BUG6 multi-candidate未完全修复 |
| 8 | metadata搜索 | kb_search(q="Transformer") | **PASS** | 5 hits across KBs, 含本KB的Transformer文档 ✓ | — |
| 9 | 索引统计 | kb_search_stats(kb_id) | **PASS** | chunk_count=33, collection=kb_<UUID> ✓ | BUG2 confirmed fixed |
| 10a | 边界: 空查询 | kb_search_two_stage(q="") | **PASS** | 不崩溃,返回结果(低分fallback) | — |
| 10b | 边界: 不存在查询 | kb_search_vector(q="xyznonexistent123456789") | **PASS** | 不崩溃,低分结果 | — |
| 10c | 边界: 非法kb_id | kb_search_two_stage | **PASS** | 不崩溃,空结果 | — |
| 11 | 清理删除 | kb_delete | **PASS** | KB删除成功 | — |

---

## Bug Regression Verification

| Bug | Description | Status | Evidence |
|-----|------------|--------|----------|
| **BUG2** | Collection命名统一kb_<UUID> | ✅ FIXED | Collection name: `kb_a46f12c0-9649-47e1-828d-1e7aad3eca0f` |
| **BUG6** | stage2_top_k严格生效 | ⚠️ PARTIAL | Single-candidate works (2→2), multi-candidate is per-candidate (2 candidates × top_k=3 = 6 results) |
| **BUG7** | stage1=0时source="vector" | ❌ UNFIXED | Empty stage1 returns source="keyword", should be "vector" |

---

## Key Observations

1. **BUG7 still unfixed**: When stage1 has 0 candidates, the stage2 source shows "keyword" instead of "vector". The system falls back to scanning all document chunks via keyword/BM25 and marks them as keyword-sourced rather than vector-sourced.

2. **BUG6 partially fixed**: For single-candidate queries, stage2_top_k=N returns exactly N results (strict enforcement works). For multi-candidate queries, it appears to apply top_k per-candidate rather than globally, so with 2 candidates and top_k=3, results = 6.

3. **Vector search semantic quality is good**: "注意力机制" correctly returns the Transformer document's self-attention section at score 0.718.

4. **Boundary handling is robust**: Empty queries, nonexistent terms, and invalid kb_ids all return gracefully without crashes.
