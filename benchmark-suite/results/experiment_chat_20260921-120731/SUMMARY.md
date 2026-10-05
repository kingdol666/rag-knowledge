# Three-Track Retrieval Experiment (chat, harness=claude)

Generated 2026-09-21 12:08 UTC · same 50-paper corpus · questions: 1 · tracks: a

## Run monitor

| QID | Track | Latency s | Tools | Tokens in | Tokens out | Cache read | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| BQ06 | a | 59.7 | 9 | 90977 | 1361 | 238080 | 0.60795 |

**Totals**: latency avg 59.7s · tokens in 90977 · out 1361 · cost $0.6079

## Verbatim answers

### [a] BQ06 — 59.7s, 9 tool calls, tokens out 1361

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

I need to stop and be straight with you rather than keep retrying.

**I could not retrieve the answer, and I should not guess at it.**

What happened:

1. **The kb-mcp tools load but do not execute.** The tool schemas resolved fine (`kb_search_stats`, `kb_search_vector`, `kb_search_two_stage`, `kb_search`, plus graph search), but every actual invocation — including a trivial `query: "test"` — returns the same string: `experiment read-only`. That is not a search result, not an empty result set, and not an error from the KB. It's a gate that intercepts every call before the MCP server sees it. `kb_search_stats` with no arguments, which normally returns index statistics, returns the same thing.

2. **The fallback path is blocked the same way.** Per pitfall #14 in the project instructions, when MCP is unusable I should check backend health (`http://localhost:8765/api/v1/health`) and the web proxy (`localhost:6789`). A `curl` for both returned `experiment read-only` — so the interception is at the tool-execution layer, not specific to kb-mcp.

3. **Net effect:** both the MCP-first path (required by the "MCP 优先原则") and the HTTP fallback path are unavailable to me in this session. I have no way to read `.tree-fs.json`, `.knowledge-base.yml`, or any indexed chunk.

**On the question itself.** "Which physical factor primarily controls the response of precipitation extremes to climate change?" is a real and well-posed climate-physics question, and I have a general prior about it (the answer usually turns on how near-surface temperature constrains moisture availability, i.e. the thermodynamic scaling of extreme precipitation with warming). But the whole point of asking me to search the KB is to get the answer *from your documents*, with the source references this KB is built to provide. Answering from my own prior would be exactly the fabrication the retrieval contract exists to prevent — I'd be inventing citations to KB documents I never read, and I cannot tell you which KB or paper in your collection covers this. So I'm not going to state an answer as if it came from the KB.

**To unblock this**, one of:

- Lift or reset the `experiment read-only` gate on tool execution, then re-run this question and I'll do the retrieval properly (vector → two-stage → content verification via `kb_doc_read`).
- Or confirm the gate is intentional and tell me explicitly that you want a from-general-knowledge answer, clearly labeled as **not** sourced from the KB.

Tell me which, and I'll proceed.
