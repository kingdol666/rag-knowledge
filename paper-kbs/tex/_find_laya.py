import re
from pathlib import Path
root = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
hits = []
for p in root.rglob("*.py"):
    if any(x in p.parts for x in (".venv", "node_modules", "__pycache__", ".git")):
        continue
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if "laya" in t.lower() and ("threshold" in t.lower() or "rubric" in t.lower()):
        hits.append(p)
for p in hits[:40]:
    print(p.relative_to(root))
print("total", len(hits))
