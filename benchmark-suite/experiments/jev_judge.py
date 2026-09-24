"""Jev judgment layer — a real relevance/evidence gate between recall and answering.

Jev is **TypeSafe.AI's "System One"** model: a fast *structured-decision* model (it does
not chat and does not write prose). One endpoint, one round trip, typed answers.

    POST https://api.typesafe.ai/v1/systemone     (official, Bearer TYPESAFE_API_KEY)
    POST https://jevtypesafeai.com/api/v1/decide  (hosted,  Bearer JEV_API_KEY, prepaid)
    body = {"model": "jev-latest", "state": <str|obj|list>, "questions": {...}}

Three question types:
    choice  ≤255 labelled options          → {choice, confidence, probabilities}
    score   2–10 ordered levels            → {score, confidence, legend, probabilities}
    noul    calibrated yes/no (no criteria)→ {noul: 0..1}

We use **noul** per candidate: "does this text contain concrete evidence that helps
answer the query?" — keep those above the threshold. `state` carries the candidate
text, `instructions` carries the query.

Backends (auto-detected, and ALWAYS reported — never silently substituted):

    sdk   jev-reranker package + key     (real Jev, recommended)
    http  raw /v1/systemone POST + key   (real Jev, no extra dependency)
    llm   platform chat API judge        (SUBSTITUTE — not Jev; runnable without a key)
    none  keep everything                (no gate; reported as such)

Enable real Jev:
    pip install jev-reranker          # or: uv add jev-reranker
    export TYPESAFE_API_KEY=...       # official key
    # or: export JEV_API_KEY=jv_live_...   (hosted endpoint, prepaid)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "experiments"))
sys.path.insert(0, str(SUITE / "scripts"))

ENDPOINTS = {
    "TYPESAFE_API_KEY": "https://api.typesafe.ai/v1/systemone",
    "JEV_API_KEY": "https://jevtypesafeai.com/api/v1/decide",
}
DEFAULT_MODEL = os.environ.get("JEV_MODEL", "jev-latest")
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # bypass sandbox proxy

NOUL_INSTRUCTION = (
    "Does the TEXT contain concrete evidence that directly helps answer the QUERY? "
    "Answer yes only if a reader could quote or paraphrase a fact, number, name, or event "
    "from the TEXT that the QUERY asks for. Topical similarity alone is NOT enough.\n"
    "QUERY: {q}"
)

# Criterion presets. The strict "evidence" wording is right for lookup questions but
# WRONG for enumeration questions: asked to "list every scene where X happens", a
# 1200-char window that contains exactly ONE such scene is a hit, yet the strict
# wording scores it low (measured 2026-09-24: 30% part recall vs 60% for vector).
# For enumeration the gate must ask "does this contain ANY instance of the class?".
CRITERIA = {
    "evidence": NOUL_INSTRUCTION,
    "instance": (
        "The QUERY asks to enumerate EVERY member of a class (scenes / events / mentions). "
        "Does the TEXT contain at least one instance of that class, or information that "
        "identifies one? Answer yes if it shows ANY such instance, even a single partial one. "
        "Answer no only if the TEXT has nothing belonging to the requested class.\n"
        "QUERY: {q}"
    ),
}

ENUMERATION_HINTS = ("list every", "list all", "every scene", "all the scenes", "enumerate",
                     "each time", "how many times", "all occasions", "列出", "列举", "所有",
                     "每一个", "每一次", "哪些", "全部")


def criterion_for(query: str) -> str:
    """Pick the gate criterion from the question shape (enumeration vs lookup)."""
    low = (query or "").lower()
    return "instance" if any(h in low for h in ENUMERATION_HINTS) else "evidence"


def _key() -> tuple[str, str, str]:
    """→ (backend_key_env, api_key, endpoint) — empty key means Jev is unavailable."""
    for env, url in ENDPOINTS.items():
        k = (os.environ.get(env) or "").strip()
        if k:
            return env, k, url
    return "", "", ""


def _jev_http(query: str, text: str, timeout: float = 60.0,
              criterion: str = "evidence") -> tuple[float | None, dict]:
    """One real Jev call for one candidate → (noul, usage)."""
    env, key, url = _key()
    body = {
        "model": DEFAULT_MODEL,
        "state": str(text)[:24000],
        "questions": {"evidence": {"type": "noul",
                                   "instructions": CRITERIA[criterion].format(q=query)}},
    }
    req = urllib.request.Request(url, method="POST",
                                 data=json.dumps(body).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {key}")
    with _OPENER.open(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode("utf-8"))
    ans = ((resp.get("answers") or {}).get("evidence") or {})
    val = ans.get("noul")
    return (float(val) if isinstance(val, (int, float)) else None), resp.get("usage") or {}


def _llm_judge(query: str, docs: list[str],
               criterion: str = "evidence") -> tuple[list[float | None], str]:
    """Substitute gate: one LLM call scoring every candidate. NOT Jev — labeled as such."""
    from chat_tracks import chat_stream
    numbered = "\n\n".join(f"[{i}] {str(d)[:1500]}" for i, d in enumerate(docs))
    if criterion == "instance":
        rule = ("The QUERY asks to enumerate EVERY member of a class. Score a candidate HIGH if it "
                "contains AT LEAST ONE instance of that class (even a single partial one); score it "
                "LOW only if it has nothing belonging to the requested class.")
    else:
        rule = ("Score a candidate HIGH only if it contains concrete evidence that directly helps "
                "answer the QUERY — a quotable fact, number, name or event. Topical similarity alone "
                "is NOT enough.")
    prompt = (
        "You are a strict evidence gate. For each numbered CANDIDATE return a 0-1 usefulness score.\n"
        f"{rule}\nReply ONLY a JSON object mapping index to a 0-1 score.\n\n"
        f"QUERY: {query}\n\nCANDIDATES:\n{numbered}")
    r = chat_stream(prompt, cwd=str(SUITE.parent), allowed_tools=[], max_turns=1, timeout_s=300)
    txt = str(r.get("answer") or "")
    m = re.search(r"\{.*\}", txt, re.S)
    scores: list[float | None] = [None] * len(docs)
    if m:
        try:
            for k, v in json.loads(m.group(0)).items():
                i = int(k)
                if 0 <= i < len(docs):
                    scores[i] = float(v)
        except Exception:  # noqa: BLE001
            pass
    return scores, "llm"


def judge(query: str, docs: list[str], threshold: float = 0.5,
          backend: str = "auto", timeout: float = 60.0,
          criterion: str = "auto") -> dict:
    """Score every candidate and keep the ones above `threshold`.

    criterion: "evidence" (strict lookup) | "instance" (enumeration) | "auto"
    (auto picks "instance" when the query asks to enumerate everything).

    Returns {backend, criterion, kept_index, scores, results:[...], usage, note}.
    """
    docs = [str(d) for d in docs]
    crit = criterion_for(query) if criterion == "auto" else criterion
    if not docs:
        return {"backend": "none", "criterion": crit, "kept_index": [], "scores": [],
                "results": [], "usage": {}, "note": "no candidates"}

    scores: list[float | None] = [None] * len(docs)
    usage: dict = {}
    note = ""
    env, key, _url = _key()
    chosen = backend
    if backend == "auto":
        chosen = "http" if key else "unavailable"
        if not key:
            note = "real Jev unavailable; auto mode is fail-closed (use backend=llm explicitly for a labelled benchmark substitute)"
    if chosen in ("sdk", "http") and not key:
        note = (f"Jev requested but no API key found — set TYPESAFE_API_KEY or JEV_API_KEY. "
                f"No candidates will be kept without a score.")
        chosen = "unavailable"

    if chosen == "sdk":
        try:
            from jev_reranker import JevReranker  # type: ignore
            rr = JevReranker()
            res = rr.relevance_rerank(query, docs, threshold=threshold, detail=True)
            idx = {r["document_index"]: r["score"] for r in res.get("results", [])}
            scores = [idx.get(i) for i in range(len(docs))]
            usage = ((res.get("detail") or {}).get("usage")) or {}
        except Exception as e:  # noqa: BLE001
            note = f"sdk backend failed ({type(e).__name__}: {str(e)[:120]}); no score returned"
            chosen = "unavailable"

    if chosen == "http":
        try:
            for i, d in enumerate(docs):
                v, u = _jev_http(query, d, timeout=timeout, criterion=crit)
                scores[i] = v
                for k, val in (u or {}).items():
                    usage[k] = (usage.get(k) or 0) + (val if isinstance(val, (int, float)) else 0)
        except Exception as e:  # noqa: BLE001
            note = f"Jev http failed ({type(e).__name__}: {str(e)[:140]}); no score returned"
            chosen = "unavailable"

    if chosen == "llm":
        scores, _ = _llm_judge(query, docs, criterion=crit)

    kept = [i for i, s in enumerate(scores) if s is not None and s >= threshold]
    if chosen == "none":
        kept = list(range(len(docs)))
        note = note or "explicit no-gate benchmark baseline (kept everything)"

    return {
        "backend": chosen,
        "criterion": crit,
        "threshold": threshold,
        "model": DEFAULT_MODEL if chosen in ("sdk", "http") else "n/a",
        "key_env": env or "",
        "kept_index": kept,
        "scores": scores,
        "usage": usage,
        "note": note,
        "results": [{"index": i, "score": scores[i], "kept": i in kept, "text": docs[i][:400]}
                    for i in range(len(docs))],
    }


def available() -> dict:
    """Report whether real Jev can be used, without making a call."""
    env, key, url = _key()
    sdk = False
    try:
        import jev_reranker  # type: ignore  # noqa: F401
        sdk = True
    except Exception:  # noqa: BLE001
        sdk = False
    return {"key_env": env, "endpoint": url, "sdk_installed": sdk,
            "model": DEFAULT_MODEL, "real_jev_ready": bool(key)}


if __name__ == "__main__":
    print(json.dumps(available(), ensure_ascii=False, indent=1))
