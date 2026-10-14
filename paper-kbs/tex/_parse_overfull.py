from pathlib import Path
log = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\paper-kbs\tex\journal\build3.log")
lines = log.read_text(encoding="utf-16", errors="replace").splitlines()
cur = "?"
for i, ln in enumerate(lines):
    if "(" in ln:
        import re
        m = re.findall(r"\((?:\./)?([A-Za-z0-9_\-]+\.(tex|sty|cls))", ln)
        if m:
            cur = m[-1][0]
    if ln.startswith("Overfull \\hbox"):
        print("=" * 68)
        print(f"[{cur}] {ln}")
        for c in lines[i+1:i+5]:
            if c.strip():
                print("   ", c[:150])
