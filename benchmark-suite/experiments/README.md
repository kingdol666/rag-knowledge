# experiments — Agent-Executed Three-Mode Retrieval Experiment

Same external corpus (the 50 exported papers: platform category KBs, exported
`data/corpus_md/*.md`, and the `Corpus-Chunks800` dense index all derive from the
identical document set), three agent-executed retrieval modes, one launcher.

## Tracks

| Track | Mode | Agent's tools |
|---|---|---|
| `a` | **Platform KB system** | external HTTP APIs only: `POST /api/v1/search/vector`, `GET /api/kb/search`, `GET /api/kb/document` (offset-addressed continuation reads) |
| `b` | **Bare agent** | plain file tools over `data/corpus_md/` (list / full-text search / line-range read) |
| `c` | **Dense RAG** | executes real dense vector retrieval itself over `Corpus-Chunks800` (`kb_search_vector`) + full-chunk fetch; answers only from retrieved chunks |

All three use the SAME agent loop (`agent_loop.ToolAgent`): the LLM (omp oneshot)
decides tool calls step by step; the runner only executes the chosen tool and
feeds observations back. Any behavioral difference is therefore attributable to
the retrieval mode, not to harness differences.

**Evidence floor (`require_evidence=True`, all tracks)**: a final answer is
REJECTED if the agent has not executed at least one successful retrieval tool
call — answers from parametric knowledge alone are policy violations, not
results. Every rejection and every tool call is persisted in the trace JSON
(`agent_log`), so each answer is auditable down to the exact retrieval that
produced it.

## Launch

```bash
cd benchmark-suite

# single question, all three tracks
python -m experiments.runner --question "Which three ontologies subdivide the Gene Ontology?"

# from the standard question set, first 2 questions, tracks a and c only
python -m experiments.runner --questions data/papers/qa_questions.json --limit 2 --tracks a,c

# tune the per-question tool-step budget
python -m experiments.runner --question "..." --max-steps 10
```

Prerequisites: backend (8771) + web (6789) healthy and indexed
(PIPELINE stages 0–5 completed: category KBs routed, corpus exported,
Corpus-Chunks800 built); `omp` on PATH; auth in `storage/loop-auth.json`
or `MCP_AUTH_TOKEN` in `.env`.

## Output

`results/experiment_<timestamp>/` — per-track JSON traces (every tool call with
args, per-step latencies, final answer) + `SUMMARY.md` side-by-side comparison
with verbatim answers.
