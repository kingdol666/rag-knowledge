---
name: knowledgebase-experience
description: >
  经验库管理 — 经验的创建、检索、应用、评审。经验是结构化的实践案例，
  包含场景、问题、方案、教训、标签、评级。用于运维/故障查询时优先检索。
  Triggered by: 经验, 经验库, experience, lesson, best practice, 实践,
  案例, 故障经验, 运维经验, lesson learned, 工作经验, previous experience.
---

# Experience — Lifecycle Management

## Create
```
experience_create(
    scenario="<when/where this applies>",
    problem="<what went wrong or what was needed>",
    solution="<what was done to fix/achieve>",
    lesson="<key takeaway / what to watch out for>",
    tags=["tag1", "tag2"],
    rating=4,                        # 1-5, default 4
    applied_count=0,                 # times applied
    related_docs=["KB/doc.md"]       # optional
)
```

## Read
`experience_read(exp_id)` — full record including review history.

## List
`experience_list(limit=20, offset=0)` — paginated summary list.

## Update
`experience_update(exp_id, fields...)` — update any field. Bumps `updated_at`.

## Delete
`experience_delete(exp_id)` — irreversible.

## Apply (record usage)
`experience_apply(exp_id, applied_by="<agent/user>", notes="<context>")` — increments `applied_count`.

## Review
`experience_review(exp_id, reviewer="<agent/user>", rating=4, comment="<feedback>")` — adds review record, recalculates average rating.

## Search
| Method | Tool |
|---|---|
| By scenario keyword | `experience_find_by_scenario(scenario="<keyword>")` |
| Semantic vector search | `experience_search_vector(query="<question>", top_k=5)` |
| Cross-KB global search | `experience_search_global(query="<question>", top_k=10)` |
| Combined keyword+vector | `experience_search(query="<question>", top_k=10)` |

## Credibility Tiers
| Condition | Tier | Action |
|---|---|---|
| scenario match ∧ vector ≥0.65 ∧ rating ≥4 | P0 Strong | Pin to top |
| vector ≥0.55 ∧ rating ≥3 | P1 Reference | Show with annotation |
| 0.45 ≤ vector <0.55 | P2 Gray | Suppress by default |
| vector <0.45 OR different equipment | Discard | Never present |

Decay: stale unverified (>30d, 0 applied) → max P1; disputed (rating <2.0, ≥3 reviews) → max P2; unvetted (0 reviews ∧ 0 applied) → max P1.
