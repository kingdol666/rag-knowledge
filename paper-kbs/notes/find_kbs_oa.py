"""Query OpenAlex for OA papers in Knowledge-Based Systems (ISSN 0950-7051)
that match the HMRS manuscript's topic, and collect verifiable OA PDF links.
"""
import json, time, urllib.parse, urllib.request
from pathlib import Path

BASE = "https://api.openalex.org/works"
ISSN = "0950-7051"
QUERIES = [
    "retrieval-augmented generation",
    "large language model knowledge base",
    "retrieval verification evidence",
    "agentic question answering system",
    "knowledge management platform framework",
    "LLM judge relevance verification",
    "document retrieval reranking knowledge",
    "abstention selective question answering",
    "multi-agent knowledge system",
    "enterprise knowledge base construction",
]

def get(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "HMRS-lit-review/1.0 (mailto:research@example.com)"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))

seen = {}
for q in QUERIES:
    params = {
        "filter": f"primary_location.source.issn:{ISSN},is_oa:true,from_publication_date:2023-01-01",
        "search": q,
        "per-page": 25,
        "select": "id,doi,title,publication_year,cited_by_count,open_access,primary_location,authorships,type",
    }
    try:
        d = get(params)
    except Exception as e:
        print(f"[warn] {q}: {e}")
        continue
    print(f"[query] {q!r}: {d['meta']['count']} hits, taking {len(d['results'])}")
    for w in d["results"]:
        wid = w["id"].rsplit("/", 1)[-1]
        if wid in seen:
            seen[wid]["queries"].append(q)
            continue
        loc = w.get("primary_location") or {}
        oa = w.get("open_access") or {}
        authors = [a["author"]["display_name"] for a in (w.get("authorships") or [])][:6]
        seen[wid] = {
            "id": wid,
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "title": w.get("title"),
            "year": w.get("publication_year"),
            "citations": w.get("cited_by_count"),
            "oa_url": oa.get("oa_url"),
            "pdf_url": loc.get("pdf_url"),
            "landing": loc.get("landing_page_url"),
            "is_oa": oa.get("is_oa"),
            "authors": authors,
            "queries": [q],
        }
    time.sleep(0.4)

out = sorted(seen.values(), key=lambda x: (-(x["citations"] or 0), -(x["year"] or 0)))
p = Path(__file__).resolve().parent / "kbs_oa_candidates.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n[done] {len(out)} unique OA KBS works -> {p}")
for w in out[:40]:
    print(f"{w['year']} | cites={w['citations']:>4} | {w['title'][:95]}")
    print(f"      doi={w['doi']} pdf={w['pdf_url'] or '-'} oa={w['oa_url'] or '-'}")
