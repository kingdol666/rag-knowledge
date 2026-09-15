"""End-to-end test for the RAG answer layer.

The decisive question this suite answers is *not* "does an answer come back" —
it is **"does the answer actually come from the file the user uploaded?"**

So the test plants an invented fact that no model could know (a made-up
instrument, value and trial), asks about it, and then runs the same question a
second time **with the document deleted**. If the number shows up only while the
document is in the corpus, the answer is demonstrably grounded in the upload
rather than in the model's prior knowledge.

This needs a live model, so it is run separately from ``e2e_test.py`` (which is
model-free and fast).

    python e2e_answer_test.py
    python e2e_answer_test.py --base http://127.0.0.1:8800 --keep

Exit code 0 means every check passed.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

_checks: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    _checks.append((ok, name, detail))
    print(f"  {'\u2713' if ok else '\u2717'} {name}" + (f"  — {detail}" if detail else ""))
    return ok


def request(base: str, method: str, path: str, body=None, raw: bytes | None = None,
            content_type: str | None = None, timeout: int = 900):
    url = base.rstrip("/") + path
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": content_type or "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8", "replace")
            try:
                return response.status, json.loads(payload)
            except json.JSONDecodeError:
                return response.status, payload
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, payload
    except urllib.error.URLError as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def post_files(base: str, path: str, files: list[tuple[str, bytes]], query: str = ""):
    boundary = "----bench" + uuid.uuid4().hex
    out = io.BytesIO()
    for name, content in files:
        out.write(f"--{boundary}\r\n".encode())
        out.write(f'Content-Disposition: form-data; name="files"; filename="{name}"\r\n'.encode())
        out.write(b"Content-Type: application/octet-stream\r\n\r\n")
        out.write(content)
        out.write(b"\r\n")
    out.write(f"--{boundary}--\r\n".encode())
    return request(base, "POST", path + query, raw=out.getvalue(),
                   content_type=f"multipart/form-data; boundary={boundary}")


# ── The planted fact. Nothing in this sentence is real, so a model cannot ────
# ── answer it from prior knowledge — only from the document.              ────
SECRET_VALUE = "42.7 mV"
SECRET_TOKEN = "42.7"

PLANTED_DOC = (
    "# Zephyr-7 field calibration report\n\n"
    "The Zephyr-7 ionisation chamber was calibrated at the Kvistad facility during "
    "the 2024 winter campaign. Its calibration constant is 42.7 mV per kilocount, "
    "traceable to standard KV-2024-11. The drift observed over the campaign was "
    "0.3 percent, within the 1 percent tolerance agreed with the manufacturer.\n"
)

# A different, unrelated document — used to prove retrieval is doing the work.
DECOY_DOC = (
    "Phase change materials absorb latent heat while melting and hold a battery "
    "pack near their melting point. Paraffin wax with a 40 to 50 Celsius melting "
    "point is used for lithium-ion battery thermal management.\n"
)

QUESTION = "What is the Zephyr-7 calibration constant?"
CONTROL_QUESTION = "What is the melting point range of the paraffin wax used for batteries?"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8800")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--method", default="dense",
                        help="algorithm used for the single-method checks")
    args = parser.parse_args()
    base = args.base

    print("=" * 78)
    print("QDCVR answer layer — end-to-end test (grounding proof)")
    print("=" * 78)

    status, health = request(base, "GET", "/api/health")
    if not check("backend reachable", status == 200, f"HTTP {status}"):
        return 2
    answering = health.get("answering", {})
    if not check("the answer channel is available", answering.get("available") is True,
                 str(answering.get("detail"))[:120]):
        print("\n  answer generation needs the 'omp' CLI; retrieval still works.")
        return 2

    print("\n[1] Upload a document containing a fact no model could know")
    request(base, "DELETE", "/api/documents")
    status, up = post_files(base, "/api/documents/upload",
                            [("zephyr7-calibration.md", PLANTED_DOC.encode()),
                             ("battery-pcm.txt", DECOY_DOC.encode())],
                            "?domain=Calibration")
    check("both files ingested", up.get("uploaded") == 2,
          f"uploaded={up.get('uploaded')} failed={up.get('failed')}")
    doc_ids = {f["filename"]: f["id"] for f in up.get("files", []) if f.get("ok")}
    check("the planted document is indexed", "zephyr7-calibration.md" in doc_ids,
          json.dumps(doc_ids))

    print("\n[2] Ask the planted question")
    started = time.perf_counter()
    status, res = request(base, "POST", "/api/answer",
                          {"query": QUESTION, "method": args.method, "top_k": 4})
    elapsed = time.perf_counter() - started
    if not check("POST /api/answer returns 200", status == 200,
                 f"HTTP {status}: {json.dumps(res)[:160] if not isinstance(res, dict) else ''}"):
        return 1
    answer = res.get("answer", {})
    text = answer.get("answer", "")
    print(f"      answer: {text[:220]}")
    check("an answer was produced", bool(text.strip()), f"{len(text)} chars")
    check("the answer is grounded in the uploaded file (contains the planted value)",
          SECRET_TOKEN in text, f"looked for {SECRET_VALUE!r}")
    check("the verdict is 'answered'", answer.get("verdict") == "answered",
          str(answer.get("verdict")))
    check("the answer carries citations", len(answer.get("citations", [])) >= 1,
          f"{len(answer.get('citations', []))} citation(s)")
    cited_docs = {c.get("doc_id") for c in answer.get("citations", [])}
    check("the citation points at the planted document",
          doc_ids.get("zephyr7-calibration.md") in cited_docs,
          json.dumps(sorted(str(c) for c in cited_docs))[:140])
    check("every citation resolves to supplied evidence (nothing invented)",
          not answer.get("unknown_citations"), str(answer.get("unknown_citations")))
    check("the answer reports the evidence it used",
          answer.get("evidence_count", 0) >= 1 and answer.get("evidence_chars", 0) > 0,
          f"{answer.get('evidence_count')} sources, {answer.get('evidence_chars')} chars")
    print(f"      (retrieval+generation took {elapsed:.1f}s)")

    print("\n[3] Control — delete the document and ask again")
    request(base, "DELETE", f"/api/documents/{doc_ids['zephyr7-calibration.md']}")
    status, control = request(base, "POST", "/api/answer",
                              {"query": QUESTION, "method": args.method, "top_k": 4})
    control_text = control.get("answer", {}).get("answer", "") if isinstance(control, dict) else ""
    control_verdict = control.get("answer", {}).get("verdict") if isinstance(control, dict) else None
    print(f"      answer: {control_text[:220]}")
    check("with the file gone the planted value is NOT in the answer",
          SECRET_TOKEN not in control_text,
          f"found {SECRET_VALUE!r} without the source document" if SECRET_TOKEN in control_text
          else "value absent, as expected")
    check("and the agent says the evidence is insufficient",
          control_verdict == "insufficient" or not control_text.strip()
          or "insufficient" in control_text.lower(),
          f"verdict={control_verdict}")

    print("\n[4] Verdict on a question the corpus can answer")
    status, good = request(base, "POST", "/api/answer",
                           {"query": CONTROL_QUESTION, "method": args.method, "top_k": 4})
    good_answer = good.get("answer", {}) if isinstance(good, dict) else {}
    print(f"      answer: {good_answer.get('answer', '')[:220]}")
    check("the control question is answered from the remaining document",
          good_answer.get("verdict") == "answered"
          and any(token in good_answer.get("answer", "") for token in ("40", "50", "Celsius", "paraffin")),
          f"verdict={good_answer.get('verdict')}")

    print("\n[5] Different algorithms, same question, same answer agent")
    request(base, "POST", "/api/documents",
            {"id": "zephyr7-calibration", "title": "Zephyr-7 field calibration report",
             "domain": "Calibration", "content": PLANTED_DOC})
    per_method = {}
    for method in ("bm25", args.method):
        status, res = request(base, "POST", "/api/answer",
                              {"query": QUESTION, "method": method, "top_k": 4})
        payload = res.get("answer", {}) if isinstance(res, dict) else {}
        per_method[method] = payload
        check(f"'{method}' retrieves and answers",
              status == 200 and bool(payload.get("answer", "").strip()),
              f"verdict={payload.get('verdict')} hits={res.get('retrieval', {}).get('count') if isinstance(res, dict) else '?'}")
    both_grounded = all(SECRET_TOKEN in p.get("answer", "") for p in per_method.values())
    check("every algorithm's answer is grounded in the same uploaded fact", both_grounded,
          " | ".join(f"{m}:{'42.7' in p.get('answer','')}" for m, p in per_method.items()))

    print("\n[6] Independent grounding verification")
    status, verified = request(base, "POST", "/api/answer",
                               {"query": QUESTION, "method": args.method, "top_k": 4,
                                "verify": True})
    verification = verified.get("verification", {}) if isinstance(verified, dict) else {}
    check("the verifier ran", verification.get("available") is True,
          str(verification.get("error") or "ok")[:100])
    check("the verifier scored the answer", isinstance(verification.get("score"), (int, float)),
          f"score={verification.get('score')} grounded={verification.get('grounded')}")

    print("\n[7] Compare with answers (one shared prompt and budget per method)")
    status, compared = request(base, "POST", "/api/compare",
                               {"query": QUESTION, "methods": ["bm25", args.method],
                                "top_k": 4, "answer": True})
    answers = compared.get("answers") if isinstance(compared, dict) else None
    check("compare returns an answer per method", isinstance(answers, dict)
          and {"bm25", args.method} <= set(answers or {}),
          json.dumps(list((answers or {}).keys())))
    if isinstance(answers, dict):
        for method, payload in answers.items():
            preview = str(payload.get("answer", ""))[:100]
            print(f"      {method}: [{payload.get('verdict')}] {preview}")
        check("each method's answer is grounded in the planted fact",
              all(SECRET_TOKEN in str(p.get("answer", "")) for p in answers.values()))

    print("\n[8] Error handling")
    status, bad = request(base, "POST", "/api/answer",
                          {"query": "x", "method": "no_such_algorithm"})
    check("an unknown algorithm is rejected", status == 422, f"HTTP {status}")

    if not args.keep:
        print("\n[9] Cleanup")
        status, cleared = request(base, "DELETE", "/api/documents")
        check("corpus cleared for the next run", status == 200,
              f"removed={cleared.get('removed')}")

    passed = sum(1 for ok, _, _ in _checks if ok)
    failed = len(_checks) - passed
    print("\n" + "=" * 78)
    print(f"RESULT: {passed} passed, {failed} failed, {len(_checks)} checks")
    if failed:
        print("\nFailures:")
        for ok, name, detail in _checks:
            if not ok:
                print(f"  \u2717 {name}" + (f"  — {detail}" if detail else ""))
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
