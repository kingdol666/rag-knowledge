# Three-Track Retrieval Experiment (chat, harness=claude)

Generated 2026-09-20 03:56 UTC · same 50-paper corpus · questions: 1 · tracks: a, b, c

## Run monitor

| QID | Track | Latency s | Tools | Tokens in | Tokens out | Cache read | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| Q1 | a | 202.6 | 6 | 179046 | 1319 | 66368 | 0.9613889999999999 |
| Q1 | b | 79.7 | 3 | 117689 | 433 | 0 | 0.59927 |
| Q1 | c | 0 | 0 | — | — | — | — |

**Totals**: latency avg 141.2s · tokens in 296735 · out 1752 · cost $1.5607

## Verbatim answers

### [a] Q1 — 202.6s, 6 tool calls, tokens out 1319

**Q:** In the paper Attention Is All You Need, what positional encoding does the Transformer use? Answer in English.

I stopped here rather than answering from memory — I need to report what actually happened.

## Result: could not retrieve from the knowledge base

**MCP status (Pre-Flight, per pitfall #14):** ✅ The kb-mcp MCP server **is connected and callable** — tool calls went through the MCP layer, no "No such tool available" error, so this is not a `.mcp.json` / connection problem.

**What failed:** Every KB tool call returned the same placeholder string instead of a real payload:

| Tool called | Arguments | Returned |
|---|---|---|
| `mcp__kb-mcp__backend_status` | — | `experiment read-only` |
| `mcp__kb-mcp__kb_list` | `lightweight=true` | `experiment read-only` |
| `mcp__kb-mcp__kb_search_vector` | query="Attention Is All You Need positional encoding Transformer sinusoidal", top_k=8, score_threshold=0.35, balance_kbs=true | `experiment read-only` |
| `mcp__kb-mcp__kb_search_two_stage` | query="positional encoding Transformer sinusoidal Attention Is All You Need" | `experiment read-only` |
| `mcp__kb-mcp__kb_list` (retry) | `lightweight=true` | `experiment read-only` |

`kb_list` is not a search tool — it performs no matching and returns a plain KB catalog synchronously. Its returning the identical string means the responses are being intercepted/replaced **before reaching the backend**, independent of query or tool. So this is not a "no documents found" outcome, not a vector-threshold issue, and not a search-strategy issue.

**Why I did not fall back:** Per CLAUDE.md rule 第五条 (MCP-first), the HTTP fallback is permitted only when MCP is *confirmed unavailable and the user explicitly allows it*. Here MCP is connected — it is responding, just not with real data — so the fallback condition is not met, and I have not been authorized to use it. I also did not substitute my own knowledge of the paper, since the request was specifically to answer *from the knowledge base*.

## What the answer would be, flagged clearly as NOT KB-sourced

I have no retrieved evidence, so I am not presenting this as a KB-backed answer. From general knowledge, not from your KB: the Transformer uses **fixed sinusoidal positional encodings** added to the input embeddings — `PE(pos,2i) = sin(pos/10000^(2i/d_model))` and `PE(pos,2i+1) = cos(pos/10000^(2i/d_model))` — chosen over learned embeddings because they are parameter-free and allow extrapolation to sequence lengths longer than those seen in training. **Treat this as unverified against your corpus**: I could not confirm that this paper is even ingested, that the search returns it, or how it is chunked. I did not read a single document.

## To unblock, one of these:

1. **Investigate the interceptor** — something in the harness is substituting tool results. Worth confirming whether this is a sandbox policy on this session, since it will silently degrade every KB task, not just this one.
2. **Authorize HTTP fallback** — say the word and I'll query `localhost:6789` directly and I'll declare the fallback explicitly in the answer, as the rule requires.
3. **Check the backend independently** — if you want, I can report on backend/service health via the shell, though that is a diagnostic step and won't itself retrieve documents.

I'd suggest option 1 — a tool layer that answers every call with a constant string, including a catalog call that does no searching, indicates a configuration problem upstream of your KB content rather than a gap in it.

### [b] Q1 — 79.7s, 3 tool calls, tokens out 433

**Q:** In the paper Attention Is All You Need, what positional encoding does the Transformer use? Answer in English.

The Transformer uses **sinusoidal positional encodings** — sine and cosine functions of different frequencies, added to the input embeddings. Specifically, `PE(pos,2i) = sin(pos/10000^(2i/d_model))` and `PE(pos,2i+1) = cos(pos/10000^(2i/d_model))`, where each dimension corresponds to a sinusoid and the wavelengths form a geometric progression from 2π to 10000·2π. The authors chose this over learned positional embeddings because it may let the model extrapolate to sequence lengths longer than those seen in training (both variants gave nearly identical results, Table 3 row E).

Source: `artificial-intelligence__1706.03762__attention-is-all-you-need.md` (Section 3.5).

### [c] Q1 — 0s, 0 tool calls, tokens out —

**Q:** In the paper Attention Is All You Need, what positional encoding does the Transformer use? Answer in English.

(track failed: NameError: name 'subprocess' is not defined)
