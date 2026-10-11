---
name: knowledgebase-hybrid
description: "Hybrid retrieval in ONE orchestrated MCP call: kb_hybrid_search runs both lanes server-side (vector wide-net + every-shelf catalog), merges on (kb_id, doc_path), caps candidates (both-lane first, vector top8, catalog top4), judges through the REAL Laya engine gate (batched ≤6, fail-closed), applies the doc-level cut with cross-domain anchor guard, reads the top kept docs, and returns the full evidence structure — the agent only synthesizes the cited answer. Use for 混合检索, hybrid retrieval, dual-lane retrieval, vector and catalog, when vector recall alone is not trusted and the complete-recall scan alone is too slow."
---
## ⭐ Related Skills

- **Vector + Jev-gate lane** → `skill://knowledgebase-search` — fast semantic proposal + engine verify gate
- **Complete-recall lane** → `skill://knowledgebase-librarian` — catalog/read/Jev, exhaustive navigation
- Document ingest → `skill://knowledgebase-ingest` — produces the descriptions the catalog lane relies on

## The default path: one call (measured 2026-10-07)

**`kb_hybrid_search(query, kb_scope="", candidate_cap=12)` is the entire flow.** The orchestration runs server-side (dual-lane fetch → merge+cap → batched Laya judge → doc cut → top-5 reads) in ~20s machine time; measured full-library hybrid_recall 0.875 with judge verification. The calling agent's ONLY jobs:

1. Call `kb_hybrid_search` once with the (bilingual-cleaned) query.
2. Synthesize the user-facing answer from `cut.kept` + `reads` — every claim cited as `doc_path + lane + engine score`.
3. Report: `merge` counts (from_both/from_vector_only/from_catalog_only/pre_filtered), `judge` (real_engine, batches, errors), `cut` (kept/dropped), plus `Confidence` and `Blind Spots` (pre_filtered docs were NOT judged — they are reported, never silently dropped; zero kept = honest engine-level not-found).

Do NOT re-implement the lanes with kb_search_vector / kb_get_documents / kb_laya_judge calls — that is the slow exploration path below, kept for debugging and for harnesses without the orchestration tool.

## Interpretation notes

- **Cross-domain anchor guard** is built in: docs sharing zero keyword tokens with the query cannot set the cut anchor (measured: lithium docs scored 0.919 on a PV question and used to cut the relevant POE). Off-domain docs may still survive on absolute score — name them in Blind Spots and do not cite them.
- **`enable_judge=false`** returns an unjudged preview (lanes+merge only) — label every such answer "预览，未经判卷验证".
- **Judge error / unavailable** is fail-closed: report it, never implicit pass.

## Exploration path (debug / no orchestration tool)

The original phase spine survives for manual tracing — vector lane `kb_search_vector(top_k=30, threshold=0.35, balance_kbs=true)`; catalog lane `kb_list` → `kb_get_documents(lightweight)` per shelf with description-overlap ranking; merge on `(kb_id, doc_path)`; `kb_laya_judge(criterion=evidence, threshold=0.5)` refs ≤6/batch, ≤2 in flight; doc cut best−0.10 + top-5 floor; `kb_doc_read` top kept docs. All constraints from the NEVER list below still apply to this path.

## ⚠️ NEVER list

| ❌ Don't | Why | ✅ Do instead |
|---|---|---|
| Wrap retrieval in bash/eval/curl or maintenance scripts | Off-contract transport; measured 27-min stall | MCP tools via the harness mechanism only |
| Re-run the manual lanes when `kb_hybrid_search` is available | 8 LLM turns ≈ 480s vs one 20s call | One orchestrated call |
| Hide `pre_filtered` / dropped docs | Pre-filter is not a verdict | Report counts in Blind Spots |
| Dedup on `doc_path` alone | Same path can exist in two KBs | Key on `(kb_id, doc_path)` |
| Answer from unscored text (unless enable_judge=false preview, labelled) | The engine verdict is final | Cite from cut.kept/reads; zero kept = honest not-found |
| Cite off-domain high-scorers without a caveat | Cross-domain inflation is real | Name them in Blind Spots |

## Quick rule reference

1. **One call**: `kb_hybrid_search(query, kb_scope?, candidate_cap=12)` → synthesize from `cut.kept` + `reads`
2. **Citations**: doc_path + lane + engine score; evidence_pack/reads are the verified text
3. **pre_filtered and dropped are reported**, never silent
4. **Zero kept = honest engine-level not-found** — never fabricate
5. Manual lane spine = exploration/debug only
