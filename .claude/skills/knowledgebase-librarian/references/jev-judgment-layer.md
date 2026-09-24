# Jev judgment layer (L5.5) — how to use it

## What Jev is

**Jev** is **TypeSafe.AI's "System One"** model. It is **not** a chat model and it does not write
prose — it makes **fast, structured decisions** and returns **typed answers** in one round trip.
That is exactly what a retrieval gate needs: a decision, not an essay.

It is available as:
- **Official API** — `POST https://api.typesafe.ai/v1/systemone`, Bearer `TYPESAFE_API_KEY`
- **Hosted API** — `POST https://jevtypesafeai.com/api/v1/decide`, Bearer `JEV_API_KEY` (prepaid,
  ≈ $0.00003 per decision)
- **Python SDK** — `pip install jev-reranker` (Python 3.11+); `JevReranker().relevance_rerank(...)`

Jev is **billed by usage** and the model itself **cannot be self-hosted** (only tokenizers are local).

## Request shape

```jsonc
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer $TYPESAFE_API_KEY
{
  "model": "jev-latest",              // or pin e.g. "jev-1.13.0" when thresholds matter
  "state": "<the candidate text>",    // string | object | array; state + questions ≤ 64k tokens
  "questions": {
    "evidence": {
      "type": "noul",                 // calibrated yes/no — no criteria needed
      "instructions": "Does the TEXT contain concrete evidence that directly helps answer the QUERY? …"
    }
  }
}
```

Three question types:

| type | shape | returns |
|---|---|---|
| `choice` | `criteria` = ≤255 labelled options | `choice`, `confidence`, `probabilities` |
| `score` | `criteria` = 2–10 ordered levels | `score`, `confidence`, `legend`, `probabilities` |
| `noul` | only `instructions` | `noul` — a calibrated probability in 0–1 |

Response: `{"model": ..., "answers": {"evidence": {"type":"noul","noul":0.87}}, "usage": {...}}`

Limits: **250 000 tokens/s**, **1 200 requests/min**; state + all questions ≤ 64k tokens,
state + the single longest question ≤ 32k. Batch several questions into **one** call — they run in
parallel and share the `state` cost.

## How this skill uses it (L5)

After L4 has read **every candidate segment** (not only a head/mid/tail sample), write a JSON manifest and call the skill-facing filter:

```bash
python .claude/skills/knowledgebase-librarian/scripts/jev_filter.py \
  --input candidates.json --output jev-result.json --require-real
```

The filter asks one `noul` question per candidate segment and returns one score record for every candidate. A candidate remains eligible only when `score >= threshold`; missing, malformed, out-of-range, timeout, HTTP error, or rate-limit results are rejected. It also returns a source-ordered, deduplicated `evidence_pack` and provenance containing KB, document ID/path, part, section, and offsets.

Use `evidence` for lookup questions and `instance` for enumeration/completeness questions. Default threshold is `0.5`; declare any recall-first (`0.35`) or precision-first (`0.65`) override. The answer model receives only the scored evidence pack and must retain its provenance.

The script is JSON-in/JSON-out and does not call MCP; the Archival agent remains responsible for `kb_list`, `kb_get_documents`, and paginated `kb_doc_read` operations.


Why `noul` and not `score`: a calibrated yes/no is directly thresholdable and needs no legend to
interpret. Use `score` only when you want graded relevance tiers (P0/P1/P2) rather than a cut.

Why not a plain vector score: the vector score measures *similarity*; Jev measures *"can this text
answer the question"*. The whole point of this lane is that similarity ≠ usefulness.

## Enabling it

```bash
pip install jev-reranker          # optional: SDK path (recommended)
export TYPESAFE_API_KEY=...       # official key
# or:  export JEV_API_KEY=jv_live_...     # hosted endpoint, prepaid
export JEV_MODEL=jev-latest       # optional; pin a version in production
```

`benchmark-suite/experiments/jev_judge.py` is benchmark-only. It may run an explicitly selected `llm` substitute or `none` baseline, but those modes are never enabled by the librarian skill and must be labelled in every report. The skill-facing `jev_filter.py` has no implicit substitute.

## Backends and honesty rule

`benchmark-suite/experiments/jev_judge.py` auto-detects and **always reports** which backend ran:

| backend | meaning |
|---|---|
| `sdk` | real Jev via `jev-reranker` |
| `http` | real Jev via raw `/v1/systemone` |
| `llm` | **substitute** — the platform chat model scoring candidates. Runnable with no key, but it is **not Jev**; label it as a substitute in any report |
| `none` | no gate — everything kept |

**Never present the `llm` substitute as Jev.** The pipeline writes the backend name into its report.

## Cost note

One noul call per candidate. 30 candidates ≈ 30 calls ≈ a fraction of a cent, and it removes the
need to put irrelevant documents into the answer context at all.
