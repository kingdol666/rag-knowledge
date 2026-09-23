# Three-Track Retrieval Experiment (chat, harness=claude)

Generated 2026-09-20 03:40 UTC · same 50-paper corpus · questions: 1 · tracks: a, b, c

## Run monitor

| QID | Track | Latency s | Tools | Tokens in | Tokens out | Cache read | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| BQ01 | a | 563.2 | 12 | 188578 | 1946 | 128 | 4.1745909999999995 |
| BQ01 | b | 0 | 0 | — | — | — | — |
| BQ01 | c | 0 | 0 | — | — | — | — |

**Totals**: latency avg 563.2s · tokens in 188578 · out 1946 · cost $4.1746

## Verbatim answers

### [a] BQ01 — 563.2s, 12 tool calls, tokens out 1946

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

The knowledge base retrieval failed at the transport layer — the Archival agent's MCP calls all returned a read-only sentinel rather than data, so no source-grounded answer could be produced.

## Search Paths
Phase 0 rewrite ("Transformer computes attention via scaled dot-product self-attention, replacing recurrence and convolution for sequence modeling") → Phase 1 `kb_search_vector(kb_id="", top_k=10, score_threshold=0.35, balance_kbs=True)` → **0 candidates returned**. Phase 2 prerequisites (`kb_list(lightweight=true)`, `fs_get_tree`, `kb_tags_list`) also returned no data, so the librarian fallback could not run and `kb_doc_read` + `0-8 scoring` were never executed — the content gate is **unexecuted, not passed**.

## Answer (No Confirmed Hit)
**The knowledge base cannot currently answer this question.** The retrieval layer returned no readable data in this session, so I cannot give you a source-referenced answer.

⚠️ Explicitly **not** from the collection — for orientation only, from general knowledge: the canonical treatment is Vaswani et al., *"Attention Is All You Need"* (NeurIPS 2017), which defines scaled dot-product attention as `Attention(Q,K,V) = softmax(QKᵀ/√d_k)·V`, and argues that replacing recurrence/convolution with pure attention shortens the path between any two positions to O(1) and permits full parallelization over sequence positions, at the cost of O(n²) complexity per layer. **I could not verify that this paper, or any explanation of it, exists in your collection.** Treat it as an unsourced answer.

## Sources
**None.** No document was read; I will not cite paths that were never retrieved.

## Confidence
**Low** — after content verification P0:0 / P1:0 documents. Zero candidates from both the vector lane and the librarian prerequisites. The failure is at the **tool-transport layer**, not a judged "no match."

## Blind Spots (Cross-Library Perspective)
- **Retrieval-blind, not corpus-blind.** This is a tooling failure, not evidence of absence — the collection may well hold a Transformer/attention document. Do not read this as "the library lacks attention material."
- **Unverified sub-domains the query touches:** the attention mechanism itself (scaled dot-product formulation, multi-head decomposition, positional encoding), the complexity argument (O(n²·d) per layer vs. O(n·d) sequential steps for recurrence), path-length/inductive-bias trade-offs vs. convolution, and the empirical machine-translation evidence.
- **Libraries that may hold relevant content but were not hit:** all of them — `kb_list(lightweight=true)` returned nothing, so no KB can even be named. Manual recheck recommended.
- **Transporant note:** every MCP call (`kb_project_status`, `kb_list`, `kb_search_vector`, `kb_search_two_stage`, `fs_get_tree`, `kb_tags_list`, `backend_status`) returned the same read-only sentinel — this session appears to have KB read access disabled, or kb-mcp is not serving data.
- **Contested/timeliness:** the original 2017 motivation is now partly contested — efficient-attention variants (sparse/linear/FlashAttention) and state-space/hybrid models have altered the recurrence-vs-attention trade-off. Any document in the collection should be checked for date.

**To get a real answer:** enable MCP read access (or restart Claude Code so `kb-mcp` reconnects), then re-issue the question — I'll rerun the search against the actual corpus.

### [b] BQ01 — 0s, 0 tool calls, tokens out —

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

(track failed: ConnectionResetError: [WinError 10054] 远程主机强迫关闭了一个现有的连接。)

### [c] BQ01 — 0s, 0 tool calls, tokens out —

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

(track failed: URLError: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>)
