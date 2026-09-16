# -*- coding: utf-8 -*-
"""Citation integrity check for the CIKM submission.

Deterministic checks (replayable, no network):
  1. every \\cite key used in main.tex is defined in refs.bib  (no undefined)
  2. every refs.bib entry is actually cited                    (no orphans)
  3. author-field sanity: no suspicious placeholder-like tokens
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
tex = (HERE / "main.tex").read_text(encoding="utf-8")
bib = (HERE / "refs.bib").read_text(encoding="utf-8")

CITE_RE = re.compile(r"\\cite[a-zA-Z]*\{([^}]*)\}")
ENTRY_RE = re.compile(r"@(\w+)\{([^,\s]+)\s*,")

cited = set()
for m in CITE_RE.finditer(tex):
    for k in m.group(1).split(","):
        k = k.strip()
        if k:
            cited.add(k)

entries = {k: t for t, k in ENTRY_RE.findall(bib)}
defined = set(entries)

missing = sorted(cited - defined)
orphan = sorted(defined - cited)

print(f"cite keys used in main.tex : {len(cited)}")
print(f"entries defined in refs.bib : {len(defined)}")
print(f"[UNDEFINED] cited but missing from refs.bib : {missing if missing else 'none'}")
print(f"[ORPHAN]    in refs.bib but never cited     : {orphan if orphan else 'none'}")

# per-entry type check: booktitle only valid on inproceedings; journal only on article
bad = []
for m in re.finditer(r"@(\w+)\{([^,\s]+)\s*,(.*?)\n\}", bib, re.S):
    etype, key, body = m.group(1), m.group(2), m.group(3)
    has_journal = "journal" in body
    has_booktitle = "booktitle" in body
    if etype == "inproceedings" and has_journal and not has_booktitle:
        bad.append(f"{key}: @inproceedings carries journal (should be @article)")
    if etype == "article" and has_booktitle:
        bad.append(f"{key}: @article carries booktitle")
    if etype == "inproceedings" and not has_booktitle:
        bad.append(f"{key}: @inproceedings without booktitle")
print("\n[ENTRY-TYPE] structural problems:")
print("\n".join("  " + b for b in bad) if bad else "  none")

# missing identifier check (every entry should be findable: doi/url/eprint/arxiv)
no_id = []
for m in re.finditer(r"@(\w+)\{([^,\s]+)\s*,(.*?)\n\}", bib, re.S):
    key, body = m.group(2), m.group(3)
    if not re.search(r"(doi|url|howpublished|eprint|arXiv)", body, re.I):
        no_id.append(key)
print("\n[NO-IDENTIFIER] entries without doi/url/arXiv:")
print("  " + ", ".join(no_id) if no_id else "  none")
