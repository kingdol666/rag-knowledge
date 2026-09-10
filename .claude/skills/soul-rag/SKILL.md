---
name: soul-rag
description: >
  SOUL retrieval-augmented adapter — combines "knowledge base retrieval" with "SOUL persona
  processing" into a unified Q&A strategy: first locate knowledge with the kb_search family,
  then auto-route to the best-matching SOUL persona per task, and produce a persona-enhanced
  answer via soul_ask (with citations + the PAS persona alignment score). It does not break
  the original knowledgebase search logic — this skill is its "persona enhancement layer",
  intervening only when persona-ized answers are needed.
  Triggers: answer with a persona after retrieval, persona-augmented retrieval, look up with
  persona XX, answer in XX's voice, SOUL enhancement, persona-augmented RAG, persona-flavored
  RAG, soul-rag, look it up and answer with the research persona, find XX in the knowledge
  base and summarize with a persona.
---

# SOUL-RAG — Retrieval-Augmented Persona Q&A

**Executor: the main agent executes directly (soul_ask is a single orchestration call; no Archival delegation)**

## Positioning (Relationship to knowledgebase-search)

```
Ordinary retrieval:    kb_search_two_stage(query, kb_id) → raw snippet list
SOUL-RAG:    kb_search_two_stage → soul_router picks a persona → soul_ask persona-ized synthesis
                              ↑ adds "persona injection + structured citations + PAS scoring"
```

- **Does not break the original logic**: when raw snippets/document location is needed, still use knowledgebase-search
- **This skill adds a layer**: when "who explains it and how" is needed, persona processing is layered on top of retrieval
- **Combined decision tree** below:

## Decision Tree ⭐

```
Does the user request combine "retrieval + persona-ization" intent?
  ├─ No (pure retrieval/pure Q&A) → knowledgebase-search / soul §C
  └─ Yes → judge:
       ├─ Explicit persona ("answer with the research persona") → soul_ask(soul_kb_id=explicit)
       ├─ Not specified → soul_ask(empty soul_kb_id) → auto routing
       └─ Needs "see raw evidence first, then persona summary"
            → kb_search_two_stage to fetch snippets → soul_ask(context_override=snippets)
```

## Execution Flow

### Step 0 — Pre-Flight
`soul_list` available → the persona system is online; `kb_list` available → the knowledge base is online.
If either fails → report the error; do not continue.

### Step 1 — Parse Intent
Extract from the user request: query (core question), persona (specified?), task_goal (teaching/research/creation),
task_type (literature review/technology selection/creative planning…).

### Step 2 — Persona Selection
- Persona specified → use it directly (explicit override of routing)
- Not specified → first `soul_router(query, task_goal, task_type)` to preview the routing decision
  (see top1 + confidence + candidates), then decide:
  - confidence ≥0.6 → use top1
  - Low confidence → present the candidate list for the user to choose, or fall back to ordinary retrieval

### Step 3 — Execute Persona Q&A
```
soul_ask(query, soul_kb_id=<selected or empty>, task_goal, task_type,
         context_override=<optional: pre-retrieved key snippets>, async_mode=True)
→ task_id → poll kb_task_status (60-120s)
```

