import json
from pathlib import Path
p = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\experiments\results\exp10_ingest_state.json")
d = json.loads(p.read_text(encoding="utf-8"))
def walk(o, pre="", depth=0):
    if depth > 2: return
    if isinstance(o, dict):
        for k, v in list(o.items())[:25]:
            if isinstance(v, (dict, list)):
                print(f"{pre}{k}: {type(v).__name__} len={len(v)}")
                walk(v, pre + "  ", depth + 1)
            else:
                print(f"{pre}{k} = {v!r}")
    elif isinstance(o, list) and o:
        print(f"{pre}[0] {json.dumps(o[0])[:200]}")
walk(d)
