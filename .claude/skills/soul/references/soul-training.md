# SOUL Training Protocol — Unified Three-Role Reinforcement Training (RL) (Actor × Critic × Updater)

> This document is the authoritative detail for soul skill §B: the unified RL training architecture,
> convergence detection, the auto-apply mechanism, and the auto-loop scheduling protocol.
>
> **⭐ Refactor highlights (2026-08)**: training is unified into a single RL mode (soul_train_rl),
> automatically integrating knowledge learning (Actor) + six-dimension evaluation (Critic) + weight updates (Updater).
> The old learn/learn_all are demoted to RL's Actor sub-components, and learn_incremental is upgraded to
> parallel batching (learn_incremental_parallel, 4-5x faster).

## 0. ⭐ Async Task Contract (unified pattern for all long tasks)

Training/batch approval are minute-scale long jobs: **always execute asynchronously + poll progress via task_id**;
no entry point blocks synchronously: triggering returns `task_id` immediately, progress is checked after a while,
and results are fetched once done.

```
Trigger (MCP/web/ragctl) → immediately returns {task_id, status: running}
  └─ the backend soul_task_runner executes the task independently (modeled on parse's task_registry pattern)
Poll progress: kb_task_status(task_id)  /  GET /api/v1/soul/tasks/{task_id}
  └─ while running, returns progress:
      training: {round, rounds, phase: actor|critic|updater|approve|distill|optimize|reward,
             questions, memories, reward, converged, global_optimized, cognitions_absorbed}
done    → result contains the full report (souls[] / per_round / results[])
error   → the error field carries the failure reason
```

- Backend: POST /api/v1/soul/{kb}/learn and /learn-all with `async_mode: true`
  → task_id returned immediately; GET /api/v1/soul/tasks lists all tasks
- MCP: soul_learn / soul_learn_all / soul_review_drafts (batch) are wrapped async,
  returning task_id → poll with kb_task_status (progress mirrored)
- web: /api/soul/learn /train-all /review default to async_mode and return task_id;
  /api/soul/tasks/:taskId proxies progress; the SOUL page training/approval modals poll and display progress
- Sync compatibility: the backend async_mode defaults to False; legacy callers behave unchanged

## 1. Training Triggers (recommended: unified RL)

### 1a ⭐ Unified RL Training (the single recommended entry)
```
soul_train_rl(soul_kb_id="soul-musk", rounds=2)   # async; task_id → poll with kb_task_status
```
Six phases per round: Actor (parallel knowledge learning) → Critic (six-dimension evaluation) →
Updater (cognition draft accumulation) → Approve (auto-approve memories) → Distill (knowledge distillation) →
Global Optimize (whole-persona optimization, not fragmentary appends).
In the converged state (reward change <0.25 for 2 consecutive rounds): the Actor halves its question count,
and global optimization consolidates cognition at convergence.

### 1b Manual Single-Document (Actor run alone)
```
soul_learn(soul_kb_id="soul-催化", doc_paths=["Chemistry-Catalysis/photocatalysis.md"], limit=6)
→ task_id → poll kb_task_status
```
Use case: precise control over which documents are learned.

### 1b Whole-Library Bootstrap (incremental)
```
soul_learn_all(soul_kb_id="", max_docs=20, dry_run=true)   # see the estimate first
soul_learn_all(soul_kb_id="", max_docs=20)                  # actual execution
```
- Empty soul_kb_id = iterate all personas × their respective kb_scope
- Document-level content SHA256 dedup: documents already learned by any persona are skipped (no cross-persona relearning)
- dry_run returns: unique_docs / duplicate_docs / cross_soul_overlap_pct / per_soul cost

### 1c Auto Schedule (unattended) ⭐
```
experience_meditation_config_update(soul_kb_id, {
  "meditation_mode": "soul",
  "enabled": true,
  "interval_hours": 24,        # learning frequency
  "max_budget_usd": 0.15,      # per-run budget cap
  "max_questions_per_run": 10, # per-run question cap
  "rounds_per_run": 2          # N RL rounds executed per scheduled training run
})
```
Prerequisites (one-time admin setup):
1. backend config.yml `experience_auto.enabled: true` (default false, prevents accidental starts)
2. the scheduler starts with the backend (auto-started by main.py lifespan)

Once enabled: every interval_hours the scheduler iterates all enabled SOULs → `train_rl` (unified three roles):
- The Actor only learns documents whose learned_hash mismatches (unlearned/changed) → zero cost when nothing is new
- Critic six-dimension evaluation + convergence detection; Updater cognition drafts (auto-applied in the converged state)
- Budget/circuit breaker/semaphore all remain in force

## 2. Curiosity Training Protocol (inside every learn)

### 2a. Basic Chain (four-layer questions + quality gates)

```
Step 1  Document read (≤50000 chars)
Step 2  Generate 6 questions (four layers):
        fact 30% | concept 30% | cross_doc 20% | challenge 20%
        LLM generation + keyword-classifier cross-validation + q_hash dedup
Step 3  Self-answer each question:
        two-stage retrieval (scope-limited, similarity ≥0.5 pre-gate)
        → graph neighbors (scope-limited) → LLM cited synthesis
Step 4  Four-dimension self-eval per answer:
        groundedness = min(code path-existence rate ×5, LLM relevance score)
        completeness / thinking-consistency / information gain (0-5)
        10% sampled double-judge (divergence >1.5 blocks)
Step 5  Distill: groundedness ≥3 and no divergence → memory draft (pending)
        PAS ≥4 and info_gain ≥3 → sync to the shared experience pool (sync_dedup_key idempotent)
Step 6  If there is output → record learned_hash (content SHA256 → document metadata)
```

