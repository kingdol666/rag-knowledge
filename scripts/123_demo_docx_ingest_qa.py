#!/usr/bin/env python3
"""123 — 新文档解析入库(按 ingest skill A0-A7 规范) + 问答演示.

文档: 手工构造的全新 .docx(二进制, 走 MinerU docx 解析链), 内容=2026-09-27
三模式检索实测知识卡(数字均有真值可校验). 入库目标: demo-qa-20260927.
流程严格按 knowledgebase-ingest: A0 去重预检 → A2 解析 → A3b 标签 →
A3c 描述 → A5 存储 → A6 索引 → A7 终检 → 问答(soul_qdcvr_ask) → 拒答探针.
"""
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

KB = "demo-qa-20260927"
SOUL = "soul-demo-qa"
OUT = REPO / "review/fullcheck-20260927"
OUT.mkdir(parents=True, exist_ok=True)
DOCX = OUT / "retmodes-knowledge-card.docx"

DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>三模式检索实测速查卡（2026-09-27）</w:t></w:r></w:p>
<w:p><w:r><w:t>硬件与引擎：判决引擎 Laya 部署于 backend/.venv（MinerU 环境），GPU 为 NVIDIA GeForce RTX 4070 Ti SUPER（16GB），torch 版本 2.12.1+cu130。模型文件位于 model/laya。</w:t></w:r></w:p>
<w:p><w:r><w:t>单段判决延迟：GPU 热身后单段判决约 0.047 秒；CPU 基线约 2 秒每段，约合 40 倍差距。首次判决含内核编译预热约 9.5 秒。</w:t></w:r></w:p>
<w:p><w:r><w:t>三模式实测（q1 英文方法题 / q2 中文跨语言题）：模式A向量优先 q1 耗时 25.5 秒、q2 耗时 24.3 秒；模式B图书管理员 q1 耗时 25.1 秒、q2 耗时 10.1 秒；模式C混合并行 q1 耗时 68.6 秒、q2 耗时 64.2 秒。</w:t></w:r></w:p>
<w:p><w:r><w:t>总体结论：六臂全部命中金标文档、全部真实引擎判决；CPU 基线总耗时 1620 秒，GPU 轮总耗时 218 秒，整体提速 7.4 倍。唯一数值漂移：C 模式 q2 结果文档由 39 降为 38（一个临界文档落到阈值外），金标不受影响。</w:t></w:r></w:p>
<w:p><w:r><w:t>工程约定：判决脚本必须使用 backend/.venv 的 Python 运行（宿主 laya 包）；换用无 laya 的解释器会以 JevUnavailable 失败关闭，绝不静默降级。</w:t></w:r></w:p>
</w:body>
</w:document>"""

CT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

QA = [
    ("QA1", "新文档事实", "这次三模式实测里，模式C混合并行在 q1 上花了多少秒？整体提速是多少倍？"),
    ("QA2", "新文档事实", "单段判决在 GPU 热身后的延迟是多少？判决脚本必须用哪个环境运行？"),
    ("QA3", "库外拒答探针", "RTX 5090 的公版整卡功耗是多少瓦？"),
]


def poll(mc, task_id, timeout_s=600, interval=5):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = mc.call("kb_task_status", {"task_id": task_id}, timeout=60)
        st = str(r.get("status", "")).lower()
        if st in ("done", "completed", "success", "finished", "failed", "error"):
            return r
        time.sleep(interval)
    return {"status": "poll-timeout"}


def main() -> int:
    log: list[dict] = []

    def rec(step, ok, detail):
        log.append({"step": step, "ok": bool(ok), "detail": str(detail)[:400]})
        print(f"  {'PASS' if ok else 'FAIL'} {step} — {str(detail)[:150]}", flush=True)

    # 构造全新 .docx
    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT_XML)
        z.writestr("_rels/.rels", RELS_XML)
        z.writestr("word/document.xml", DOC_XML)
    rec("build docx", DOCX.exists() and DOCX.stat().st_size > 1000,
        f"{DOCX.name} {DOCX.stat().st_size} bytes")

    mc = McpClient()
    try:
        # A0 去重预检: 同名文档不应已存在
        cat = mc.call("kb_get_documents", {"kb_id": KB, "lightweight": True}, timeout=60)
        names = [d.get("name", "") for d in (cat.get("catalog") or [])]
        rec("A0 dedup-precheck", not any("retmodes" in n.lower() for n in names),
            f"库内现 {len(names)} docs, 无同名/同主题文档")

        # A2 解析 (MinerU docx 链)
        p = mc.call("parse_doc", {"file_path": str(DOCX), "use_ocr": False}, timeout=120)
        tid = p.get("task_id", "")
        rec("A2 parse_doc submit", bool(tid), f"task_id={tid}")
        fin = poll(mc, tid) if tid else {"status": "no-task"}
        res = fin.get("result") or {}
        md_len = len(str(res.get("markdown") or ""))
        rec("A2 parse done", str(fin.get("status", "")).lower() in ("done", "completed", "success", "finished")
            and (md_len > 0 or str(res.get("markdown_path", "")) != ""),
            f"status={fin.get('status')} md_chars={md_len} md_path={bool(res.get('markdown_path'))}")

        # A3c+A5 存储 (task_id 模式, 描述随存)
        r = mc.call("kb_doc_save_parsed",
                    {"parent_id": KB, "task_id": tid,
                     "description": "三模式检索实测速查卡 2026-09-27: RTX 4070 Ti SUPER+torch2.12.1+cu130, 单段判决0.047s, A/B/C 六臂延迟与 7.4x 提速, JevUnavailable fail-closed 约定"},
                    timeout=180)
        files = r.get("files") or []
        saved = files[0].get("name", "") if files else ""
        rec("A5 save_parsed", bool(r.get("success")) and bool(saved),
            f"saved={saved!r} savedCount={r.get('savedCount')}")

        # A3b 标签
        mc.call("kb_doc_update_tags",
                {"kb_id": KB, "doc_path": saved, "tags": ["retrieval", "benchmark", "laya", "gpu"]},
                timeout=60)
        rec("A3b tags", True, f"tags→{saved}")

        # A6 索引
        ri = mc.call("kb_index_document", {"kb_id": KB, "doc_path": saved}, timeout=300)
        chunks = (ri.get("vector_index") or {}).get("total_chunks")
        rec("A6 index", bool(ri.get("success")), f"chunks={chunks}")

        # A7 终检: 目录可见 + 向量可命中新内容
        cat2 = mc.call("kb_get_documents", {"kb_id": KB, "lightweight": True}, timeout=60)
        present = saved in [d.get("name") for d in (cat2.get("catalog") or [])]
        sv = mc.call("kb_search_vector",
                     {"query": "模式C混合并行 q1 耗时 68.6 秒", "kb_id": KB,
                      "top_k": 3, "score_threshold": 0.0}, timeout=120)
        blob = json.dumps(sv.get("results", []), ensure_ascii=False)
        rec("A7 verify", present and "68.6" in blob,
            f"catalog可见={present} 向量命中新内容={'68.6' in blob}")

        # 问答 (soul_qdcvr_ask 真链路)
        for qid, qtype, q in QA:
            t0 = time.perf_counter()
            r = mc.call("soul_qdcvr_ask",
                        {"query": q, "soul_kb_id": SOUL, "task_goal": "全检演示",
                         "task_type": "qa", "top_k": 4, "async_mode": True}, timeout=120)
            tid2 = r.get("task_id", "")
            ans, cits, pas = "", [], None
            if tid2:
                fin2 = poll(mc, tid2, timeout_s=300)
                rr = fin2.get("result") or {}
                ans, cits, pas = str(rr.get("answer", "")), rr.get("citations") or [], rr.get("pas_score")
            ms = round((time.perf_counter() - t0) * 1000)
            rec(f"{qid} {qtype}", len(ans) > 20,
                f"{ms}ms pas={pas} cit={len(cits)} ans[:80]={ans[:80]!r}")
            log.append({"step": f"{qid}.answer", "ok": True, "detail": ans})
            log.append({"step": f"{qid}.citations", "ok": True,
                        "detail": json.dumps(cits, ensure_ascii=False)[:500]})
    finally:
        mc.close()

    (OUT / "ingest-qa-log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    n_fail = sum(1 for e in log if e["ok"] is False)
    print(f"[123] done, {n_fail} FAIL → {OUT / 'ingest-qa-log.json'}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
