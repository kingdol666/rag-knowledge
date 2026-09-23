# Meditation Workflow — Meditation Memory: Auto-Inducing Experiences from Questions

> OpenClaw-style "meditation memory": periodically scan high-frequency user questions, combine them
> with knowledge-base answers, and automatically distill them into structured experiences.
> Similar to how the human brain organizes memories during sleep.

## Table of Contents
- [Core Concept](#core-concept)
- [Trigger Timing](#trigger-timing)
- [Four-Phase Flow](#four-phase-flow)
- [Signal Judgment](#signal-judgment-when-is-a-question-worth-inducing-as-an-experience)
- [Quality Gate](#quality-gate)
- [Anti-Patterns](#anti-patterns)

---

## Core Concept

```
Traditional experiences: the user explicitly says "summarize this experience" → manual ingest
Meditation memory: the system proactively discovers "this question has been asked many times" → auto-induction

Key difference: the experience source is not an explicit user instruction, but a pattern discovered across high-frequency questions.
```

---

## Trigger Timing

| Timing | Triggered by | Notes |
|------|--------|------|
| User says "冥想" "整理记忆" "归纳经验" ("meditate" / "tidy memories" / "induce experiences"), "meditation", "reflect" | User, explicit | Run this flow |
| After every N sessions / periodically (e.g. weekly) | System, scheduled | See "Periodic scheduling" |
| The experience dashboard shows a domain with frequent queries but sparse experiences | Dashboard-driven | `experience_dashboard` discovers the gap |

### Periodic Scheduling (requires external cron/task)

This skill is an on-demand LLM flow and **has no built-in timer**. Periodic meditation requires external scheduling:

```
# Option 1: the user says "help me meditate" in conversation (most common)
# Option 2: external cron calls weekly (e.g. a system scheduled task)
#   ragctl meditation --days 7 --dry-run  # if ragctl supports it in the future
# Option 3: combined with experience_dashboard gap detection
```

An Agent flow cannot start a timer by itself. Periodicity comes from: user habit / external cron / dashboard-driven triggers.

---

## Four-Phase Flow

### Phase 1: Collect Question Sources

**Prefer the current session context** (most precise), supplemented by the historical chat library.

#### A. Current Session Context (Preferred, Most Precise)

KB Q&A that has already happened in the current session is the most precise meditation source — KB-relevant by construction, with answers guaranteed.

```
Review this session:
  - Which KB-related questions did the user ask?
  - How good was the retrieval/answer quality for each?
  - Which questions recurred, or took multiple rounds to resolve?
  - Which answers are worth solidifying into experiences?

Extract a candidate question list (with answer summaries from the session).
```

#### B. Historical Chat Library (Supplementary, Needs Cleaning)

Run the collection script to mine high-frequency question clusters from chat history:

```bash
python scripts/meditation_source.py --days 7 --top 30
# or JSON mode for parsing:
python scripts/meditation_source.py --json --days 14
```

**Script responsibility**: read `storage/claude-chat.db` → clean noise (tests/system output) →
cluster by semantic similarity → output the high-frequency question list. **Read-only, never writes.**

The script outputs JSON:
```json
{
  "success": true,
  "window_days": 7,
  "total_questions": 23,
  "total_clusters": 15,
  "clusters": [
    {"representative": "...", "count": 3, "max_relevance": 5,
     "samples": ["...", "...", "..."]}
  ]
}
```

> ⚠️ The historical chat library may contain test noise / non-KB chit-chat. The script cleans it,
> but the Agent must still run a second KB-relevance confirmation on every candidate (see Phase 2).

### Phase 2: KB Relevance Confirmation + Answer Retrieval

For each candidate question cluster, confirm it really is in KB territory and retrieve existing answers:

```
For each cluster.representative:
  1. KB relevance judgment:
     - Does the question fall within some KB's domain? (match via kb_list(lightweight=true))
     - No → discard (non-KB questions are not induced into experiences)
  2. Existing-experience check:
     experience_search_smart(query=representative, top_k=5)
     - Already covered by a high-quality experience (P0/P1 content ≥5) → skip (no duplicate induction)
     - Partially covered → mark "supplement" (take the update path)
     - Not covered → mark "create" (take the create path)
  3. Answer-source retrieval:
     kb_search_two_stage(query=representative, kb_id=<matching KB>)
     - Extract the top hit documents as related_docs
     - Extract key conclusions from the documents as the basis for solution
  4. Output: candidate experience list (with question / answer source / target KB / create-or-supplement marks)
```

### Phase 3: LLM Induction + Quality Gate

For candidates that passed Phase 2, the LLM distills structured experience drafts:

```
For each candidate (answer source in hand):
  LLM distillation (per the gold standard in quality-standards.md):
    - From the question cluster + document answers → distill problem (a reproducible scenario)
    - From document conclusions + the conversation's solution → distill solution (executable steps)
    - From the multi-turn interaction → distill key_lessons (independently citable)
    - Match category / tags / severity / related_docs

  Quality gate (mandatory, see quality-standards.md §Completeness Checklist):
    - Any field below the bar → discard the candidate (quality over quantity)
    - All fields pass → proceed to Phase 4
```

> ⭐ Quality over quantity: candidates that fail the quality gate are discarded outright. Meditation produces
> high-value experiences, not low-quality filler. 1 high-quality experience > 10 junk experiences.

### Phase 4: Persist (Create or Update)

```
For each candidate that passed the quality gate:

  Create path (no coverage):
    experience_create(kb_id, **draft) → exp_id
    experience_read(kb_id, exp_id) to verify

  Update path (partially covers an existing experience):
    experience_update(kb_id, existing_exp_id,
      key_lessons=[...merged...],
      solution="<supplemented new solution>",
      updated_at=now)
```

### Output Report

```
🧘 Meditation induction complete (window: 7 days)
   Questions scanned: 23 → KB-relevant: 15 → skipped (already covered): 8
   Passed the quality gate: 4 → discarded (below the bar): 3
   Created experiences: 3
     · exp-xxx "Common retrieval pitfalls in the XX domain" (原文: "XX 领域常见检索误区") @ AI-ML-Research
     · exp-yyy "Knowledge-graph build pitfall guide" (原文: "图谱构建避坑指南") @ Materials-Science
     · exp-zzz "Cross-KB retrieval optimization tips" (原文: "跨库检索优化技巧") @ Embodied-AI
   Updated experiences: 1 (added key_lessons)
     · exp-aaa added 2 lessons
```

---

## Signal Judgment: When Is a Question Worth Inducing as an Experience?

Not every question deserves induction. Induction signals:

| Signal | Strength | Notes |
|------|------|------|
| The same kind of question appears ≥2 times | Strong | High frequency = a common need |
| The answer took multiple documents / multiple rounds to resolve | Strong | Complex = worth solidifying |
| The answer contains concrete steps/configs/commands | Strong | Actionable = reusable |
| The user explicitly says "this is useful" / "write it down" | Strong | User endorsed it |
| The question is simple but the answer documents are scattered | Medium | Solidifying saves retrieval time later |
| Appeared only once and the answer is simple | Weak | Possibly a one-off need |

**Weak signals do not trigger induction** — this keeps the experience library from bloating with low-quality content. At least 1 strong signal or 2 medium signals is required.

---

## Quality Gate

Experiences produced by meditation must pass the complete checklist in [quality-standards.md](quality-standards.md).
Additional emphases:

- **related_docs must be verified**: `kb_doc_read(kb_id, doc_path)` confirms the path exists
- **scenario dedup**: `experience_list(kb_id, scenario=...)` confirms no duplicate
- **No orphan experiences**: every experience has at least 1 related_doc or a clear domain home

---

## Anti-Patterns

| ❌ Don't | Why | ✅ Do instead |
|--------|------|---------|
| Induce every question into an experience | Bloats the library with low quality | Only induce what meets the signal threshold |
| Skip KB relevance confirmation | Produces non-KB junk | Match every candidate against kb_list(lightweight=true) first |
| Skip the existing-experience check | Duplicate induction | Run experience_search_smart first |
| Lower the quality bar (because it is automatic) | Meditation ≠ mass-producing junk | Run the same complete quality gate |
| Ingest automatically without reporting | The user is unaware | Phase 4 outputs a report; important experiences can still get user confirmation |
| Let collection scripts write anything | Scripts are read-only | Scripts only produce lists; ingestion goes through MCP |
