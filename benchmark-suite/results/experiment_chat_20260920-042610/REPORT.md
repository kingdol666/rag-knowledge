# Final Report — 10-Question × 3-Track Experiment (chat API, harness=claude)

Run: `results/experiment_chat_20260920-042610/` · launched via `scripts/start_experiment.py`
· 30 monitored runs, 0 failures · 2 self-heal events (service restart + retry, logged).

## Correctness (gold-keyword check against qa_questions.json)

| Track | Gold-kw ≥1 | Substantively correct | Errors | Notes |
|---|---|---|---|---|
| **A · Platform (external chat API, QDCVR)** | **10/10** | 10/10 | 0 | full skill flow; 2 answers contain honest caveats |
| **B · Bare agent** | 9/10 | 10/10 | 0 | BQ05 paraphrased without the literal keyword |
| **C · Agent-executed dense RAG** | **10/10** | 10/10 | 0 | grounded in retrieved chunks, cited chunk ids |

## Monitored usage (per-track totals)

| Track | Avg latency | Avg tool calls | Tokens in (Σ) | Tokens out (Σ) | Cost (Σ) |
|---|---:|---:|---:|---:|---:|
| A | ~245 s | 7.6 | 1,850,231 | 20,322 | $10.10 |
| B | ~122 s | 3.7 | 995,697 | 5,660 | $4.96 |
| C | ~94 s | 2.5 | 846,576 | 4,906 | $4.36 |

(Full per-run table with cache-read tokens: `SUMMARY.md`.)

## Observations

1. **Track A answered correctly on all 10 questions through the external API**
   (`POST /api/claude/chat`, engine=claude, read-only tool allowlist) — the QDCVR
   flow ran end-to-end behind the product interface, including gate reads and
   offset continuations.
2. **Track C (agent-executed dense RAG) went 10/10** — the agent performed the
   vector searches itself and grounded every answer in retrieved chunk text,
   citing chunk file names.
3. Track B's single keyword miss is a literal-string artifact: the answer is
   substantively correct but paraphrases "Unified Growth Theory".
4. Latency ordering A > B > C reflects protocol depth (QDCVR gate reads vs.
   direct file reads vs. two vector calls). Token consumption follows the same
   ordering; cache reads significantly discount A's repeated system prompts.
5. Two mid-run nuxt dev crashes were transparently recovered by the runner's
   self-heal (restart + single retry), and both retried runs passed.
