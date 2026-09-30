---
name: knowledgebase-search
description: "QDCVR retrieval for knowledge-base questions: rewrite the query, cast a WIDE vector net (high top_k) over the library, verify every candidate's real content through the fail-closed Laya/Jev decision gate (kb_doc_read → segments → engine scores every segment; yes = keep, no LLM re-judging), keep ALL yes docs, answer content-enhanced from the survivor set, escalate zero-survivor or complete-recall requests to the librarian lane once, and report honest blind spots or an honest not-found. Use for search, find, query, retrieve, Q&A, cross-KB, 搜索, 检索, 查询, 问答, 全库搜索, 跨知识库, or any request asking what the knowledge base contains."
---

## Related lanes

- **Complete-recall lane** → `skill://knowledgebase-librarian` — catalog/description navigation when the shelf is unknown, the vector lane missed, or the user asks for all/every/逐级检索.
- **Parallel hybrid** → `skill://knowledgebase-hybrid` — both lanes concurrently, dedup, one shared gate.
- Engine internals → [../knowledgebase-librarian/references/laya-sdk.md](../knowledgebase-librarian/references/laya-sdk.md) · remote Jev → [../knowledgebase-librarian/references/jev-judgment-layer.md](../knowledgebase-librarian/references/jev-judgment-layer.md) · platform data model → [../knowledgebase/references/kb-architecture.md](../knowledgebase/references/kb-architecture.md)
- Query-prep detail (intent table, more rewrite examples) → [references/query-prep.md](references/query-prep.md) — read it when the query is ambiguous, incident/ops-flavored, or a multi-entity comparison.

## Execution contract (all harnesses)

**Preflight — MCP-first, one call.** Start with `kb_project_status`: it verifies the MCP connection and auto-starts backend/web when they are down. If your session exposes no kb-mcp tools at all, report "kb-mcp not connected" and stop — never bypass via HTTP/curl/scripts. Tool names are prefixed per harness (`mcp__kb-mcp__*` in Claude, `mcp__kb_mcp_*` in OMP); use your host's tool listing.

**Subagent retrieves, main agent answers.** When the harness has a subagent tool (Task/Agent), spawn exactly ONE retrieval subagent, hand it the question + scope + this skill, and let it run the whole lane itself. The subagent returns the retrieval result (format below) — never document bodies, never the user-facing answer. The main agent synthesizes the final answer from that result (spot-read a doc with `kb_doc_read` to verify a quote if needed). Without a subagent tool, execute the same lane in-process — the shape never changes, only who holds the layers.

Example subagent prompt:

```text
Vector+verify retrieval for: <question>
Scope: <KB id/name | whole library>
Execute skill://knowledgebase-search yourself with MCP tools only:
rewrite → kb_search_vector wide net (slim=true) → filter → pass candidate refs
to kb_laya_judge (it fetches bodies server-side) → re-check survivor quality
→ return the retrieval result.
Zero survivors after one librarian handoff → return NOT_FOUND + what was searched.
Do not answer the question; do not return full document text.
```

**No orchestration scripts.** The only scripted step is the verify-gate fallback (`scripts/jev_filter.py` per-step, `backend/.venv` interpreter, when the MCP judge is unavailable). No end-to-end runner exists or may be created — one was removed 2026-09-28 for bypassing MCP governance with self-fetched tokens. Never assemble your own backend client; auth belongs to the MCP server.

## The lane

**Phase 0 — Rewrite before retrieving.** Extract subject × attribute × constraints, rewrite the raw query as a declarative sentence + keywords; split multi-entity/comparison queries into parallel sub-queries. Never feed the raw colloquial query to the retriever (measured: "PET film" hit PP literature). Incident/ops questions → experience search first (`experience_search_global`).

**Phase 1 — Vector wide net.**

```text
kb_search_vector(query=<rewritten>, kb_id=<named KB or "">, top_k=30,
                 score_threshold=0.35, balance_kbs=true, slim=true)
```

Whole-library default with `balance_kbs=true` stops large libraries dominating. `slim=true` keeps each hit to a 240-char snippet — screening needs only provenance, and the gate fetches real content server-side. Filter: drop chunks < threshold, dedup per normalized doc_path keeping the best chunk, then KEEP ALL deduped docs — the wide net exists so the engine can judge many documents, so no top-3 cut. Parent/sub-KB note: search the PARENT id to aggregate descendants; empty-content entries are containers, not documents. 0 results → retry once at `score_threshold=0.30`; still 0 → go to the fallback step.

**Phase 2 — Verify gate by REFERENCE (the engine decides; text stays server-side).** Pass document references — NOT bodies — to the judge:

```text
kb_laya_judge(query=<rewritten>,
              documents='[{"kb_id":...,"doc_path":...}, ...]',   # refs, no content
              criterion="auto")
# → {status, real_engine, criterion, threshold, scored_count, survivor_count,
#    docs_with_yes, survivors[](provenance+score), evidence_pack, errors[]}
```

The tool fetches every referenced body ITSELF (server-side), segments, and scores — raw document text never enters your context. A vector 0.95 whose segments all score no is discarded; a vector 0.40 with one yes survives — vector scores never overrule the engine. Fail-closed: on `unavailable`/`error` do NOT retry-storm; clean up stray python/torch processes, wait, retry once; still failing → record the blind spot.

**Phase 3 — ONE content return, then answer.** The verdict's `evidence_pack` is the merged surviving content — the only full-content return in this lane. Read it, run the quality re-check yourself (which survivors actually answer the question; incidental term-hits are labelled, kept for audit, never leaned on), and synthesize. Optionally `kb_doc_read` ONE survivor to verify a specific quote.

**Phase 4 — Retrieval result → answer.** The subagent returns the retrieval result (below); the main agent synthesizes the answer content-enhanced from the survivor set (evidence_pack + provenance; optionally one `kb_doc_read` to verify a specific quote): cite doc + KB + score, quote key numbers verbatim, annotate credibility (P0 direct / P1 partial / P2 weak).

**Fallback (once) then stop.** Zero survivors after the retry → escalate ONCE to the librarian lane (`skill://knowledgebase-librarian` — spawn a librarian retrieval subagent, or execute it yourself). Still zero → stop: honest not-found with what was searched. Never loop, never switch engines back and forth, never answer from prior knowledge.

## Early exit — honest not-found

Both lanes exhausted (or the question is out of domain for every library) → return the honest not-found immediately: what was searched (KBs, query variants, gates run), what was not found, and why. "找不到" is a valid, expected answer; minutes of doomed re-searching is a contract violation.

## Retrieval result (subagent → main agent)

```text
RESULT
- <kb_id> | <doc_id> | <doc_path> | <best_score> | <1-2 line evidence note: which facts it answers>
SCANNED queries=<n> candidates=<n> judged_segments=<n> survivors=<n> fallback=<none|librarian>
BLIND_SPOTS <unscoped KBs / engine errors / unavailable gates>
```

## Never

- Skip the rewrite or the verify gate — retrieval quality lives in those two steps.
- Let a vector score keep a document the engine rejected, or cut engine-yes survivors by hand.
- Keep searching past one librarian fallback — report honestly instead.
- Let the subagent write the user-facing answer, or invoke/create an end-to-end script.
