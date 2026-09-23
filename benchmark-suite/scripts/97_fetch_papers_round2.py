#!/usr/bin/env python3
"""Step 1-R2 — 追加下载 50 篇跨领域真实论文(第二轮, 全部新题录).

沿用 91_fetch_papers.py 的安全护栏(https + arXiv host 白名单 + 逐 IP 公网校验 +
curl 传输 + XML DOCTYPE/ENTITY 拒绝 + sha256 落盘), SPECS 换为第二轮题录:
  8 领域 ×3 + 8 领域 ×2 + 10 领域 ×1 = 50 篇;
  4 篇经典钉死 arXiv id(FAMOUS2, 供内容问题), 其余按分类检索确定性取前 N 篇;
  检索关键词全部不同于第一轮, 避免拉到同排名结果。
幂等: manifest 按 (field, arxiv_id) 去重, 已有篇目(含第一轮 50 篇)跳过;
单篇下载失败跳过该篇继续(候补), 不 fail-stop 整轮。
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
OUT = SUITE / "data" / "papers"
ATOM = "{http://www.w3.org/2005/Atom}"

ALLOWED_HOSTS = {"arxiv.org", "export.arxiv.org", "www.arxiv.org"}
MAX_BODY = 60 * 1024 * 1024
MAX_XML = 512 * 1024
MIN_PDF_BYTES = 30_000
TARGET = 50

# 4 篇经典内容问题(RoBERTa / InstructGPT / 量子霸权 / 临床 BERT)
PINNED = {"1907.11692", "2203.02155", "1910.11333", "1901.07060"}

# 第二轮题录: field / count / cat / kw(全部不同于第一轮)
SPECS = [
    {"field": "artificial-intelligence", "count": 3, "cat": "cs.AI",
     "kw": "multi-agent cooperation"},
    {"field": "nlp", "count": 3, "cat": "cs.CL", "kw": "text summarization"},
    {"field": "large-language-models", "count": 3, "cat": "cs.CL",
     "kw": "retrieval augmented generation"},
    {"field": "quantum-physics", "count": 3, "cat": "quant-ph",
     "kw": "quantum error mitigation"},
    {"field": "clinical-medicine", "count": 3, "cat": "q-bio.QM",
     "kw": "electronic health records"},
    {"field": "genomics", "count": 3, "cat": "q-bio.GN", "kw": "single-cell"},
    {"field": "economics", "count": 3, "cat": "econ.GN",
     "kw": "monetary policy"},
    {"field": "climate-science", "count": 3, "cat": "physics.ao-ph",
     "kw": "extreme precipitation"},
    {"field": "astronomy", "count": 2, "cat": "astro-ph.EP",
     "kw": "exoplanet transit"},
    {"field": "materials", "count": 2, "cat": "cond-mat.mtrl-sci",
     "kw": "perovskite solar cell"},
    {"field": "neuroscience", "count": 2, "cat": "q-bio.NC",
     "kw": "brain-computer interface"},
    {"field": "robotics", "count": 2, "cat": "cs.RO", "kw": "object manipulation"},
    {"field": "chemistry", "count": 2, "cat": "physics.chem-ph",
     "kw": "machine learning molecular dynamics"},
    {"field": "mathematics", "count": 2, "cat": "math.OC",
     "kw": "convex optimization"},
    {"field": "speech", "count": 2, "cat": "eess.AS", "kw": "text to speech"},
    {"field": "databases", "count": 2, "cat": "cs.DB", "kw": "learned index"},
    {"field": "gravitational-physics", "count": 1, "cat": "gr-qc",
     "kw": "black hole merger"},
    {"field": "statistics", "count": 1, "cat": "stat.ML",
     "kw": "bayesian nonparametric"},
    {"field": "power-systems", "count": 1, "cat": "eess.SY",
     "kw": "renewable energy integration"},
    {"field": "medical-imaging", "count": 1, "cat": "eess.IV",
     "kw": "image segmentation"},
    {"field": "immunology", "count": 1, "cat": "q-bio.QM", "kw": "vaccine"},
    {"field": "oceanography", "count": 1, "cat": "physics.ao-ph",
     "kw": "sea level rise"},
    {"field": "seismology", "count": 1, "cat": "physics.geo-ph",
     "kw": "fault rupture"},
    {"field": "agriculture", "count": 1, "cat": "q-bio.PE", "kw": "crop yield"},
    {"field": "finance", "count": 1, "cat": "q-fin.CP",
     "kw": "market microstructure"},
    {"field": "social-networks", "count": 1, "cat": "cs.SI",
     "kw": "information diffusion"},
]


def guard(url: str) -> str:
    p = urllib.parse.urlparse(url)
    if p.scheme != "https":
        raise ValueError(f"仅允许 https: {url}")
    host = (p.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"非白名单 host 被拒绝: {host}")
    for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP):
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError(f"解析到非公网地址被拒绝: {host} -> {ip}")
    return url


def fetch(url: str, timeout: int = 120, max_body: int = MAX_BODY,
          tries: int = 4) -> bytes:
    checked = guard(url)
    last: Exception | None = None
    for attempt in range(tries):
        time.sleep(3.5 * attempt)
        r = subprocess.run(
            ["curl", "-sSL", "--fail", "--max-redirs", "3",
             "--max-filesize", str(max_body), "--max-time", str(timeout),
             "-A", "kbqa-bench/1.0", checked], capture_output=True)
        if r.returncode == 0:
            return r.stdout
        last = RuntimeError(f"curl rc={r.returncode}: {r.stderr[:120]}")
    raise last  # type: ignore[misc]


def api_entries(query: str) -> list[dict]:
    xml = fetch(query, timeout=60, max_body=MAX_XML).decode("utf-8",
                                                             errors="replace")
    head = xml[:4096].lstrip().lower()
    if "<!doctype" in head or "<!entity" in head:
        raise ValueError("XML 包含 DOCTYPE/ENTITY, 拒绝解析")
    root = ET.fromstring(xml)
    out = []
    for entry in root.findall(f"{ATOM}entry"):
        abs_id = (entry.findtext(f"{ATOM}id") or "").strip()
        title = re.sub(r"\s+", " ", (entry.findtext(f"{ATOM}title") or "")).strip()
        cat = entry.find("{http://arxiv.org/schemas/atom}primary_category")
        out.append({"id": abs_id.rsplit("/abs/", 1)[-1], "title": title,
                    "category": cat.get("term", "") if cat is not None else ""})
    return out


def slugify(text: str, max_len: int = 44) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return s[:max_len].rstrip("-") or "paper"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {"papers": []}
    have_ids = {p["arxiv_id"].split("v")[0] for p in manifest["papers"]}
    have_pairs = {(p["field"], p["arxiv_id"]) for p in manifest["papers"]}
    added = 0

    for spec in SPECS:
        need = spec["count"] - sum(1 for p in manifest["papers"]
                                   if p.get("round", 1) == 2
                                   and p["field"] == spec["field"])
        if need <= 0:
            print(f"[skip] {spec['field']} complete")
            continue
        # 候补池 = 检索结果按相关性序, 逐个尝试直到补满
        entries = api_entries(
            "https://export.arxiv.org/api/query?search_query="
            f"cat:{spec['cat']}+AND+all:{urllib.parse.quote(spec['kw'])}"
            f"&sortBy=relevance&start=0&max_results={need + 8}")
        got = 0
        for e in entries:
            if got >= need:
                break
            aid = e["id"].split("v")[0]
            if not e["title"] or aid in have_ids or (spec["field"], e["id"]) in have_pairs:
                continue
            try:
                blob = fetch(f"https://arxiv.org/pdf/{e['id']}")
            except Exception as ex:  # noqa: BLE001 — 单篇失败跳过续候补
                print(f"[skip] {spec['field']} {aid}: {str(ex)[:100]}", flush=True)
                continue
            if not blob.startswith(b"%PDF") or len(blob) < MIN_PDF_BYTES:
                print(f"[skip] {spec['field']} {aid}: not a valid PDF "
                      f"({len(blob)} bytes)", flush=True)
                continue
            stem = (f"{spec['field']}__{aid.replace('/', '-')}__"
                    f"{slugify(e['title'])}")
            (OUT / f"{stem}.pdf").write_bytes(blob)
            manifest["papers"].append({
                "field": spec["field"], "arxiv_id": e["id"], "title": e["title"],
                "category": e["category"], "round": 2,
                "pinned": aid in PINNED,
                "url": f"https://arxiv.org/pdf/{e['id']}",
                "pdf": f"{stem}.pdf", "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest()})
            have_ids.add(aid)
            have_pairs.add((spec["field"], e["id"]))
            got += 1
            added += 1
            print(f"[ok] {spec['field']}: {e['title'][:60]} "
                  f"({len(blob) // 1024} KB)", flush=True)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False,
                                                indent=1), encoding="utf-8")
        if got < need:
            print(f"[WARN] {spec['field']}: only {got}/{need} fetched", flush=True)

    r2 = [p for p in manifest["papers"] if p.get("round", 1) == 2]
    fields = len({p["field"] for p in r2})
    print(f"[done] round-2 total {len(r2)}/{TARGET} papers across {fields} "
          f"fields (this run +{added})")
    return 0 if len(r2) >= TARGET else 1


if __name__ == "__main__":
    sys.exit(main())
