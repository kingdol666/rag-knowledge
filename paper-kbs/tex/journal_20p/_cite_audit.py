"""Citation/bibliography consistency audit: every \\cite key resolves, and
every bibliography entry is used. Run from paper-kbs/tex/journal_20p.
"""
from __future__ import annotations

import glob
import pathlib
import re

texs = [pathlib.Path(p) for p in glob.glob("n*.tex")] + [pathlib.Path("main_20p.tex")]
text = "\n".join(p.read_text(encoding="utf-8") for p in texs)

cited: set[str] = set()
for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", text):
    cited.update(k.strip() for k in m.group(1).split(",") if k.strip())

defined: dict[str, str] = {}
for bib in ("refs.bib", "refs_new_verified.bib"):
    s = pathlib.Path(bib).read_text(encoding="utf-8")
    for m in re.finditer(r"@\w+\{([^,]+),", s):
        key = m.group(1).strip()
        if key in defined:
            print(f"DUPLICATE key {key} in {bib} (also {defined[key]})")
        defined[key] = bib

missing = sorted(cited - set(defined))
unused = sorted(set(defined) - cited)
print(f"cited keys: {len(cited)}  |  defined entries: {len(defined)}")
print(f"cited but undefined: {missing if missing else 'none'}")
print(f"defined but never cited: {unused if unused else 'none'}")
