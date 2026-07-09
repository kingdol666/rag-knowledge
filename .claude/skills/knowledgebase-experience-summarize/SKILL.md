---
name: knowledgebase-experience-summarize
description: >
  经验总结入库 — 将用户的实践、流程或经验教训自动提炼为结构化经验并存入知识库。
  识别场景 → 智能总结 → 用户确认 → experience_create 持久化 → 验证。
  确保经验完整（问题/方案/教训/标签/指标/关联文档）且人机皆可读。
  Triggered by: 记录这个经验, 总结一下, 保存教训, 记住流程,
  提炼成经验, 把...做成经验, 帮我记录一下,
  save this as experience, summarize as lesson, record this workflow,
  and any phrase expressing intent to persist a process/lesson/experience as structured knowledge.
  Do NOT trigger for read-only experience queries.
---

# Experience Summarize — Persist as Structured Experience

## Step 1 — Identify Scenario + Target KB
From conversation, extract: what happened, what was done, what was learned. Identify the operational context (equipment, system, domain). Determine target `kb_id` from existing KBs via `kb_list()`.

## Step 2 — Draft Experience
```
kb_id:       "<target KB ID or path>"
title:       "<concise experience title>"
scenario:    "<scenario identifier, e.g. 'biaxial-stretching-quality-issue'>"
category:    "lesson_learned"       # best_practice|troubleshooting|lesson_learned|optimization|tip|workflow|decision
problem:     "<what went wrong or what was needed>"
solution:    "<steps/methods taken>"
result:      "success"              # success|partial|failed|inconclusive
key_lessons: ["actionable lesson 1", "actionable lesson 2"]
tags:        ["domain", "method", "equipment"]
severity:    "normal"               # critical|important|normal|tip
related_docs: ["KB/doc.md"]         # if KB docs were referenced
```

Completeness check — all of `title`, `scenario`, `problem`, `solution`, `key_lessons` must be non-empty and specific. If any is vague, ask the user for more detail.

## Step 3 — User Confirmation
Present the draft. Ask: "确认入库？" User confirms or edits.

## Step 4 — Persist
```
result = experience_create(
    kb_id, title, scenario, category,
    problem, solution, result,
    key_lessons, tags, severity, related_docs
)
exp_id = result.experience.id
```

## Step 5 — Verify
`experience_read(kb_id, exp_id)` — confirm all fields stored correctly. Report `exp_id` to user.
