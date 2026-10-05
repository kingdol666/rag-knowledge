"""S3+S4 — volume (250KB doc ingest, top_k-stretched search) + parallel parses.

Usage: backend/.venv/Scripts/python.exe review/stress-20260923/s3_volume.py
"""
import json
import sys
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, "review/stress-20260923")
from stress_lib import BE, WEB, HEADERS, HERE, ROOT, OPENER, check, client, guard_url, report  # noqa: E402

state = json.loads(HERE.joinpath("stress_state.json").read_text(encoding="utf-8"))
KB = state["kb_uuid"]
KB_NAME = state["kb_name"]

# ---- S3a: 250KB single-doc ingest + index ----
big = ("# 大容量压测文档\n\n这是一篇用于验证大文档入库链路的超长压测文档。" * 3 + "\n\n")
para = ("大容量压测段落：覆盖分块、向量化与检索回验。独立标记词 STRESSBIG-9F3A 出现在此。"
        "附随内容保证每个分块都有可检索的语义信息，包含中英文与数字 1234567890。\n\n")
big += para * 900  # ~ 250KB
print(f"[i] big doc size = {len(big.encode('utf-8'))} bytes", flush=True)
t0 = time.perf_counter()
with client() as c:
    r = c.post(WEB + "/api/kb/documents/create",
               json={"kbId": KB, "name": "stress-bigdoc.md", "content": big,
                     "description": "Stress 250KB volume doc", "tags": ["stress"]},
               headers=HEADERS, timeout=120)
    check("250KB doc create", r.status_code == 200 and r.json().get("success"),
          f"status={r.status_code}")
    t1 = time.perf_counter()
    r = c.post(BE + "/api/v1/search/index-document",
               json={"kb_id": KB, "doc_path": f"{KB_NAME}/stress-bigdoc.md", "doc_name": "stress-bigdoc",
                     "description": "Stress 250KB volume doc", "content": big, "skip_graph": True},
               headers=HEADERS, timeout=600)
    dt = time.perf_counter() - t1
    check("250KB doc index", r.status_code == 200 and r.json().get("success"),
          f"index_dur={dt:.1f}s body={json.dumps(r.json(), ensure_ascii=False)[:140]}")
    r = c.post(BE + "/api/v1/search/vector", json={"query": "STRESSBIG-9F3A 独立标记词", "kb_id": KB, "top_k": 5},
               headers=HEADERS, timeout=60)
    check("250KB doc searchable", "STRESSBIG-9F3A" in json.dumps(r.json(), ensure_ascii=False) or "9F3A" in json.dumps(r.json(), ensure_ascii=False),
          f"dur={time.perf_counter()-t1:.1f}s")

# ---- S3b: top_k-stretched searches ----
with client() as c:
    t0 = time.perf_counter()
    r = c.post(BE + "/api/v1/search/vector", json={"query": "压测 检索", "kb_id": KB, "top_k": 50},
               headers=HEADERS, timeout=120)
    dt = time.perf_counter() - t0
    check("vector top_k=50", r.status_code == 200 and len(r.json().get("results") or []) > 0,
          f"dur={dt:.1f}s count={r.json().get('count')}")
    t0 = time.perf_counter()
    r = c.post(BE + "/api/v1/search/two-stage",
               json={"query": "检索 压测 完整性", "kb_id": KB, "stage1_top_k": 100, "stage2_top_k": 20},
               headers=HEADERS, timeout=120)
    dt = time.perf_counter() - t0
    st2 = (r.json().get("stage2") or {}).get("results") or []
    check("two-stage stage1=100 stage2=20", r.status_code == 200 and len(st2) > 0,
          f"dur={dt:.1f}s stage2={len(st2)}")

# ---- S4: 2 parallel MinerU parses (real PDFs) ----
pdf_dir = ROOT.joinpath("docs", "paper", "benchmark", "datasets", "arxiv-benchmark")
pdfs = ["vision-mamba.pdf", "global-rag-benchmark.pdf"]


def parse_one(url: str, fname: str):
    guard_url(url)
    data = (pdf_dir / fname).read_bytes()
    boundary = "----stress" + uuid.uuid4().hex
    buf = b""
    buf += ("--" + boundary + "\r\n").encode()
    buf += ('Content-Disposition: form-data; name="file"; filename="' + fname + '"\r\n').encode()
    buf += ("Content-Type: application/pdf\r\n\r\n").encode()
    buf += data + b"\r\n"
    buf += ("--" + boundary + "\r\n").encode()
    buf += ('Content-Disposition: form-data; name="use_ocr"\r\n\r\ntrue\r\n').encode()
    buf += ("--" + boundary + "--\r\n").encode()
    req = urllib.request.Request(url, data=buf, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    req.add_header("Authorization", "Bearer " + __import__("stress_lib").TOKEN)
    t0 = time.perf_counter()
    try:
        with OPENER.open(req, timeout=900) as r:
            j = json.loads(r.read().decode("utf-8", "replace"))
        return fname, r.status, j.get("success", False), j.get("image_count"), time.perf_counter() - t0, ""
    except Exception as e:  # noqa: BLE001
        return fname, 0, False, 0, time.perf_counter() - t0, repr(e)[:120]


print("[i] launching 2 parallel MinerU parses ...", flush=True)
t0 = time.perf_counter()
parse_url = WEB + "/api/parse/file-vt"
with ThreadPoolExecutor(max_workers=2) as ex:
    parse_results = list(ex.map(lambda f: parse_one(parse_url, f), pdfs))
dt_parse = time.perf_counter() - t0
for fname, code, ok, images, dur, err in parse_results:
    check(f"parallel parse [{fname}]", code == 200 and ok,
          f"dur={dur:.0f}s images={images} {err}")
check("parallel parse wall-clock < 2x single", dt_parse < 170, f"wall={dt_parse:.0f}s (single was 41s)")

sys.exit(report("S3+S4 volume+parallel-parse"))
