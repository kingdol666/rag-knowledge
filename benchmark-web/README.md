# benchmark-web — paper-replication dashboard

A runnable RAG benchmark: **upload your own documents**, ask questions about them,
and compare eight retrieval algorithms — each with **its own tunable parameters** —
on the same corpus. Every algorithm is tagged with its provenance:

| tag | meaning |
|---|---|
| `REAL-CODE` | an actual open-source library (rank_bm25, FAISS, sentence-transformers) |
| `REAL-ALGO` | a published paper's algorithm implemented here from its description |
| `PROJECT` | this platform's own QDCVR retrieval path, called over its API |

![dashboard](dashboard.png)

---

## Quick start

```bash
# 1. backend — FastAPI on 127.0.0.1:8800
cd benchmark-web/backend
uv pip install --python .venv/Scripts/python.exe -r requirements.txt   # first time
python verify.py                                                       # dependency check
python main.py

# 2. frontend — Nuxt on 127.0.0.1:3001
cd benchmark-web/frontend
npm install                                                            # first time
npm run dev
```

Open <http://127.0.0.1:3001>. Upload files on the **Corpus** tab, ask questions on
the **Ask** tab, compare algorithms on the **Benchmark** tab. The API's own
interactive docs are at <http://127.0.0.1:8800/docs>.

The `qdcvr_*` baselines additionally need the **platform** running
(`ragctl up` in the repo root); answer generation needs the **`omp`** CLI. Both
are optional — retrieval works without either, and `/api/health` reports what is
available.

### Pointing the UI at a different backend

```bash
NUXT_PUBLIC_API_BASE=http://127.0.0.1:9000 npm run dev
```

No port, URL or model name is hardcoded: `backend/config.py` reads the monorepo's
`config.yml` and `.env` (same `env var > config.yml > default` priority as the
rest of the platform), and the front end reads the algorithm catalogue from the
API at runtime.

---

## Algorithms and their parameters

`GET /api/algorithms` is the single source of truth. Every entry publishes a
parameter schema — name, type, default, bounds, description — which drives
request validation *and* the UI's parameter panel, so the two can never drift.

| id | family | implementation | parameters |
|---|---|---|---|
| `bm25` | sparse | `REAL-CODE` rank_bm25 | `top_k`, `k1` (0–3), `b` (0–1) |
| `dense` | dense | `REAL-CODE` FAISS + BGE-M3 | `top_k`, `score_threshold` |
| `hybrid` | hybrid | `REAL-CODE` BM25+FAISS fusion | `top_k`, `alpha`, `candidate_k`, `norm`, `k1`, `b` |
| `ce_rerank` | rerank | `REAL-CODE` FAISS → ms-marco cross-encoder | `top_k`, `candidate_k`, `score_threshold` |
| `crag` | corrective | `REAL-ALGO` Yan et al., NAACL 2024 | `top_k`, `candidate_k`, `upper_threshold`, `lower_threshold`, `expand_trigger`, `expand_k`, `w_overlap`, `w_dense` |
| `selfrag` | self-reflective | `REAL-ALGO` Asai et al., 2023 | `top_k`, `candidate_k`, `threshold`, `w_rel`, `w_sup`, `w_use`, `support_gain` |
| `qdcvr_flat` | project | `PROJECT` platform API, all KBs | `top_k`, `score_threshold`, `kb_id` |
| `qdcvr_domain` | project | `PROJECT` platform API, one KB | `top_k`, `score_threshold`, `kb_id` (required) |

Aliases accepted for backwards compatibility: `vector` → `dense`,
`qdcvr` → `qdcvr_flat`, `self_rag` → `selfrag`, `cross_encoder` → `ce_rerank`.

Example — three algorithms, three different parameter sets:

```bash
curl -s -X POST http://127.0.0.1:8800/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "query": "battery thermal management",
    "methods": ["bm25", "dense", "hybrid", "crag"],
    "top_k": 5,
    "params": {
      "bm25":   { "k1": 1.2, "b": 0.6 },
      "hybrid": { "alpha": 0.3, "norm": "minmax" },
      "crag":   { "upper_threshold": 0.7, "expand_trigger": 0.4 }
    },
    "relevant": ["battery-thermal"]
  }'
```

