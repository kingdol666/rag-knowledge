---
name: soul
description: >
  SOUL persona system — full persona lifecycle management (create/delete/configure/list),
  Butian (nuwa-skill × dot-skill dual-engine) distillation of initial personas (including
  text distillation), curiosity-driven training and RL reinforcement evolution, task control
  (pause/resume/training history), and retrieval-augmented Q&A that auto-routes to the
  matching persona per task (QDCVR retrieves first, then persona-processes). A persona = a
  soul-<name> knowledge base (4 constitutional-layer documents + config), with a memory/
  cognition draft approval loop. Parallel to the knowledgebase skill: knowledgebase manages
  "knowledge itself", soul manages "which persona processes the knowledge". Triggers: persona,
  SOUL, create/delete/train/distill a persona, butian, persona Q&A, answer with persona XX,
  persona-augmented retrieval, one-click retrieval, RL reinforcement, persona evolution,
  pause training, resume training, training history, persona, soul_ask, soul_qdcvr_ask,
  soul_init, soul_learn, soul_train_rl, soul_review_drafts, soul_delete, soul_router,
  auto training, curiosity training, fixed-round training.
---

# SOUL — Persona System Dispatcher (Innate Distillation + Acquired Evolution)

**Executor: the main agent executes directly (SOUL operations are management/Q&A orchestration; no Archival delegation)**

The SOUL persona system is the "persona processing layer" above the knowledge base:
- **The knowledge base manages "what there is"** (knowledgebase skill, 72 kb_* tools)
- **SOUL manages "who explains it and how"** (soul_* MCP tools)
- **Butian (dot-skill) manages "where initial personas come from"** (source material → persona.md/work.md → SOUL seed)

> **⭐ SOUL mental model**: every persona = a `soul-<name>` knowledge base containing 4 persona documents
> (soul-definition/values/thinking-style/memory-conventions) + soul-config.yml
> (kb_scope learning scope/domain_labels routing labels/is_template). The template library `soul-template`
> is the only is_template=true library and never appears in any persona operation.
>
> **MANDATORY — load references on demand**:
> - Training/RL/scheduling details → **must read first** [references/soul-training.md](references/soul-training.md) (async contract/budget/learned_hash)
> - Full Butian distillation protocol → **must read first** [references/soul-distill-integration.md](references/soul-distill-integration.md)
> - Architecture/storage model → read [references/soul-architecture.md](references/soul-architecture.md) when needed
> - Q&A strategy combos → read [references/soul-rag-strategy.md](references/soul-rag-strategy.md) when needed
> - **Do NOT Load**: pure list/status queries (§A3) read no references; memory approval (§D1) does not read rag-strategy

---

## Mental Framework: Scenario Classification ⭐

```
The user says something
  └── Contains SOUL keywords?
       ├── Yes → match the scenario table below
       └── No → if it contains knowledge base keywords → hand to Skill("knowledgebase")
                otherwise → "Please clarify: manage personas / distill a persona / train a persona / Q&A with a persona / check persona status?"
```

After matching:
  ├── Persona distillation (Butian seed) → execute §E
  ├── Persona management (CRUD) → execute §A
  ├── Persona training (auto/manual/fixed rounds) → execute §B
  ├── Persona Q&A (explicit/auto routing/QDCVR one-click) → execute §C
  ├── Persona evaluation (self-rating/calibration/reflection) → execute §D
  └── Mixed scenarios → in the order management → training → evaluation → Q&A

---

## Scenario Classification Table

