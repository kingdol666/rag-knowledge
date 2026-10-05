# SOUL-RAG Strategy Reference — Complete Decision Guide for Retrieval + Persona Augmentation

> Authoritative details for the soul-rag skill. Answers "when to apply SOUL augmentation, how to augment, and how to degrade gracefully".

## 1. Three Q&A Modes (choose by need)

| Mode | Trigger | Flow | Returns |
|---|---|---|---|
| **Pure retrieval** | "look up / search / find XX material" | kb_search_two_stage | raw snippets |
| **Persona Q&A** | "answer with persona XX / in XX's voice" | soul_ask (explicit persona) | persona-ized answer + citations + PAS |
| **Retrieval + persona augmentation** | "look up XX, then summarize/answer with a persona" | kb_search → soul_ask (context_override) | evidence + persona-ized answer |

## 2. The Full Auto-Routing Chain

```
query + task_goal + task_type
  → soul_router:
     (query_hash, task_type) TTL cache → on hit, return directly
     → soul_list (template excluded) → candidates
     → >8? domain_labels embedding cosine pre-filter to top8
     → read profile-summary (cached; refreshed after learn/approval/reflect)
     → LLM scoring (route_weight weighted, ≤8 candidates)
     → top1 score ≥ 0.6 → selected; otherwise route_uncertain
     → complete() failure → embedding cosine fallback (marked embedding_fallback)
     → router-log.jsonl audit
  → soul_ask(soul_kb_id=top1): persona injection + in-scope retrieval + memory summary + synthesis + PAS
```

**Routing quality measurement**: the calibration script `scripts/soul/calibrate.py` uses
`backend/app/data/router-test-queries.jsonl` (≥20 entries) to measure accuracy,
target ≥80%. The report is written to `reports/router-calibration-YYYYMMDD.md`.

## 3. When to Use context_override

| Scenario | Usage |
|---|---|
| Persona summary after cross-KB retrieval | kb_search_two_stage(balance_kbs=True) → snippets → context_override |
| User supplied documents/snippets | Inject them directly as context_override |
| Multi-turn conversation background | Essence of prior answers → context_override (valid for this call only) |
| Knowledge outside the persona's scope | Retrieve globally for evidence first, then inject it for that persona to process |

**Injection format**: plain-text snippets (≤1000 chars), annotated with source paths. The persona answers
based on them; citation anchors are still validated against real paths.

## 4. Degradation Path (quality degradation ladder)

```
1. soul_ask normal → persona-ized answer + citations + PAS
2. Routing uncertain (route_uncertain=true) → return the candidate list for the user to choose
3. Retrieval failed (citations=[]) → the persona honestly declares blind spots + gives retrieval suggestions
   (the persona still explains in its own style that "the knowledge base has no relevant evidence"; it does not fabricate)
4. harness unavailable → readable error prompting a retry
```

**Degrade to ordinary retrieval**: the user only wants raw snippets, or the persona system is unavailable →
call kb_search_two_stage directly; do not force a persona onto it.

## 5. Integration with Knowledge-Base Capabilities

SOUL-RAG reuses existing knowledge-base capabilities:
- Retrieval: two_stage (BM25+vector+graph fusion) — the same stack as knowledgebase
- Indexing: approved persona memories go through the same indexing pipeline (vector+graph+BM25)
- Graph: persona documents/memories also enter the graph; cross-KB neighbors are expandable
- Budget: routing cost has its own separate pool, independent of the learning budget

**The persona is a "processing layer over retrieval results", not a replacement for retrieval**: persona answers
without retrieval evidence are blocked by the quality gate (groundedness); this is the root of hallucination prevention.

## 6. End-to-End Example

```
User: "Look up the MXene energy storage mechanism (MXene 储能机理) and answer with the research persona"
  → kb_search_two_stage("MXene energy storage mechanism (MXene 储能机理)", kb_id="Materials-Science")
  → hits snippets (score≥0.5)
  → soul_router("MXene energy storage mechanism (MXene 储能机理)", task_type="literature review (文献综述)") → soul-材料学 (0.95)
  → soul_ask(query, soul_kb_id="soul-材料学", context_override=<snippets>)
  → answer: research style, conclusion first then argumentation + citations + PAS 5.0
```

## 7. Operations Notes

- A stale persona profile degrades routing: the system auto-refreshes profile-summary after training/approval/reflection
- Calibration requires ≥20 entries; prompt changes automatically trigger a calibration rerun
- The routing log router-log.jsonl audits every decision (including threshold/confidence)
- Bringing a new persona online: soul_init → soul_learn on 1-2 documents → add 2 routing test-set entries
  → verify via calibration
