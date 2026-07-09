---
name: knowledgebase-experience
description: >
  经验库管理 — 经验的创建、检索、应用、评审。经验是结构化的实践案例，
  包含场景、问题、方案、教训、标签、评级。用于运维/故障查询时优先检索。
  Triggered by: 经验, 经验库, experience, lesson, best practice, 实践,
  案例, 故障经验, 运维经验, lesson learned, 工作经验, previous experience.
---

# Experience — Lifecycle Management

> All tools require `kb_id` (KB ID or path) as first parameter, except `experience_search_global`.

## Create
```
experience_create(
    kb_id="<target KB>",
    title="<experience title>",
    scenario="<scenario identifier, e.g. 'coal-mill-fault-prediction'>",
    category="lesson_learned",         # best_practice|troubleshooting|lesson_learned|optimization|tip|workflow|decision
    problem="<what went wrong or what was needed>",
    solution="<steps/methods taken>",
    result="success",                  # success|partial|failed|inconclusive
    key_lessons=["lesson1", "lesson2"], # actionable takeaway items
    tags=["tag1", "tag2"],
    severity="normal",                 # critical|important|normal|tip
    related_docs=["KB/doc.md"]         # optional
)
```

## Read
`experience_read(kb_id, exp_id)` — full record including review history.

## List
`experience_list(kb_id, scenario="", category="", tag="")` — filtered by scenario/category/tag, sorted by rating.

## Update
`experience_update(kb_id, exp_id, <fields to change>)` — pass only fields to update. Bumps `updated_at`.

## Delete
`experience_delete(kb_id, exp_id)` — irreversible.

## Apply (record usage)
```
experience_apply(kb_id, exp_id, user="<agent/user>", context="<scenario>", result="success", notes="<optional>")
```
Increments `applied_count`.

## Review
```
experience_review(kb_id, exp_id, reviewer="<agent/user>", rating=5.0, comment="<feedback>")
```
Adds review record, recalculates `rating_avg` and `review_count`.

## Search
| Method | Tool |
|---|---|
| By scenario | `experience_find_by_scenario(kb_id, scenario="<keyword>")` |
| Keyword (metadata) | `experience_search(kb_id, query="<question>", top_k=10)` |
| Semantic vector | `experience_search_vector(kb_id, query="<question>", top_k=5)` |
| Cross-KB global | `experience_search_global(query="<question>", top_k=10)` |
| Summary | `experience_summary(kb_id)` — overview stats |

## Credibility Tiers (based on `rating_avg` from reviews + vector score)
| Condition | Tier | Action |
|---|---|---|
| scenario match ∧ vector ≥0.65 ∧ rating_avg ≥4 | P0 Strong | Pin to top |
| vector ≥0.55 ∧ rating_avg ≥3 | P1 Reference | Show with annotation |
| 0.45 ≤ vector <0.55 | P2 Gray | Suppress by default |
| vector <0.45 OR different equipment | Discard | Never present |

Decay: stale unverified (>30d, 0 applied) → max P1; disputed (rating_avg <2.0, ≥3 reviews) → max P2; unvetted (0 reviews ∧ 0 applied) → max P1.