Only the deviations from the defaults need to be sent; the response echoes the
**fully resolved** parameter set that actually ran, so a result is always
reproducible from its own record.

---

## Asking questions (answer generation)

`POST /api/answer` retrieves with the algorithm you choose, then has a model answer
**from that evidence only**.

```bash
curl -s -X POST http://127.0.0.1:8800/api/answer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the Zephyr-7 calibration constant?",
    "method": "hybrid",
    "params": { "hybrid": { "alpha": 0.3 } },
    "top_k": 5,
    "verify": true
  }'
```

```json
{
  "method": "hybrid",
  "params": { "top_k": 5, "alpha": 0.3, "candidate_k": 20, "norm": "minmax", "k1": 1.5, "b": 0.75 },
  "retrieval": { "count": 3, "latency_ms": 92.4, "results": [ … ] },
  "answer": {
    "answer": "The Zephyr-7 ionisation chamber's calibration constant is 42.7 mV per kilocount …",
    "verdict": "answered",
    "citations": [ { "source_id": "1", "doc_id": "zephyr7-calibration.md", "title": "…", "score": 0.71 } ],
    "cited_ids": ["1"], "unknown_citations": [],
    "evidence_chars": 625, "latency_s": 29.2, "grounded": true
  },
  "verification": { "score": 10.0, "grounded": true, "unsupported_claims": [] }
}
```

### Why the answer can be trusted to come from your files

* **The agent runs with no tools and no session** (`omp -p --mode=json
  --no-session --no-tools`). It cannot go and fetch anything, so the reply can
  only be built from the evidence it was handed.
* **Every algorithm is answered by the same agent, under the same prompt and the
  same character budget** (4000 chars, as in the published matrix). Answering is
  therefore peeled away from retrieval: differences in the reply are
  attributable to retrieval quality, not to a different model or instruction.
* **The prompt forbids outside knowledge** and requires an explicit
  `"verdict": "insufficient"` when the evidence does not contain the answer.
* **Citations are verified against the evidence actually supplied.** Ids the
  model invented are dropped and reported in `unknown_citations` rather than
  presented as references. Numbered ids (`1`, `[1]`), file names
  (`zephyr7-calibration.md`) and paraphrased titles all resolve; anything that
  matches nothing is flagged.
* **`verify: true` adds an independent second call** — a separate process with no
  shared context — that grades the answer's grounding against the same evidence
  and lists any unsupported claims.

`e2e_answer_test.py` proves this end to end: it uploads a document containing an
**invented** fact (an instrument and value that appear nowhere on the internet),
asks for it, and then repeats the question **with the document deleted**. The
value appears only while the document is in the corpus, and the control run
answers *"the evidence does not contain a Zephyr-7 calibration constant"*.

### Answering per method

`POST /api/compare` with `"answer": true` answers once per selected method, each
from its own evidence, under the shared prompt and budget; add `"verify": true`
to grade each reply. This is the paper's protocol — one model call per method, so
it is slow, which is why it is opt-in.

---

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | self-describing index (routes, algorithms, resolved config) |
| `GET` | `/api/health` | liveness + corpus/index readiness + answer-channel availability |
| `GET` | `/api/algorithms` | registry **including every parameter schema** |
| `GET` | `/api/domains` | local domains + platform knowledge bases |
| `POST` | `/api/documents` | add or replace one document (JSON) |
| `POST` | `/api/documents/batch` | add many documents |
| `POST` | `/api/documents/upload` | **upload files** (multipart, multi-file) |
| `GET` | `/api/documents` | list the corpus |
| `GET` | `/api/documents/{id}` | read one document and its chunks |
| `DELETE` | `/api/documents/{id}` | delete one document |
| `DELETE` | `/api/documents` | clear the corpus |
| `POST` | `/api/search` | run algorithms for one query |
| `POST` | `/api/compare` | same, plus the cross-method comparison block |
| `POST` | `/api/answer` | **retrieve then answer**, with citations |
| `POST` | `/api/ask` | alias of `/api/answer` |
| `POST` | `/api/reindex` | rebuild the dense index |

Legacy paths from the original dashboard are kept as aliases: `GET /api/docs`,
`GET /api/documents/list`, `POST /api/docs/add`, `POST /api/docs/batch`,
`POST /api/documents/add`.

### Uploads

