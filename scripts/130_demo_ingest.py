#!/usr/bin/env python3
"""demo-qa: 真实内容解析入库 (3 篇维基 md + 1 篇 arXiv PDF 走真实 parse 链)."""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

KB = "demo-qa-20260927"
DOCS = REPO / "review/demo-qa-20260927/docs"
PDF = REPO / "benchmark-suite/data/papers/artificial-intelligence__1706.03762__attention-is-all-you-need.pdf"

mc = McpClient()


def poll(task_id, timeout_s, interval=5):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = mc.call("kb_task_status", {"task_id": task_id}, timeout=60)
        st = str(r.get("status", "")).lower()
        if st in ("done", "completed", "success", "finished", "failed", "error"):
            return r
        time.sleep(interval)
    return {"status": "poll-timeout"}


def main():
    # 0) 幂等: 清掉旧的同名库
    try:
        cat = mc.call("kb_get_documents", {"kb_id": KB, "lightweight": True}, timeout=60)
        names = [d["name"] for d in (cat.get("catalog") or []) if d.get("name")]
        if names:
            mc.call("kb_doc_batch_delete", {"kb_id": KB, "doc_paths": names}, timeout=180)
        mc.call("kb_delete", {"kb_id": KB}, timeout=60)
        print(f"[cleanup] removed old {KB}")
    except Exception:
        pass

    r = mc.call("kb_create", {"name": KB,
                              "description": "Demo QA library: random real-world content (wiki x3 + arXiv PDF)"})
    assert r.get("success"), r
    print("[kb] created", KB)

    # 1) 3 篇 md 直存 (文本格式按契约免 parse) + A3c 描述 + A3b 标签
    metas = [
        ("great-wall.md", "万里长城: 长度(21,196.18 km/2012年国家文物局)、明代 8,850 km、 sticky rice 糯米砂浆、太空可见性误区、1987 入选世界遗产",
         ["great-wall", "history", "长城"]),
        ("voyager-1.md", "Voyager 1: 1977 发射的 NASA 探测器、2012 年穿越日球层进入星际空间、最远的人造物体、黄金唱片",
         ["voyager", "space", "航天"]),
        ("photosynthesis.md", "光合作用: 植物藻类蓝菌将光能转化为化学能、叶绿素吸光、光反应在类囊体膜、Calvin 循环固定 CO2 产糖并释放 O2",
         ["photosynthesis", "biology", "生物"]),
    ]
    for fname, desc, tags in metas:
        content = (DOCS / fname).read_text(encoding="utf-8")
        r = mc.call("kb_doc_save_parsed",
                    {"parent_id": KB, "markdown": content, "source_filename": fname,
                     "description": desc}, timeout=120)
        assert r.get("success"), (fname, r)
        saved_name = r["files"][0]["name"]
        rt = mc.call("kb_doc_update_tags", {"kb_id": KB, "doc_path": saved_name, "tags": tags}, timeout=60)
        print(f"[ingest] {saved_name} tags={rt.get('success')}")
        ri = mc.call("kb_index_document", {"kb_id": KB, "doc_path": saved_name, "content": content},
                     timeout=180)
        print(f"[index] {saved_name} →", str(ri.get("vector_index", {}).get("total_chunks", ri))[:60])

    # 2) PDF 走真实解析链: parse_doc → 轮询 → save_parsed → index
    print("[parse] submitting PDF to parse_doc (MinerU lane)…")
    p = mc.call("parse_doc", {"file_path": str(PDF), "use_ocr": False}, timeout=120)
    tid = p.get("task_id", "")
    print("[parse] task_id =", tid)
    if not tid:
        print("[parse] SKIP:", str(p)[:150])
        return
    fin = poll(tid, 900, interval=10)
    print("[parse] status =", fin.get("status"))
    res = fin.get("result") or {}
    md = res.get("markdown", "") or ""
    print("[parse] markdown_chars =", len(md))
    if str(fin.get("status", "")).lower() not in ("done", "completed", "success", "finished") or not md.strip():
        print("[parse] FAILED/EMPTY →", json.dumps(fin, ensure_ascii=False)[:300])
        return
    r = mc.call("kb_doc_save_parsed",
                {"parent_id": KB, "task_id": tid,
                 "description": "Attention Is All You Need (Vaswani et al., 2017): Transformer 架构, 自注意力 self-attention, 多头注意力, positional encoding, WMT14 翻译 SOTA",
                 }, timeout=180)
    print("[save-parsed]", json.dumps(r, ensure_ascii=False)[:200])
    if r.get("success"):
        saved = r["files"][0]
        mc.call("kb_doc_update_tags",
                {"kb_id": KB, "doc_path": saved["name"], "tags": ["transformer", "deep-learning", "论文"]},
                timeout=60)
        mc.call("kb_index_document", {"kb_id": KB, "doc_path": saved["name"]}, timeout=300)
        print("[ingest] PDF saved as", saved["name"])

    # 3) 终检
    cat = mc.call("kb_get_documents", {"kb_id": KB, "lightweight": True}, timeout=60)
    print("[final] catalog:", [d["name"] for d in cat.get("catalog", [])])
    st = mc.call("kb_search_stats", {}, timeout=60)
    cols = [c for c in (st.get("stats", {}).get("collections") or []) if "demo" in str(c)]
    print("[final] demo collections:", cols)
    mc.close()


if __name__ == "__main__":
    main()
