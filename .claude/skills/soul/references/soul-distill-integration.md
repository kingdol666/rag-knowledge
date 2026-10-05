# SOUL × Butian (补天) Distillation (dot-skill) Integration Protocol — Innate Distillation + Acquired Evolution

> Authoritative details for soul skill §E: how to wire the initial persona produced by
> Butian (补天) distillation into SOUL, and how curiosity training keeps evolving the seed.

## 1. Dual-Engine Model

```
Butian dispatch (one-shot)                SOUL curiosity training (lifelong)
─────────────────────                  ─────────────────────
nuwa-skill (deep research on public figures/topics)      documents within kb_scope
  [person]-perspective/SKILL.md           │
  mental models / decision heuristics / expression DNA / intellectual lineage
  │ → nuwa_to_seed.py conversion          │    four-layer questions (fact/concept/cross-doc/challenge)
dot-skill (colleagues/relationships/local materials)     retrieval self-answer → four-dimension self-eval → distillation
  persona.md (identity/style/catchphrases)            │
  work.md (duties/norms/processes)                │
  meta.json (name/tags/impression)       │
   │                                      │
   └──────────┬─────────────────────────────┘
              ▼
        SOUL persona (soul-<name>)
        ├─ Constitutional layer (written at initialization, read-only afterwards):
        │    soul-definition.md (template + persona.md)
        │    thinking-style.md (template + work.md)
        │    values.md (template [+nuwa values]) / memory-conventions.md (template)
        └─ Evolution layer (training writes continuously):
             memories/ (approved memories) · questions/learned-hashes.json
             cognition/ · checkpoints/ · audit/cost-log.jsonl
```

**Innate = identity and style (distilled once); acquired = knowledge and experience (continuously accumulated).**

## 2. Distillation Artifacts → SOUL Mapping

| dot-skill artifact | SOUL document | Notes |
|---|---|---|
| `persona.md` (Layer0 core personality/Layer1 identity/Layer2 expression style) | `soul-definition.md` appended section | Template sections preserved (the profile-summary generator and language-style parser depend on template structure); Butian content is appended as a "# 补天蒸馏人格" (Butian-distilled persona) section |
| `work.md` (scope of duties/work norms) | `thinking-style.md` appended section | Same as above; Butian working style appended |
| `meta.json.tags.personality` | `domain_labels` (default) | Routing labels: which questions get dispatched to whom |
| `meta.json.impression` | `domain_labels` supplement + KB description | The persona impression also participates in routing scores |
| `meta.json.slug` / `--name` | `soul-<slug>` | Persona KB name |
| (template default) | `values.md` / `memory-conventions.md` | Research-oriented values; can be customized later as needed |

**nuwa-skill artifacts** (landed via the same contract after conversion by butian `nuwa_to_seed.py`; section-level mapping in
`../../nuwa-skill/references/soul-seed-mapping.md`):

| nuwa SKILL.md section | → seed → SOUL document | Notes |
|---|---|---|
| Identity card / Expression DNA / Role-play rules / Honesty boundaries | persona.md → `soul-definition.md` appended section | Identity + language style + boundaries |
| Answering workflow / Core mental models / Decision heuristics / Intellectual lineage / Figure timeline / Failure modes | work.md → `thinking-style.md` appended section | Thinking framework + working style |
| Values and anti-patterns | values.md → `values.md` appended section | Constitutional-layer values, fused at creation via `ragctl soul distill --values` |
| frontmatter name/description | meta.json → `soul-<slug>` + domain_labels | Routing labels = persona name + model name |

## 3. Two Execution Paths

### 3a. One-Step ragctl (recommended; same backend as the frontend/MCP)
```bash
ragctl soul distill <dot-skill output directory> \
  --name soul-<name> --scope kb1,kb2 --labels label1,label2 --harness omp
```
Internally completes automatically: web KB creation → web writes the 4 documents (template + Butian fusion) → backend bootstrap
(soul-config + profile-summary + meditation config) → indexes the 4 documents.
Default domain_labels = first 3 of meta.tags.personality + first 12 chars of impression.

