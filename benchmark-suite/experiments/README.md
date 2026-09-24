# experiments — agent tracks + reproducible baselines

One external corpus (100 exported papers), one answer channel (the platform's
`POST /api/claude/chat`), many retrieval methods. Only the retrieval affordance
differs, so answer differences are attributable to retrieval, not to the harness
or the answering prompt.

## Tracks

| Track | Mode | Tools | cwd |
|---|---|---|---|
| `a` | platform + file tools | `kb_*` **and** Read/Grep/Glob | corpus dir (sandboxed) |
| `a2` | **platform only** (default, leakage-free) | `kb_*` only | repo root (harmless: no file tools) |
| `b` | bare agent | Read/Grep/Glob | corpus dir |
| `c` | dense RAG | `kb_search_vector` only | repo root |

`a − a2` isolates the marginal value of the file tools. `a2` is the primary
platform arm because it cannot read the answer key (see below).

## Baselines (`--tracks bm25,vector,rrf,rerank,crag,selfrag`)

| Method | What it does |
|---|---|
| `bm25` | Okapi BM25 over the 100 corpus documents (local index) |
| `vector` | dense top-k via `POST /api/v1/search/vector` on `Corpus-Chunks800` |
| `rrf` | reciprocal-rank fusion of `bm25` + `vector` (k=60) |
| `rerank` | vector top-30 → listwise LLM rerank → top-10 (CE-reranker stand-in) |
| `crag` | vector → LLM evaluator (Correct/Incorrect/Ambiguous) → keep Correct, else rewrite + re-retrieve (simplified) |
| `selfrag` | vector → LLM sufficiency reflection → on-demand re-retrieval (≤2 rounds) (simplified) |

All baselines retrieve locally, pack a fixed 4 000-char evidence bundle, then
answer through `chat_tracks.answer_closed_book` — the same chat API with no
tools. `crag`/`selfrag` are simplified re-implementations, **not** the authors'
original code; the report must say so.

## Answer-key isolation (internal validity)

The gold answers live under the repo (`data/papers/qa_questions*.json`,
`results/experiment_chat_*/SUMMARY.md`). A track that can Read/Grep the repo
root could read the key. Guard: file-tool-bearing tracks are pinned to the
corpus directory, and the platform-only arm carries no file tools.
`chat_tracks` asserts this at import time and refuses to build a leaking track.

## Prompt neutrality

One task template, one slot for the affordance (`PROMPT_VERSION = "v3-neutral"`).
Older runs: `v1` (unfair length caps), `v2-fair` (identical contract, per-track
role prompts). Runs declare their version in the manifest.

## Launch

```bash
cd benchmark-suite

# quick smoke (3 questions, tracks a2,b,c)
python -m experiments.runner --fast

# full fair set on a question file
python -m experiments.runner --questions data/papers/qa_questions_r2.json --tracks a2,b,c

# baselines only
python -m experiments.runner --questions data/papers/qa_questions_r2.json \
    --tracks bm25,vector,rrf,rerank,crag,selfrag

# what can I run?
python -m experiments.runner --list-tracks
```

Prerequisites: backend (8771) + web (6789) healthy and indexed (PIPELINE
stages V0–V3), `storage/loop-auth.json` present. Order is randomised per
question (`--seed`, disable with `--no-shuffle`); the self-heal web restart is
off in `--fast` and `--no-selfheal`.

## Unified launcher (recommended)

`benchmark-suite/exp.py` is the one-command entry point: same question, project
vs baselines, side-by-side output + resource monitoring.

```bash
cd benchmark-suite
python exp.py "Which three ontologies subdivide the Gene Ontology?"
python exp.py --questions data/papers/qa_v2.json --limit 10
python exp.py --fast                 # 1 question, project a2 + 4 baselines
python exp.py --full                 # a,a2,b,c + 6 baselines
python exp.py --monitor-system       # + CPU/RSS/GPU sampling (needs psutil)
python exp.py --check                # platform preflight only
python exp.py --dry-run              # wiring check — NO API call, placeholder cells
python exp.py --report <run_dir> --questions data/papers/qa_v2.json
```

It preflights the platform, runs `runner.execute(...)`, then builds
`COMPARE.md` + `monitor.json` and prints a console comparison table.

## Output

Every run goes to the canonical `results/runs/<run_id>/` (run_id =
`run-<utc-ts>-<gitsha>`), never overwritten in place.

| file | contents |
|---|---|
| `track_<method>_<qid>.json` | one cell: answer, tool calls, latency, tokens, cost |
| `run_manifest.json` | provenance (git, config hash, prompt version, seed, max_turns, totals, dry_run) |
| `SUMMARY.md` | run monitor table + verbatim answers |
| **`COMPARE.md`** | **per-question project-vs-baseline table + resource monitoring + functional verification + self-checks** |
| **`COMPARE.html`** | **self-contained visual dashboard (sortable, filterable, light/dark)** |
| `monitor.json` | machine-readable `COMPARE.md` |

`COMPARE.md` / `COMPARE.html` sections: resource-monitoring totals · functional
verification (retrieval gold-hit rate, citation gold-hit rate, abstention count) ·
per-question side-by-side (with full verbatim answers) · consistency self-checks
(missing cells, duplicates, errors, cost reconciliation, cell count, provenance).

A dry-run run is stamped `dry_run: true` everywhere and shows a warning banner in
the HTML — it must never be reported as a real result.

## Verify the pipeline without the platform

```bash
python scripts/117_pipeline_selfcheck.py      # 39 checks, offline, 0 API calls
```
