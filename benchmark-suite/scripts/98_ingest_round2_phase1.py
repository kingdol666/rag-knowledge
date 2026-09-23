#!/usr/bin/env python3
"""Ingest R2 Phase 1 (A2+A2-Q+A2.5+A1) — round-2 50 篇 PDF 走官方解析链路.

逐篇: parse_doc(MinerU, MCP) → 轮询(校验 result.success) → A2-Q 质量门禁
(前 1500 字符逐症状检查, 命中即停该篇并记录) → A2.5 拆分门禁
(skills/knowledgebase-ingest/scripts/split_large_doc.py, 读 config.yml
ingestion.large_doc.max_chars=30000, 写 part 文件删原件) → A1/A3 调研摘要
(标题 H1 + 头 3000 / 中 ±1500 / 尾 2000 三窗口) 落盘 results/r2_survey.json
供 Archival(执行 Agent) 内容驱动分类(A3d)与 A3b/A3c 判断件。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402

PAPERS = SUITE / "data" / "papers"
SPLIT_SCRIPT = Path.home() / ".zcode" / "skills" / "knowledgebase-ingest" \
    / "scripts" / "split_large_doc.py"
PARSE_TIMEOUT = 900


def poll_parse(mc, task_id: str) -> dict:
    deadline = time.time() + PARSE_TIMEOUT
    while time.time() < deadline:
        r = mc.call("parse_task_status", {"task_id": task_id}, timeout=120)
        st = str((r or {}).get("status") or "").lower()
        if st in ("done", "success", "succeeded", "completed", "finished"):
            result = (r or {}).get("result") or {}
            if isinstance(result, dict) and result.get("success") is False:
                raise RuntimeError(f"parse failed (done but success=false): "
                                   f"{str(result.get('error'))[:260]}")
            return r
        if st == "error":
            raise RuntimeError(f"parse failed: {str(r)[:300]}")
        time.sleep(6)
    raise RuntimeError(f"parse timeout {PARSE_TIMEOUT}s")


def a2q_gate(markdown: str) -> str:
    """返回空串=通过; 否则返回拒绝原因(A2-Q 五症状)。"""
    head = markdown[:1500]
    if len(markdown.strip()) < 100:
        return "body<100 chars (parse failure)"
    if markdown.count("\x00") > 10 or len(
            re.findall(r"[A-Za-z0-9+/=]{200,}", markdown)) > 3:
        return "binary/base64 residue"
    printable = sum(1 for c in head if c.isascii() and c.isprintable()) + sum(
        1 for c in head if "\u4e00" <= c <= "\u9fff")
    if len(head) > 200 and printable / len(head) < 0.5:
        return f"OCR garbage (printable {printable}/{len(head)})"
    if len(re.findall(r"^#{1,3} ", markdown, re.M)) > 30 and \
            len(markdown.strip()) < 200:
        return "headings without body"
    if "\n\n\n\n\n\n\n" in markdown:
        return "excess whitespace"
    return ""


def three_windows(text: str) -> dict:
    n = len(text)
    mid = max(0, n // 2 - 1500)
    return {"head": text[:3000],
            "middle": text[mid:mid + 3000] if n > 6000 else "",
            "tail": text[-2000:] if n > 5000 else ""}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 篇(0=全部)")
    args = ap.parse_args()

    manifest = json.loads((PAPERS / "manifest.json").read_text(encoding="utf-8"))
    papers = [p for p in manifest["papers"] if p.get("round", 1) == 2]
    if args.limit:
        papers = papers[:args.limit]
    if not papers:
        print("[A0] no round-2 papers in manifest — run 97 first")
        return 1
    print(f"[A0] {len(papers)} round-2 papers", flush=True)

    mc = McpClient()
    survey_path = SUITE / "results" / "r2_survey.json"
    survey = json.loads(survey_path.read_text(encoding="utf-8")) \
        if survey_path.exists() else {"papers": []}
    done_ids = {p["arxiv_id"] for p in survey["papers"]}
    if done_ids:
        print(f"[resume] {len(done_ids)} already surveyed", flush=True)

    for p in papers:
        aid = p["arxiv_id"].split("v")[0]
        if aid in done_ids:
            continue
        pdf = PAPERS / p["pdf"]
        slug = pdf.stem
        t1 = time.perf_counter()
        try:
            task = mc.call("parse_doc", {"file_path": str(pdf)}, timeout=300)
            task_id = (task or {}).get("task_id") or ""
            if not task_id:
                raise RuntimeError(f"parse_doc no task_id: {str(task)[:200]}")
            pr = poll_parse(mc, task_id)
            result = (pr or {}).get("result") or {}
            markdown = str(result.get("markdown") or (pr or {}).get("markdown") or "")
            # markdown_path 嵌在 result 里; 大文档 markdown_omitted=true 不走内联
            markdown_path = str(result.get("markdown_path")
                                or (pr or {}).get("markdown_path") or "")
            if not markdown and markdown_path and \
                    Path(markdown_path).exists():
                markdown = Path(markdown_path).read_text(encoding="utf-8",
                                                         errors="replace")
            image_count = int(result.get("image_count")
                              or (pr or {}).get("image_count") or 0)

            reason = a2q_gate(markdown)
            if reason:
                survey["papers"].append({
                    "arxiv_id": aid, "field": p["field"], "title": p["title"],
                    "slug": slug, "rejected": reason})
                print(f"[A2-Q REJECT] {slug[:50]}: {reason}", flush=True)
                survey_path.write_text(json.dumps(survey, ensure_ascii=False,
                                                  indent=1), encoding="utf-8")
                continue

            # A2.5 拆分门禁(脚本读 config.yml, 写 parts 删原件)
            split = {"split": False}
            if markdown_path and Path(markdown_path).exists():
                r = subprocess.run(
                    [sys.executable, str(SPLIT_SCRIPT), markdown_path],
                    capture_output=True, text=True, encoding="utf-8",
                    timeout=300, cwd=str(SUITE.parent))
                line = next((l for l in (r.stdout or "").splitlines()
                             if l.strip().startswith("{")), "")
                if line:
                    split = json.loads(line)
                if not split.get("success", False):
                    raise RuntimeError(f"split gate failed: {r.stdout[-200:]} "
                                       f"{r.stderr[-200:]}")

            if split.get("split"):
                parts = [Path(x["file"]) for x in split.get("parts", [])]
                full = "\n\n".join(pp.read_text(encoding="utf-8")
                                   for pp in parts)
            else:
                full = markdown
                if markdown_path:
                    Path(markdown_path).write_text(full, encoding="utf-8")
                parts = []
            windows = three_windows(full)
            survey["papers"].append({
                "arxiv_id": aid, "field": p["field"], "title": p["title"],
                "slug": slug, "chars": len(full),
                "split": bool(split.get("split")),
                "part_count": split.get("part_count", 1),
                "parts": [str(pp.name) for pp in parts],
                "part_dir": str(parts[0].parent) if parts else "",
                "single_path": markdown_path if not parts else "",
                "image_count": image_count,
                "parse_seconds": round(time.perf_counter() - t1, 1),
                "windows": windows})
            survey_path.write_text(json.dumps(survey, ensure_ascii=False,
                                              indent=1), encoding="utf-8")
            print(f"[parsed] {len(survey['papers'])} done | {slug[:52]} "
                  f"{len(full)} ch, parts={split.get('part_count', 1)} "
                  f"img={image_count} "
                  f"{round(time.perf_counter() - t1, 1)}s", flush=True)
        except Exception as ex:  # noqa: BLE001 — 单篇失败记录后继续
            survey["papers"].append({
                "arxiv_id": aid, "field": p["field"], "title": p["title"],
                "slug": slug, "error": str(ex)[:300]})
            survey_path.write_text(json.dumps(survey, ensure_ascii=False,
                                              indent=1), encoding="utf-8")
            print(f"[ERROR] {slug[:50]}: {str(ex)[:200]}", flush=True)

    ok = [x for x in survey["papers"] if not x.get("error")
          and not x.get("rejected")]
    bad = [x for x in survey["papers"] if x.get("error") or x.get("rejected")]
    print(f"[done] survey ok={len(ok)} rejected/error={len(bad)} "
          f"→ {survey_path}", flush=True)
    mc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
