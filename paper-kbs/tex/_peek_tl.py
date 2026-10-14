import json
from pathlib import Path
p = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\experiments\results\exp10_papers_toollayer.json")
d = json.loads(p.read_text(encoding="utf-8"))
print(json.dumps(d, ensure_ascii=False)[:2600])
