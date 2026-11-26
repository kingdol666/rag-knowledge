"""Effective artwork font-size audit: min Tf size x (placed width / PDF width).

KBS/Elsevier artwork guidance: text >= ~7 pt at final printed size.
Uses pypdf (backend/.venv). Widths: elsarticle final 5p textwidth=522pt,
columnwidth=252pt (measured with a probe document).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"D:\codes\ClaudeGPT\rag_project\rag-knowledge\backend\.venv\Lib\site-packages")
from pypdf import PdfReader
from pypdf.generic import ContentStream

HERE = Path(__file__).resolve().parents[1]
TEXTWIDTH_PT = 522.0
COLUMNWIDTH_PT = 252.0

TEX = ["main_20p.tex", "n1_intro.tex", "n2_related.tex", "n3_overview.tex",
       "n4_acquisition.tex", "n5_organization.tex", "n6_retrieval.tex",
       "n7_implementation.tex", "n8a_eval.tex", "n8b_eval.tex",
       "n8c_eval.tex", "n8d_eval.tex", "n9_discussion.tex",
       "n10_threats.tex", "n11_conclusion.tex", "n_back.tex",
       "supplementary.tex", "supplementary-arm-tables.tex",
       "supplementary-baseline-quality.tex", "supplementary-external-baselines.tex"]

uses = {}
for f in TEX:
    t = (HERE / f).read_text(encoding="utf-8")
    for m in re.finditer(r"\\includegraphics\[width=\\(textwidth|columnwidth)\]\{([^}]+)\}", t):
        uses.setdefault(m.group(2), m.group(1))

bad = []
for name, widthkind in sorted(uses.items()):
    pdf = HERE / "figs" / (name + ".pdf")
    if not pdf.exists():
        print("MISSING", name)
        bad.append(name)
        continue
    r = PdfReader(str(pdf))
    page = r.pages[0]
    box = page.mediabox
    pdf_w_pt = float(box.width)
    target = TEXTWIDTH_PT if widthkind == "textwidth" else COLUMNWIDTH_PT
    scale = target / pdf_w_pt
    cs = ContentStream(page.get_contents(), r)
    sizes = [float(operands[1]) for operands, operator in cs.operations
             if operator == b"Tf" and operands]
    if not sizes:
        print(f"{name}: no text ops (paths only?) scale={scale:.3f}")
        continue
    eff = min(sizes) * scale
    flag = "OK " if eff >= 7.0 else "LOW"
    if eff < 7.0:
        bad.append(name)
    print(f"{flag} {name}: min_declared={min(sizes):.2f}pt scale={scale:.3f} effective={eff:.2f}pt")
print("BAD:", bad)