# SOUL Architecture Reference — How the Persona System Works

> Gives executors of the soul / soul-rag skills the correct mental model.

## 1. What a Persona Is

**A persona = one special knowledge base `soul-<name>`**, containing:

```
soul-<name>/
├── soul-definition.md      # Persona definition (five identity dimensions / five personality dimensions / knowledge boundaries / language style)
├── values.md               # Values (constitutional layer — read-only for automated flows)
├── thinking-style.md       # Thinking style (reasoning patterns / argumentation habits / answer organization)
├── memory-conventions.md   # Memory conventions (admission criteria / lifecycle / approval rules)
├── soul-config.yml         # Config (constitutional layer — modified only via soul_config_update)
│     kb_scope: [...]           # Learning scope (public KBs it may learn from; empty = Q&A only, no learning)
│     domain_labels: [...]      # Routing labels (which topics get dispatched to whom)
│     supported_task_types: []  # Registered task-type values for routing
│     route_weight: 1.0         # Routing weight (0 = exits routing)
│     is_template: false        # Only soul-template is true
├── memories/               # Persona memories (approved = registered + indexed, pending = quarantined)
├── cognition/              # Self-cognition (reflection conclusions)
├── cognition-drafts/       # Cognition drafts (awaiting approval)
├── checkpoints/            # Checkpoints (rollback basis, keeps 30)
├── reports/                # profile-summary / drift reports
├── questions/gaps.md       # Learning gap records
├── calibration/            # Calibration set (manual scoring)
├── training/               # Exported training data
└── audit/                  # Approval / cost audit logs
```

The template library `soul-template` is the only is_template=true library:
- Never appears in soul_list / routing candidates / learn_all
- All write operations against it are rejected
- New personas copy the 4 persona documents from it via `soul_init`

## 2. Data Flow (five-layer consistency)

```
Disk .md  ←→  .tree-fs.json  ←→  .knowledge-base.yml  ←→  ChromaDB vectors  ←→  Neo4j graph
```

Identical to the knowledgebase 5-layer model. SOUL-specific rules:
- **Pending drafts are not registered as documents** (not indexed, quarantined)
- **Approved memories are registered + indexed** (searchable 60s after approval)
- soul-config.yml is a bare file, read/written directly on the FS, not part of the vector index

## 3. Persona Q&A (soul_ask) Internal Chain

```
soul_ask(query, soul_kb_id?, task_goal?, task_type?, context_override?)
  │
  ├─ soul_kb_id empty? → soul_router auto-routing
  │     ├─ candidates = soul_list (template excluded)
  │     ├─ >8 → domain_labels embedding cosine pre-filter to top8
  │     ├─ read profile-summary (cached; refreshed after learn/approval/reflect)
  │     ├─ LLM scoring (route_weight injected) → top1 ≥ threshold 0.6 → selected
  │     └─ complete() failure → embedding cosine fallback routing
  │
  ├─ load persona (4 documents + config)
  ├─ retrieve the knowledge pack: two_stage within kb_scope (balance_kbs for multi-KB in one call)
  │     + graph neighbors (scope-limited) + the 10 most recent approved memory summaries
  ├─ LLM synthesis: persona injection + knowledge pack → answer + citations
  ├─ PAS scoring: persona consistency (language-style phrase hits + values alignment)
  └─ return: answer / citations[{path, chunk_text, score, relevance_reason}]
           / pas_score / selected_soul / route_*
```

**Sync/async**: async_mode=True returns task_id immediately; poll with `kb_task_status`
(synthesis + PAS, two LLM calls, ~60-120s).

## 4. Persona Training (soul_learn) Internal Chain

```
soul_learn(soul_kb_id, doc_paths, limit)
  ├─ Lock: per-soul asyncio.Lock (same persona serializes)
  ├─ Validation: not template / scope non-empty / document within scope / budget sufficient
  ├─ Per document:
  │    generate_questions (LLM four-layer questions + keyword-classifier cross-validation + q_hash dedup)
  │      → self_answer (in-scope retrieval + similarity ≥0.5 pre-gate + LLM cited self-answer)
  │      → eval_answer (code groundedness × LLM four dimensions, take min + 10% double-judge)
  │      → distill (groundedness ≥3 with no divergence → memory draft; PAS ≥4 → sync to the shared experience pool)
  │      → learned_hash recorded only when there is output (content SHA256 → metadata)
  ├─ Budget: check-and-deduct (0.15/run); call count ≤30/run
  └─ Report: questions_generated / memories_created / gaps_count / cost
```

**Curiosity engine**: four-layer questions = fact (30%) / concept (30%) / cross-document (20%) /
challenge (20%). Deliberately weighted toward challenge questions → explores knowledge boundaries.

**Continue training after evaluation (incremental)**:
- learned_hash lives in document metadata; matching content SHA256 → skip (zero-cost idempotency)
- Document updated → hash mismatch → automatic relearning
- Newly ingested documents → automatically enter the training scope next round

## 5. Automatic Training Schedule

- Each SOUL has an independent meditation config (mode=soul, enabled, interval_hours, budget)
- The backend scheduler (experience_meditation_service) iterates every interval_hours:
  `mode==soul` → `_run_soul_meditation` → `learn_incremental`
- **Default enabled=false** (safe): requires explicit enablement + global experience_auto.enabled=true
- Budget protection: 0.15 USD/run per SOUL; global Semaphore(2) concurrency; circuit breaker opens 24h after 3 consecutive failures

## 6. Quality Gate Chain (guards against self-congratulation)

```
Retrieval pre-gate (≥0.5) → code groundedness (path-existence rate ×5) × LLM groundedness → min
→ four-dimension scoring → 10% double-judge (divergence >1.5 blocks) → distill (draft written only at ≥3)
→ manual approval (≥3 normal, <3 needs force + audit) → register + index
→ calibration set (≥20 entries) drift detection → reflect drift report
```

## 7. Division of Labor with knowledgebase

| Scenario | Which skill |
|---|---|
| Ingest/parse/manage/search knowledge | `knowledgebase` (72 kb_* tools) |
| Persona management/training/evaluation | `soul` (16 soul_* tools) |
| Retrieval + persona-augmented answering | `soul-rag` (kb_search → soul_ask combo) |
| Persona training-data export / fine-tuning | `soul` §D4 + docs/soul-lora-pipeline.md |

## 8. Common Error Codes

| Error | Meaning | Handling |
|---|---|---|
| kb_not_found | soul_kb_id is not a SOUL KB | Check name/path |
| is_template | Operation targeted the template KB | Use a real persona |
| scope_contains_soul_kb | kb_scope contains a soul- prefix | Remove it |
| scope_kb_missing | A KB in scope does not exist | Verify with kb_list |
| budget_exceeded | Insufficient budget | Wait for reset or confirm spend |
| insufficient_calibration | Calibration set <20 entries | Add calibration entries first |
| no_prompt_change | Prompt unchanged, no rerun needed | Normal state |
| lock_timeout | Persona locked by another operation | Retry later |