| Signal keywords | Scenario | Execute |
|---|---|---|
| distill a persona, butian, dot-skill, initial persona, create a persona from chat logs | **Distill** | §E `ragctl soul distill` / dot-skill |
| create persona, new SOUL, new persona, initialize persona, soul_init, create persona | **Create** | §A1 `soul_init` |
| delete persona, remove persona, soul_delete, delete persona | **Delete** | §A2 `soul_delete` |
| persona list, all personas, view personas, soul_list, list personas | **List** | §A3 `soul_list` + `soul_status` |
| persona config, modify persona, adjust learning scope, change domain labels, change engine, soul_config_update | **Configure** | §A4 `soul_config_update` + meditation config |
| train persona, persona learning, auto training, curiosity training, whole-library bootstrap, fixed rounds, rounds, RL reinforcement, persona evolution, train_rl | **Train** | §B0 `soul_train_rl` (rounds) unified RL |
| manual learning, learn specified documents, soul_learn, learn_all | **LearnOnly** | §B1/B2 `soul_learn`/`soul_learn_all` (Actor only) |
| approve memories, memory drafts, persona memories, soul_review_drafts, approve memory | **Review** | §D1 `soul_review_drafts` |
| persona evaluation, self-rating, calibration, soul_eval, soul_calibrate | **Evaluate** | §D2 `soul_eval`/`soul_calibrate` |
| persona reflection, drift report, soul_reflect, reflect | **Reflect** | §D3 `soul_reflect` |
| persona Q&A, answer with persona XX, persona-augmented retrieval, soul_ask | **Ask** | §C1/C2 `soul_ask` |
| one-click retrieval + persona answer, QDCVR persona Q&A, soul_qdcvr_ask | **QdcvrAsk** | §C4 `soul_qdcvr_ask` |
| retrieve the KB first then answer, summarize with a persona after retrieval | **RagAsk** | §C3 context_override combo |
| export training data, fine-tuning data, soul_export, LoRA | **Export** | §D4 `soul_export` |
| checkpoints, roll back persona, soul_checkpoint, soul_rollback | **Rollback** | §D5 `soul_checkpoint`/`soul_rollback` |

---

## Sequential Workflow

### Step 0 — Pre-Flight (Mandatory)

SOUL operations depend on the kb-mcp service (soul_* tools) + backend (LLM synthesis channel).
Before executing any scenario, call `soul_list` to verify:
- Tool reachable → MCP connected
- Returns a list (possibly empty) → backend online
On failure, prompt "MCP/backend unavailable"; do not continue.

### Step 1 — Scenario Matching
Match per the table above, longest keyword first. Persona Q&A and knowledge base retrieval can overlap:
- User says "help me look up/search XX" → **knowledgebase-search** (knowledge retrieval)
- User says "answer with persona XX / in XX's voice / persona-augmented" → **soul Ask** (persona processing)
- User says "retrieve then answer as a persona" / "one-click retrieval + persona answer" → **soul_qdcvr_ask** (QDCVR integration)
- User says "distill a persona / butian" → **§E Butian distillation**

### Step 2 — Execute the Corresponding Scenario (below)

---

## §A Persona Management (CRUD)

### A1 Create — `soul_init`
```
soul_init(soul_name="soul-<name>", kb_scope=[<public KB list>],
          domain_labels=[<domain labels>], supported_task_types=[<task types>],
          harness="omp|claude (empty=global default)", model="(empty=engine default)")
```
- Naming rules: `soul-` prefix + letters/Chinese/digits/hyphens; Windows reserved names are rejected
- kb_scope safety default: **missing/empty = ["*"] all public KBs** (all libraries participate in training by default);
  for "Q&A only" (no learning), explicitly set kb_scope=[] via soul_config_update after creation
- harness default = global default (config.yml soul.default_harness, default omp)
- ⭐ **Async contract (30s timeout fixed)**: soul_init returns quickly (≈2s), returning
  `kb_id` (immediately usable) + `docs_created` + `task_id` (indexing in background) + `profile_pending`/`profile_task_id` (profile generated in background).
  After creation you must:
  1. Poll `kb_task_status(task_id)` until done (confirms the 4 constitutional documents are vector-indexed)
  2. If profile_pending=true: poll the backend `GET /api/v1/soul/tasks/{profile_task_id}` or
     later confirm via `soul_status`/`soul_list` that profile_summary was generated (does not block later operations)
- **Butian distillation entry in §E** (generate the initial persona from source material, replacing the default template persona)

### A2 Delete — `soul_delete`
```
soul_delete(soul_kb_id)   # auto-checkpoints first → deletes the KB → clears the routing cache
```
- A snapshot is automatically kept before deletion (auditable); after deletion the persona no longer appears in soul_list

### A3 List — `soul_list` + `soul_status`
```
soul_list()                # all personas (template excluded), including the meditation summary (harness/schedule/rounds)
soul_status(soul_kb_id)    # learning metrics: drafts/memories/gaps/cost/mastery curve
```
- Report: persona name + kb_scope + harness + draft/memory counts + budget consumption + schedule status

