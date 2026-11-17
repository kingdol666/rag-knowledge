# -*- coding: utf-8 -*-
"""S0c — 重测前平台预检：①判卷修复活性 ②10 库向量探针 ③题集×库存完整性。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge")
EXP = ROOT / "review" / "experiment-redesign-20261101"
TREE = ROOT / "storage" / "tree-file-system"

PROBES = {
    "MD语料-法律-中文": "个人信息保护法 敏感个人信息 同意",
    "MD语料-政务-中文": "政府工作报告 国内生产总值",
    "MD语料-文学-中文": "红楼梦 贾宝玉 大观园",
    "MD语料-文学-英文": "Pride and Prejudice Elizabeth Darcy",
    "MD语料-科学-英文": "quantum entanglement photon",
    "MD语料-医学-英文": "sepsis biomarkers procalcitonin",
    "MD语料-技术-英文": "kubernetes node components",
    "MD语料-历史-中文": "史记 项羽 本纪",
    "MD语料-哲学-英文": "Nietzsche Zarathustra",
    "MD语料-经济-英文": "wealth of nations division of labour",
}


def mc(tool, args, timeout=120):
    r = subprocess.run(
        ["uv", "run", "--no-sync", "--directory", str(ROOT / "backend"), "python",
         str(ROOT / "scripts" / "mcp_call.py"), tool, json.dumps(args), "--raw"],
        capture_output=True, text=True, timeout=timeout)
    raw = r.stdout
    i, j = raw.find("{"), raw.rfind("}")
    return json.loads(raw[i:j + 1]) if i >= 0 else {"_raw": raw[:150]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    kbs = {k["name"]: k["kbId"] for k in (mc("kb_list", {})["knowledgeBases"]) if k.get("name") and k.get("kbId")}

    print("== ① judge 修复活性（bad_request 分类）")
    r = mc("kb_laya_judge", {"query": "probe", "criterion": "auto",
                             "documents": '[{"kb_id":"x","doc_path":"bad\\path"}]'})
    ek = (r.get("errors") or [{}])[0].get("error_kind")
    print(f"   status={r.get('status')} error_kind={ek} ->",
          "PASS" if r.get("status") == "bad_request" and ek == "bad_request" else "FAIL")

    print("== ② 10 库向量探针")
    chroma_bad = []
    for name, q in PROBES.items():
        kid = kbs.get(name)
        if not kid:
            print(f"   [FAIL] {name}: KB 不在列表")
            chroma_bad.append(name)
            continue
        r = mc("kb_search_vector", {"query": q, "kb_ids": [kid], "top_k": 3, "threshold": 0.2},
               timeout=180)
        hits = r.get("results") or r.get("hits") or []
        err = str(r.get("error", ""))[:60]
        ok = len(hits) > 0 and "Nothing found" not in err
        if not ok:
            chroma_bad.append(name)
        print(f"   [{'PASS' if ok else 'FAIL'}] {name}: hits={len(hits)} {err}")
    print("   chroma 异常库:", chroma_bad or "无")

    print("== ③ 题集×库存完整性（经 s2 入库报告 file→入库名映射 + 磁盘核验）")
    rep = json.loads((EXP / "artifacts" / "s2_ingest_report_v2.json").read_text(encoding="utf-8"))
    file2kbname = {}
    for kb_name, entry in rep["kbs"].items():
        for d in entry.get("docs", []):
            if isinstance(d, dict) and d.get("file") and d.get("name"):
                file2kbname[d["file"]] = (kb_name, d["name"])
    kb_files = {}
    for f in TREE.iterdir():
        if f.is_dir() and f.name.startswith("MD语料"):
            kb_files[f.name] = {p.name for p in f.glob("*.md")}
    import re
    stem = re.compile(r" \(part \d+ of \d+\)")
    def resolve(kb_name, iname):
        names = kb_files.get(kb_name, set())
        if iname in names:
            return True
        base = stem.sub("", iname)
        return any(n.startswith(base) for n in names)
    rows = [json.loads(l) for l in (EXP / "artifacts" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    gold_rows = [q for q in rows if q.get("kind") == "gold"]
    missing, ok_n, stem_ok = [], 0, 0
    for q in gold_rows:
        gd = str(q.get("gold_doc", ""))
        hit = file2kbname.get(gd)
        resolved = False
        if hit:
            kb_name, iname = hit
            resolved = resolve(kb_name, iname)
        if not resolved:
            # 回退：gold_doc 词干前缀匹配任一 MD 库文件（PDF/XML 解析链入库更名）
            base = Path(gd).stem
            for kb_name, names in kb_files.items():
                if any(n == base + ".md" or stem.sub("", n).startswith(base) for n in names):
                    resolved = True
                    stem_ok += 1
                    break
        if resolved:
            ok_n += 1
        else:
            missing.append((q["id"], q.get("domain"), gd))
    print(f"   gold 题金标文档可解析且在库: {ok_n} / {len(gold_rows)}（其中词干回退 {stem_ok}）")
    for m in missing[:15]:
        print("   [MISSING]", m)
    if len(missing) > 15:
        print(f"   ...共 {len(missing)} 条缺失")
    return 0


if __name__ == "__main__":
    sys.exit(main())
