# -*- coding: utf-8 -*-
"""Per-section size report for main.tex — where is the page budget spent?"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
tex = (HERE / "main.tex").read_text(encoding="utf-8")

# strip preamble up to \begin{document}
body_start = tex.find(r"\begin{document}")
preamble = tex[:body_start]
body = tex[body_start:]

SEC = re.compile(r"\\section\*?\{([^}]*)\}")
marks = [(m.start(), m.group(1)) for m in SEC.finditer(body)]
marks.append((len(body), "END"))

print(f"{'section':<52} {'chars':>7}  {'share':>6}")
print("-" * 70)
total = len(body)
for i in range(len(marks) - 1):
    start, name = marks[i]
    end = marks[i + 1][0]
    size = end - start
    print(f"{name[:50]:<52} {size:>7}  {100*size/total:5.1f}%")
print("-" * 70)
print(f"{'BODY TOTAL (incl. floats/bib)':<52} {total:>7}")
print(f"{'PREAMBLE':<52} {len(preamble):>7}")
