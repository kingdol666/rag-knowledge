---
name: knowledgebase-search
description: >
  Vector-First Content-Verified Retrieval (VFCR) — 向量快速召回，内容真实裁决。
  核心流程：向量检索锁定候选 → 读真实内容验证 → 命中则直接回答（快速退出）；
  未命中则用标签+描述扩展召回 → 再次内容验证。
  向量负责"快"，内容负责"准"，标签描述负责"补"。
  Triggered by: "search", "find", "query", "ask", "retrieve", "what is",
  "how to", "explain", "rag", "回答", "检索", "搜索", "查找内容", "问答",
  "知识检索", "帮我查", "问一下知识库", "搜", "查询知识库", "知识库问答",
  "知识库搜索", "问题", "哪里", "办法", "怎么解决".
---

# VFCR — Vector-First Content-Verified Retrieval

Vector finds candidates fast; content read decides if they're relevant.

## Step 1 — Vector Recall
```
kb_search_two_stage(query="<user query>", kb_id="", stage1_top_k=20, stage2_top_k=5)
```
- `kb_id=""` for cross-KB search
- Returns `stage2.results`: top docs with `{content, doc_path, score, kb_id}`

## Step 2 — Content Verification (core decision)
For top 3-5 candidates:
```
kb_doc_read(kb_id, doc_path, max_chars=3000)
```
Score each 0-8: topic relevance (0-3) + scenario match (0-3) + answer potential (0-2).

**Content score overrides vector score.** Vector 0.9 but content irrelevant → discard.

## Step 2-Early Exit
If any doc scores **≥6**: skip to Step 6, answer directly.

| Top score | Action |
|---|---|
| ≥6 | ✅ Early exit — answer directly |
| 5 | ⚠️ Usable but supplement — continue to Step 3 |
| ≤4 | ❌ Miss — continue to Step 3 |

## Step 3 — Tag + Description Expansion (when vector missed)
```
kb_tags_list()
# Match query concepts to tags semantically (not string match)
kb_doc_get_by_tag(tag="<matched_tag>", kb_id="")
kb_doc_catalog(kb_id)  # for new KBs found via tags
```
Optionally: `kb_search_vector(query, kb_id="", top_k=10)` for wider recall.

## Step 4 — Expanded Content Verification
Read new candidates with `kb_doc_read(kb_id, doc_path, max_chars=3000)`. Score 0-8. Keep ≥5, discard ≤4.

## Step 5 — Confidence Assessment
| Source + Score | Tier |
|---|---|
| Vector/tag recall + content ≥6 | **P0 Strong** |
| Vector/tag recall + content =5 | **P1 Confirmed** |
| Description-only match + content =5 | **P2 Supplement** |
| Any ≤4 | Discard |

Cross-KB blind spot: if confirmed P0/P1 from <2 KBs → upgrade to `Skill("knowledgebase-search-enterprise")`.

## Step 6 — Answer
Synthesize answer from confirmed docs. Include: sources (doc name, path, KB, tier), confidence level, blind spots.

## Rules
1. Vector is the starting line — `kb_search_two_stage` first
2. Content is the judge — read 3000 chars, score independently of vector score
3. Hit and exit — score ≥6 means answer now
4. Tags are the expander — only when vector misses
5. Short content (<200 chars) → downgrade one tier
6. Experience-first for operational/fault queries — check experience before docs
7. Declare blind spots honestly
