"""KBS initial-submission compliance audit (programmatic checks).

Run from paper-kbs/tex/journal_20p:
    python _kbs_compliance_check.py
"""
from __future__ import annotations

import glob
import pathlib
import re

files = [pathlib.Path(p) for p in glob.glob("n*.tex")] + [
    pathlib.Path("main_20p.tex"),
    pathlib.Path("highlights.tex"),
]
src = {p.name: p.read_text(encoding="utf-8") for p in files}
allt = "\n".join(src.values())

main = src["main_20p.tex"]
print("--- KBS checklist (programmatic) ---")

m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", main, re.S)
words = len(re.sub(r"\\[a-zA-Z]+|\{|\}", " ", m.group(1)).split())
print(f"abstract words (<=250): {words}")

hl_block = re.search(r"\\begin\{highlights\}(.*?)\\end\{highlights\}",
                     src["highlights.tex"], re.S).group(1)
hl = [x.strip() for x in re.findall(r"\\item\s+(.*)", hl_block)]
print(f"highlights: {len(hl)} items, max chars {max(len(h) for h in hl)}"
      " (3-5 items, <=85 chars)")

kw = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}", main, re.S).group(1)
print(f"keywords: {len([k for k in kw.split(r'\sep') if k.strip()])}")

decls = {
    "CRediT": "CRediT authorship contribution statement" in allt,
    "competing interest": "Declaration of competing interest" in allt,
    "funding": r"\section*{Funding}" in allt,
    "ethics": "Ethics statement" in allt,
    "data availability": "Data availability" in allt,
    "acknowledgments": "Acknowledgments" in allt,
    "GenAI declaration": ("Declaration of generative AI and AI-assisted "
                          "technologies") in allt,
}
print("declarations present:", decls)

print("journal name:", bool(re.search(r"\\journal\{Knowledge-Based Systems\}", main)))
print("bibliography style:", re.search(r"\\bibliographystyle\{([^}]+)\}", main).group(1),
      "| bib files:", re.search(r"\\bibliography\{([^}]+)\}", main).group(1))

ph = {k: allt.count(k) for k in [
    "Author Name", "Co-author Name", "author@example.com",
    "Affiliation Department", "Author 1", "Author 2", "AUTHOR ACTION",
]}
print("placeholders still present (user choice):", ph)
print("figures referenced:", len(re.findall(
    r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", allt)))

# GenAI declaration text as rendered
g = re.search(r"manuscript preparation process\}\s*(.*?)\n\n", allt, re.S)
if g:
    print("GenAI declaration text:", " ".join(g.group(1).split())[:260])