### 3b. Manual Orchestration via MCP/Frontend (executed by the main agent)
```
1. kb_create(name=soul-<name>, description=impression)      # web layer
2. kb_doc_create ×4:                                         # web layer
     soul-definition.md = template + persona.md
     thinking-style.md  = template + work.md
     values.md / memory-conventions.md = template
3. POST /api/v1/soul/bootstrap {
     soul_kb_id, kb_scope(default ["*"]), domain_labels, harness }
4. index_document ×4 (soul-definition/thinking-style/values/memory-conventions)
```
Once complete it is visible in soul_list; the frontend SOUL page card shows harness/scope/schedule status.

## 4. Acquired Evolution (the seed-growth loop)

```
Stage 1 Curiosity training (immediate):
  soul_learn_all(soul_kb_id, rounds=2)   # learn a batch of incremental documents per round
  # or soul_learn(soul_kb_id, doc_paths=[...], rounds=1) for specified documents

Stage 2 Memory approval (the only channel of evolution):
  soul_review_drafts(soul_kb_id, action=list)
  soul_review_drafts(soul_kb_id, action=approve, draft_ids=[...])
  # Approve → register + vector/graph indexing → profile refresh → routing basis updated

Stage 3 Scheduled auto-evolution (unattended):
  experience_meditation_config_update(soul_kb_id, {
    meditation_mode: soul, enabled: true,
    interval_hours: 24, rounds_per_run: 2,   # 2 RL rounds per scheduled training run
    max_budget_usd: 0.15, max_questions_per_run: 10})

Stage 4 Health checks (drift guard):
  soul_reflect(soul_kb_id)     # cognition drafts vs persona definition diff
  soul_calibrate(soul_kb_id)   # evaluator calibration (requires calibration set ≥20 entries)
  soul_checkpoint / soul_rollback   # safety net

Stage 5 Usage (persona-augmented retrieval):
  soul_qdcvr_ask(query, soul_kb_id)   # one click: QDCVR retrieval → persona synthesis
  # or ragctl soul ask "..." --soul soul-<name>
  # or the frontend Q&A modal "one-click retrieval + persona answer"
```

## 5. Consistency Across the Three Entry Points

| Operation | Frontend (SOUL page) | ragctl | MCP tools | Same data |
|---|---|---|---|---|
| Distill-create | — (ragctl recommended) | `soul distill` | soul_init + document overwrite | ✅ |
| Training | Training modal (rounds/documents/whole library) | `soul learn/learn-all` | soul_learn/learn_all | ✅ |
| Approval | Approval modal | `soul review` | soul_review_drafts | ✅ |
| Q&A | One-click retrieval + persona answer | `soul ask --soul` | soul_qdcvr_ask / soul_ask | ✅ |
| Schedule | Config modal (interval/rounds) | `meditation config` | experience_meditation_config_update | ✅ |
| harness | Config modal | `harness` / `soul harness` | soul_init harness / config | ✅ |

All entry points read and write the same backend storage (.knowledge-base.yml / memories / learned-hashes);
after an operation at any entry point, the others see it immediately (a refresh suffices).

## 6. Common Issues

| Symptom | Cause | Handling |
|---|---|---|
| Generic-feeling profile after distill | The bootstrap profile-summary is generated from the fused documents; Butian content sits in the latter half | Run soul_config_update again to trigger a profile refresh; or edit profile-summary directly (not recommended) |
| Training returns skipped instantly | This SOUL already learned it (per-SOUL learned_hash) | Use new documents; or wait for document content changes to trigger automatic relearning |
| Q&A style doesn't match the distilled persona | Distilled content lives in the soul-definition appended section; prompt injection takes only the first 1500 chars | Move the persona's core section toward the front of the document; or trim the template header |
| domain_labels too generic | meta has no personality tags | Pass --labels explicitly at distill time |
