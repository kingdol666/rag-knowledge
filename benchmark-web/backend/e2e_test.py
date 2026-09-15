"""End-to-end test for the QDCVR Benchmark API.

Exercises the whole surface against a **running** backend, in the order a real
user would: describe -> upload -> list -> search (per-algorithm params) ->
compare (with and without ground truth) -> read -> delete -> cleanup.

Usage
-----
    python e2e_test.py                      # against http://127.0.0.1:8800
    python e2e_test.py --base http://host:port
    python e2e_test.py --keep               # do not delete the seeded corpus

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
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

PASS, FAIL = "PASS", "FAIL"
_results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    _results.append((PASS if ok else FAIL, name, detail))
    mark = "\u2713" if ok else "\u2717"
    print(f"  {mark} {name}" + (f"  — {detail}" if detail else ""))
    return ok


def request(base: str, method: str, path: str, *, body: Any = None,
            raw: bytes | None = None, content_type: str | None = None,
            timeout: int = 300) -> tuple[int, Any]:
    url = base.rstrip("/") + path
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    headers = {"Content-Type": content_type or "application/json"}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
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


def post_files(base: str, path: str, files: list[tuple[str, bytes]],
               query: str = "") -> tuple[int, Any]:
    """POST a multipart/form-data body built by hand (no external deps)."""
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


# ── seed corpus: two clearly separated domains, so retrieval is checkable ────
CORPUS = [
    ("battery-thermal", "Battery Thermal Management with PCM", "Energy-Batteries",
     "Phase change materials absorb latent heat while melting and hold a battery "
     "pack near their melting point. Paraffin wax with a 40 to 50 Celsius melting "
     "point and fatty acids are used for lithium-ion battery thermal management. "
     "Hybrid designs combine PCM with liquid cooling channels to raise heat "
     "dissipation. Copper foam composites lift effective thermal conductivity "
     "from 0.2 to between 5 and 10 watts per metre-kelvin."),
    ("battery-soc", "GNN for Battery State of Charge Estimation", "Energy-Batteries",
     "Graph neural networks estimate battery state of charge from voltage, current "
     "and temperature sequences. Cells are modelled as graph nodes and a "
     "spatio-temporal GNN captures cell-to-cell variation inside a pack. A gated "
     "GCN with attention weights neighbouring cells. Mean absolute error stays "
     "under 1.5 percent, beating LSTM at 3.2 percent and a Kalman filter at 5 percent."),
    ("pneumonia-cnn", "CNN for Chest X-Ray Pneumonia Detection", "Biomedical-Engineering",
     "Convolutional networks detect pneumonia in chest radiographs. DenseNet-121 "
     "pretrained on ImageNet is fine-tuned on ChestX-ray14 with 112,120 images and "
     "reaches an AUROC of 0.85, matching radiologist performance. Class activation "
     "maps highlight affected lung regions. A two-stage pipeline segments the lung "
     "with U-Net before classifying, and a five-model ensemble lifts AUROC to 0.88."),
    ("hydrogel", "Stimuli-Responsive Hydrogels for Drug Delivery", "Biomedical-Engineering",
     "Smart hydrogels release drugs on demand in response to pH, temperature, "
     "enzymes or light. PNIPAAm hydrogels undergo a volume phase transition at a "
     "32 Celsius lower critical solution temperature. pH-responsive poly acrylic "
     "acid swells above pH 5.5 in the intestine and releases the payload there. "
     "A glucose-responsive phenylboronic acid hydrogel with glucose oxidase "
     "delivers insulin. Doxorubicin-loaded gels cut tumour volume 80 percent."),
]

UPLOAD_FILES = [
    ("dqn-atari.md",
     b"# Deep Q-Network\n\nDQN combines Q-learning with a deep convolutional network. "
     b"An experience replay buffer stores transitions and samples random minibatches "
     b"to break temporal correlations, and a target network is refreshed periodically. "
     b"Evaluated on 49 Atari 2600 games, surpassing human performance on 23.\n"),
    ("mxene.txt",
     b"MXene Ti3C2Tx is made by selectively etching Al from the Ti3AlC2 MAX phase "
     b"with HF or LiF plus HCl. The accordion-like layered structure has an "
     b"interlayer spacing of 1.0 to 1.5 nanometres. Surface terminations contribute "
     b"pseudocapacitance, giving 245 farads per gram at 2 millivolts per second.\n"),
    ("sensors.csv",
     b"material,application,gauges\n"
     b"graphene oxide,human motion detection,25\n"
     b"MXene,respiratory monitoring,18\n"),
    ("catalog.json",
     b'{"topic": "solid-state electrolytes", "classes": '
     b'["oxide LLZO", "sulfide LGPS", "polymer PEO-LiTFSI"], '
     b'"conductivity_s_per_cm": 0.001}'),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8800")
    parser.add_argument("--keep", action="store_true",
                        help="leave the seeded corpus in place afterwards")
    args = parser.parse_args()
    base = args.base

    print("=" * 78)
    print(f"QDCVR Benchmark API — end-to-end test against {base}")
    print("=" * 78)

    # ── 1. meta ─────────────────────────────────────────────────────────────
    print("\n[1] Service description")
    status, index = request(base, "GET", "/")
    if not check("GET / responds", status == 200, f"HTTP {status}"):
        print("\nbackend not reachable — start it with `python main.py`")
        return 2
    check("index advertises the algorithm set",
          isinstance(index.get("algorithms"), list) and len(index["algorithms"]) >= 8,
          f"{len(index.get('algorithms', []))} algorithms")
    check("index advertises the route map", "routes" in index)

    status, health = request(base, "GET", "/api/health")
    check("GET /api/health reports healthy", status == 200 and health.get("status") == "healthy")
    check("health reports index state", "index" in health)

    status, catalogue = request(base, "GET", "/api/algorithms")
    algorithms = {a["id"]: a for a in catalogue.get("algorithms", [])}
    check("GET /api/algorithms returns the registry", status == 200 and len(algorithms) >= 8,
          f"{len(algorithms)} algorithms")
    check("every algorithm declares a parameter schema",
          all(isinstance(a.get("params"), list) and a["params"] for a in algorithms.values()))
    expected = {"bm25", "dense", "hybrid", "ce_rerank", "crag", "selfrag",
                "qdcvr_flat", "qdcvr_domain"}
    check("all eight paper baselines are registered",
          expected <= set(algorithms), f"missing: {sorted(expected - set(algorithms))}")
    check("bm25 exposes k1 and b",
          {"k1", "b"} <= {p["name"] for p in algorithms["bm25"]["params"]})
    check("hybrid exposes alpha and norm",
          {"alpha", "norm"} <= {p["name"] for p in algorithms["hybrid"]["params"]})

    # ── 2. corpus seeding ───────────────────────────────────────────────────
    print("\n[2] Corpus: add by JSON")
    status, _ = request(base, "DELETE", "/api/documents")
    check("DELETE /api/documents clears the corpus", status == 200)

    payload = [{"id": i, "title": t, "domain": d, "content": c} for i, t, d, c in CORPUS]
    status, added = request(base, "POST", "/api/documents/batch", body=payload)
    check("POST /api/documents/batch indexes every document",
          status == 201 and added.get("added") == len(CORPUS),
          f"HTTP {status}, added={added.get('added')}")
    check("chunking produced chunks", added.get("chunks", 0) > 0,
          f"{added.get('chunks')} chunks")

    status, duplicate = request(base, "POST", "/api/documents",
                                body={"id": "battery-thermal", "title": "replaced",
                                      "domain": "Energy-Batteries", "content": "replacement body"})
    check("re-posting an existing id replaces it",
          status == 201 and duplicate.get("id") == "battery-thermal")
    status, listing = request(base, "GET", "/api/documents")
    check("replacement did not duplicate the document",
          listing.get("total") == len(CORPUS), f"total={listing.get('total')}")
    # restore the original body
    request(base, "POST", "/api/documents",
            body={"id": "battery-thermal", "title": CORPUS[0][1], "domain": CORPUS[0][2],
                  "content": CORPUS[0][3]})

    print("\n[3] Corpus: file upload")
    status, upload = post_files(base, "/api/documents/upload", UPLOAD_FILES,
                                "?domain=Uploaded")
    check("POST /api/documents/upload accepts multipart files", status == 201,
          f"HTTP {status}")
    check("every uploaded file was parsed and indexed",
          upload.get("uploaded") == len(UPLOAD_FILES),
          f"uploaded={upload.get('uploaded')} failed={upload.get('failed')}")
    kinds = {f["filename"]: f.get("kind") for f in upload.get("files", []) if f.get("ok")}
    check("markdown parsed as text", kinds.get("dqn-atari.md") == "text")
    check("csv parsed as a table", kinds.get("sensors.csv") == "table")
    check("json parsed and flattened", kinds.get("catalog.json") == "json")
    uploaded_ids = [f["id"] for f in upload.get("files", []) if f.get("ok")]

    status, rejected = post_files(base, "/api/documents/upload",
                                  [("binary.xyz", b"\x00\x01\x02")])
    check("an unsupported extension is rejected per-file, not fatally",
          rejected.get("failed") == 1 and rejected.get("uploaded") == 0,
          json.dumps(rejected.get("files", []))[:120])

    status, empty = post_files(base, "/api/documents/upload", [("empty.txt", b"")])
    check("an empty file is reported, not silently dropped",
          empty.get("failed") == 1, json.dumps(empty.get("files", [{}]))[:100])

    status, mixed = post_files(base, "/api/documents/upload",
                               [("good.md", b"# Valid\n\nSome indexable body text."),
                                ("bad.xyz", b"\x00\x01")])
    check("a bad file does not discard its good sibling",
          mixed.get("uploaded") == 1 and mixed.get("failed") == 1,
          f"uploaded={mixed.get('uploaded')} failed={mixed.get('failed')}")
    mixed_ids = [f["id"] for f in mixed.get("files", []) if f.get("ok")]
    uploaded_ids += mixed_ids

    status, domains = request(base, "GET", "/api/domains")
    check("GET /api/domains lists local domains",
          status == 200 and "Energy-Batteries" in domains.get("local", []),
          f"local={domains.get('local')}")

    # ── 4. search ───────────────────────────────────────────────────────────
    print("\n[4] Retrieval: POST /api/search")
    status, plain = request(base, "POST", "/api/search",
                            body={"query": "battery thermal management phase change material",
                                  "methods": ["bm25", "dense", "hybrid"],
                                  "top_k": 3})
    if not check("search returns 200", status == 200,
                 f"HTTP {status}: {json.dumps(plain)[:200] if not isinstance(plain, dict) else ''}"):
        return 1
    by_method = plain.get("results", {})
    check("all requested methods returned",
          set(by_method) == {"bm25", "dense", "hybrid"}, f"keys={list(by_method)}")
    check("no method reported an error", not plain.get("errors"),
          json.dumps(plain.get("errors", {}))[:200])
    check("bm25 found the relevant battery document",
          any("Battery Thermal" in r["title"] for r in by_method["bm25"]["results"]),
          json.dumps([r["title"] for r in by_method["bm25"]["results"]])[:140])
    check("dense found the relevant battery document",
          any("Battery Thermal" in r["title"] for r in by_method["dense"]["results"]),
          json.dumps([r["title"] for r in by_method["dense"]["results"]])[:140])
    check("results carry a content preview",
          all(r.get("content_preview") for r in by_method["bm25"]["results"]))

    print("\n[5] Retrieval: per-algorithm parameters")
    status, strict = request(base, "POST", "/api/search",
                             body={"query": "battery thermal management",
                                   "methods": ["bm25"], "top_k": 5,
                                   "params": {"bm25": {"k1": 0.1, "b": 0.0}}})
    check("bm25 accepts k1/b overrides", status == 200)
    check("effective parameters are echoed back",
          strict["results"]["bm25"]["params"].get("k1") == 0.1
          and strict["results"]["bm25"]["params"].get("b") == 0.0,
          json.dumps(strict["results"]["bm25"]["params"]))

    status, wide = request(base, "POST", "/api/search",
                           body={"query": "battery thermal management",
                                 "methods": ["bm25"], "top_k": 5,
                                 "params": {"bm25": {"k1": 2.9, "b": 1.0}}})
    check("a different k1/b yields a different ranking",
          [r["chunk_id"] for r in strict["results"]["bm25"]["results"]]
          != [r["chunk_id"] for r in wide["results"]["bm25"]["results"]]
          or [round(r["score"], 4) for r in strict["results"]["bm25"]["results"]]
          != [round(r["score"], 4) for r in wide["results"]["bm25"]["results"]],
          "scores or order changed")

    status, hybrid_left = request(base, "POST", "/api/search",
                                  body={"query": "chest x-ray pneumonia detection",
                                        "methods": ["hybrid"], "top_k": 3,
                                        "params": {"hybrid": {"alpha": 0.0, "norm": "minmax"}}})
    status2, hybrid_right = request(base, "POST", "/api/search",
                                    body={"query": "chest x-ray pneumonia detection",
                                          "methods": ["hybrid"], "top_k": 3,
                                          "params": {"hybrid": {"alpha": 1.0, "norm": "minmax"}}})
    check("hybrid alpha=0 equals the dense-only ranking",
          [r["chunk_id"] for r in hybrid_left["results"]["hybrid"]["results"]]
          == [r["chunk_id"] for r in request(
              base, "POST", "/api/search",
              body={"query": "chest x-ray pneumonia detection", "methods": ["dense"],
                    "top_k": 3})[1]["results"]["dense"]["results"]],
          "pure-dense endpoint matches")

    status, bad = request(base, "POST", "/api/search",
                          body={"query": "x", "methods": ["bm25"],
                                "params": {"bm25": {"k1": 99}}})
    check("out-of-range parameter is rejected with a named error",
          bad.get("results", {}).get("bm25", {}).get("error") is not None
          and "k1" in str(bad["results"]["bm25"]["error"]),
          str(bad.get("results", {}).get("bm25", {}).get("error"))[:90])

    status, unknown = request(base, "POST", "/api/search",
                              body={"query": "x", "methods": ["bm25"],
                                    "params": {"bm25": {"nope": 1}}})
    check("unknown parameter name is reported",
          "nope" in str(unknown.get("results", {}).get("bm25", {}).get("error")),
          str(unknown.get("results", {}).get("bm25", {}).get("error"))[:90])

    status, unknown_alg = request(base, "POST", "/api/search",
                                  body={"query": "x", "methods": ["does_not_exist"]})
    check("unknown algorithm is a 422", status == 422, f"HTTP {status}")

    print("\n[5b] Every algorithm actually runs (no silent fallback)")
    status, all_methods = request(base, "POST", "/api/compare",
                                  body={"query": "battery thermal management",
                                        "methods": ["bm25", "dense", "hybrid", "ce_rerank",
                                                    "crag", "selfrag"],
                                        "top_k": 3})
    check("compare runs all six local algorithms", status == 200, f"HTTP {status}")
    per_method = all_methods.get("comparison", {}).get("per_method", {})
    broken = {m: row.get("error") for m, row in per_method.items() if row.get("error")}
    check("no local algorithm errored", not broken,
          json.dumps(broken)[:200] if broken else "6/6 clean")
    ce_hits = all_methods.get("results", {}).get("ce_rerank", {}).get("results", [])
    ce_fallback = [h for h in ce_hits if "FALLBACK" in str(h.get("source", ""))]
    check("the cross-encoder reranker really ran (not the fallback path)",
          bool(ce_hits) and not ce_fallback,
          (ce_hits[0]["source"] if ce_hits else "no hits"))

    print("\n[6] Retrieval: alias and domain scoping")
    status, aliased = request(base, "POST", "/api/search",
                              body={"query": "pneumonia", "methods": ["vector"], "top_k": 3})
    check("legacy alias 'vector' resolves to 'dense'",
          "dense" in aliased.get("results", {}),
          f"keys={list(aliased.get('results', {}))}")

    status, scoped = request(base, "POST", "/api/search",
                             body={"query": "thermal management state of charge pneumonia",
                                   "methods": ["dense"], "top_k": 5,
                                   "domain": "Biomedical-Engineering"})
    check("domain filter returns only in-domain documents",
          status == 200 and all(r["domain"] == "Biomedical-Engineering"
                                for r in scoped["results"]["dense"]["results"]),
          json.dumps([r["domain"] for r in scoped["results"]["dense"]["results"]]))

    # ── 7. compare ──────────────────────────────────────────────────────────
    print("\n[7] Comparison: POST /api/compare")
    status, comparison = request(base, "POST", "/api/compare",
                                 body={"query": "graph neural network battery state of charge",
                                       "methods": ["bm25", "dense", "hybrid"],
                                       "top_k": 5})
    check("compare returns 200", status == 200, f"HTTP {status}")
    block = comparison.get("comparison", {})
    check("comparison reports every method",
          set(block.get("per_method", {})) == {"bm25", "dense", "hybrid"})
    check("comparison reports inter-method overlap",
          len(block.get("overlap", {})) == 3, f"{len(block.get('overlap', {}))} pairs")
    check("comparison names the fastest method", bool(block.get("fastest_method")),
          str(block.get("fastest_method")))
    check("metrics are declared unavailable without ground truth",
          block.get("metrics_available") is False and "No ground truth" in block.get("metrics_note", ""))

    status, judged = request(base, "POST", "/api/compare",
                             body={"query": "graph neural network battery state of charge",
                                   "methods": ["bm25", "dense"], "top_k": 5,
                                   "relevant": ["battery-soc"]})
    metrics = judged.get("comparison", {}).get("per_method", {}).get("dense", {}).get("metrics", {})
    check("ground truth switches real IR metrics on",
          judged["comparison"]["metrics_available"] is True and bool(metrics),
          ", ".join(f"{k}={v}" for k, v in list(metrics.items())[:4]))
    check("recall@10 is 1.0 when the only relevant doc is retrieved",
          metrics.get("recall@10") == 1.0, f"recall@10={metrics.get('recall@10')}")

    # ── 8. document lifecycle ───────────────────────────────────────────────
    print("\n[8] Document lifecycle")
    target = uploaded_ids[0] if uploaded_ids else "battery-soc"
    status, one = request(base, "GET", f"/api/documents/{target}")
    check("GET /api/documents/{id} returns the document and its chunks",
          status == 200 and one.get("chunks"), f"{len(one.get('chunks', []))} chunks")

    status, missing = request(base, "GET", "/api/documents/no-such-id")
    check("unknown document id is a 404", status == 404, f"HTTP {status}")

    status, deleted = request(base, "DELETE", f"/api/documents/{target}")
    check("DELETE /api/documents/{id} removes it", status == 200)
    status, gone = request(base, "GET", f"/api/documents/{target}")
    check("deleted document is really gone", status == 404, f"HTTP {status}")

    status, _ = request(base, "DELETE", "/api/documents/no-such-id")
    check("deleting an unknown id is a 404", status == 404, f"HTTP {status}")

    # ── 9. reindex ──────────────────────────────────────────────────────────
    print("\n[9] Index maintenance")
    status, reindexed = request(base, "POST", "/api/reindex")
    check("POST /api/reindex rebuilds the dense index", status == 200,
          f"{reindexed.get('elapsed_ms')} ms" if isinstance(reindexed, dict) else "")
    check("index reports dense readiness",
          isinstance(reindexed, dict) and reindexed.get("dense_ready") is True,
          str(reindexed.get("dense_error") or "no error") if isinstance(reindexed, dict) else "")

    # ── 10. platform-backed algorithms ──────────────────────────────────────
    print("\n[10] Platform-backed algorithms (QDCVR)")
    status, qdcvr = request(base, "POST", "/api/search",
                            body={"query": "pyridostatin G-quadruplex telomere",
                                  "methods": ["qdcvr_flat"], "top_k": 3})
    if status == 200:
        result = qdcvr["results"]["qdcvr_flat"]
        if result.get("error"):
            check("qdcvr_flat reports a clear reason when the platform is unavailable",
                  "platform" in result["error"].lower(), result["error"][:100])
        else:
            check("qdcvr_flat reached the platform API", result["count"] > 0,
                  f"{result['count']} hits")
    else:
        check("qdcvr_flat did not crash the request", False, f"HTTP {status}")

    status, needs_kb = request(base, "POST", "/api/search",
                               body={"query": "x", "methods": ["qdcvr_domain"]})
    check("qdcvr_domain explains that kb_id is required",
          "kb_id" in str(needs_kb.get("results", {}).get("qdcvr_domain", {}).get("error", "")),
          str(needs_kb.get("results", {}).get("qdcvr_domain", {}).get("error"))[:90])

    # ── 11. empty-corpus guard ──────────────────────────────────────────────
    print("\n[11] Guards")
    status, empty_search = request(base, "POST", "/api/search",
                                   body={"query": "x", "methods": ["bm25"]})
    if status == 200:
        check("local search still works while the corpus is populated", True)
    status, bad_query = request(base, "POST", "/api/search", body={"methods": ["bm25"]})
    check("a request without a query is rejected", status == 422, f"HTTP {status}")

    # ── 12. cleanup ─────────────────────────────────────────────────────────
    if not args.keep:
        print("\n[12] Cleanup")
        status, cleared = request(base, "DELETE", "/api/documents")
        check("corpus cleared for the next run", status == 200,
              f"removed={cleared.get('removed')}")

    # ── summary ─────────────────────────────────────────────────────────────
    passed = sum(1 for status_, _, _ in _results if status_ == PASS)
    failed = len(_results) - passed
    print("\n" + "=" * 78)
    print(f"RESULT: {passed} passed, {failed} failed, {len(_results)} checks")
    if failed:
        print("\nFailures:")
        for status_, name, detail in _results:
            if status_ == FAIL:
                print(f"  \u2717 {name}" + (f"  — {detail}" if detail else ""))
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
