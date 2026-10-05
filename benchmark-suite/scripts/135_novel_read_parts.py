#!/usr/bin/env python3
"""Read every Novel-PridePrejudice doc via kb_doc_read; extract chapter headings + head/tail."""
import json
import re
import sys

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient

KB = "b4c48237-6937-440a-9696-cc1e66bed5c1"
OUT = "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/_novel_parts_content.json"

# chapter marker forms seen: "Chapter I.]" and "CHAPTER II."
CH = re.compile(r"(?:CHAPTER|Chapter)\s+([IVXL]+)\s*\.?\s*\]?", )


def roman_to_int(s):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = prev = 0
    for ch in reversed(s):
        v = vals[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total


c = McpClient()
out = []
try:
    docs = c.call("kb_get_documents", {"kb_id": KB, "lightweight": True}, timeout=120)["catalog"]
    for d in docs:
        dp = d["doc_path"]
        r = c.call("kb_doc_read", {"kb_id": KB, "doc_path": dp, "max_chars": 40000}, timeout=180)
        txt = ""
        for k in ("content", "text", "markdown", "body"):
            if isinstance(r.get(k), str) and r[k]:
                txt = r[k]
                break
        if not txt:
            txt = json.dumps(r, ensure_ascii=False)[:200]
        total_chars = r.get("total_chars") or r.get("chars") or len(txt)
        heads = [(roman_to_int(m.group(1)), m.group(1)) for m in CH.finditer(txt)]
        rec = {
            "doc_path": dp,
            "old_description": d.get("description", ""),
            "read_chars": len(txt),
            "total_chars": total_chars,
            "chapters": [h[1] for h in heads],
            "chapter_nums": [h[0] for h in heads],
            "head": txt[:900],
            "tail": txt[-700:],
        }
        out.append(rec)
        nums = sorted({h[0] for h in heads})
        rng = f"{min(nums)}-{max(nums)}" if nums else "NONE"
        print(f"{dp.split(chr(92))[-1]:<55} read={len(txt):>6} tot={total_chars} n={len(heads):>2} range={rng}")
finally:
    c.close()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("saved", OUT)
