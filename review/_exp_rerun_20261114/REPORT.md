# 100-Paper Re-ingest + Tiered Retrieval Rerun (2026-11-14/15)

## Verdict

- **Corpus**: 100/100 arXiv papers on disk as 328 markdown parts across the
  five domain libraries (计算机与人工智能 137 / 自然科学与地球科学 75 /
  生命科学与医学 53 / 工程与能源 39 / 经济与社会 24).
- **Descriptions**: 328/328 part docs carry content-derived descriptions
  (>=60 chars, zero "arXiv paper {stem}" placeholders left) — skill A3c
  satisfied by the earlier organisation round; verified via
  `desc_audit.json` (PyYAML parse of each `.knowledge-base.yml`).
- **Retrievability (scoped vector probe, short title query, top-8)**:
  **100/100 HIT** after repair. Best rank distribution recorded in
  `probe5_final.json` (probe5b log: `hit=100/100 miss=0`).
- **Tiered gold run (BQ01–BQ10)**: vector **rank-1 = 10/10**, Hit@5 = 10/10;
  kb_laya_judge **real engine 10/10**; **gold present in judged survivors /
  evidence pack: 10/10** (`gold_bq_retry.json`, FINAL SUMMARY line).

## What was actually wrong before this run (and what I did)

1. Historical "79 retrievable / 21 not" (2026-10-13 snapshot) is stale: all
   100 papers are now on disk. But the vector index had drifted:
   - 17/100 failed the title probe before repair.
   - Fix A: `kb_reindex(force=true)` on all five libraries (async tasks
     polled to done) → +3 papers.
   - Fix B: explicit `kb_index_document` on 14 papers' parts (library-
     relative forward-slash paths) → +2 papers.
   - Remaining 14 "misses" were measurement-tool artifacts, not index state
     (see below). After fixing the probe tooling: 100/100.
2. **Product bug fixed (kb-mcp/server.py)**: judge reference-mode fetch sent
   `kb_id+doc_path` for prefixed paths; the web layer 400s that combo
   ("doc_id, path, or kb_id+doc_path is required") — it expects `path`.
   `_fetch` now routes prefixed paths via `path=` (bare names keep
   `kb_id+doc_path`). Resident kb-mcp :8000 restarted to load the fix;
   BQ01 immediately judged with `real_engine=true`.
3. **Measurement-tool bugs fixed (scripts/mcp_call.py + probe harness)**:
   - SSE reader treated each `data:` line as a whole message, truncating
     large responses mid-JSON (~3.2–3.4K); now accumulates all `data:` lines
     per SSE event (spec-compliant).
   - Default tool-side `--max-chars 4000` truncated big outputs; reruns use
     `--max-chars 200000`.

## Tiered gold protocol (per question, scripted, no gold leakage into queries)

1. Route: content prefix → owning library (equivalent to full route-card
   catalogue routing).
2. Gather: `kb_search_vector(kb_id=<lib>, query=<question text>, top_k=30)`.
3. Judge: `kb_laya_judge(query, documents=[{kb_id, doc_path}×5])` reference
   mode (server fetches bodies itself; fail-closed).
4. Gold hit: gold arXiv id appears in survivor provenance or evidence pack.

| qid | field | gold (arXiv) | vector rank | judge real | survivors | gold hit |
|---|---|---|---:|---:|---:|---|
| BQ01 | artificial-intelligence | 1706.03762 | 1 | true | 9 | ✅ |
| BQ02 | quantum-physics | 1801.00862 | 1 | true | 3 | ✅ |
| BQ03 | clinical-medicine | 2212.13138 | 1 | true | 3 | ✅ |
| BQ04 | genomics | 1602.01876 | 1 | true | 4 | ✅ |
| BQ05 | economics | 1512.08067 | 1 | true | 3 | ✅ |
| BQ06 | climate-science | 1503.07557 | 1 | true | 6 | ✅ |
| BQ07 | nlp (MameLoshnLM) | 2608.05850 | 1 | true | 4 | ✅ |
| BQ08 | materials | 2408.09942 | 1 | true | 6 | ✅ |
| BQ09 | robotics | 2410.10669 | 1 | true | 10 | ✅ |
| BQ10 | immunology | 2604.01385 | 1 | true | 3 | ✅ |

## Honest limits

- Routing here is scripted prefix→library (equivalent to the A0 full-card
  route); it is not an independent LLM agent-routing benchmark.
- Gold-string containment / survivor presence is a retrieval proxy, not
  semantic answer accuracy.
- These BQ numbers are on the 10-question BQ set (different corpus/question
  family from the 72-question routing corpus used for A0/A0h in the paper);
  they must not be mixed into the paper's E3/E5 tables.

## Artifacts

- `probe5_final.json` / `probe5b_log.txt` — 100/100 final probes.
- `desc_audit.json` — 328/328 description compliance.
- `gold_bq_retry.json` — per-question tiered results (final).
- Scripts: `run100_probe.py`, `run100_stage2.py`, `run100_stage3.py`,
  `run100_stage4.py`, `run100_stage5.py`, `run100_gold.py`,
  `run100_gold_retry.py` (review/experiment-redesign-20261101/scripts/).
- Code fixes: `kb-mcp/server.py` (judge fetch path drift),
  `scripts/mcp_call.py` (SSE accumulation).
