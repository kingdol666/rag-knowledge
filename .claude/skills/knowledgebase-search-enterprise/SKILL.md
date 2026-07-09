---
name: knowledgebase-search-enterprise
description: >
  企业级多策略向量优先检索。从 knowledgebase-search 自动升级：
  向量+标签+描述三道门产出确认 P0/P1 文档来自 <2 个 KB，
  或用户明确要求 "全库搜索" / "全面"。
  并行 3 路（向量 + 标签扩展 + BM25）召回，交叉验证去重，
  内容裁决，融合呈现。
  Triggered by: 全库搜索, 所有KB, 跨知识库, 跨库, 联表, 宏观,
  cross-KB, all KBs, enterprise search, 全局搜索, 全面的, thorough search, comprehensive.
---

# Enterprise Multi-Strategy Retrieval

Three parallel recall paths → cross-validation → content rerank.

## Phase 1 — Parallel 3-Path Recall
```
# Path A: Vector (wider net)
kb_search_two_stage(query, kb_id="", stage1_top_k=30, stage2_top_k=10)

# Path B: Tags (expanded semantic matching)
kb_tags_list() → kb_doc_get_by_tag(tag, kb_id="") for each matched tag

# Path C: BM25 keyword-only
kb_search_two_stage(query, kb_id="", stage1_top_k=25, stage2_top_k=0)
```

## Phase 2 — Cross-Validate + Dedup
Merge all results by `doc_path`. Record hit paths per doc:

| Hit pattern | Confidence |
|---|---|
| A+B+C three paths | P0 candidate |
| A+B or B+C two paths | P0 candidate |
| A+C two paths | P1 candidate |
| Single path only | P1/P2 (needs content verify) |

## Phase 3 — Content Rerank
For each unique candidate (≤12):
```
kb_doc_read(kb_id, doc_path, max_chars=3000)
```
Score 0-8: topic (0-3) + scenario (0-3) + answer potential (0-2).

| Score | Verdict |
|---|---|
| 6-8 | P0 — use in answer |
| 5 | P1 — supplementary |
| ≤4 | Discard |

**Agent content judgment overrides all scores.** Short content (<200 chars) → downgrade one tier.

## Phase 4 — Graph Expansion (optional, when P0 <3)
```
kb_graph_document_related(doc_path)       # related docs
kb_graph_central_documents(kb_id)         # hub/survey docs
kb_graph_cross_kb_documents(min_kbs=2)    # cross-KB bridges
```
New docs from graph → enter Phase 3 content rerank.

## Phase 5 — Fused Answer
Present: search path summary, answer from P0/P1 docs, sources sorted by confidence, blind spots.
