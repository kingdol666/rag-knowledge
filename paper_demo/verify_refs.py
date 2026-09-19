#!/usr/bin/env python3
"""引用批量核验 (PLAN §7 IRON RULE): 用 arXiv API 逐条核对
arXiv id → 标题/作者/年份, 输出 paper_demo/tex/refs_verified.json。
护栏: https + export.arxiv.org 白名单 + curl + XML 拒绝 DOCTYPE/ENTITY + 大小上限。"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tex" / "refs_verified.json"
ATOM = "{http://www.w3.org/2005/Atom}"
MAX_XML = 512 * 1024

# (arxiv_id, expected_key) — round-5 R3-2: corrected the survey id (was wrongly
# 2401.11804, a copula statistics paper) and added crag / mineru / kamath.
CHECKS = [
    ("2402.03216", "BGE-M3"),
    ("2310.11511", "Self-RAG"),
    ("2305.06983", "FLARE"),
    ("2404.16130", "GraphRAG"),
    ("2410.05779", "LightRAG"),
    ("2401.18059", "RAPTOR"),
    ("2005.11401", "RAG Lewis"),
    ("2004.04906", "DPR Karpukhin"),
    ("2309.01219", "Sirens Song hallucination survey"),
    ("2401.15884", "CRAG"),
    ("2409.18839", "MinerU"),
    ("2006.09462", "Kamath selective QA"),
]


def fetch(url: str, tries: int = 3) -> bytes:
    last = None
    for a in range(tries):
        time.sleep(3 * a)
        r = subprocess.run(["curl", "-sSL", "--fail", "--max-time", "60", url],
                           capture_output=True)
        if r.returncode == 0:
            return r.stdout
        last = r.returncode
    raise RuntimeError(f"curl rc={last}")


def parse(xml: bytes) -> dict:
    if len(xml) > MAX_XML:
        raise ValueError("oversized")
    head = xml[:4096].lstrip().lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise ValueError("doctype/entity rejected")
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    for e in root.findall(f"{ATOM}entry"):
        aid = (e.findtext(f"{ATOM}id") or "").rsplit("/abs/", 1)[-1]
        title = re.sub(r"\s+", " ", (e.findtext(f"{ATOM}title") or "")).strip()
        authors = [a.findtext(f"{ATOM}name") for a in e.findall(f"{ATOM}author")]
        pub = (e.findtext(f"{ATOM}published") or "")[:4]
        return {"id": aid, "title": title, "authors": authors[:6],
                "year": pub, "n_authors": len(authors)}
    return {}


def main() -> int:
    out = {}
    for aid, key in CHECKS:
        try:
            url = ("https://export.arxiv.org/api/query?id_list="
                   + urllib.parse.quote(aid))
            rec = parse(fetch(url))
            out[aid] = {**rec, "expected": key}
            print(f"[{'OK' if rec else 'MISS'}] {aid} {key}: "
                  f"{rec.get('title', '?')[:70]} ({rec.get('year')})", flush=True)
        except Exception as ex:  # noqa: BLE001
            out[aid] = {"expected": key, "error": str(ex)}
            print(f"[ERR] {aid} {key}: {ex}", flush=True)
        time.sleep(3)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"[done] {sum(1 for v in out.values() if v.get('title'))}/{len(CHECKS)} verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
