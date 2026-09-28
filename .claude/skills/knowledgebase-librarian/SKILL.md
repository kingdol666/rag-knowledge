---
name: knowledgebase-librarian
description: "Complete-recall librarian retrieval following ONE lean spine: layered navigation (catalog → shelf → document descriptions) to collect doc IDs, Laya/Jev judgment (batched refs ≤6 — larger bursts fail fetch fail-closed), survivor doc IDs, kb_doc_read verification, then answer ONLY from read-verified content. Literal/enumeration questions (哪些/列出所有/提到X) first run scripts/enumerate_scan.py — the semantic engine under-recalls literal mentions (measured 3/9; scanner 9/9 in ~11s). Fixed call budget ≤12, no full-library read sweeps, no criterion re-runs. Use for librarian, 逐级检索, 穷尽召回, 哪个知识库, 完整召回, Jev 判断."
---

## Related lanes

- **Vector + verify lane** → `skill://knowledgebase-search` — fast semantic candidates; default when the shelf is known and the question is factual.
- **Parallel hybrid** → `skill://knowledgebase-hybrid` — both lanes concurrently, dedup on (kb_id, doc_path), one shared gate.
- Judge engine internals → [references/laya-sdk.md](references/laya-sdk.md) · remote Jev option → [references/jev-judgment-layer.md](references/jev-judgment-layer.md)

This lane recalls by navigation, not similarity. Its promise: high recall over scanned scopes at MINIMUM latency — the spine is fixed, every step has a hard budget, and anything unscanned is reported, never silently skipped.

## Efficiency doctrine (spec, 2026-09-29 — user mandate)

1. **Every tool call must buy information.** Never repeat a call with the same tool + equivalent arguments; never call a tool whose result cannot change the outcome. Redundancy is a bug, not thoroughness.
2. **Early-exit at the layer that already knows.** If the L0 catalog descriptions show no shelf plausibly covers the question's domain, STOP THERE and return the honest not-found. Do not sweep document descriptions KB by KB, do not escalate to content scans.
3. **Honest not-found is a terminal state, not a failure.** 没有能回答该问题的知识 → 如实返回"知识库中没有对应内容"，列出已扫描的范围即止。不要钻牛角尖反复翻找知识库——效率是最重要的；一个 3 轮的诚实"未找到"远优于一个 22 轮的空扫描。
4. **Fast path first.** Literal/enumeration questions use `enumerate_scan.py` (seconds, machine-side); semantic questions use the batched judge. Never walk document bodies that the gate can fetch server-side.

## Measured engineering facts (2026-09-28, PridePrejudice 28-part bench — design constraints, not folklore)

