# -*- coding: utf-8 -*-
"""US-3 — Crime and Punishment 全本入库（27 卷，MD语料-文学-英文）。
A3c 描述=逐卷实际章节标记范围归纳；逐卷 kb_index_document（禁 reindex）；
图谱一次；双通道自检；kb_list docCount 核验。"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge")
SRC = ROOT / "review/experiment-redesign-20261101/artifacts/us3-ingest"
KBNAME = "MD语料-文学-英文"
KB = None  # 运行时按名解析（禁止硬编码 uuid——曾因硬编码错 id 把 27 卷写进自然科学库）
TAGS = ["crime-and-punishment", "dostoyevsky", "russian-literature",
        "psychological-novel", "gutenberg-full-text"]


def mc(tool, args, t=300):
    r = subprocess.run(
        ["uv", "run", "--no-sync", "--directory", str(ROOT / "backend"), "python",
         str(ROOT / "scripts/mcp_call.py"), tool, json.dumps(args, ensure_ascii=False), "--raw"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
    raw = r.stdout
    i, j = raw.find("{"), raw.rfind("}")
    return json.loads(raw[i:j + 1]) if i >= 0 else {"_raw": raw[:150]}


def part_desc(i, total, text):
    marks = re.findall(r"(PART\s+[IVX]+|CHAPTER\s+[IVX]+)", text)
    head = f"{marks[0]}–{marks[-1]}" if marks else "连续正文（无章节标记）"
    return (f"【Part {i}/{total} · {head}】Crime and Punishment（《罪与罚》Dostoyevsky，Gutenberg 英译全本）："
            f"拉斯柯尔尼科夫犯罪与救赎主线的连续章节文本。可答：本卷覆盖的情节（放贷老妇一案、"
            f"波尔菲里审讯、索尼娅、忏悔与自首等）的定位与原文引文。不含：其他卷内容。")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    global KB
    d = mc("kb_list", {"lightweight": True}, t=60)
    match = [k for k in (d.get("catalog") or []) if k.get("name") == KBNAME]
    if not match:
        print(f"KB '{KBNAME}' not found — abort", flush=True)
        return 1
    KB = match[0].get("kb_id") or match[0].get("kbId")
    print(f"KB resolved by name: {KBNAME} -> {KB[:13]} (docs={match[0].get('documentCount') or match[0].get('doc_count')})", flush=True)
    files = sorted(SRC.glob("crime_punishment (part * of 27).md"),
                   key=lambda p: int(re.search(r"part (\d+) of", p.name).group(1)))
    total = len(files)
    print(f"parts: {total}", flush=True)
    paths = []
    for k, f in enumerate(files, 1):
        i = int(re.search(r"part (\d+) of", f.name).group(1))
        content = f.read_text(encoding="utf-8")
        name = f"Crime and Punishment (part {i} of {total}).md"
        payload = {"kb_id": KB, "name": name, "content": content,
                   "description": part_desc(i, total, content)}
        pf = Path(r"C:/Users/87287/AppData/Local/Temp/us3_p.json")
        pf.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(
            ["uv", "run", "--no-sync", "--directory", str(ROOT / "backend"), "python",
             str(ROOT / "scripts/mcp_call.py"), "kb_doc_create", f"@{pf}", "--raw"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        raw = r.stdout
        a, b = raw.find("{"), raw.rfind("}")
        d = json.loads(raw[a:b + 1]) if a >= 0 else {"_raw": raw[:120]}
        ok = bool(d.get("success"))
        print(f"create p{i}: ok={ok}", flush=True)
        paths.append((i, f"{KBNAME}/{name}"))
        time.sleep(0.5)
    for i, p in paths:
        r = mc("kb_doc_update_tags", {"kb_id": KB, "doc_path": p, "tags": TAGS}, t=120)
        print(f"tags p{i}: {r.get('success')}", flush=True)
    for i, p in paths:
        r = mc("kb_index_document", {"kb_id": KB, "doc_path": p}, t=600)
        vi = r.get("vector_index") or {}
        print(f"index p{i}: chunks={vi.get('total_chunks')}", flush=True)
    r = mc("kb_graph_build", {"kb_id": KB, "force": True}, t=120)
    tid = r.get("task_id")
    print("graph task:", str(tid)[:16], flush=True)
    if tid:
        for _ in range(60):
            time.sleep(10)
            ts = mc("kb_task_status", {"task_id": tid}, t=60)
            if str(ts.get("status", "")).lower() in ("done", "completed", "success", "finished"):
                print("graph done", flush=True)
                break
    # 双通道自检（针对新入库卷的内容问题）
    for label, tool, q in (
            ("kw", "Raskolnikov pawnbroker axe murder confession", "kb_search"),
            ("vec", "Why does Raskolnikov confess his crime?", "kb_search_vector")):
        if tool == "kb_search":
            d = mc(tool, {"query": q, "top_k": 6}, t=120)
            hits = d.get("hits") or []
            ranks = [(n, str(h.get('docName'))[:50]) for n, h in enumerate(hits, 1)
                     if "Crime and Punishment" in str(h.get('docName') or '')]
        else:
            d = mc(tool, {"query": q, "kb_ids": [KB], "top_k": 6, "threshold": 0.3}, t=120)
            hits = d.get("results") or []
            ranks = [(n, str(h.get('doc_path'))[:50]) for n, h in enumerate(hits, 1)
                     if "Crime and Punishment" in str(h.get('doc_path') or '')]
        print(f"A3c-R {label}: cot_rank={ranks[:4]}", flush=True)
    d = mc("kb_list", {"lightweight": True}, t=60)
    for k in (d.get("catalog") or []):
        if k.get("name") == KBNAME:
            print(f"kb_list {KBNAME}: documentCount={k.get('documentCount') or k.get('doc_count')}", flush=True)
    (ROOT / "review/experiment-redesign-20261101/artifacts/us3-ingest/ingest_result.json").write_text(
        json.dumps({"docs": [{"part": i, "path": p} for i, p in paths]}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print("US-3 ingest complete", flush=True)


if __name__ == "__main__":
    main()
