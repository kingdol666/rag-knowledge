# -*- coding: utf-8 -*-
"""S0j2 — scoped chroma 干净周期重建（s0j 的参数化变体，R3 复现轮新增）。

用法: uv run --no-sync --directory backend python s0j2_rebuild_scoped.py --libs 文学-中文
      uv run --no-sync --directory backend python s0j2_rebuild_scoped.py --libs 文学-中文,法律-中文

配方（s0j 已验证）：停 backend（杀全树，防 reload master 复活 worker）→ 独占直连
delete_collection → 起 backend → 逐卷 kb_index_document（禁 kb_reindex）→
+30s/+150s 双点衰减探针（题面级）→ 全 10 库 sweep。
"""
import argparse
import json
import re
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


def yml_ids(shorts):
    """停机态从每库 .knowledge-base.yml 读 id（kb_list 不可用）。"""
    out = {}
    tree = Path(ROOT) / "storage" / "tree-file-system"
    for d in tree.iterdir():
        if d.is_dir() and d.name.startswith("MD语料-"):
            short = d.name.replace("MD语料-", "")
            if short in shorts:
                t = (d / ".knowledge-base.yml").read_text(encoding="utf-8")
                m = re.search(r"id:\s*([0-9a-f-]{36})", t)
                if m:
                    out[short] = m.group(1)
    return out


def kill_backend_tree():
    """杀 8771 属主及其父链（reload master 会复活 worker，必须杀树）。"""
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "$c = Get-NetTCPConnection -LocalPort 8771 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; "
                    "if ($c) { $own = $c.OwningProcess; "
                    "$proc = Get-CimInstance Win32_Process -Filter \"ProcessId=$own\" -ErrorAction SilentlyContinue; "
                    "if ($proc) { $pp = $proc.ParentProcessId; "
                    "Stop-Process -Id $own -Force -ErrorAction SilentlyContinue; "
                    "Stop-Process -Id $pp -Force -ErrorAction SilentlyContinue } "
                    "Write-Output ('stopped ' + $own) } "
                    "else { Write-Output 'already free' }"],
                   capture_output=True, text=True, timeout=60)


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--libs", required=True, help="逗号分隔，如 文学-中文")
    args = ap.parse_args()
    libs = [s.strip() for s in args.libs.split(",") if s.strip()]
    qmap = domain_first_question()

    # ① 停 backend（杀树）
    kill_backend_tree()
    time.sleep(3)

    # ② 独占删集合
    import chromadb
    client = chromadb.PersistentClient(path=ROOT + "/chroma_db")
    ids = yml_ids(set(libs))
    for short in libs:
        kid = ids.get(short)
        if not kid:
            print(f"[del] {short}: no yml id — skip", flush=True)
            continue
        try:
            client.delete_collection(f"kb_{kid}")
            print(f"[del] {short}: collection deleted", flush=True)
        except Exception as e:
            print(f"[del] {short}: ({str(e)[:60]})", flush=True)

    # ③ 起 backend
    if not start_backend():
        print("backend failed to start — abort", flush=True)
        return 1

    # ④ 逐卷索引
    kbm = md_kbs_all()
    for short in libs:
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
            r = mc("kb_index_document", {"kb_id": kid, "doc_path": dp}, t=300)
            ok = (r.get("success") is True) or r.get("indexed") or r.get("chunks", 0)
            print(f"   {str(dp)[:44]} -> {str(r.get('status', r.get('success', '?')))[:20]} chunks={r.get('chunks', '?')}", flush=True)
        print(f"[idx] {short}: indexed", flush=True)

    # ⑤ 双点衰减探针（题面级）
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


def md_kbs_all():
    d = mc("kb_list", {"lightweight": True}, t=60)
    cat = d.get("catalog") or []
    return {k["name"].replace("MD语料-", ""): k["kb_id"] for k in cat
            if str(k.get("name", "")).startswith("MD语料")}


if __name__ == "__main__":
    sys.exit(main())
