import json, pathlib
r = pathlib.Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\experiments\results")
p8 = json.loads((r / "exp8_graded_probes.json").read_text(encoding="utf-8"))
print("exp8 top keys:", list(p8.keys()))
for layer in ("tool_layer", "agent_layer"):
    rows = p8.get(layer)
    print(f"== {layer}: n={len(rows) if rows else 0}")
    if rows:
        for x in rows:
            keys = [k for k in x.keys()]
            print("   keys:", keys)
            print("   row:", {k: x[k] for k in keys if k not in ("answer", "text", "citations", "packed", "evidence")})
            break
p3 = json.loads((r / "exp3_abstention.json").read_text(encoding="utf-8"))
print("exp3 top keys:", list(p3.keys()))
pr = p3.get("probes") or []
print("exp3 probes n:", len(pr))
for x in pr:
    print("   ", {k: v for k, v in x.items() if not isinstance(v, (list, dict))})
