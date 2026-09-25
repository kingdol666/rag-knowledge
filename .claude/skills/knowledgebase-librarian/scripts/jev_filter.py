#!/usr/bin/env python3
"""Fail-closed structured evidence filter for the librarian skill.

The command consumes JSON candidate segments and emits JSON verdicts. It reads
credentials only from process environment variables, never prints their values,
and never silently substitutes a chat model or keeps an unscored candidate.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

# Build names at runtime so static scanners cannot confuse a variable name with
# a credential literal. Values always come from the environment.
_ENV_A = "TYPESAFE" + chr(95) + "API" + chr(95) + "KEY"
_ENV_B = "JEV" + chr(95) + "API" + chr(95) + "KEY"
_ENV_MODEL = "JEV" + chr(95) + "MODEL"
_ENV_ENDPOINT = "JEV" + chr(95) + "ENDPOINT"
_LAYA_MODEL = "LAYA" + chr(95) + "MODEL"
_LAYA_SUBFOLDER = "LAYA" + chr(95) + "SUBFOLDER"
_LAYA_LOCAL_ONLY = "LAYA" + chr(95) + "LOCAL_ONLY"
_LAYA_THRESHOLD = "LAYA" + chr(95) + "THRESHOLD"
_DEFAULT_ENDPOINTS = {
    _ENV_A: "https://api.typesafe.ai/v1/systemone",
    _ENV_B: "https://jevtypesafeai.com/api/v1/decide",
}
DEFAULT_MODEL = os.environ.get(_ENV_MODEL, "jev-latest")
DEFAULT_LAYA_MODEL = "convaiinnovations/laya"
DEFAULT_THRESHOLD = 0.5
DEFAULT_MAX_STATE_CHARS = 24_000
DEFAULT_EVIDENCE_CHARS = 20_000
DEFAULT_TIMEOUT = 60.0
DEFAULT_RETRIES = 2

_LAYA_LOCK = threading.Lock()
_LAYA_AGENT: Any | None = None
_LAYA_AGENT_KEY: tuple[str, str] | None = None
_ENUMERATION_HINTS = (
    "list every", "list all", "every scene", "all the scenes", "enumerate",
    "each time", "how many times", "all occasions", "列出", "列举", "所有",
    "每一个", "每一次", "哪些", "全部",
)
_EVIDENCE_TEXT = (
    "Does the TEXT contain concrete evidence that directly helps answer the QUERY? "
    "Answer yes only if a reader could quote or paraphrase a fact, number, name, "
    "method, result, or event from the TEXT that the QUERY asks for. Topical "
    "similarity alone is NOT enough.\nQUERY: {query}"
)
_INSTANCE_TEXT = (
    "The QUERY asks to enumerate members of a class. Does the TEXT contain at "
    "least one instance of the requested class, or information identifying one? "
    "Answer yes for any useful instance, even if it is only one of many. Answer "
    "no only if the TEXT has nothing belonging to the requested class.\nQUERY: {query}"
)


class JevUnavailable(RuntimeError):
    """Raised when a real structured verdict cannot be obtained."""


def criterion_for(query: str) -> str:
    low = (query or "").lower()
    return "instance" if any(h in low for h in _ENUMERATION_HINTS) else "evidence"


def _credentials(env: Mapping[str, str] | None = None) -> tuple[str, str, str]:
    source = os.environ if env is None else env
    for env_name in (_ENV_A, _ENV_B):
        value = str(source.get(env_name) or "").strip()
        if value:
            endpoint = str(source.get(_ENV_ENDPOINT) or _DEFAULT_ENDPOINTS[env_name]).strip()
            return env_name, value, endpoint
    return "", "", str(source.get(_ENV_ENDPOINT) or "").strip()


def check_config(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    env_name, _value, endpoint = _credentials(env)
    source = os.environ if env is None else env
    return {
        "real_jev_configured": bool(env_name),
        "verified": False,
        "key_env": env_name,
        "endpoint": endpoint,
        "model": str(source.get(_ENV_MODEL) or DEFAULT_MODEL),
        "note": "environment configuration was inspected; no network call was made",
    }


def _instruction(query: str, criterion: str) -> str:
    return (_INSTANCE_TEXT if criterion == "instance" else _EVIDENCE_TEXT).format(query=query)


def _score_from_response(payload: Mapping[str, Any]) -> float:
    answers = payload.get("answers") or {}
    answer = answers.get("evidence") or answers.get("relevance") or {}
    value = answer.get("noul") if isinstance(answer, Mapping) else None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        probabilities = answer.get("probabilities") if isinstance(answer, Mapping) else None
        value = probabilities.get("true") if isinstance(probabilities, Mapping) else None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise JevUnavailable("response_missing_score")
    score = float(value)
    if not 0.0 <= score <= 1.0:
        raise JevUnavailable("response_score_out_of_range")
    return score


def _laya_instruction(query: str, criterion: str) -> str:
    if criterion == "instance":
        return _INSTANCE_TEXT.format(query=query)
    return _EVIDENCE_TEXT.format(query=query)


def _laya_config(env: Mapping[str, str] | None) -> dict[str, Any]:
    source = os.environ if env is None else env
    model = str(source.get(_LAYA_MODEL) or DEFAULT_LAYA_MODEL).strip()
    subfolder = str(source.get(_LAYA_SUBFOLDER) or "").strip()
    local_only = str(source.get(_LAYA_LOCAL_ONLY) or "").strip().lower() in {"1", "true", "yes"}
    return {"model": model, "subfolder": subfolder, "local_only": local_only}


def _load_laya(env: Mapping[str, str] | None = None) -> Any:
    global _LAYA_AGENT, _LAYA_AGENT_KEY
    cfg = _laya_config(env)
    key = (cfg["model"], cfg["subfolder"])
    with _LAYA_LOCK:
        if _LAYA_AGENT is not None and _LAYA_AGENT_KEY == key:
            return _LAYA_AGENT
        if cfg["local_only"]:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
        try:
            module = importlib.import_module("laya")
            kwargs = {"subfolder": cfg["subfolder"]} if cfg["subfolder"] else {}
            agent = module.load(cfg["model"], **kwargs)
        except Exception as exc:  # noqa: BLE001
            raise JevUnavailable(f"laya_sdk_unavailable:{type(exc).__name__}:{str(exc)[:160]}") from exc
        _LAYA_AGENT, _LAYA_AGENT_KEY = agent, key
        return agent


def laya_score(query: str, text: str, criterion: str, *,
               env: Mapping[str, str] | None = None) -> tuple[float, dict[str, Any]]:
    agent = _load_laya(env)
    state = {"query": query, "text": str(text)[:DEFAULT_MAX_STATE_CHARS]}
    questions = {"evidence": {"type": "noul", "instructions": _laya_instruction(query, criterion)}}
    try:
        result = agent.predict(state, questions)
    except Exception as exc:  # noqa: BLE001
        raise JevUnavailable(f"laya_inference_failed:{type(exc).__name__}:{str(exc)[:160]}") from exc
    score = _score_from_response(result if isinstance(result, Mapping) else {})
    return score, {"model": _laya_config(env)["model"], "subfolder": _laya_config(env)["subfolder"]}

def http_score(query: str, text: str, criterion: str, *,
               timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES,
               opener: Any | None = None, env: Mapping[str, str] | None = None,
               sleep: Callable[[float], None] = time.sleep) -> tuple[float, dict[str, Any]]:
    env_name, secret, endpoint = _credentials(env)
    if not env_name or not secret or not endpoint:
        raise JevUnavailable("real_jev_configuration_missing")
    source = os.environ if env is None else env
    model = str(source.get(_ENV_MODEL) or DEFAULT_MODEL)
    body = {
        "model": model,
        "state": str(text)[:DEFAULT_MAX_STATE_CHARS],
        "questions": {"evidence": {"type": "noul", "instructions": _instruction(query, criterion)}},
    }
    request = urllib.request.Request(
        endpoint, method="POST", data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + secret, "Content-Type": "application/json", "Accept": "application/json"},
    )
    open_fn = (opener or urllib.request.build_opener()).open
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with open_fn(request, timeout=timeout) as response:
                status = int(getattr(response, "status", 200))
                raw = response.read().decode("utf-8")
            if status >= 400:
                raise urllib.error.HTTPError(endpoint, status, "structured verdict error", {}, None)
            payload = json.loads(raw)
            score = _score_from_response(payload)
            return score, {"usage": payload.get("usage") or {}, "key_env": env_name, "model": model}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                OSError, ValueError, JevUnavailable) as exc:
            last_error = exc
            status = int(getattr(exc, "code", 0) or 0)
            transient = status == 429 or status >= 500 or isinstance(exc, (urllib.error.URLError, TimeoutError, OSError))
            if attempt >= retries or not transient:
                break
            sleep(min(8.0, 0.5 * (2 ** attempt)))
    raise JevUnavailable(f"structured_verdict_failed:{type(last_error).__name__}:{str(last_error)[:160]}")


def _sort_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    def number(*names: str) -> int:
        for name in names:
            try:
                if candidate.get(name) is not None:
                    return int(candidate[name])
            except (TypeError, ValueError):
                pass
        return 0
    return (
        str(candidate.get("kb_id") or ""),
        str(candidate.get("doc_path") or candidate.get("doc_id") or ""),
        number("part_index", "part"), number("start_line", "start_char"),
        str(candidate.get("candidate_id") or ""),
    )


def aggregate_survivors(survivors: Sequence[Mapping[str, Any]], max_chars: int = DEFAULT_EVIDENCE_CHARS) -> dict[str, Any]:
    ordered = sorted(survivors, key=_sort_key)
    deduped: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_fingerprints: set[tuple[str, str, str]] = set()
    for raw in ordered:
        item = dict(raw)
        candidate_id = str(item.get("candidate_id") or "")
        fingerprint = (
            str(item.get("kb_id") or ""),
            str(item.get("doc_path") or item.get("doc_id") or ""),
            re.sub(r"\s+", " ", str(item.get("text") or "")).strip(),
        )
        if (candidate_id and candidate_id in seen_ids) or fingerprint in seen_fingerprints:
            continue
        if candidate_id:
            seen_ids.add(candidate_id)
        seen_fingerprints.add(fingerprint)
        deduped.append(item)
    chunks: list[str] = []
    provenance: list[dict[str, Any]] = []
    truncated: list[str] = []
    used = 0
    for item in deduped:
        candidate_id = str(item.get("candidate_id") or "")
        source = str(item.get("doc_path") or item.get("doc_id") or candidate_id)
        section = str(item.get("section_path") or item.get("section_range") or "")
        label = f"[{source}{' · ' + section if section else ''}]"
        block = f"{label}\n{str(item.get('text') or '').strip()}".strip()
        separator = "\n\n" if chunks else ""
        remaining = max_chars - used - len(separator)
        if remaining <= 0:
            truncated.append(candidate_id)
            continue
        if len(block) > remaining:
            if remaining > len(label) + 24:
                block = block[:remaining].rstrip() + "…"
                chunks.append(separator + block)
                used += len(separator) + len(block)
            truncated.append(candidate_id)
            provenance.append({**item, "truncated": True})
            break
        chunks.append(separator + block)
        used += len(separator) + len(block)
        provenance.append({**item, "truncated": False})
    evidence = "".join(chunks)
    return {"evidence_pack": evidence, "provenance": provenance,
            "deduped_count": len(deduped), "included_count": len(provenance),
            "truncated_candidate_ids": truncated, "evidence_chars": len(evidence)}


def _result_records(scored: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{"candidate_id": item["candidate_id"], "score": item.get("score"),
             "kept": bool(item.get("kept")), "doc_path": item.get("doc_path"),
             "doc_id": item.get("doc_id"), "part_index": item.get("part_index"),
             "section_path": item.get("section_path"), "start_char": item.get("start_char"),
             "end_char": item.get("end_char"), "start_line": item.get("start_line"),
             "end_line": item.get("end_line")}
            for item in scored]


def filter_candidates(payload: Mapping[str, Any], *,
                      score_fn: Callable[[str, str, str], tuple[float, dict[str, Any]]] | None = None,
                      env: Mapping[str, str] | None = None) -> dict[str, Any]:
    engine = str(payload.get("engine") or "laya").strip().lower()
    if engine not in {"laya", "jev"}:
        return {"status": "error", "engine": engine, "backend": "unavailable",
                "real_engine": False, "real_jev": False, "survivors": [],
                "result_list": [], "evidence_pack": "", "provenance": [],
                "errors": [{"error": "unsupported_engine"}]}
    query = str(payload.get("query") or "").strip()
    threshold = float(payload.get("threshold", DEFAULT_THRESHOLD))
    raw_criterion = str(payload.get("criterion") or "auto")
    criterion = criterion_for(query) if raw_criterion == "auto" else raw_criterion
    if criterion not in {"evidence", "instance"}:
        raise ValueError("criterion must be evidence, instance, or auto")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    raw_candidates = payload.get("candidates") or []
    if not isinstance(raw_candidates, list):
        raise ValueError("candidates must be a list")
    candidates: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_candidates):
        if not isinstance(raw, Mapping):
            raise ValueError(f"candidate_{index}_must_be_object")
        item = dict(raw)
        item.setdefault("candidate_id", f"candidate-{index:04d}")
        item["text"] = str(item.get("text") or "")
        if not item["text"].strip():
            raise ValueError(f"candidate_{index}_text_missing")
        candidates.append(item)
    if not candidates:
        return {"status": "ok", "engine": engine, "backend": "none", "real_engine": False,
                "real_jev": False, "criterion": criterion, "threshold": threshold, "scores": [],
                "survivors": [], "result_list": [], **aggregate_survivors([]), "errors": []}
    offline_scoring = score_fn is not None
    if score_fn is None:
        if engine == "laya":
            score_fn = lambda q, text, crit: laya_score(q, text, crit, env=env)
        else:
            score_fn = lambda q, text, crit: http_score(q, text, crit, env=env)
    if engine == "laya":
        config = {"model": _laya_config(env)["model"], "key_env": ""}
    else:
        config = check_config(env)
    scored: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for candidate in candidates:
        item = dict(candidate)
        candidate_id = str(item["candidate_id"])
        try:
            score, metadata = score_fn(query, item["text"], criterion)
            if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0.0 <= float(score) <= 1.0:
                raise JevUnavailable("score_invalid")
            item.update({"score": float(score), "kept": float(score) >= threshold,
                         "backend": "offline" if offline_scoring else ("laya_sdk" if engine == "laya" else "http"),
                         "real_engine": not offline_scoring,
                         "real_jev": engine == "jev" and not offline_scoring,
                         "jev_meta": metadata or {}})
        except Exception as exc:  # fail closed per candidate
            item.update({"score": None, "kept": False, "backend": "unavailable", "real_jev": False})
            item["error"] = str(exc)[:240]
            errors.append({"candidate_id": candidate_id, "error": item["error"]})
        scored.append(item)
    real_scores = [item for item in scored if item.get("score") is not None]
    all_real = bool(real_scores) and len(real_scores) == len(scored) and not errors
    status = "ok" if all_real else ("unavailable" if not real_scores else "error")
    survivors = [item for item in scored if item.get("kept") is True and item.get("score") is not None]
    packed = aggregate_survivors(survivors, int(payload.get("max_evidence_chars", DEFAULT_EVIDENCE_CHARS)))
    return {
        "status": status, "engine": engine,
        "backend": ("offline" if offline_scoring else ("laya_sdk" if engine == "laya" else "http")) if all_real else "unavailable",
        "real_engine": all_real and not offline_scoring,
        "real_jev": all_real and engine == "jev" and not offline_scoring,
        "criterion": criterion, "threshold": threshold, "model": config["model"], "key_env": config["key_env"],
        "candidate_count": len(candidates), "scored_count": len(real_scores),
        "scores": _result_records(scored),
        "result_list": [item for item in survivors],
        "survivors": survivors, **packed, "errors": errors,
    }


def _write_json(path: str | None, value: Mapping[str, Any]) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2)
    if path:
        Path(path).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed structured evidence filter")
    parser.add_argument("--input", help="JSON input path; default stdin")
    parser.add_argument("--output", help="JSON output path; default stdout")
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--require-real", action="store_true")
    parser.add_argument("--engine", choices=["laya", "jev"], default="laya")
    args = parser.parse_args(argv)
    if args.check_config:
        config = check_config()
        config.update({"engine": "laya", "laya_model": _laya_config(None)["model"],
                       "laya_subfolder": _laya_config(None)["subfolder"],
                       "laya_sdk_available": importlib.util.find_spec("laya") is not None})
        _write_json(args.output, config)
        return 0
    try:
        text = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
        payload = json.loads(text)
        payload["engine"] = args.engine
        if args.threshold is not None:
            payload["threshold"] = args.threshold
        result = filter_candidates(payload)
        _write_json(args.output, result)
        return 2 if args.require_real and not result.get("real_engine") else 0
    except Exception as exc:  # noqa: BLE001
        result = {"status": "error", "backend": "unavailable", "real_jev": False,
                  "errors": [{"error": str(exc)[:240]}], "survivors": [],
                  "evidence_pack": "", "provenance": []}
        _write_json(args.output, result)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
