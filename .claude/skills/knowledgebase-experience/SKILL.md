---
name: knowledgebase-experience
description: >
  经验管理系统 — 记录、检索、应用、评审经验。经验是实践总结的可复用知识，
  有评分、应用记录、场景绑定等结构化维度。用于故障排查、最佳实践、经验教训
  的动态管理和检索。Invoked by Archival 或用户直接请求。
  Trigger keywords: 查经验, 评分, 评审, 应用经验, lesson learned,
  best practice, 经验教训, 经验库, 看看经验, review experience,
  apply experience, 怎么处理的, 之前怎么解决, 类似情况.
---

# Knowledge Experience — Experience Management

## E1 — Create
`experience_create(kb_id, title, scenario, category, problem, solution, result, key_lessons, tags, severity, related_docs, prerequisites, metrics)` then verify with `experience_read`.

## E2 — Retrieve (strict relevance)

**Strategy:**
| Intent | Tool |
|---|---|
| Exact scenario match | `experience_find_by_scenario(kb_id, scenario)` |
| Natural language | `experience_search_vector(kb_id, query, top_k=5)` |
| Cross-KB global | `experience_search_global(query, top_k=10)` |
| Keyword search | `experience_search(kb_id, query, top_k=10)` |

**Confidence Tiers (combined relevance + credibility):**
- **P0**: scenario exact match AND vector >= 0.65 AND rating >= 4 — strongly recommend
- **P1**: vector >= 0.55 AND rating >= 3 — recommend with credibility annotation
- **P2**: 0.45 <= vector < 0.55 — suppress by default
- **Discard**: vector < 0.45 OR different equipment/scenario

**Credibility Decay:**
- applied_count=0 AND >30d old → label "unverified"
- rating_avg < 2.0 AND review_count >= 3 → label "contested", downgrade to P1 max
- review_count=0 AND applied_count=0 → never P0 (P1 ceiling)

**Short Content Guard:** chunk <50 chars → suppress. Document with >50% short chunks → downgrade.

**Content Verify (mandatory):** `experience_read` to confirm problem/solution matches query. Mismatch → downgrade or discard.

## E3 — Apply
`experience_apply(kb_id, exp_id, user, context, result, notes)` — records usage, increments applied_count.

## E4 — Review
`experience_review(kb_id, exp_id, reviewer, rating(0-5), comment)` — updates rating_avg.

## E5 — Statistics
`experience_summary(kb_id)` — total count, by_category, by_severity, top N.
