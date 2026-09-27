#!/usr/bin/env python3
"""聚焦探针: 复现 move 失败的真实报错 + 近重复的真实向量相似度."""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

KB_A = "s-probe-a-20260927"
KB_B = "s-probe-b-20260927"

DOC1 = """# Zephyr-7 Quantum Widget Specification

The Zephyr-7 quantum widget has a coolant capacity of 42 liters.

Operating frequency is 18.4 GHz under standard lab conditions.
"""
DOC3V = DOC1 + "\nVariant note: this copy adds one line for duplicate audit.\n"

mc = McpClient()


def docs(kb):
    r = mc.call("kb_get_documents", {"kb_id": kb, "lightweight": True}, timeout=60)
    return r.get("catalog") or []


try:
    for kb in (KB_A, KB_B):
        try:
            mc.call("kb_delete", {"kb_id": kb}, timeout=60)
        except Exception:
            pass
    mc.call("kb_create", {"name": KB_A}, timeout=60)
    mc.call("kb_create", {"name": KB_B}, timeout=60)
    mc.call("kb_doc_save_parsed", {"parent_id": KB_A, "markdown": DOC1,
                                   "source_filename": "doc1.md", "description": "d1"}, timeout=60)
    mc.call("kb_doc_create", {"kb_id": KB_A, "name": "doc3v.md", "content": DOC3V,
                              "description": "near dup"}, timeout=60)
    mc.call("kb_batch_index", {"kb_id": KB_A, "doc_paths": ["doc1.md", "doc3v.md"],
                               "force": True}, timeout=180)
    time.sleep(2)

    # 1) 真实跨文档相似度: 用 doc3v 内容查, 看 doc1 命中的 score
    r = mc.call("kb_search_vector", {"query": DOC3V, "kb_id": KB_A, "top_k": 5,
                                     "score_threshold": 0.0}, timeout=120)
    print("vector scores for doc3v query:")
    for h in r.get("results", []):
        print(f"  {h.get('doc_path','').split('/')[-1]:<16} score={h.get('score')}")

    # 2) find_duplicates 两个阈值
    for th in (0.90, 0.5):
        r = mc.call("kb_find_duplicates", {"kb_id": KB_A, "threshold": th}, timeout=300)
        print(f"dup threshold={th}: groups={r.get('total_duplicate_groups')} "
              f"exact={r.get('exact_duplicates')} near={r.get('near_duplicates')}")
        for g in (r.get("duplicate_groups") or [])[:2]:
            print("   ", g.get("type"), g.get("similarity"),
                  [d.get("name") for d in g.get("documents", [])])

    # 3) rename → 立即 move, 抓完整报错; 若失败, 2s 后重试对比
    rr = mc.call("kb_doc_update_meta", {"kb_id": KB_A, "doc_path": "doc3v.md",
                                        "name": "doc3v-renamed.md"}, timeout=60)
    print("rename:", json.dumps(rr, ensure_ascii=False)[:150])
    try:
        rm = mc.call("kb_doc_move", {"doc_path": f"{KB_A}/doc3v-renamed.md",
                                     "target_kb_id": KB_B}, timeout=120)
        print("immediate move:", json.dumps(rm, ensure_ascii=False)[:400])
    except Exception as e:
        print("immediate move EXC:", str(e)[:400])
    time.sleep(2)
    try:
        rm2 = mc.call("kb_doc_move", {"doc_path": f"{KB_A}/doc3v-renamed.md",
                                      "target_kb_id": KB_B}, timeout=120)
        print("retry move(+2s):", json.dumps(rm2, ensure_ascii=False)[:300])
    except Exception as e:
        print("retry move EXC:", str(e)[:400])
    print("A docs:", [d["name"] for d in docs(KB_A)])
    print("B docs:", [d["name"] for d in docs(KB_B)])
finally:
    for kb in (KB_A, KB_B):
        try:
            names = [d["name"] for d in docs(kb) if d.get("name")]
            if names:
                mc.call("kb_doc_batch_delete", {"kb_id": kb, "doc_paths": names}, timeout=120)
            mc.call("kb_delete", {"kb_id": kb}, timeout=60)
        except Exception as e:
            print("cleanup", kb, type(e).__name__)
    mc.close()
    print("probe done")
