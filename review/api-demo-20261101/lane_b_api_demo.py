# -*- coding: utf-8 -*-
"""Lane B（对外 API 实测）：纯 HTTP，不经过 MCP 工具面。

  web(6789)  /api/kb/*            —— KB/文档管理 REST（前端与外部插件面）
  backend(8771) /api/v1/*         —— 解析/索引/检索引擎 REST
  鉴权：.env MCP_AUTH_TOKEN（Bearer），与 soul.py 后端→web 内呼同款。

  健康探针 → 目录基线 → 建库 → MinerU 解析 3 PNG（multipart 上传）
  → 文档创建（解析 markdown 全文落库）→ 单文档索引 + reindex
  → 向量检索 3 题（金标判分）→ 批量删文档 → 空库核验 → 删库 → 目录核验

运行: uv run --no-sync --directory backend python ../review/api-demo-20261101/lane_b_api_demo.py
"""
import json
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
ART = BASE / "artifacts" / "lane_b"
ART.mkdir(parents=True, exist_ok=True)
GOLD = json.loads((BASE / "gallery" / "gold.json").read_text(encoding="utf-8"))
REPO = BASE.parents[1]

WEB = "http://127.0.0.1:6789"
BE = "http://127.0.0.1:8771"
KB_NAME = "图库演示-20261101-API车道"
KB_DESC = "2026-11-01 图库全生命周期对外 API 实测沙箱库（HTTP 车道）：解析-检索-删除，用后即删"

TOKEN = ""
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
        break
H = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

REPORT = {"lane": "B 对外 API 实测（web 6789 /api/kb/* + backend 8771 /api/v1/*）",
          "steps": [], "started": ""}


