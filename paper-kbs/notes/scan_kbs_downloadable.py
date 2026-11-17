"""Scan ALL OA Knowledge-Based Systems works (2023+) with their locations,
and list those that (a) match HMRS topics / system-paper genre and (b) have a
downloadable non-ScienceDirect PDF (arXiv or institutional repository).
"""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (HMRS lit review)"}
HERE = Path(__file__).resolve().parent
rows = []
for page in range(1, 10):
    params = {
        "filter": "primary_location.source.issn:0950-7051,is_oa:true,from_publication_date:2023-01-01",
        "per-page": 200, "page": page,
        "select": "id,doi,title,publication_year,cited_by_count,locations,open_access",
    }
    u = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
    except Exception as e:
        print("page", page, "ERR", e)
        break
    if not d["results"]:
        break
    rows.extend(d["results"])
    print(f"page {page}: +{len(d['results'])} (total {len(rows)})")
    if len(d["results"]) < 200:
        break
    time.sleep(0.3)

TOPIC = ["retrieval", "rag", "knowledge base", "knowledge graph", "question answer",
         "agent", "framework", "platform", "architecture", "system", "verif",
         "evidence", "abstain", "hallucin", "large language", "llm", "document",
         "chunk", "provenance", "trust", "observab", "attribution", "judge",
         "rerank", "search", "grounding", "fact", "explainab", "decision support",
         "ingestion", "corpus", "dialogue", "open-source"]

out = []
for w in rows:
    t = (w.get("title") or "").lower()
    if not any(k in t for k in TOPIC):
        continue
    pdfs = []
    for loc in (w.get("locations") or []):
        pu = loc.get("pdf_url")
        if pu and "sciencedirect.com" not in pu and "linkinghub" not in pu:
            pdfs.append(pu)
        land = loc.get("landing_page_url") or ""
        m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})", land)
        if m:
            pdfs.append("https://arxiv.org/pdf/" + m.group(1))
    pdfs = list(dict.fromkeys(pdfs))
    if not pdfs:
        continue
    out.append({
        "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
        "title": w.get("title"), "year": w.get("publication_year"),
        "citations": w.get("cited_by_count"),
        "pdfs": pdfs[:4],
    })

out.sort(key=lambda x: (-(x["citations"] or 0), -(x["year"] or 0)))
p = HERE / "kbs_downloadable_scan.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n[done] {len(rows)} OA works scanned, {len(out)} topic-matched with downloadable PDF -> {p}")
for x in out[:60]:
    print(f"{x['year']} c={x['citations'] or 0:>4} | {x['title'][:96]}")
    print(f"      {x['pdfs'][0][:120]}")
