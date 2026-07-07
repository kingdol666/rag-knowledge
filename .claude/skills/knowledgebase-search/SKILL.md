---
name: knowledgebase-search
description: >
  Agentic RAG — 真正的智能检索。核心原则：Agent 读 description 智能判断为主，
  向量相似度为辅助确认。先读轻量 catalog 的 description 判断 KB/文档相关性，
  筛除无关项；再用向量在已确认候选内精排；最后读真实内容验证满足场景。
  绝不只是"向量 top-k 返回"。经验优先（操作类问题先查经验，严格相关度，
  宁可不给也不要错给）。Triggered by: "search", "find", "query", "ask",
  "retrieve", "what is", "how to", "explain", "rag", "回答", "检索", "搜索",
  "查找内容", "问答", "知识检索", "帮我查", "问一下知识库", "搜",
  "查询知识库", "知识库问答", "知识库搜索", "问题", "哪里", "办法", "怎么解决".
---

# Agentic RAG — Agent Judgment First + Vector Assist + Content Verify

## Core Principles
1. **Agent judgment first** — read descriptions (kb_catalog/kb_doc_catalog), don't jump to vector top-k
2. **Hierarchical awareness** — scan sub-KB descriptions first (more precise than parent)
3. **Lightweight first** — catalog tools (id+description only), no file_size/tags in initial scan
4. **Content verify mandatory** — kb_doc_read to confirm relevance before answering
5. **Experience strict** — P0/P1 only, suppress P2 gray zone. Never give wrong experience.
6. **Honest blind spots** — if KB lacks content, say so. Don't fabricate.

## Adaptive Depth
| Depth | Scenario | Flow |
|---|---|---|
| L1 Shallow | Fact lookup (1-2 KBs) | Catalog → Read → Answer |
| L2 Standard | Knowledge Q&A (2-3 KBs) | Catalog → Doc Catalog → Vector → Content Verify → Answer |
| L3 Deep | Comparison/analysis (3-5 KBs) | Full + graph expansion |
| L4 Explore | Cross-domain exploration | Full + enterprise upgrade |

## Complete Workflow (7 Steps)

### Step 0 — Intent
- Operation/fault query ("怎么处理", "排查") → experience-first
- Knowledge/comparison ("什么是", "原理", "对比") → document-first

### Step 1 — KB Catalog Scan
kb_catalog() → read descriptions. Prioritize sub-KBs.
Rate: ★★★ (direct match), ★★☆ (category match), ★☆☆ (tangential)

### Step 2 — Doc Catalog Scan
kb_doc_catalog(kb_id) → read each doc's description. Score 0-10. Discard <5.

### Step 3 — Experience Priority (operation queries only)
| Signal | Tool | Strength |
|---|---|---|
| Exact scenario | experience_find_by_scenario(kb_id, scenario) | ★★★ Strongest |
| Semantic | experience_search_vector(kb_id, query, top_k=5) | ★★ (threshold >=0.55) |
| Cross-KB | experience_search_global(query, top_k=10) | ★ (fallback) |

Confidence: P0 (scenario exact + >=0.65 + rating>=4), P1 (>=0.55 + rating>=3), P2 (0.45-0.55, suppressed). Short chunk (<50 chars) -> suppress. Credibility decay: unverified if applied=0 >30d.

### Step 4 — Vector Confirm (within confirmed candidates)
kb_search_two_stage(query, kb_id, stage2_top_k=3).
Cross-validate: Agent score vs vector score. Agent wins on conflict.
Cross-KB blind: if candidates from <2 KBs -> upgrade to enterprise.

### Step 4.5 — Graph Expansion (optional, when candidates are sparse)
See [graph-tools.md](../knowledgebase-graph/references/graph-tools.md) for:
kb_graph_document_related(doc_path) — discover related docs
kb_graph_central_documents(kb_id) — find hub docs (reviews/surveys)
kb_graph_kb_overview(kb_id) — understand KB's structure
kb_graph_cross_kb_documents(min_kbs=2) — find bridge docs

### Step 5 — Sub-KB Backtrack (fallback, if candidates too few)
fs_get_children(parent_id) to scan sibling sub-KBs for overlapping topics.

### Step 6 — Content Verify (mandatory)
kb_doc_read(kb_id, doc_path, max_chars=1200). Score 0-8 (topic 0-3 + scenario 0-3 + answer potential 0-2). <=4 discard.

### Step 7 — Synthesize
Answer with: retrieval trace (sub-KB->doc->vector->verify) + experience (if P0/P1) + source docs + certainty + blind spots.