def save(name, payload):
    (ART / f"{name}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def step(name, ok, detail=""):
    REPORT["steps"].append({"step": name, "ok": bool(ok), "detail": str(detail)[:300]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}", flush=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    REPORT["started"] = time.strftime("%Y-%m-%d %H:%M:%S")
    cli = httpx.Client(trust_env=False, timeout=60, headers=H)
    parse_cli = httpx.Client(trust_env=False, timeout=420, headers=H)

    # b01 后端健康
    r = cli.get(f"{BE}/api/v1/health")
    save("b01_backend_health", {"status": r.status_code, "body": r.json() if r.status_code == 200 else r.text[:300]})
    step("b01 backend health", r.status_code == 200, f"HTTP {r.status_code}")

    # b02 目录基线
    r = cli.get(f"{WEB}/api/kb/catalog")
    cat = r.json() if r.status_code == 200 else {}
    save("b02_catalog_baseline", {"status": r.status_code, "body": cat})
    step("b02 web catalog reachable", r.status_code == 200, f"count={cat.get('count')} KBs, auth={'Bearer' if H else 'NONE'}")

    # b03 建库
    r = cli.post(f"{WEB}/api/kb/create", json={"name": KB_NAME, "description": KB_DESC})
    body = {}
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:300]}
    save("b03_kb_create", {"status": r.status_code, "body": body})
    kb_id = (body.get("knowledgeBase", {}) or {}).get("id") or body.get("id") or body.get("kbId") or body.get("path") or ""
    step("b03 kb create", r.status_code in (200, 201) and bool(kb_id), f"kb_id={kb_id}")
    if not kb_id:
        (BASE / "lane_b_report.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    # b04 MinerU 解析 3 PNG（multipart）
    md_paths = {}
    for img in GOLD["images"]:
        p = BASE / "gallery" / img["file"]
        t0 = time.time()
        r = parse_cli.post(f"{BE}/api/v1/parse/file/vt",
                           files={"file": (img["file"], p.read_bytes(), "image/png")},
                           data={"use_ocr": "true"})
        dt = round(time.time() - t0, 1)
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:300]}
        save(f"b04_parse_{img['file'][:2]}", {"status": r.status_code, "seconds": dt, "body": body})
        mp = body.get("markdown_path") or (body.get("result") or {}).get("markdown_path") or ""
        md_paths[img["file"]] = mp
        step(f"b04 parse {img['file'][:2]}", r.status_code == 200 and bool(mp), f"{dt}s markdown_path={mp}")

    # b05 文档创建（markdown 全文落库 + 描述）
    doc_paths = {}
    for img in GOLD["images"]:
        mp = md_paths.get(img["file"])
        if not mp or not Path(mp).exists():
            step(f"b05 create {img['file'][:2]}", False, f"markdown missing: {mp}")
            continue
        content = Path(mp).read_text(encoding="utf-8", errors="replace")
        r = cli.post(f"{WEB}/api/kb/documents/create",
                     json={"kbId": kb_id, "name": img["doc_title"],
                           "content": content, "description": img["description"]})
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:300]}
        save(f"b05_create_{img['file'][:2]}", {"status": r.status_code, "body": body})
        dp = (body.get("document") or {}).get("path") or body.get("docPath") or body.get("path") or ""
        doc_paths[img["file"]] = dp
        step(f"b05 create {img['file'][:2]}", r.status_code in (200, 201) and bool(dp),
             f"chars={len(content)} doc_path={dp}")

    # b06 单文档索引 + 库级 reindex
    for i, img in enumerate(GOLD["images"]):
        dp = doc_paths.get(img["file"])
        if not dp:
            continue
        r = cli.post(f"{BE}/api/v1/search/index-document",
                     json={"kb_id": kb_id, "doc_path": dp,
                           "doc_name": img["doc_title"], "description": img["description"]})
        save(f"b06_index_{img['file'][:2]}", {"status": r.status_code, "body": r.json() if r.status_code == 200 else r.text[:300]})
        step(f"b06 index {img['file'][:2]}", r.status_code == 200, f"HTTP {r.status_code}")
    r = cli.post(f"{BE}/api/v1/search/reindex", json={"kb_id": kb_id})
    save("b06b_reindex", {"status": r.status_code, "body": r.json() if r.status_code == 200 else r.text[:300]})
    step("b06b reindex", r.status_code == 200, f"HTTP {r.status_code}")

    # b07 向量检索 3 题（金标判分）
    for i, img in enumerate(GOLD["images"]):
        t0 = time.time()
        r = cli.post(f"{BE}/api/v1/search/vector",
                     json={"query": img["query"], "kb_id": kb_id, "top_k": 5})
        dt = round(time.time() - t0, 1)
        try:
            body = r.json()
        except Exception:
            body = {}
        hits = body.get("results") or []
        save(f"b07_vector_q{i+1}", {"status": r.status_code, "seconds": dt, "body": body})
        top1 = str((hits[0] if hits else {}).get("doc_path") or (hits[0] if hits else {}).get("path") or "")
        score = (hits[0] if hits else {}).get("score", 0) or 0
        # 金标断言：top1 必须正是 b05 为该图创建的文档（API 车道文档以标题命名，不能按 03 前缀匹配）
        expect_name = Path(doc_paths[img["file"]]).name if doc_paths.get(img["file"]) else img["expect_doc"]
        step(f"b07 vector q{i+1} ({img['file'][:2]})",
             r.status_code == 200 and bool(hits) and expect_name in top1,
             f"{dt}s top1={top1 or 'EMPTY'} score={round(score, 4)}")

    # b08 批量删文档
    dps = [d for d in doc_paths.values() if d]
    r = cli.post(f"{WEB}/api/kb/documents/batch-delete", json={"kbId": kb_id, "docPaths": dps})
    save("b08_batch_delete", {"status": r.status_code, "body": r.json() if r.status_code == 200 else r.text[:300]})
    try:
        bd = r.json()
        step("b08 batch delete docs", r.status_code == 200 and bd.get("failed", 1) == 0 and bd.get("successful", 0) == len(dps),
             f"successful={bd.get('successful')} failed={bd.get('failed')}")
    except Exception:
        step("b08 batch delete docs", False, r.text[:150])

    # b09 空库核验
    r = cli.get(f"{WEB}/api/kb/documents", params={"kb_id": kb_id})
    body = r.json() if r.status_code == 200 else {}
    save("b09_verify_empty", {"status": r.status_code, "body": body})
    step("b09 verify empty (count==0)", body.get("count") == 0, f"count={body.get('count')}")

    # b10 删库 + 目录核验
    r = cli.request("DELETE", f"{WEB}/api/kb/delete", content=json.dumps({"kbId": kb_id}),
                    headers={**H, "Content-Type": "application/json"})
    save("b10_kb_delete", {"status": r.status_code, "body": r.text[:300]})
    step("b10 kb delete", r.status_code in (200, 201, 204), f"HTTP {r.status_code}")
    r = cli.get(f"{WEB}/api/kb/catalog")
    gone = KB_NAME not in r.text
    save("b10b_catalog_after", {"status": r.status_code, "kb_gone": gone})
    step("b10b verify KB gone from catalog", gone, "catalog clean" if gone else "STILL PRESENT")

    passed = sum(1 for x in REPORT["steps"] if x["ok"])
    REPORT["summary"] = f"{passed}/{len(REPORT['steps'])} PASS"
    (BASE / "lane_b_report.json").write_text(
        json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== Lane B done: {REPORT['summary']} ===")


if __name__ == "__main__":
    main()