### Step 4 — Output Assembly
Return to the user:
- **answer**: the persona-ized answer (knowledge processed in the persona's style)
- **citations**: structured citations (real document paths + similarity + relevance reason)
- **pas_score**: persona alignment score (0-5; higher = closer to that persona)
- **selected_soul + route_confidence**: routing decision (auditable)

### Step 5 — Quality Self-Check
| Check | Pass criteria |
|---|---|
| citations ≥1 real path | Yes → augmentation effective |
| pas_score ≥3 | Persona alignment meets the bar |
| language_style_warning=false | Persona language style was injected |
| Retrieval failed (no citations) | Honest downgrade: state the knowledge base has no related documents; do not fabricate |

## context_override Use Cases

When retrieval hits multi-library/cross-library snippets, or the user explicitly wants "check evidence first, then answer":
1. `kb_search_two_stage(query, kb_id=<target KB>, stage2_top_k=5)` to get key snippets
2. Extract 1-3 essential passages (chunk_text + path)
3. `soul_ask(query, soul_kb_id=..., context_override=<snippet text>)`
   → the persona processes based on the given evidence; citations remain traceable

**Note**: context_override is injected only for this synthesis; it is not persisted and not written to memory.

## Persona Selection Hints (Routing Label Quick Reference)

| Persona | Typical domain_labels | Applicable scenarios |
|---|---|---|
| soul-materials | materials science/defect detection/machine learning/thin films | materials/thin films/defect detection |
| soul-ML | machine learning/deep learning/algorithms | algorithms/models/technology selection |
| soul-creative | creativity/branding/narrative/content creation | creativity/brand/copy/planning |
| soul-catalysis | catalysis/electrocatalysis/photocatalysis/chemistry | catalysis/chemistry/energy materials |

(Actual values depend on `soul_list`; new personas can be created at any time)

## ⭐ One-Click Entry (Recommended): soul_qdcvr_ask

The backend provides a combined QDCVR+SOUL orchestration entry; one call completes
"two-stage retrieval → hard threshold 0.35 → document dedup → short-content filtering → persona synthesis":

```
soul_qdcvr_ask(query, soul_kb_id="", task_goal, task_type, top_k=5, async_mode=True)
→ {answer, citations, pas_score, selected_soul, route_*, evidence_count}
```

- Explicit persona → retrieval scope = that persona's kb_scope; auto routing → cross-library
- No hits → the persona honestly downgrades (does not fabricate)
- Frontend: Q&A modal "one-click retrieval + persona answer"; ragctl: `ragctl soul ask --qdcvr`

## Relationship to knowledgebase-search-enterprise

- enterprise (cross-library precise retrieval): for cross-library evidence location → use kb_search_two_stage(balance_kbs)
- soul-rag: for persona-ized answers → layer soul_ask on top of enterprise retrieval
- Composable: enterprise retrieval → context_override → soul_ask persona-ized summary

## NEVER List

| ❌ | ✅ |
|---|---|
| Treat ordinary retrieval results as "persona answers" | Must go through soul_ask (with persona injection) |
| Assemble citations without validation | Citations must come from real retrieval paths |
| Answer categorically without selecting a persona | Route or specify explicitly; give candidates at low confidence |
| Ignore low pas_score | <3 means poor persona fit; switch personas and retry |
| Fabricate answers when retrieval fails | Honestly declare blind spots; give retrieval suggestions |
| Override the original knowledgebase-search flow | Pure retrieval needs still go through the original skill |

## Tool Quick Reference

- `soul_router(query, task_goal, task_type)` — routing decision preview (auditable)
- `soul_ask(query, soul_kb_id="", task_goal, task_type, context_override, async_mode=True)` — persona Q&A
- `soul_qdcvr_ask(query, soul_kb_id="", task_goal, task_type, top_k=5, async_mode=True)` — one-click retrieval + persona answer (recommended)
- `kb_task_status(task_id)` — async polling
- `kb_search_two_stage(query, kb_id, stage2_top_k)` — pre-retrieval (optional)
- `soul_list()` — persona list/label quick reference

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- Retrieval tool must be named: in 'retrieval + persona answer' tasks, the reply text must contain the string `kb_search_vector` verbatim (e.g. 'retrieve with kb_search_vector' or 'kb_search_vector(query, kb_id, top_k=5)'); writing only kb_search_two_stage, soul_ask, or 'check MCP connectivity' does not qualify.
- One-click entry mandatory: retrieval + persona answers must be executed via `soul_qdcvr_ask`, and the reply text must contain the string `soul_qdcvr_ask` verbatim (e.g. 'call soul_qdcvr_ask(query, soul_kb_id, task_goal, task_type, top_k=5, async_mode=True)'); substituting soul_ask/soul_router or plan-only wording is not allowed.
- Output blocks mandatory: the final reply must include the structured fields `pas_score` (a 0-5 numeric value) and `citations` (real document path citations); the reply text must contain 'pas_score' and 'citations' (or 'citations'); missing either is a failure.
- Overrides the Step 0/Step 1 "check first, then execute" flow above: for 'retrieval + persona answer' requests, the first reply must not be plan/confirmation language only (e.g. 'let me check MCP connectivity first… then…'); the first reply must directly give the call chain (kb_search_vector → soul_qdcvr_ask) and include the answer plus pas_score and citations fields.
<!-- SKILLOPT-SLEEP:LEARNED END -->