### A4 Configure — `soul_config_update` + meditation config
```
soul_config_update(soul_kb_id, kb_scope/domain_labels/supported_task_types/route_weight)
experience_meditation_config_update(soul_kb_id, {harness, model, enabled, interval_hours,
                                                 rounds_per_run, max_budget_usd, max_questions_per_run})
```
- Scope narrowing → memories from the old scope are automatically flagged stale (not deleted)
- route_weight=0 → that persona exits routing
- **harness is per-SOUL** (a meditation config field); falls back to the global default when unspecified
- Frontend: config modal for visual management; ragctl: `ragctl soul harness <soul> <omp|claude>`

---

## §B Persona Training (Unified Three-Role RL)

> **⭐ Training principle (post-refactor)**: SOUL training uses a **three-role DRL architecture** (Actor × Critic × Updater),
> automatically integrating knowledge learning + self-evolution in one unified RL loop. **RL is the only training mode** —
> the old learn/learn_all have been integrated as RL's Actor phase and are no longer used independently.
>
> **Three-role mental model (DRL → SOUL mapping)**:
> - **Actor** πθ: parallel batch knowledge learning — curiosity questions → retrieval self-answers → distilled memories.
>   "Weights" = memories/*.md (knowledge mastery). Parallel batching speeds up 4-5x.
> - **Critic** Vφ: six-dimension evaluation + convergence detection (identity/values/thinking/language/knowledge mastery/
>   self-consistency). Outputs the reward signal (median-smoothed).
> - **Updater** ∇θ: generates cognition drafts (status=active) — **does not write the persona definition directly**.
>   Cognition drafts are the "gradient direction", injected into prompts at Q&A time (training cognition takes effect immediately).
> - **Global optimization engine**: when cognition accumulates ≥3 / reward declines / convergence locks in, it reads the full context
>   (4 constitutional documents + active cognition + memories + knowledge synthesis) and the LLM performs a **complete, coherent global rewrite**
>   (replacing old content, not fragmentary appends), eliminating contradictions and refining structure → reward monotonically improves.
>
> **Training effect**: the SOUL becomes more and more like "itself" (persona consistency converges) + knowledge mastery gets firmer
> (memory consolidation + weak-topic ZPD relearning + continuously refreshed mastery profile).
> Full protocol in [references/soul-training.md](references/soul-training.md).

#   Phase 1 ACTOR:   parallel batch knowledge learning (curiosity questions → retrieval self-answers → distillation, 4-5x speedup)
#   Phase 2 CRITIC:  six-dimension evaluation (identity/values/thinking/language/knowledge mastery/self-consistency)
#   Phase 3 UPDATER: generate cognition drafts (status=active, does not pollute the persona definition)
#   Phase 4 APPROVE: auto-approve high-quality memories (groundedness≥3.5 → index → searchable in Q&A)
#   Phase 5 DISTILL: cross-memory knowledge distillation (experience summaries → knowledge-synthesis.md)
#   Phase 6 OPTIMIZE: global persona optimization (triggered when cognition≥3/reward declines/convergence locks in;
#     full context → LLM complete rewrite → replaces old documents, not fragmentary appends; checkpoint-protected)
#   Phase REWARD:   evolution curve recording
```
- **Cognition accumulation mode**: the Updater only generates active cognition drafts; it doesn't write the persona definition directly (avoids fragmentary appends piling up contradictions)
- **Global optimization**: triggered when cognition ≥3 / reward declines consecutively / convergence locks in (replaces old content and digests active drafts)
- **Cognition participates in Q&A**: active cognition drafts are injected into prompts during soul_ask/soul_qdcvr_ask (training cognition takes effect immediately)
- **Convergence awareness**: reward changing <0.25 for 2 consecutive rounds → converged state: the Actor halves its question count (focus on deepening)
- **Auto-approved memories**: training memories with groundedness≥3.5 and all four dimensions ≥3.5 are auto-approved + indexed (searchable in Q&A)
- **Knowledge distillation**: per-round cross-memory synthesis → knowledge-synthesis.md (heuristics + knowledge points, not pile-ups)
- **Parallel speedup**: the Actor phase self-answers in parallel (harness parallelism configurable via config.yml soul.train_concurrency, default 4)
- **Reward stability**: the Critic median-smooths 2 samples by default (resists LLM variance)
- **Equivalent entry points**: POST /api/v1/soul/{kb}/train-rl; ragctl: soul train-rl; MCP: soul_train_rl

### B1 Manual Learning (Actor Phase Only — Precise Document Control)
```
soul_learn(soul_kb_id, doc_paths=[...], limit=6, rounds=1)   # async; returns task_id
# Runs only the Actor phase (knowledge learning); does not trigger Critic/Updater. For precise control of which documents are learned.
```
- Note: this is RL's Actor sub-component used alone; for full training use soul_train_rl

### B2 Whole-Library Learning (Actor Phase Batch — All Personas × Incremental Documents)
```
soul_learn_all(soul_kb_id="", max_docs=20, dry_run=False, rounds=1)
# Recommended: first dry_run=True to see estimated cost/overlap rate
```
- Note: this is RL's Actor sub-component used in batch; for full training use soul_train_rl

### B3 ⭐ Auto-Training Loop (Unattended; Automatically Invokes RL)
```
1. Enable the schedule for each SOUL:
   experience_meditation_config_update(soul_kb_id, {
     "meditation_mode": "soul", "enabled": true,
     "interval_hours": 24, "rounds_per_run": 2,     # each scheduled training run executes N RL rounds
2. Every interval_hours the scheduler iterates SOULs → train_rl(rounds=rounds_per_run):
   automatically executing the full RL loop of Actor+Critic+Updater+global optimization
3. Cognition drafts accumulating ≥3 automatically trigger global optimization; manual soul_review_drafts approval also works
```
- **The scheduler calls train_rl**: unified three roles; no longer only learn_incremental
- **Global optimization auto-triggers**: the persona definition is rewritten automatically when cognition≥3/reward declines/convergence locks in

### B4 ⭐ RL Evolution Curve and Cognition Draft Approval
```
soul_review_drafts(soul_kb_id, draft_type="cognition", action="list")  # view pending approvals
                   draft_ids=[...])   # approve → triggers global optimization rewriting the persona definition
soul_evaluate(soul_kb_id)             # independently invoke the Critic's six-dimension scoring
# During training, global optimization automatically digests active drafts; manual approval also triggers global optimization
```
- **Six-dimension evaluation**: identity/values/thinking/language/knowledge/coherence (0-5)
- **Cognition draft states**: active (awaiting global optimization) → applied (digested by global optimization); manual approve also triggers global optimization
- **Q&A participation**: active cognition drafts are automatically injected into prompts during soul_ask/soul_qdcvr_ask
- ragctl: soul evaluate / review-cognition --all

### B5 ⭐ Task Control and Training History (SQLite)
```
ragctl soul task pause|resume|status <task_id>   # pause/resume/status (effective at round boundaries)
ragctl soul training [soul_kb_id] [--run run_id] # training history / single-run event stream
curl -X POST /api/v1/soul/tasks/{id}/pause       # API equivalent
```
- Pause: the current LLM call isn't interrupted; stops at the next round boundary; resumes from the breakpoint
- SQLite persistence (storage/soul-training.db): every training/distillation/approval run
  records runs (metrics: rounds/questions/memories/documents/cost/reward) + events (phase event stream)
- Frontend: training console "📚 Training History" panel (list + event stream + status chips) + during training
  "⏸ Pause/▶ Resume" buttons; monitoring with real-time progress
- Queries: GET /api/v1/soul/training/history?[soul_kb_id] / training/runs/{run_id}

### B6 ⭐ Text Butian Distillation (Frontend/CLI/Agent — Three Entry Points)
```
ragctl soul distill-text <name> --req "persona requirement" --material "source material" [--scope k1,k2]
POST /api/v1/soul/distill {name, personality_req, source_material, ...}  # async task_id
```
- Complements ragctl soul distill (dot-skill output directory): this entry directly accepts raw
  source material (chat logs/documents/descriptions) + a persona requirement; the LLM extracts identity/values/thinking/
  language/expertise → creates the KB + 4 documents (template+distillation fused) + bootstrap + index
- The frontend creation modal includes a "Butian distillation (optional)" section: filling in requirement+source material runs distillation;
  leaving them empty uses template initialization; distillation progress is tracked in real time via the training console
- Distillation runs are also written to the SQLite training history (soul_distill)

---

## §C Persona Q&A (Retrieval-Augmented)

> **⭐ Augmentation principle**: soul_ask = persona injection (identity/values/thinking-style)
> + two-stage retrieval within kb_scope + persona memory summary + LLM synthesis → answer with structured citations
> + PAS (persona alignment score). Retrieval scope = the persona's bound kb_scope; persona memories are also retrieved.

### C1 Explicit Persona
```
soul_ask(query, soul_kb_id="soul-<name>", task_goal, task_type, async_mode=True)
```
- async_mode=True returns a task_id → poll kb_task_status
- Returns: answer/citations[]/pas_score/selected_soul/route_*

### C2 Auto Routing (No Persona Specified)
```
soul_ask(query, task_goal, task_type, async_mode=True)
# Empty soul_kb_id → soul_router scores domain_labels + profile summaries to pick the best persona
```
- Routing decisions are auditable (router-log); explicit specification can override
- Low confidence → route_uncertain=true + candidate list; no forced choice

### C3 Retrieval + Persona Augmentation Combo (kb_search → soul_ask)
When the user asks "look up XX in the knowledge base and answer as persona YY", or needs "retrieve first, then persona-ize":
1. `kb_search_two_stage(query, kb_id=<target KB>, ...)` to locate knowledge
2. `soul_ask(query, soul_kb_id="soul-<name>", context_override=<key retrieved snippets>)`
   → context_override injects retrieved results as temporary background; persona-ized processing
Full strategy in [references/soul-rag-strategy.md](references/soul-rag-strategy.md),
or directly use `Skill("soul-rag")`.

### C4 ⭐ QDCVR One-Click Integration (soul_qdcvr_ask — Recommended Entry)
```
soul_qdcvr_ask(query, soul_kb_id="", task_goal, task_type, top_k=5, async_mode=True)
```
**First retrieves per the knowledgebase-search skill flow, then injects the persona for an augmented answer** —
not a direct soul_ask, but the complete chain "retrieve → verify → persona synthesis":
- Retrieval side (aligned with skill Steps 2/2.5): two-stage retrieval (BM25+vector+graph) → hard threshold 0.35
  → document-level dedup → short-content filtering (<50 chars dropped) → top_k snippets
- Synthesis side: evidence injected via context_override → persona synthesis (citation anchor validation + PAS scoring)
- With explicit soul_kb_id, retrieval scope = that persona's kb_scope; auto-routing is cross-library
- Returns answer + citations + pas_score + route_* + **evidence_count** (injected evidence count)
- On no hits, the persona honestly downgrades (declares knowledge base blind spots; does not fabricate)
- Frontend: Q&A modal "one-click retrieval + persona answer" button; ragctl: `ragctl soul ask` with --qdcvr

---

## §D Persona Evaluation and Evolution

| Scenario | Tool | Notes |
|---|---|---|
| D1 Memory approval | `soul_review_drafts` action=list/approve/reject | Approve → register+index, searchable in 60s; low scores need force; **batch (≥2 items) is automatically async: returns task_id → poll progress {processed, total, approved, rejected} via kb_task_status (a single item takes ~20s including indexing; serial batching would exceed the MCP 30s)**; `draft_type="cognition"` approval → merged into the persona definition (RL strategy landing) |
| D2 Self-rating/calibration | `soul_eval` / `soul_calibrate` | Four-dimension scoring; calibration-set reruns detect drift |
| D3 Reflection | `soul_reflect` | Structured diff drift report: cognition drafts vs persona definition |
| D4 Export | `soul_export(min_score)` | High-quality memories → JSONL training data (LoRA/DPO) |
| D5 Rollback | `soul_checkpoint` / `soul_rollback` | Snapshot/restore the memory layer; the constitutional layer is never rolled back |

Approval golden rules:
- Groundedness ≥3 and all four dimensions ≥3 → approve normally
- Below → requires force=True with a recorded reason (audit log)
- After approval the persona profile auto-refreshes → routing basis updates in sync

---

## §E ⭐ Butian Distillation Integration (Innate Seed → Acquired Evolution)

> **⭐ Dual-engine model**: Butian (butian dispatch: nuwa-skill deep research × dot-skill local materials)
> provides the "innate persona seed" (identity/style/thinking framework, distilled once); SOUL curiosity training provides
> "acquired knowledge evolution" (continuous learning on KB evidence, lifelong). The two are orthogonal and complementary. Full protocol in
> [references/soul-distill-integration.md](references/soul-distill-integration.md);
> dispatch protocol in `../butian/SKILL.md`.

### E1 Distill the Initial Persona (Source Material → Persona Seed)
```
# Path 1: nuwa-skill (deep research on public figures/topics/thinking frameworks)
#   Skill("butian") → Skill("nuwa-skill") → output [person]-perspective/SKILL.md
#   → butian converter nuwa_to_seed.py → seed package (meta/persona/work/values)
# Path 2: dot-skill (colleagues/acquaintances/relationships/local materials)
#   Skill("butian") → Skill("dot-skill") → output directory (meta.json+persona.md+work.md)
# Path 3: direct source material (chat logs/documents/descriptions)
#   ragctl soul distill-text / distill-files (backend LLM distillation, bypassing the seed package)

# 2) One-click conversion into a SOUL persona (ragctl):
ragctl soul distill <seed dir> --name soul-<name> \
  --scope kb1,kb2 --labels label1,label2 --harness omp \
  [--values <seed dir>/values.md]   # nuwa output: values constitutional layer fused
```
- Conversion logic: persona.md → soul-definition.md append (template structure preserved,
  profile/language-style parse normally); work.md → thinking-style.md append;
  values.md (optional, nuwa output) → values.md append (constitutional layer fused at creation);
  meta.json tags/impression → domain_labels (routing basis)
- Automatically completes: create KB → write 4 documents → bootstrap (profile+meditation config)
  → index → trainable

### E2 Acquired Curiosity Evolution (Seed Growth)
```
ragctl soul learn-all soul-<name> --rounds 2     # fixed 2 rounds of curiosity training
ragctl soul review soul-<name> --action list      # review memory drafts
ragctl soul review soul-<name> --action approve --draft <id>
ragctl soul harness soul-<name> omp               # training engine
ragctl soul ask "question" --soul soul-<name>          # persona-augmented Q&A
# Or the frontend SOUL page: training (rounds)/approval/config (schedule)/Q&A (one-click retrieval + persona answer)
```
- Evolution loop: training produces drafts → approval registers → profile refresh → better routing → scheduled
  training keeps learning new documents → reflect guards against drift → checkpoints allow rollback

---

## Rules — Mandatory Execution

1. **MCP first**: all SOUL operations go through `mcp__kb-mcp__soul_*` tools; direct curl/python calls are forbidden
2. **Constitutional layer controlled modification**: automated flows do not directly edit values.md / soul-definition.md / soul-config.yml themselves;
   **the sole exception is the RL reinforcement channel** — after cognition drafts are approved via `soul_review_drafts(draft_type="cognition")`,
   they are automatically merged into the corresponding sections of soul-definition.md (only appending/refining lines within sections, no deleting or rewriting existing content; checkpoint before write)
3. **Budget reverence**: check soul_status.estimated_cost_usd before training; reject rounds over 0.15
4. **Template isolation**: soul-template never participates in training/routing/Q&A
5. **Approval loop**: memory/cognition drafts take effect only after soul_review_drafts approval (the only channel of persona evolution)
6. **Routing is overridable**: if auto-routing is unsatisfactory → retry with an explicit soul_kb_id
7. **Division of labor with knowledgebase**: knowledge operations (ingest/search/manage) go through the knowledgebase skill;
   this skill handles only the "persona layer". Mixed needs → knowledgebase executes, then soul augments
8. **Three entry points consistent**: frontend (SOUL page) / ragctl (soul subcommands) / MCP (soul_* tools)
   use the same backend and the same data; an operation at any entry is immediately visible to the others

## NEVER List

| ❌ | ✅ | Why |
|---|---|---|
| Use kb_doc_create to build persona memories | Memories only via soul_learn→soul_review_drafts | Bypassing the self-rating gate = no quality gate; pollutes the persona memory library |
| Directly edit soul-config.yml | Only via soul_config_update | Bypasses validation/indexing; routing data becomes inconsistent |
| Train the template library soul-template | Rejected via is_template | The template is the copy source; training it pollutes all new personas |
| Train personas with no kb_scope | Empty scope = Q&A only; learn refuses | No documents to learn = burning budget idling |
| Use drafts as memories without approval | Registered + indexed only after approval, then searchable | Unregistered = vectors/graph can't find them; training wasted |
| Run whole-library bootstrap ignoring budget | Check cost with dry_run first | Whole-library bootstrap cost = Σ personas × 0.15; must estimate first |
| Treat SOUL Q&A as ordinary retrieval | Persona Q&A must go through soul_ask (with persona injection) | Ordinary retrieval has no persona injection; answers lose identity consistency |
| Push butian outputs directly into memories | Butian persona is only an initialization document (constitutional layer); knowledge evolution goes through training | persona is "innate identity", not "acquired knowledge"; mixing them breaks the constitutional layer |

**Failure fallback**: training/approval tasks invisible (possibly MCP not restarted) → use the REST equivalent entry
`GET/POST http://localhost:8765/api/v1/soul/*` (same data as MCP); still failing →
`kb_project_status()` to check service health.

## Tool Quick Reference

- `soul_list()` / `soul_status(soul_kb_id)` — view personas and learning metrics
- `soul_init(soul_name, kb_scope, domain_labels, supported_task_types, harness, model)` — create a persona
- `soul_config_update(soul_kb_id, ...)` — modify config (scope/labels/weights)
- `soul_delete(soul_kb_id)` — delete a persona (snapshot kept first)
- `soul_train_rl(soul_kb_id, rounds)` — ⭐ unified RL training (three roles: Actor×Critic×Updater; async; the only training entry)
- `soul_learn(soul_kb_id, doc_paths, limit, rounds)` / `soul_learn_all(soul_kb_id, max_docs, dry_run, rounds)` — Actor phase alone (knowledge learning, async)
- `soul_evaluate(soul_kb_id)` — Critic six-dimension persona scoring (RL reward signal)
- `soul_eval(soul_kb_id, question, answer, evidence_paths)` / `soul_calibrate` — evaluation
- `soul_review_drafts(soul_kb_id, action, draft_ids, force, draft_type=memory|cognition)` — memory/cognition draft approval
- `soul_reflect(soul_kb_id)` / `soul_checkpoint` / `soul_rollback` — reflect/rollback
- `soul_export(soul_kb_id, min_score)` — training data export
- `soul_router(query, task_goal, task_type)` — routing decision preview
- `soul_ask(query, soul_kb_id, task_goal, task_type, context_override, async_mode)` — persona Q&A
- `soul_qdcvr_ask(query, soul_kb_id, task_goal, task_type, top_k, async_mode)` — QDCVR one-click retrieval + persona answer (recommended)
- `experience_meditation_config_update(soul_kb_id, {...})` — auto-training schedule config (includes rounds_per_run)
- `ragctl soul distill <dot-skill dir> [--name] [--scope] [--labels] [--harness]` — Butian distillation → SOUL
- `ragctl harness [omp|claude]` — global default harness; `ragctl soul harness <soul> <harness>` — per-persona override

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- OVERRIDE (overrides Step 0's "pre-flight first" opener habit): for any SOUL task, the reply (including the first reply) must write the complete execution plan in the body, verbatim, listing the concrete tool names to be called: soul_init, kb_task_status, soul_qdcvr_ask (or the other soul_* tools actually used in the scenario), while also containing an async-contract word (async_mode or task_id or profile_pending or "async"). Openers containing no tool names or async words, like "starting execution…/first a connectivity check", are forbidden; tool names in the plan must match the tool calls actually executed afterwards.
- For the combined scenario of creating a persona and immediately answering with it (scenario table Create→Ask): the fixed execution chain = soul_init (create; the reply must note the async contract task_id/profile_pending) → kb_task_status (poll the 4 constitutional documents' indexing until done) → soul_qdcvr_ask (one-click retrieval + persona answer; recommended entry; async_mode=True returns task_id). The reply body for this scenario must contain the three tool names soul_init, kb_task_status, soul_qdcvr_ask verbatim — all three are required.
- Whenever calling an asynchronously-returning SOUL tool (soul_init / soul_learn / soul_learn_all / soul_train_rl / soul_qdcvr_ask / batch soul_review_drafts), the reply must immediately follow the tool name with async wording containing task_id or async_mode or profile_pending or "async", e.g.: soul_init asynchronously returns task_id+profile_pending; soul_qdcvr_ask(async_mode=True) returns a task_id to poll.
- SOUL tasks must run to completion: the final reply must include the full execution results (creation result/index polling result/Q&A answer); ending after outputting the plan or the first tool call is not allowed. If any tool call fails, times out, or output is interrupted, the following reply must explain the error and retry or switch to the REST equivalent entry (see "Failure fallback"), and subsequent replies must likewise contain the original plan's tool names and async keywords verbatim (soul_init, kb_task_status, soul_qdcvr_ask, task_id/async).
<!-- SKILLOPT-SLEEP:LEARNED END -->
