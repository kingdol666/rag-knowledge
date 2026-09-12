#!/usr/bin/env python3
"""模块 A — 文档解析与入库基准.

流程(全部生产链路):
  1. 创建 3 个知识库 KB-Demo-EN/ZH/JA (web /api/kb/create)
  2. 15 篇 md 走 web /api/kb/documents/create (大文档自动拆分为 part)
  3. PDF(wind-energy.pdf) 走 MCP 真链路解析: parse_doc(MinerU) → 轮询 →
     kb_doc_create 写入 KB-Demo-EN (文档解析能力实测)
  4. batch-index force 重索引(触发 BM25 失效重建)
指标:
  parse_success          PDF 解析成功率(产出正文字符数>500)
  ingest_success_rate    create 成功率(409=已存在, 记成功; 含 PDF 文档)
  membership_accuracy    指定库归属正确率(文档出现在目标 KB 清单)
  storage_completeness   回读字符数 / 源字符数(按 part 求和)
  self_retrieval_hit1    以文档首 200 字符为查询, 库内向量检索 top-3 命中自身
输出: results/module_a_ingestion_r{1,2}.json
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (BACKEND, WEB, McpClient, doc_basename,  # noqa: E402
                 env_fingerprint, http_delete, http_get, http_post, mean, now_iso)

DATA = Path(__file__).resolve().parent.parent / "data"
RESULTS = Path(__file__).resolve().parent.parent / "results"
KBS = {"en": "KB-Demo-EN", "zh": "KB-Demo-ZH", "ja": "KB-Demo-JA"}
ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"


def sanitize(title: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]', "_", title).strip().rstrip(".")
    return s or "untitled"


def ensure_kb(name: str) -> str:
    try:
        r = http_post(f"{WEB}/api/kb/create",
                      {"name": name, "description": "benchmark-suite demo KB"},
                      timeout=90)
        return r["knowledgeBase"]["id"]
    except urllib.error.HTTPError as e:
        if e.code != 409:
            raise
    catalog = http_get(f"{WEB}/api/kb/catalog", timeout=120)
    for k in catalog.get("knowledgeBases") or []:
        if k.get("name") == name:
            return k.get("kbId") or k.get("id")
    raise RuntimeError(f"KB {name} not in catalog")


def batch_index(kb_id: str, paths: list[str], force: bool = False) -> None:
    try:
        r = http_post(f"{BACKEND}/api/v1/search/batch-index",
                      {"kb_id": kb_id, "doc_paths": paths, "force": force},
                      timeout=600)
        print(f"  batch-index {len(r.get('indexed', []))}/{len(paths)} ok")
    except Exception as e:  # noqa: BLE001
        print(f"  batch-index error: {str(e)[:100]}")


def wait_vector_ready(kb_id: str, timeout_s: int = 240) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = http_post(f"{BACKEND}/api/v1/search/vector",
                          {"query": "probe content", "kb_id": kb_id, "top_k": 1},
                          timeout=90)
            if r.get("results"):
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(6)
    return False


def parse_pdf_via_mcp(mc: McpClient, pdf_path: Path, kb_id: str) -> tuple[bool, int, str]:
    """PDF → MCP parse_doc(MinerU) → 轮询 → kb_doc_save_parsed 入库(官方推荐链路).

    parse_task_status 有意省略全文, 只回 markdown_length; 持久化走 save_parsed。
    返回 (success, markdown_length, doc_name)。
    """
    task = mc.call("parse_doc", {"file_path": str(pdf_path), "use_ocr": False},
                   timeout=180)
    task_id = str(task.get("task_id") or task.get("taskId") or "")
    if not task_id:
        md = str(task.get("markdown") or task.get("content") or "")
        return (len(md) > 500, len(md), "Wind Energy Basics")
    md_len, md_path = 0, ""
    for _ in range(60):  # 最多 10 分钟
        st = mc.call("parse_task_status", {"task_id": task_id}, timeout=120)
        status = str(st.get("status", "")).lower()
        if status in ("done", "success", "completed", "finished"):
            result = st.get("result") or {}
            md_len = int(result.get("markdown_length") or 0)
            md_path = str(result.get("markdown_path") or "")
            break
        if status in ("failed", "error"):
            return (False, 0, "Wind Energy Basics")
        time.sleep(10)
    if md_len <= 500:
        return (False, md_len, "Wind Energy Basics")
    doc_name = "Wind Energy Basics"
    r = mc.call("kb_doc_save_parsed",
                {"parent_id": kb_id, "task_id": task_id,
                 "markdown_path": md_path,
                 "source_filename": pdf_path.name,
                 "description": "parsed from wind-energy.pdf via MinerU"},
                timeout=180)
    doc_name = str((r.get("document") or {}).get("name") or doc_name)
    return (bool(r.get("success", True)), md_len, doc_name)


def main() -> int:
    # ── 建库 ──
    kb_ids = {lang: ensure_kb(name) for lang, name in KBS.items()}
    print("KBs:", kb_ids)

    # ── md 入库 ──
    plan = []  # (lang, kb_id, doc_name, content)
    for lang, kb_name in KBS.items():
        for src in sorted((DATA / lang).glob("*.md")):
            plan.append((lang, kb_ids[lang], sanitize(src.stem) + ".md",
                         src.read_text(encoding="utf-8")))
    created = exists = failed = 0
    for lang, kb_id, doc_name, content in plan:
        try:
            http_post(f"{WEB}/api/kb/documents/create",
                      {"kbId": kb_id, "name": doc_name, "content": content,
                       "description": "demo corpus"}, timeout=90)
            created += 1
        except urllib.error.HTTPError as e:
            if e.code == 409:
                exists += 1
            else:
                failed += 1
                print(f"  create failed {doc_name}: HTTP {e.code}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  create failed {doc_name}: {str(e)[:80]}")
    n_md = len(plan)
    print(f"md ingest: created={created} exists={exists} failed={failed} / {n_md}")

    # ── PDF 解析(MCP 真链路: parse_doc → kb_doc_create) ──
    pdf = DATA / "en" / "wind-energy.pdf"
    mc = McpClient()
    parse_ok, md_len, pdf_doc_name = False, 0, "Wind Energy Basics"
    try:
        parse_ok, md_len, pdf_doc_name = parse_pdf_via_mcp(mc, pdf, kb_ids["en"])
        print(f"pdf parse: ok={parse_ok} chars={md_len} doc={pdf_doc_name}")
    except Exception as e:  # noqa: BLE001
        print(f"  pdf parse failed: {str(e)[:120]}")
        parse_ok = False
    finally:
        mc.close()

    # ── 索引(force 重索引 → BM25 失效由后续首查重建) ──
    listed_by_kb: dict[str, list[str]] = {}
    for lang, kb_id in kb_ids.items():
        docs = http_get(f"{WEB}/api/kb/documents?kb_id={kb_id}", timeout=180)
        names = [str(d.get("name")) for d in (docs.get("documents") or [])]
        listed_by_kb[kb_id] = names
        for start in range(0, len(names), 40):
            batch_index(kb_id, names[start:start + 40], force=True)
        ok = wait_vector_ready(kb_id)
        print(f"  [{KBS[lang]}] {len(names)} files, vector ready={ok}")

    # ── 测量 ──
    ingest_success = (created + exists + (1 if parse_ok else 0)) / (n_md + 1)
    # 归并清单: 基名 → 原始文件名列表(供 part 求和回读)
    raw_by_base: dict[tuple[str, str], list[str]] = {}
    for kb_id, names in listed_by_kb.items():
        for n in names:
            b = n[:-3] if n.endswith(".md") else n
            raw_by_base.setdefault((kb_id, doc_basename(b)), []).append(n)

    membership, completeness, selfhit = [], [], []
    probes = []
    for lang, kb_id, doc_name, content in plan:
        base = doc_basename(doc_name)
        parts = raw_by_base.get((kb_id, base), [])
        membership.append(1 if parts else 0)
        content_len = 0
        for pn in parts:
            try:
                d = http_get(f"{WEB}/api/kb/document?kb_id={kb_id}"
                             f"&doc_path={urllib.parse.quote(pn)}"
                             f"&max_chars=999999", timeout=60)
                content_len += len(d.get("content") or "")
            except Exception:  # noqa: BLE001
                pass
        completeness.append(min(1.0, content_len / max(len(content), 1)))
        probes.append((kb_id, base, content))
    if parse_ok:
        probes.append((kb_ids["en"], pdf_doc_name, "Wind power is the generation of electricity from wind. The Betz limit 59.3 percent efficiency derived by Albert Betz in 1919 and global installed wind capacity reached about 1 terawatt in 2023."))

    for kb_id, base, content in probes:
        try:
            r = http_post(f"{BACKEND}/api/v1/search/vector",
                          {"query": content[:200], "kb_id": kb_id, "top_k": 3},
                          timeout=120)
            names = {doc_basename(x.get("doc_path", ""))
                     for x in (r.get("results") or [])}
            selfhit.append(1 if base in names else 0)
        except Exception:  # noqa: BLE001
            selfhit.append(0)
        time.sleep(0.2)

    summary = {
        "round": ROUND,
        "n_md_docs": n_md, "n_pdf_docs": 1,
        "parse_success": 1.0 if parse_ok else 0.0,
        "pdf_parse_chars": md_len,
        "ingest_success_rate": round(ingest_success, 4),
        "membership_accuracy": round(mean(membership) or 0, 4),
        "storage_completeness": round(mean(completeness) or 0, 4),
        "self_retrieval_hit1": round(mean(selfhit) or 0, 4),
        "env": env_fingerprint(),
        "generated": now_iso(),
    }
    out = RESULTS / f"module_a_ingestion_r{ROUND}.json"
    out.write_text(json.dumps({"summary": summary}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"-> {out}")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