1. **MCP is fast; LLM turns are the cost.** Every MCP call here is 0.2-15s (judge ≈ 11-15s per batch). A lean run is ~15-60s of tool time — multi-minute runs mean the executor burned LLM rounds digesting oversized outputs. Obey the budgets below.
2. **Judge refs MUST be batched ≤6 documents per call.** A 28-ref single call fires that many concurrent body fetches into web; measured result: every fetch `ConnectError` → fail-closed `unavailable`. Batches of ≤6 scored 5/5 clean.
3. **The semantic judge under-recalls literal mentions.** "Which parts mention Pemberley" (ground truth 9): instance criterion at threshold 0.5 AND 0.3 each recalled only 3/9 — semantic scoring down-weights incidental mentions. Enumeration questions need `enumerate_scan.py` (literal match: 9/9 in 11.3s, zero agent context).
4. **Machine-consumed output needs `--raw`.** The default 4000-char truncation cuts JSON mid-string; anything you will parse must use `--raw`. Pass payloads with backslash paths via `@file` (shell argv mangles `\`).
5. **One judge pass, one criterion.** `criterion=evidence` on an enumeration question scores 111/111 segments above threshold (boilerplate survives too) — a wasted round. Pick the criterion from query shape BEFORE calling; never re-run to "try another mode".

## Execution contract (all harnesses)

**Preflight — verify MCP is truly connected, then work.** One call before anything: hosts with native kb-mcp tools use their tool listing (`mcp__kb-mcp__*` / `mcp__kb_mcp_*`); script transports run the connectivity probe (`python scripts/mcp_call.py --tools`, ~0.2s). Not connected → report "kb-mcp not connected" and stop. Never bypass via direct HTTP to backend/web; never fetch tokens yourself — auth belongs to the MCP server.

**Subagent retrieves, main agent answers.** With a subagent tool, spawn exactly ONE retrieval subagent. Hand it: the question, the scope, this skill, and the budget block below. The subagent returns the retrieval result (doc IDs + evidence notes) — never document bodies, never the user-facing answer. The main agent answers from that result. Without a subagent tool, run the same spine in-process.

```text
Librarian retrieval for: <question>
Scope: <KB ids/names | all shelves>
Execute skill://knowledgebase-librarian yourself, MCP tools only, fixed spine:
preflight → kb_list → kb_get_documents(--raw) → [enumerate_scan.py | batched
kb_laya_judge] → survivor doc IDs → kb_doc_read survivors (≤2000 chars each)
→ return RESULT.
Hard budget: ≤12 MCP calls total; docread only survivor docs; ONE judge pass;
NO full-library reading, NO criterion switching, NO include_text=true.
Do not answer the question; do not return full document text.
```

**Scripted steps — the only two, both MCP-only.** `scripts/enumerate_scan.py` (literal recall layer; reads bodies via `mcp_call kb_doc_read` machine-side and assembles judge payloads — every content byte still passes through the MCP server) and `kb_laya_judge` (verify gate; fallback `scripts/jev_filter.py` under `backend/.venv/Scripts/python.exe` only when the MCP judge is unavailable). No other runner exists or may be created — the removed 2026-09-28 runner was banned for self-fetching tokens and hitting the backend directly. Never assemble your own client.

## The spine (preflight → L5)

**Preflight · connectivity (1 call, ~0.2s).** See contract above. Already verified this session (e.g. by the dispatcher)? Skip — do not re-probe.

**L0 · Catalog (1 call).** `kb_list(lightweight=true)` — read every KB's id + name + description + doc_count. Match the query's subject × attribute × constraints: keep every `relevant`/`possible` shelf; prune `out_of_scope` only on a present, trustworthy description. Guessing KBs by name is forbidden.

**L1 · Description sweep — the doc-ID layer (1 call per shelf).** `kb_get_documents(lightweight=true, kb_id)` with `--raw`; collect every doc_id/doc_path + description. Group `(part k of N)` siblings for reasoning; keep every concrete ID. Normalize `\` vs `/` when passing paths between tools. Descriptions are claims, not facts (measured: 24/26 novel-part descriptions read "Gutenberg front/back matter" while the parts held chapters) — never prune on description alone.

**L2 · Query-shape routing (zero calls).**
- **Enumeration / literal-mention** ("哪些/列出所有/提到 X/出现 Y"): run `enumerate_scan.py --kb-id <uuid> --terms <literal terms> [--docs-json <L1 output>]`. It scans every doc via MCP machine-side and returns hit doc IDs + evidence windows. This is the recall layer — expect ~0.5s/doc.
- **Semantic / evidence** ("怎么排查/为什么/如何/X 是什么"): go straight to L3 with the full candidate set.
- Compound question: do the scan, then judge the union.

**L3 · Verify gate — Laya/Jev judgment (1-5 calls, ONE pass).**

```text
kb_laya_judge(query=<question>, criterion=<picked from query shape>,
              threshold=<0.3 enumeration | 0.5 semantic>,
              documents='[{"kb_id":...,"doc_path":...}, ...]')   # ≤6 refs per call
# batches of ≤6, run sequentially; aggregate survivors across batches
# → {status, real_engine, scored_count, survivor_count, docs_with_yes,
#    survivors[](doc_path + start_line/end_line + score), evidence_pack, errors[]}
```

`documents` is a JSON-encoded **string** (double-encoded), never an inline array — measured: a plain array is pydantic-rejected server-side and burns a call (build the payload with `json.dumps` into a file, call with `@file`). `enumerate_scan` hits go to the gate too (semantic confirmation + best-segment provenance) unless the question is purely literal — then the scan IS the verdict and the gate may be skipped (record that choice in RESULT). Fail-closed: `unavailable`/`error` rejects, never implicit pass; on engine error retry ONCE after checking for stray python/torch processes; still failing → BLIND_SPOTS. Every yes survivor is kept: no doc-level cut, no re-scoring, no pruning.

**L4 · Read — survivors only.** Evidence comes in two forms, both already `kb_doc_read` verbatim: scanner `windows` (machine-read — citable evidence for every hit) and in-context `kb_doc_read(kb_id, doc_path, max_chars≤2000)` aimed at the docs the answer will lean on (prefer judge `start_line` provenance). There is no fixed cap — read what the answer needs, cite the rest from scanner windows; docs whose read contradicts their verdict stay in RESULT, labelled unverified.

**L5 · Result — compose and stop.** Return the retrieval result below. Answer strictly from read-verified content with verbatim quotes + doc_path citations. Unscanned scopes are blind spots, not assumptions.

## Early exit — honest not-found (terminal, by design)

Zero plausible candidates at L0+L1 (or a zero-hit scan on a kept shelf): STOP, return the honest not-found — shelves scanned, descriptions read, why nothing matches. This is the CORRECT answer when the knowledge does not exist; do not keep digging. Do not escalate to full-content reads, do not switch lanes, do not loop, never answer from prior knowledge.

## Retrieval result (subagent → main agent)

```text
RESULT
- <kb_id> | <doc_id> | <doc_path> | <score/literal-count> | <1-2 line evidence note from the read>
SCANNED shelves=<n> descriptions=<n> candidates=<n> judged_segments=<n> survivors=<n> read_verified=<n>
CALLS <actual MCP call count> ELAPSED <tool-time s>
BLIND_SPOTS <unscanned shelves/docs / engine errors / unverified survivors>
```

Final-answer shape (main agent): `Search Paths` (L0-L4 counts, gate backend/criterion/threshold) → `Answer` (synthesized from read-verified survivors, key facts quoted verbatim) → `Sources` (KB + doc_id/doc_path + quote) → `Confidence` (coverage-based) → `Blind Spots`. Partial scans are labelled partial, never exhaustive.

## Never

- Re-probe a verified connection, restart services, or bypass MCP with direct HTTP / self-fetched tokens.
- Read a whole library into your context (the 28×40k-char sweep measured 735k tokens and ~10 minutes for what the scanner does in 11s).
- Re-run the gate with a different criterion/threshold to "improve" a verdict you dislike.
- Send >6 refs in one judge call.
- Call `kb_search_vector` / `kb_search_two_stage` inside this lane (hand off to the vector lane only when the caller explicitly chooses vector-first).
- Let the subagent write the user-facing answer, or answer anything not backed by a read.
