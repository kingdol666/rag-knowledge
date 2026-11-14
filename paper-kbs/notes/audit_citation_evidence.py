"""Build an auditable evidence table for citation--claim consistency checking.

Outputs:
  kbs_abstract_evidence.json : first-page/abstract text of every downloaded PDF
  citation_contexts.json     : every \\cite in the active manuscript with its
                               surrounding sentence(s) and the section it lives in
  bib_titles.json            : title/DOI of every defined bib entry

No judgments are made here; this only collects evidence so claims can be checked
against what the cited papers actually say.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "paper-kbs" / "reference" / "kbs"
J = ROOT / "paper-kbs" / "tex" / "journal_20p"
HERE = Path(__file__).resolve().parent

# ---------- 1. PDF first-page / abstract evidence ----------
from pypdf import PdfReader

pdf_evidence = []
for f in sorted(REF.glob("*.pdf")):
    try:
        r = PdfReader(str(f))
        text = ""
        for p in r.pages[:2]:
            text += (p.extract_text() or "") + "\n"
        text = re.sub(r"\s+", " ", text).strip()
        # Prefer the abstract window when present.
        m = re.search(r"(?i)\babstract\b", text)
        abstract = text[m.start():m.start() + 1100] if m else text[:1100]
        pdf_evidence.append({"file": f.name, "pages": len(r.pages),
                             "first_page": text[:700], "abstract_window": abstract})
    except Exception as e:
        pdf_evidence.append({"file": f.name, "error": f"{type(e).__name__}: {e}"})
(HERE / "kbs_abstract_evidence.json").write_text(
    json.dumps(pdf_evidence, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------- 2. Bib titles ----------
titles = {}
for bib in (J / "refs.bib", J / "refs_new_verified.bib"):
    s = bib.read_text(encoding="utf-8")
    for m in re.finditer(r"^@\w+\{([^,]+),(.*?)(?=^@|\Z)", s, re.M | re.S):
        key, body = m.group(1), m.group(2)
        t = re.search(r"\btitle\s*=\s*\{+([^}]*)", body, re.S)
        d = re.search(r"\bdoi\s*=\s*\{([^}]+)\}", body)
        y = re.search(r"\byear\s*=\s*\{([^}]+)\}", body)
        titles[key] = {"title": re.sub(r"\s+", " ", t.group(1)).strip() if t else "",
                       "doi": d.group(1) if d else "", "year": y.group(1) if y else "",
                       "source": bib.name}
(HERE / "bib_titles.json").write_text(
    json.dumps(titles, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------- 3. Citation contexts ----------
contexts = []
for tex in sorted(J.glob("n*.tex")):
    s = tex.read_text(encoding="utf-8")
    section = ""
    for m in re.finditer(r"\\cite[tp]?\{([^}]*)\}", s):
        # nearest preceding section/subsection heading
        head = s[:m.start()]
        hs = list(re.finditer(r"\\(?:sub)?section\*?\{([^}]*)\}", head))
        section = hs[-1].group(1) if hs else "(front matter)"
        start = max(0, m.start() - 420)
        end = min(len(s), m.end() + 220)
        contexts.append({
            "file": tex.name, "section": section,
            "keys": [k.strip() for k in m.group(1).split(",")],
            "before": re.sub(r"\s+", " ", s[start:m.start()]).strip(),
            "after": re.sub(r"\s+", " ", s[m.end():end]).strip(),
        })
(HERE / "citation_contexts.json").write_text(
    json.dumps(contexts, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"[evidence] PDFs: {len(pdf_evidence)} | bib titles: {len(titles)} | "
      f"citation sites: {len(contexts)}")
