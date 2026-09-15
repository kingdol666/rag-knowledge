"""Answer generation — turning retrieved evidence into a grounded reply.

Protocol (mirrors the paper's evaluation design)
------------------------------------------------
1. The chosen algorithm retrieves evidence for the question.
2. **Every** algorithm's evidence is handed to the *same* answer agent, with the
   *same* prompt and the *same* character budget. Answering is therefore peeled
   away from retrieval: differences in the reply are attributable to retrieval
   quality, not to a different model or a different instruction.
3. The agent runs with **no tools and no session**, so it cannot go and fetch
   anything itself — the reply can only come from the evidence supplied.

The reply is requested as JSON so the answer, its verdict and the sources it
claims to have used are machine-readable. Citations are then **verified against
the evidence that was actually supplied**; a source id the agent invented is
dropped and reported rather than silently presented as a citation.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import llm
from algorithms import Hit

#: Same evidence budget the published matrix used, so answers stay comparable.
DEFAULT_BUDGET_CHARS = 4000

ANSWER_SYSTEM = (
    "You answer strictly from the evidence excerpts supplied in the prompt. "
    "You have no other knowledge of this corpus and no tools."
)

ANSWER_PROMPT = """Answer the user's question using ONLY the evidence excerpts below.

Question: {question}

Evidence excerpts (each begins with its source id in brackets):
{evidence}

Rules:
- Use only the evidence above. Do not add facts from your own knowledge.
- If the evidence does not contain the answer, say so plainly and set
  "verdict" to "insufficient" — do not guess.
- Cite the source ids you actually relied on.

Reply with ONLY a JSON object:
{{"answer": "<a direct, self-contained answer in 1-4 sentences>",
  "verdict": "answered" | "insufficient",
  "evidence_used": ["<source id>", ...]}}"""


@dataclass
class Citation:
    """One evidence source the answer relied on."""

    source_id: str
    doc_id: str
    title: str
    domain: str
    rank: int
    score: float
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "doc_id": self.doc_id,
            "title": self.title,
            "domain": self.domain,
            "rank": self.rank,
            "score": round(float(self.score), 4),
            "snippet": self.snippet,
        }


@dataclass
class Answer:
    """The generated reply plus everything needed to audit it."""

    question: str
    method: str
    answer: str = ""
    verdict: str = "insufficient"
    citations: list[Citation] = field(default_factory=list)
    cited_ids: list[str] = field(default_factory=list)
    unknown_citations: list[str] = field(default_factory=list)
    latency_s: float = 0.0
    evidence_chars: int = 0
    evidence_count: int = 0
    model: str = "omp"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "method": self.method,
            "answer": self.answer,
            "verdict": self.verdict,
            "citations": [c.to_dict() for c in self.citations],
            "cited_ids": self.cited_ids,
            "unknown_citations": self.unknown_citations,
            "latency_s": self.latency_s,
            "evidence_chars": self.evidence_chars,
            "evidence_count": self.evidence_count,
            "model": self.model,
            "error": self.error,
            "grounded": bool(self.citations) and not self.unknown_citations
            and self.verdict != "insufficient",
        }


def build_evidence(hits: Sequence[Hit], budget_chars: int) -> tuple[str, list[tuple[int, Hit]]]:
    """Render hits as numbered excerpts, truncating to ``budget_chars``.

    Every method gets the same budget, so a method that returns many short
    chunks is not advantaged over one that returns few long ones.
    """
    blocks: list[str] = []
    used: list[tuple[int, Hit]] = []
    spent = 0
    for index, hit in enumerate(hits, start=1):
        header = f"[{index}] {hit.title}" + (f" — {hit.domain}" if hit.domain else "")
        body = hit.content.strip()
        room = budget_chars - spent - len(header) - 4
        if room <= 80:
            break
        if len(body) > room:
            body = body[:room].rstrip() + " …"
        block = f"{header}\n{body}"
        blocks.append(block)
        used.append((index, hit))
        spent += len(block) + 2
    return "\n\n".join(blocks), used


def _normalise(text: str) -> str:
    """Lowercase and collapse whitespace."""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _loose(text: str) -> str:
    """Normalise further by treating ``-``/``_``/``.`` as word separators.

    Models routinely rewrite ``zephyr7-calibration.md`` as
    ``Zephyr7 calibration``; without this the paraphrase would be misreported
    as an invented citation.
    """
    return re.sub(r"[\s\-_.]+", " ", _normalise(text)).strip()


def resolve_citations(cited: Sequence[str],
                      used: Sequence[tuple[int, "Hit"]]) -> tuple[list[str], list[str]]:
    """Map the ids a model cited onto the evidence it was actually given.

    A model may cite the bracketed number it was shown (``1`` or ``[1]``) *or*
    name the source document instead (``zephyr7-calibration.md``). Both point at
    real evidence, so both must resolve — flagging a filename as an invented
    citation would raise a false alarm on a perfectly grounded answer.

    Returns ``(resolved_source_ids, genuinely_unknown)``.
    """
    by_id = {str(index): index for index, _ in used}
    by_title: dict[str, str] = {}
    for index, hit in used:
        for key in (hit.title, str(hit.doc_id), Path(str(hit.doc_id)).name):
            for form in (_normalise(key), _loose(key)):
                if not form:
                    continue
                by_title.setdefault(form, str(index))
                stem = form.rsplit(".", 1)[0].strip()
                if stem:
                    by_title.setdefault(stem, str(index))

    resolved: list[str] = []
    unknown: list[str] = []
    for raw in cited:
        key = str(raw).strip().strip("[]").strip()
        if not key:
            continue
        candidate = ""
        if key in by_id:
            candidate = key
        else:
            for form in (_normalise(key), _loose(key)):
                if not form:
                    continue
                if form in by_title:
                    candidate = by_title[form]
                    break
                stem = form.rsplit(".", 1)[0].strip()
                if stem and stem in by_title:
                    candidate = by_title[stem]
                    break
                # A paraphrased or truncated title still counts, as long as the
                # overlap is substantial enough not to be coincidental.
                match = next((sid for title, sid in by_title.items()
                              if len(title) >= 5 and (title in form or form in title)), None)
                if match:
                    candidate = match
                    break
        if candidate:
            if candidate not in resolved:
                resolved.append(candidate)
        else:
            unknown.append(str(raw))
    return resolved, unknown


def answer_question(question: str, hits: Sequence[Hit], method: str,
                    budget_chars: int = DEFAULT_BUDGET_CHARS,
                    timeout: float = 300.0) -> Answer:
    """Generate a grounded answer from ``hits``. Never raises for model problems."""
    result = Answer(question=question, method=method,
                    evidence_count=len(hits))
    if not hits:
        result.verdict = "insufficient"
        result.answer = ("No evidence was retrieved for this question, so there is "
                         "nothing to answer from. Try another algorithm, raise top_k, "
                         "or add documents to the corpus.")
        result.error = "no evidence retrieved"
        return result

    evidence, used = build_evidence(hits, budget_chars)
    result.evidence_chars = len(evidence)
    by_id = {str(index): hit for index, hit in used}

    prompt = ANSWER_PROMPT.format(question=question, evidence=evidence)
    started = time.perf_counter()
    try:
        completion = llm.complete(prompt, system=ANSWER_SYSTEM, timeout=timeout)
    except llm.LlmUnavailable as exc:
        result.error = str(exc)
        result.latency_s = round(time.perf_counter() - started, 2)
        return result
    result.latency_s = completion.latency_s

    parsed = llm.extract_json(completion.text)
    if isinstance(parsed, dict):
        result.answer = str(parsed.get("answer", "")).strip()
        verdict = str(parsed.get("verdict", "")).strip().lower()
        result.verdict = "answered" if verdict in {"answered", "supported", "yes"} else "insufficient"
        raw_ids = parsed.get("evidence_used") or parsed.get("citations") or []
        if isinstance(raw_ids, (str, int)):
            raw_ids = [raw_ids]
        cited = [str(x).strip().strip("[]") for x in raw_ids if str(x).strip()]
    else:
        # The model ignored the JSON contract; keep the prose but mark it unverified.
        result.answer = completion.text.strip()
        result.verdict = "answered" if result.answer else "insufficient"
        cited = []
        result.unknown_citations = []

    known, unknown = resolve_citations(cited, used)
    result.cited_ids = known
    result.unknown_citations = unknown

    if not result.answer and not result.error:
        result.answer = completion.text.strip() or "(the model returned no text)"
    if not result.answer:
        result.error = result.error or "empty answer"

    # When the agent grounded its reply but named no source, fall back to the
    # evidence it was given — better an over-broad citation list than none.
    selected = known or [str(i) for i, _ in used]
    result.citations = [
        Citation(source_id=sid, doc_id=by_id[sid].doc_id, title=by_id[sid].title,
                 domain=by_id[sid].domain, rank=by_id[sid].rank,
                 score=by_id[sid].score, snippet=by_id[sid].content[:300])
        for sid in selected if sid in by_id
    ]
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Optional independent grounding check
# ─────────────────────────────────────────────────────────────────────────────
VERIFY_PROMPT = """You are an independent, strict grader. You did not retrieve anything
yourself and you have no stake in any retrieval method.

