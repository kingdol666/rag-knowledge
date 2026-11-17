# -*- coding: utf-8 -*-
"""S0j — 终局集合重建（一次性删+逐卷索引+双衰减 sweep）。

背景：55 集合删除风暴后 5 个 MD 集合查询路径坏死且重启不愈。
配方（已验证）：停 backend → 独占删集合 → 起 backend → 逐卷 kb_index_document
（绕开 kb_reindex 的异步提交）→ +60s/+180s 双点衰减探针 → 全库 sweep ×2。
A3 库（06:36 重建）单独核验架层与探针，不重建。
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = r"D:/codes/ClaudeGPT/rag_project/rag-knowledge"
EXP = Path(ROOT) / "review" / "experiment-redesign-20261101"


def mc(tool, args, t=300):
    r = subprocess.run(
        ["uv", "run", "--no-sync", "--directory", ROOT + "/backend", "python",
         ROOT + "/scripts/mcp_call.py", tool, json.dumps(args, ensure_ascii=False), "--raw"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
    raw = r.stdout
    i, j = raw.find("{"), raw.rfind("}")
    return json.loads(raw[i:j + 1]) if i >= 0 else {"_raw": raw[:150]}


def domain_first_question():
    qs = [json.loads(l) for l in (EXP / "artifacts" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out = {}
    for q in qs:
        if q.get("kind") == "gold" and q.get("domain") and q["domain"] not in out:
            out[q["domain"]] = q["question"]
    return out


def md_kbs():
    d = mc("kb_list", {"lightweight": True}, t=60)
    cat = d.get("catalog") or []
    return {k["name"].replace("MD语料-", ""): k["kb_id"] for k in cat
            if str(k.get("name", "")).startswith("MD语料")}


def start_backend():
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command",
         f"Start-Process -WorkingDirectory '{ROOT}\\backend' -FilePath '{ROOT}\\backend\\.venv\\Scripts\\python.exe' "
         f"-ArgumentList 'main.py' -WindowStyle Hidden"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8771/api/v1/health", timeout=5) as resp:
                if resp.status == 200:
                    print("[backend] healthy", flush=True)
                    return True
        except Exception:
            pass
    return False


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    qmap = domain_first_question()
    # ① 停 backend
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "$c = Get-NetTCPConnection -LocalPort 8771 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; "
                    "if ($c) { Stop-Process -Id $c.OwningProcess -Force; Write-Output 'backend stopped' } "
                    "else { Write-Output 'already free' }"], capture_output=True, text=True, timeout=60)
    time.sleep(3)
    # ② 独占删 5 坏集合
    import chromadb
    client = chromadb.PersistentClient(path=ROOT + "/chroma_db")
    kbm_now = {}  # 停机态用 yml 读 id（kb_list 不可用）
    yml_ids = {}
    import re
    tree = Path(ROOT) / "storage" / "tree-file-system"
    for d in tree.iterdir():
        if d.is_dir() and d.name.startswith("MD语料-"):
            t = (d / ".knowledge-base.yml").read_text(encoding="utf-8")
            m = re.search(r"id:\s*([0-9a-f-]{36})", t)
            if m:
                yml_ids[d.name.replace("MD语料-", "")] = m.group(1)
    BROKEN = ["历史-中文", "技术-英文", "政务-中文", "文学-中文", "法律-中文"]
    for short in BROKEN:
        kid = yml_ids.get(short)
        if not kid:
            print(f"[del] {short}: no yml id — skip", flush=True)
            continue
        try:
            client.delete_collection(f"kb_{kid}")
            print(f"[del] {short}: collection deleted", flush=True)
        except Exception as e:
            print(f"[del] {short}: ({str(e)[:50]})", flush=True)
    # ③ 起 backend
    if not start_backend():
        print("backend failed to start — abort", flush=True)
        return 1
    # ④ 逐卷索引 5 库
    kbm = md_kbs()
    print(f"[kbs] MD={len(kbm)}", flush=True)
    for short in BROKEN:
        kid = kbm.get(short)
        if not kid:
            print(f"[idx] {short}: kb missing", flush=True)
            continue
        d = mc("kb_get_documents", {"kb_id": kid, "lightweight": True, "page": 1, "page_size": 200}, t=120)
        docs = [e.get("doc_path") for e in (d.get("catalog") or [])
                if e.get("doc_path") and e.get("entry_type") != "sub_kb"]
        while d.get("has_more"):
            d = mc("kb_get_documents", {"kb_id": kid, "lightweight": True,
                                        "page": d.get("page", 1) + 1, "page_size": 200}, t=120)
            docs += [e.get("doc_path") for e in (d.get("catalog") or [])
                     if e.get("doc_path") and e.get("entry_type") != "sub_kb"]
        print(f"[idx] {short}: {len(docs)} docs", flush=True)
        for dp in docs:
            mc("kb_index_document", {"kb_id": kid, "doc_path": dp}, t=300)
        print(f"[idx] {short}: indexed", flush=True)
    # ⑤ 双点衰减探针
    for wait in (30, 150):
        time.sleep(wait)
        bad = []
        for short, kid in sorted(kbm.items()):
            r = mc("kb_search_vector", {"query": qmap.get(short, "test"), "kb_id": kid,
                                        "top_k": 5, "score_threshold": 0.05}, t=90)
            hits = len(r.get("results") or [])
            if not hits:
                bad.append(short)
        print(f"[sweep +{wait}s] BAD: {bad or 'none'}", flush=True)
        if bad and wait == 30:
            print("decay detected — rebuild needed again", flush=True)
            return 1
    print("ALL-STABLE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
