"""Generate a verified BibTeX file + reading guide for the downloaded KBS papers."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = HERE.parent / "reference" / "kbs"
UA = {"User-Agent": "Mozilla/5.0 (HMRS lit review)"}
verified = json.loads((HERE / "kbs_verified.json").read_text(encoding="utf-8"))
manifest = json.loads((HERE / "kbs_download_manifest.json").read_text(encoding="utf-8"))

KEYS = {
    "SoftwareRefArch_JournalisticKnowledgePlatforms_2023": "gallofr2023jkp",
}


def bibkey(title: str, year: int | None, authors: list) -> str:
    surname = "anon"
    if authors:
        surname = re.sub(r"[^a-z]", "", authors[0].split()[-1].lower())[:10] or "anon"
    word = ""
    for w in re.findall(r"[A-Za-z]{4,}", title or ""):
        if w.lower() not in ("with", "from", "using", "based", "for", "and", "the", "towards"):
            word = w.lower()[:9]
            break
    return f"{surname}{year or 0}{word}"


def esc(s: str) -> str:
    return (s or "").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def meta(doi: str) -> dict:
    if not doi:
        return {}
    u = "https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi, safe="/")
    try:
        d = json.loads(urllib.request.urlopen(
            urllib.request.Request(u, headers=UA), timeout=35).read())
        return {
            "authors": [a["author"]["display_name"] for a in (d.get("authorships") or [])],
            "biblio": d.get("biblio") or {},
            "journal": ((d.get("primary_location") or {}).get("source") or {}).get("display_name"),
        }
    except Exception:
        return {}


used: set[str] = set()
entries = []
guide = []
for x in verified:
    doi = x["doi"]
    m = meta(doi)
    authors = m.get("authors") or x.get("authors") or []
    b = m.get("biblio") or {}
    key = bibkey(x["title"] or x["file"], x["year"], authors)
    base = key
    i = 2
    while key in used:
        key = base + chr(96 + i)
        i += 1
    used.add(key)
    fields = [
        ("title", "{" + esc(x["title"] or "") + "}"),
        ("author", " and ".join(esc(a) for a in authors) if authors else ""),
        ("journal", "Knowledge-Based Systems"),
        ("year", str(x["year"] or "")),
    ]
    pages_val = None
    for k, src in (("volume", "volume"), ("number", "issue"), ("pages", "first_page")):
        v = b.get(src)
        if k == "pages" and b.get("first_page") and b.get("last_page"):
            fp, lp = str(b["first_page"]), str(b["last_page"])
            # Elsevier article numbers yield first_page == last_page; print once.
            v = pages_val = fp if fp == lp else f"{fp}--{lp}"
        if v:
            fields.append((k, str(v)))
    if doi:
        fields.append(("doi", doi))
    fields.append(("note", "OA PDF: paper-kbs/reference/kbs/" + x["file"]))
    body = ",\n".join(f"  {k:8s} = {{{v}}}" for k, v in fields if v)
    entries.append(f"@article{{{key},\n{body}\n}}")
    guide.append({**x, "bibkey": key, "authors_full": authors,
                  "volume": b.get("volume"), "pages": pages_val})
    time.sleep(0.2)

# CEUR companion is not a KBS article
ceur = next((g for g in guide if "COMPANION" in g["file"]), None)
if ceur:
    entries = [e for e in entries if ceur["bibkey"] not in e]
    entries.append(
        "@inproceedings{gallofr2021jkpdesign,\n"
        "  title     = {Developing a Software Reference Architecture for Journalistic Knowledge Platforms},\n"
        "  author    = {Gallofr\\'e Oca\\~na, Marc and Opdahl, Andreas L.},\n"
        "  booktitle = {Proceedings of the 6th Workshop on Semantic Access to Big Data and AI (SAML)},\n"
        "  series    = {CEUR Workshop Proceedings},\n"
        "  volume    = {2978},\n"
        "  year      = {2021},\n"
        "  note      = {Open-access design-science precursor; not a KBS article}\n"
        "}")

(REF / "kbs_refs.bib").write_text("\n\n".join(entries) + "\n", encoding="utf-8")
(HERE / "kbs_guide_data.json").write_text(
    json.dumps(guide, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"[bib] {len(entries)} entries -> {REF / 'kbs_refs.bib'}")
print(f"[guide data] {len(guide)} -> {HERE / 'kbs_guide_data.json'}")