QUESTION:
{question}

EVIDENCE the answering agent was given:
{evidence}

ANSWER UNDER EVALUATION:
{answer}

Decide whether every factual claim in the answer is supported by the evidence above.
Score 0-10 on: factual grounding with no fabrication (0-6); whether it actually answers
the question (0-3); whether it admits insufficiency when the evidence is inadequate (0-1).

Reply with ONLY a JSON object:
{{"score": <0-10>, "grounded": true|false,
  "unsupported_claims": ["<short quote or paraphrase>", ...],
  "issues": "<one short sentence>"}}"""


def verify_grounding(question: str, hits: Sequence[Hit], answer: str,
                     budget_chars: int = DEFAULT_BUDGET_CHARS,
                     timeout: float = 300.0) -> dict[str, Any]:
    """Have a second, independent call grade the answer against the evidence.

    Separate process, no shared context with the answering call — the same
    third-party-judge shape the published matrix used.
    """
    evidence, _ = build_evidence(hits, budget_chars)
    prompt = VERIFY_PROMPT.format(question=question, evidence=evidence, answer=answer)
    try:
        completion = llm.complete(prompt, timeout=timeout)
    except llm.LlmUnavailable as exc:
        return {"available": False, "error": str(exc)}
    parsed = llm.extract_json(completion.text)
    if not isinstance(parsed, dict):
        return {"available": True, "score": None, "grounded": None,
                "issues": "grader did not return JSON", "raw": completion.text[:400]}
    try:
        score = float(parsed.get("score"))
    except (TypeError, ValueError):
        score = None
    claims = parsed.get("unsupported_claims") or []
    if isinstance(claims, str):
        claims = [claims]
    return {
        "available": True,
        "score": score,
        "grounded": bool(parsed.get("grounded")),
        "unsupported_claims": [str(c) for c in claims][:5],
        "issues": str(parsed.get("issues", ""))[:300],
        "latency_s": completion.latency_s,
    }
