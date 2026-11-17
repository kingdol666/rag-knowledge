# -*- coding: utf-8 -*-
"""S9b2 — A3 无描述孪生库清场（R3 复现轮）：删除全部 A3无描述-* 库，输出清理清单。

 Chroma 孤儿集合风险由后续 s0k 式审计兜底（若 A3 臂复跑前发现旧 kb_id 段残留再清剿）。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:/codes/ClaudeGPT/rag_project/rag-knowledge/scripts")
import subprocess

ROOT = r"D:/codes/ClaudeGPT/rag_project/rag-knowledge"


def mc(tool, args, t=120):
    r = subprocess.run(
        ["uv", "run", "--no-sync", "--directory", ROOT + "/backend", "python",
         ROOT + "/scripts/mcp_call.py", tool, json.dumps(args, ensure_ascii=False), "--raw"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
    raw = r.stdout
    i, j = raw.find("{"), raw.rfind("}")
    return json.loads(raw[i:j + 1]) if i >= 0 else {"_raw": raw[:150]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    d = mc("kb_list", {"lightweight": True}, t=60)
    cat = d.get("catalog") or []
    twins = [(k.get("name"), k.get("kb_id")) for k in cat
             if str(k.get("name", "")).startswith("A3无描述")]
    print(f"found {len(twins)} A3 twins")
    out = []
    for name, kid in twins:
        r = mc("kb_delete", {"kb_id": kid}, t=120)
        ok = r.get("success") is True or "deleted" in json.dumps(r).lower()
        out.append({"name": name, "kb_id": kid, "deleted": bool(ok),
                    "resp": str(r)[:120]})
        print(f"  {name} ({str(kid)[:8]}): {'OK' if ok else 'FAIL ' + str(r)[:80]}")
    log = Path(__file__).parent.parent / "artifacts" / "replication_bench_20261112" / "a3_twin_purge.json"
    log.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"log: {log}")
    return 0 if all(o["deleted"] for o in out) else 1


if __name__ == "__main__":
    sys.exit(main())
