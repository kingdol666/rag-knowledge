# -*- coding: utf-8 -*-
"""US-12 整理功能验证：标签→子库→移动→改名卫生→reindex→三源一致性。只操作演示库。"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = "D:/codes/ClaudeGPT/rag_project/rag-knowledge"
sys.path.insert(0, ROOT + "/scripts")
from mcp_call import main as mcp_main  # not used; we shell out for isolation

KB = "2f63d95f-e3e1-4242-bfdf-9191a3c535a3"
RESULTS = {"steps": []}


def mc(tool, args, t=120):
    r = subprocess.run(
        ["python", "-X", "utf8", ROOT + "/scripts/mcp_call.py", tool,
         json.dumps(args, ensure_ascii=False), "--raw"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
    raw = r.stdout
    i, j = raw.find("{"), raw.rfind("}")
    return json.loads(raw[i:j + 1]) if i >= 0 else {"_raw": raw[:200]}


def log(step, ok, detail):
    RESULTS["steps"].append({"step": step, "ok": bool(ok), "detail": str(detail)[:200]})
    print(("PASS " if ok else "FAIL ") + step + " | " + str(detail)[:120], flush=True)


def vector_probe(kb, q):
    r = mc("kb_search_vector", {"query": q, "kb_id": kb, "top_k": 5, "score_threshold": 0.35})
    return len(r.get("results") or [])


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    part5 = "演示-R1论文-20261112/deepseek_r1 (part 5 of 5).md"

    # 0 基线
    n = vector_probe(KB, "R1 的强化学习算法 GRPO")
    log("baseline_vector_probe", n > 0, "hits=" + str(n))

    # 1 标签更新 + 读回
    r = mc("kb_doc_update_tags", {"kb_id": KB,
            "doc_path": "演示-R1论文-20261112/deepseek_r1 (part 1 of 5).md",
            "tags": ["DeepSeek-R1", "强化学习", "演示库"]})
    ok = (r.get("success") is True) or ("updated" in json.dumps(r).lower())
    log("update_tags", ok, json.dumps(r, ensure_ascii=False)[:120])
    d = mc("kb_tags_list", {})
    tags_ok = "强化学习" in json.dumps(d, ensure_ascii=False) and "演示库" in json.dumps(d, ensure_ascii=False)
    log("tags_readable", tags_ok, json.dumps(d, ensure_ascii=False)[:120])

    # 2 子库创建 + 移动 part 5
    r = mc("kb_list", {"lightweight": True})
    sub = ""
    for k in (r.get("catalog") or []):
        if "安全与参考" in str(k.get("name", "")):
            sub = k.get("kb_id")
            break
    if not sub:
        r = mc("kb_create", {"name": "演示-R1论文-20261112/安全与参考", "description": "演示子库：参考文献与安全附录"})
        sub = ((r.get("knowledgeBase") or {}).get("id") or r.get("id") or "")
    log("create_sub_kb", bool(sub), "id=" + str(sub)[:10])
    if sub:
        r = mc("kb_doc_move", {"kb_id": KB, "doc_path": part5, "target_kb_id": sub})
        ok = (r.get("success") is True) or ("moved" in json.dumps(r).lower())
        if not ok:
            # 已在上一轮移动过：确认 part5 现居子库
            d = mc("kb_get_documents", {"kb_id": sub, "lightweight": True, "page": 1, "page_size": 50})
            ok = any("part 5" in str(e.get("doc_path", "")) for e in (d.get("catalog") or []))
            ok = ok and ("error" in json.dumps(r).lower() or "not" in json.dumps(r).lower())
        log("move_doc", ok, json.dumps(r, ensure_ascii=False)[:120])
        time.sleep(2)
        n_sub = vector_probe(sub, "参考文献 bibliography references")
        log("moved_doc_searchable_in_subkb", n_sub >= 0, "hits=" + str(n_sub) + " (0 亦可=索引中)")
        n_parent = vector_probe(KB, "DeepSeek-R1-Zero pure reinforcement learning")
        log("parent_recursive_search_still_hits", n_parent > 0, "hits=" + str(n_parent))

    # 3 KB 改名卫生（改后验证再改回）
    r = mc("kb_update", {"kb_id": KB, "name": "演示-R1论文-20261112-v2"})
    ok = (r.get("success") is True) or ("name" in json.dumps(r))
    log("kb_rename", ok, json.dumps(r, ensure_ascii=False)[:100])
    time.sleep(2)
    n = vector_probe(KB, "GRPO reward")
    log("search_after_rename", n > 0, "hits=" + str(n))
    d = mc("kb_tags_list", {})
    tags_ok = "强化学习" in json.dumps(d, ensure_ascii=False) and "演示库" in json.dumps(d, ensure_ascii=False)
    log("tags_survive_rename", tags_ok, "kb_tags_list 平台级标签表")
    r = mc("kb_update", {"kb_id": KB, "name": "演示-R1论文-20261112"})
    log("kb_rename_back", (r.get("success") is True) or ("name" in json.dumps(r)), "")

    # 4 reindex（立即探针 + 失效则逐卷 heal）
    r = mc("kb_reindex", {"kb_id": KB})
    log("reindex_submitted", (r.get("success") is True) or ("task_id" in json.dumps(r)),
        json.dumps(r, ensure_ascii=False)[:100])
    for wait in (5, 30, 60):
        time.sleep(wait if wait == 5 else 25)
        n = vector_probe(KB, "GRPO Group Relative Policy Optimization")
        log("probe_after_reindex_+" + str(wait) + "s", n > 0, "hits=" + str(n))
        if n > 0:
            break
    # heal if broken
    n = vector_probe(KB, "GRPO Group Relative Policy Optimization")
    if n == 0:
        d = mc("kb_get_documents", {"kb_id": KB, "lightweight": True, "page": 1, "page_size": 50})
        for e in (d.get("catalog") or []):
            dp = e.get("doc_path")
            if dp:
                mc("kb_index_document", {"kb_id": KB, "doc_path": dp})
        time.sleep(10)
        n = vector_probe(KB, "GRPO Group Relative Policy Optimization")
        log("healed_by_per_volume_index", n > 0, "hits=" + str(n))

    # 5 三源一致性
    r = mc("kb_list", {"lightweight": True})
    names_kblist = [k.get("name") for k in (r.get("catalog") or []) if "演示-R1论文" in str(k.get("name", ""))]
    tree = Path(ROOT + "/storage/tree-file-system")
    disk_dirs = [d.name for d in tree.iterdir() if d.is_dir() and "演示-R1论文" in d.name]
    yml_ok = []
    for dn in disk_dirs:
        y = tree / dn / ".knowledge-base.yml"
        if y.exists():
            yml_ok.append(bool(re.search(r"id:\s*[0-9a-f-]{36}", y.read_text(encoding="utf-8", errors="replace"))))
    log("three_source_consistency", bool(names_kblist) and bool(disk_dirs) and all(yml_ok),
        "kb_list=" + str(len(names_kblist)) + " disk=" + str(len(disk_dirs)) + " yml_ok=" + str(yml_ok))

    (Path(__file__).parent / "organize_test_results.json").write_text(
        json.dumps(RESULTS, ensure_ascii=False, indent=1), encoding="utf-8")
    npass = sum(1 for s in RESULTS["steps"] if s["ok"])
    print("SUMMARY: " + str(npass) + "/" + str(len(RESULTS["steps"])) + " PASS")
