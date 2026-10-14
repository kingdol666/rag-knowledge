import json, pathlib
r = pathlib.Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\experiments\results")
d = json.loads((r / "exp8b_absent_agent.json").read_text(encoding="utf-8"))
print("type:", type(d), "n:", len(d))
for x in d:
    if isinstance(x, dict):
        print({k: (v if not isinstance(v, (list, dict)) else f"<{type(v).__name__} len={len(v)}>") for k, v in x.items()})
