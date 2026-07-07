---
name: knowledgebase-experience-summarize
description: 经验总结入库 — 将用户的实践、流程或经验教训自动提炼为结构化经验并存入知识库。识别场景 → 智能总结 → 用户确认 → experience_create 持久化 → 验证。确保经验完整（问题/方案/教训/标签/指标/关联文档）且人机皆可读。Triggered by: "记录这个经验", "总结一下", "保存教训", "记住流程", "提炼成经验", "把...做成经验", "帮我记录一下", "save this as experience", "summarize as lesson", "record this workflow", and any phrase expressing intent to persist a process/lesson/experience as structured knowledge. Do NOT trigger for read-only experience queries.
---

# Experience Summarize — Summarize & Store Experience

## S1 — Diagnose Source
Type A (conversation): extract from recent dialog
Type B (document): kb_doc_read → extract
Type C (manual input): guide user through structured fields
Type D (copy/migrate): experience_read → recreate in target KB
Target KB: user-specified or kb_catalog() → Agent best match → confirm

## S2 — Extract Fields
title (<30 chars), problem, solution (numbered steps), result (success/partial/failed), key_lessons (3-5 actionable items), tags (3-6), category (troubleshooting/best_practice/lesson_learned/tip), severity (critical/important/normal/tip), scenario (kebab-case for exact match), metrics (JSON, any custom keys), related_docs (auto-link via kb_search), prerequisites

## S3 — Present Draft
Markdown preview: Problem → Solution → Result → Lessons → Metrics → Tags
Include all structured fields clearly labeled.

## S4 — User Confirm
**Hard gate: never write without user confirmation.**
User says "confirm/save" → S5. User edits → update → re-present. User says "cancel" → abort.

## S5 — Persist
experience_create(kb_id, title, scenario, category, problem, solution, result, key_lessons, tags, severity, related_docs, prerequisites, metrics=json.dumps(metrics))
Verify: experience_read(exp_id) → confirm all fields
Report: "Saved to {KB}, ID {exp_id}, searchable by scenario '{scenario}'"

## Quality Rules
1. Each key_lesson must be independently actionable. Don't fabricate.
2. problem/solution/result must come from user or source doc — no hallucination.
3. metrics must have sources — don't invent numbers.
4. scenario should be precise kebab-case (e.g. "coal-mill-vibration" not "fault").
5. User confirmation is mandatory before writing.
6. Write then verify via experience_read.
