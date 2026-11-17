# -*- coding: utf-8 -*-
"""S0i — 终局预检（修正 kb_list 解析：lightweight 响应键为 catalog）。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = r"D:/codes/ClaudeGPT/rag_project/rag-knowledge"
EXP = Path(ROOT) / "review" / "experiment-redesign-20261101"


def mc(tool, args, t=120):
    r = subprocess.run(
        ["uv", "run", "--no-sync", "--directory", ROOT + "/backend", "python",
         ROOT + "/scripts/mcp_call.py", tool, json.dumps(args, ensure_ascii=False), "--raw"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
    raw = r.stdout
    i, j = raw.find("{"), raw.rfind("}")
    return json.loads(raw[i:j + 1]) if i >= 0 else {"_raw": raw[:150]}


def md_kbs():
    d = mc("kb_list", {"lightweight": True}, t=60)
    cat = d.get("catalog") or []
    return {k["name"].replace("MD语料-", ""): k["kb_id"] for k in cat
            if str(k.get("name", "")).startswith("MD语料")}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    kbm = md_kbs()
    print(f"[kbs] MD={len(kbm)}", flush=True)
    qs = [json.loads(l) for l in (EXP / "artifacts" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    flt = [q for q in qs if not q.get("needs_expansion")]
    qmap = {}
    for q in flt:
        if q.get("kind") == "gold" and q.get("domain") and q["domain"] not in qmap:
            qmap[q["domain"]] = q["question"]
    bad = []
    for short, kid in sorted(kbm.items()):
        r = mc("kb_search_vector", {"query": qmap.get(short, "test"), "kb_id": kid,
                                    "top_k": 5, "score_threshold": 0.05}, t=90)
        hits = len(r.get("results") or [])
        if not hits:
            bad.append(short)
        print(f"{'OK ' if hits else 'BAD'} {short:14s} q-hits={hits}", flush=True)
    print("SWEEP-BAD:", bad or "none", flush=True)
    return 0 if (len(kbm) == 10 and not bad) else 1


if __name__ == "__main__":
    sys.exit(main())
