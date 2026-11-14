"""Second-pass retrieval for the KBS papers that were MISS in the first download run.

Only legal open-access mirrors are used: arXiv API, Semantic Scholar Graph API,
OpenAlex full-text search (preprint / repository locations). ScienceDirect and
bot-protected institutional repositories are NOT bypassed.

On success: save verified PDF, patch kbs_download_manifest.json, append to
kbs_verified.json so make_kbs_bib.py can regenerate the .bib and guide data.
"""
from __future__ import annotations

import difflib
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = HERE.parent / "reference" / "kbs"
UA = {"User-Agent": "Mozilla/5.0 (HMRS literature review; mailto:lit@example.org)"}
ATOM = "{http://www.w3.org/2005/Atom}"

manifest = json.loads((HERE / "kbs_download_manifest.json").read_text(encoding="utf-8"))
verified = json.loads((HERE / "kbs_verified.json").read_text(encoding="utf-8"))
Slug = {
    "A Software Reference Architecture for Journalistic Knowledge Platforms":
        "SoftwareRefArch_JournalisticKnowledgePlatforms_2023",
    "TreeQA: Enhanced LLM-RAG with logic tree reasoning for reliable and interpretable multi-hop question answering":
        "TreeQA_LLM_RAG_LogicTree_2025",
    "Addressing hallucinations in generative AI agents using observability and dual memory knowledge graphs":
        "Hallucinations_Observability_DualMemoryKG_2026",
    "Intermediate triple table: A general architecture for virtual knowledge graphs":
        "IntermediateTripleTable_VKG_Architecture_2025",
    "Optimising retrieval performance in RAG systems: A new growing window semantic chunking strategy to address weak semantic boundaries":
        "Optimising_RAG_GrowingWindowChunking_2025",
    "LLM-based harmonized data ingestion for dataspace: a novel system for automating data ingestion across heterogeneous data sources":
        "LLM_HarmonizedDataIngestion_Dataspace_2026",
    "DamageRAG: Benchmarking and diagnosing multi-hop retrieval-augmented reasoning for structural damage inspection":
        "DamageRAG_BenchmarkDiagnose_MultiHopRAG_2026",
    "QueCo: Query-conditioned consensus over unverified evidence for training-free zero-shot anomaly detection":
        "QueCo_Consensus_UnverifiedEvidence_2026",
    "Generating knowledge graphs from news articles via multi-agent claim extraction and attribution":
        "GeneratingKG_MultiAgent_ClaimAttribution_2026",
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def get(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def arxiv_urls(title: str) -> list[str]:
    words = [w for w in re.findall(r"[A-Za-z]{4,}", title)
             if w.lower() not in {"with", "from", "using", "based", "for", "and", "the",
                                  "towards", "into", "that", "this", "novel", "general"}]
    phrase = " ".join(words[:9])
    q = urllib.parse.urlencode({"search_query": f'all:"{phrase}"',
                                "start": 0, "max_results": 8})
    out = []
    try:
        root = ET.fromstring(get("https://export.arxiv.org/api/query?" + q, 30))
        for e in root.findall(ATOM + "entry"):
            t = (e.findtext(ATOM + "title") or "").replace("\n", " ").strip()
            if similar(t, title) < 0.72:
                continue
            aid = (e.findtext(ATOM + "id") or "").rsplit("/", 1)[-1]
            if aid:
                out.append("https://arxiv.org/pdf/" + aid)
    except Exception as ex:
        print(f"    [arxiv] {type(ex).__name__}: {ex}")
    return out


def s2_urls(doi: str, title: str) -> list[str]:
    out = []
    for u in (
        "https://api.semanticscholar.org/graph/v1/paper/DOI:" +
        urllib.parse.quote(doi, safe="") +
        "?fields=title,openAccessPdf,externalIds",
        "https://api.semanticscholar.org/graph/v1/paper/search?limit=3&fields=title,openAccessPdf,externalIds&query=" +
        urllib.parse.quote(title[:120]),
    ):
        try:
            d = json.loads(get(u))
        except Exception as ex:
            print(f"    [s2] {type(ex).__name__}: {ex}")
            continue
        for rec in ([d] if "data" not in d else d["data"]):
            if not isinstance(rec, dict):
                continue
            if similar(rec.get("title") or "", title) < 0.75:
                continue
            pdf = ((rec.get("openAccessPdf") or {}).get("url") or "")
            ext = rec.get("externalIds") or {}
            if ext.get("ArXiv"):
                out.append("https://arxiv.org/pdf/" + ext["ArXiv"])
            if pdf and "sciencedirect" not in pdf:
                out.append(pdf)
    return out


def oa_urls(title: str) -> list[str]:
    try:
        u = ("https://api.openalex.org/works?per-page=5&select=id,title,locations,best_oa_location&search="
             + urllib.parse.quote(title[:120]))
        d = json.loads(get(u, 30))
    except Exception as ex:
        print(f"    [openalex] {type(ex).__name__}: {ex}")
        return []
    out = []
    for w in d.get("results") or []:
        if similar(w.get("title") or "", title) < 0.80:
            continue
        locs = list(w.get("locations") or [])
        if w.get("best_oa_location"):
            locs.append(w["best_oa_location"])
        for l in locs:
            p = l.get("pdf_url") or ""
            if p and "sciencedirect" not in p and "linkinghub" not in p:
                out.append(p)
    return out


def download(url: str, dest: Path) -> tuple[bool, str]:
    if not url.startswith("http"):
        return False, "bad url"
    try:
        data = get(url, 60)
    except Exception as ex:
        return False, f"{type(ex).__name__}: {ex}"
    if not data.startswith(b"%PDF"):
        return False, f"not a PDF ({len(data)}B)"
    if len(data) < 30_000:
        return False, f"too small ({len(data)}B)"
    dest.write_bytes(data)
    return True, f"{len(data)}B"


misses = [m for m in manifest if not m.get("downloaded") and m.get("doi")]
print(f"[retry] {len(misses)} MISS entries to re-check\n")
new_files: list[dict] = []
for m in misses:
    title = m["title"]
    slug = Slug.get(title)
    if not slug:
        print(f"[skip] no slug for {title[:60]}")
        continue
    print(f"[try] {title[:78]}")
    urls: list[str] = []
    for fn, arg in ((arxiv_urls, title), (s2_urls, None), (oa_urls, title)):
        try:
            got = fn(arg) if fn is oa_urls else (
                s2_urls(m["doi"], title) if fn is s2_urls else arxiv_urls(title))
            urls += got
        except Exception as ex:
            print(f"    [{fn.__name__}] {ex}")
        time.sleep(0.4)
    seen, ordered = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    print(f"    candidates: {len(ordered)}")
    ok = False
    for u in ordered[:6]:
        dest = REF / f"{m['tier']}_{slug}.pdf"
        good, note = download(u, dest)
        print(f"    -> {'OK  ' if good else 'FAIL'} {u[:100]} {note[:70]}")
        if good:
            m.update(downloaded=True, file=dest.name, source_url=u,
                     candidates_tried=len(ordered), note="second-pass OA mirror")
            new_files.append({**m, "pages": None, "first": None})
            ok = True
            break
    if not ok:
        m["candidates_tried"] = len(ordered)
        m["note"] = (m.get("note") or "") + " | second-pass: no legal OA PDF found"
    print()

(HERE / "kbs_download_manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

if new_files:
    # pypdf lives only in backend/.venv; this script is run with that interpreter.
    from pypdf import PdfReader
    for x in new_files:
        f = REF / x["file"]
        r = PdfReader(str(f))
        x["pages"] = len(r.pages)
        x["first"] = (r.pages[0].extract_text() or "")[:180].replace("\n", " ")
    verified.extend(new_files)
    (HERE / "kbs_verified.json").write_text(
        json.dumps(verified, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"[done] newly saved: {len(new_files)}; total saved: "
      f"{sum(1 for m in manifest if m.get('downloaded'))}/{len(manifest)}")