### 2b. ⭐ Butian (补天) Curiosity Engine v2 (metacognitive adaptation — enabled by default)

Algorithm framework: arXiv:2604.25648 (Desvaux/Oudeyer et al., Curiosity and
Metacognition), three principles → concrete implementation:

| Paper principle | v2 implementation (backend/app/services/soul_curiosity.py) |
|---|---|
| Metacognitive monitoring and control | After each training round, refresh the `questions/mastery.json` mastery profile (per-topic memory counts/avg scores/gaps/learning footprints, zero LLM cost) |
| Individual-profile customization | `compute_question_mix()`: dynamically adjust the four-layer ratios by topic mastery (zone of proximal development) |
| Cognitive-partner anti-shortcut | Known memory summaries injected into the prompt + `novelty_filter()` jaccard dedup, preventing relearning of the known |

**Adaptive question distribution (zone of proximal development, ZPD)**:

```
New topic (first pass)     fact 35 | concept 30 | cross 20 | challenge 15   ← build foundations
Weak / has gaps      fact 20 | concept 30 | cross 30 | challenge 20   ← repair base linkages
Medium mastery       fact 15 | concept 25 | cross 30 | challenge 30   ← balanced deepening
Strong mastery (≥4.0)    fact 10 | concept 20 | cross 20 | challenge 50   ← challenge boundaries
```

**Exploration-exploitation balance (document selection)**: each incremental scan = new documents (exploration) first +
relearning of weakly-mastered documents (exploitation: topics with gaps / zero memories / avg score <3);
explore first, then reinforce, within budget.

**Metacognitive input**: the training prompt injects the topic's mastery profile (approved memory summaries + gap count +
a "slightly harder than current mastery" instruction), ensuring every round of curiosity lands in the zone of proximal development.

**Inspecting the profile**: after training use `soul_status`, or read
`storage/tree-file-system/soul-<name>/questions/mastery.json` directly.


## 3. Continue Training After Evaluation (the continuous evolution loop)

```
Document ingested/updated
  └─> learned_hash mismatch
        └─> the next learn_incremental round relearns automatically
              └─> new drafts → manual approval (soul_review_drafts)
                    ├─ approve → register + index (searchable in 60s) → profile refresh
                    │           → persona memories consolidate → cited by future soul_ask
                    └─ reject → kept in gaps.md (traceable)
```

**Key mechanism**: learned_hash (first 12 chars of the content SHA256) is stored in
`.knowledge-base.yml` document metadata.learned_hash:
- Content unchanged → skip (idempotent, zero cost)
- Content changed → hash mismatch → relearn
- **Zero-question output is never marked learned** (guarantees documents whose parsing failed are retried next round)

## 4. Training Health Checks

After every training run call `soul_status(soul_kb_id)` and inspect:
- `drafts_pending_review`: drafts awaiting approval (clear periodically)
- `total_gaps`: learning gaps (grounding_below_3 / retrieval_failure)
- `judge_divergence_count`: judge divergence (quality red line)
- `mastery`: mastery curve (question count / average score)
- `estimated_cost_usd`: budget spend (watch it above 0.12)

**Gap warning**: if retrieval_failure accounts for >30% of gaps → a retrieval configuration problem
(insufficient scope document coverage / chunk parameters); investigate rather than hard-tuning thresholds.

## 5. Approval and Evolution Golden Rules

| Draft score | Action |
|---|---|
| Groundedness ≥3 and average ≥3 | normal approve |
| Groundedness <3 or average <3 | requires force=True + a stated reason (written to audit) |
| judge_divergence flagged | reject by default (double-judge disagreement = quality in doubt) |

After approval the system automatically:
1. memory file status → approved
2. registers as a KB document + vector/graph/BM25 indexing
3. profile-summary refresh (routing basis synced)
4. audit-log entry (operator/time/scores)

## 6. Budget and Safety

- Per-SOUL independent budget of 0.15 USD/run (over-limit rejected, no overdraft)
- Routing cost has a separate global pool (route_cost_usd, not counted against the learning budget)
- All LLM calls pass through a global Semaphore(2) + circuit breaker (opens 24h after 3 consecutive failures)
- Budget checks at the learn/learn_all entries (insufficient estimate rejected)
- **Multi-persona cost is capped at ΣN×0.15**; actual cost is lower thanks to document dedup

## 7. Common Issues

| Symptom | Cause | Handling |
|---|---|---|
| learn returns skipped=1 instantly | document already learned (hash matches) | normal idempotency; use a new document |
| questions_generated=0 | parse failure (rare; fence extraction fixed) | retry; confirm it is not wrongly marked learned |
| budget_exceeded | budget exhausted | check spend via soul_status; wait for the cycle to reset |
| 0 memories, 4 gaps | document mismatched the persona's scope knowledge | normal quality gate; use more relevant documents |
| slow training | 2-3 LLM calls per question | control with limit=4; poll asynchronously |