`POST /api/documents/upload` accepts `pdf · docx · md · markdown · rst · txt ·
log · csv · tsv · json · jsonl · html`. Each file is parsed, chunked and indexed
independently — **one bad file never discards the rest of the batch**:

```json
{
  "uploaded": 3, "failed": 1,
  "files": [
    { "filename": "paper.pdf", "ok": true, "kind": "pdf", "chunks": 12, "characters": 5821 },
    { "filename": "notes.md",  "ok": true, "kind": "text", "chunks": 2,  "characters": 940 },
    { "filename": "dump.xyz",  "ok": false, "error": "unsupported file type '.xyz'. Supported: …" }
  ]
}
```

Scanned PDFs with no text layer are reported with a warning rather than indexed
as empty documents.

### Metrics

`/api/search` and `/api/compare` differ only in that `/api/compare` always
returns the `comparison` block. It reports latency, score distribution and
inter-method overlap (Jaccard) unconditionally, and **real IR metrics —
`precision@k`, `recall@k`, `ndcg@10`, `mrr` — only when you supply `relevant`
(ground-truth document ids)**. Without ground truth the response says so
explicitly; it never derives a precision figure from a similarity score.

### Failure isolation

Algorithms run independently. If one cannot run — the platform API is down, a
model is missing, a parameter is out of range — its own result carries an
`error` string, and the other methods still return their results. A broken
baseline never turns a comparison into a 500.

---

## Tests

```bash
# API surface — 61 checks, no model needed
cd benchmark-web/backend && python e2e_test.py

# Answer layer — grounding proof with a live model (~4 min, needs the omp CLI)
cd benchmark-web/backend && python e2e_answer_test.py

# UI — 36 checks driving a real Chromium through upload -> ask -> compare
cd benchmark-web && python e2e_ui_test.py --headed

# Chart sanity: proves the latency canvas actually painted pixels
python check_chart.py
```

`e2e_ui_test.py` needs Playwright (`pip install playwright && playwright install
chromium`). It seeds a known corpus through the API, then verifies the browser
renders the algorithm registry, the per-algorithm parameter panel, an upload, a
grounded answer containing the planted value, a comparison table, real IR metrics
with ground truth, and the API tab.

---

## Layout

```
benchmark-web/
├── backend/                 FastAPI service
│   ├── main.py              routes + request models
│   ├── algorithms.py        algorithm registry, parameter schemas, runners
│   ├── store.py             chunking, BM25 index, FAISS index, persistence
│   ├── loaders.py           file -> text (pdf/docx/csv/json/html/…)
│   ├── llm.py               omp one-shot channel for answer generation
│   ├── answer.py            grounded prompt, citation verification, grader
│   ├── metrics.py           P@k, R@k, nDCG, MRR, Jaccard (no invented numbers)
│   ├── config.py            reads the monorepo config.yml + .env
│   ├── verify.py            dependency + config pre-flight
│   ├── e2e_test.py          API end-to-end suite (model-free)
│   ├── e2e_answer_test.py   answer-layer end-to-end suite (live model)
│   └── data/corpus.json     persisted corpus (gitignored)
├── frontend/                Nuxt 3 dashboard (Ask / Benchmark / Corpus / API)
├── benchmark/               corpus-build + ingestion pipelines (see BENCHMARK-TEST-PLAN.md)
├── e2e_ui_test.py           browser end-to-end suite
└── check_chart.py           canvas paint check
```

## Notes

* **Chunking is character-based** with sentence-boundary preference, so CJK
  documents chunk correctly (whitespace splitting collapses them to one chunk).
* **BM25 tokenisation** uses lowercased Latin words plus CJK character bigrams —
  reasonable recall without pulling in a segmenter.
* **BM25 on tiny corpora**: Okapi's Robertson IDF is exactly zero when a term
  appears in half the corpus, so with two documents every term scores zero. The
  method therefore falls back to its ranked list (honest `score: 0`,
  `lexical_match: false`) instead of returning nothing — a single-file corpus
  still gets results.
* **Models are read from `models_cache/`** via `HF_HUB_CACHE`. That variable is
  set explicitly rather than relying on `HF_HOME`, which is often already
  defined machine-wide and would otherwise silently win.
* The corpus persists to `backend/data/corpus.json`, so restarting the server
  does not empty the benchmark.
