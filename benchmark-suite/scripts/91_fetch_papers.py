#!/usr/bin/env python3
"""Step 1 — 下载 50 篇跨领域真实论文到 data/papers/ 单一文件夹.

26 个领域: 12 个领域在已有首篇外各 +2(分类检索), 14 个新领域各 1 篇 → 共 50。
幂等: manifest 按 (field, arxiv_id) 去重, 已有篇目跳过。
安全护栏: 仅 https + arXiv host 白名单 + DNS 解析逐 IP 公网校验;
XML 拒绝 DOCTYPE/ENTITY; 传输层 curl(本机网络对 urllib TLS 指纹间歇 406)。
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

# 每个领域 {field, count, arxiv_id?, cat?, kw?}:
# - arxiv_id 指定确证经典(首篇); 其余按分类检索确定性取前 count 篇
SPECS = [
    {"field": "artificial-intelligence", "count": 3, "arxiv_id": "1706.03762",
     "cat": "cs.AI", "kw": "reasoning"},
    {"field": "nlp", "count": 3, "arxiv_id": "1810.04805",
     "cat": "cs.CL", "kw": "language models"},
    {"field": "large-language-models", "count": 3, "arxiv_id": "2005.14165",
     "cat": "cs.CL", "kw": "instruction tuning"},
    {"field": "quantum-physics", "count": 3, "arxiv_id": "1801.00862",
     "cat": "quant-ph", "kw": "quantum error correction"},
    {"field": "clinical-medicine", "count": 3, "arxiv_id": "2212.13138",
     "cat": "q-bio.QM", "kw": "clinical prediction"},
    {"field": "genomics", "count": 3, "arxiv_id": "1602.01876",
     "cat": "q-bio.GN", "kw": "transcriptomics"},
    {"field": "economics", "count": 3, "arxiv_id": "1512.08067",
     "cat": "econ.GN", "kw": "economic growth"},
    {"field": "climate-science", "count": 3, "arxiv_id": "1503.07557",
     "cat": "physics.ao-ph", "kw": "monsoon"},
    {"field": "astronomy", "count": 2, "arxiv_id": "",
     "cat": "astro-ph.IM", "kw": "galaxy survey"},
    {"field": "materials", "count": 2, "arxiv_id": "",
     "cat": "cond-mat.mtrl-sci", "kw": "battery cathode"},
    {"field": "neuroscience", "count": 2, "arxiv_id": "",
     "cat": "q-bio.NC", "kw": "neural circuits"},
    {"field": "robotics", "count": 2, "arxiv_id": "",
     "cat": "cs.RO", "kw": "SLAM"},
    {"field": "chemistry", "count": 2, "cat": "physics.chem-ph", "kw": "catalysis"},
    {"field": "mathematics", "count": 2, "cat": "math.OC", "kw": "optimal control"},
    {"field": "gravitational-physics", "count": 1, "cat": "gr-qc",
     "kw": "gravitational waves"},
    {"field": "statistics", "count": 1, "cat": "stat.ML", "kw": "causal inference"},
    {"field": "speech", "count": 2, "cat": "eess.AS", "kw": "speech recognition"},
    {"field": "power-systems", "count": 1, "cat": "eess.SY", "kw": "power grid"},
    {"field": "medical-imaging", "count": 1, "cat": "eess.IV",
     "kw": "medical imaging"},
    {"field": "immunology", "count": 1, "cat": "q-bio.QM", "kw": "immune response"},
    {"field": "oceanography", "count": 1, "cat": "physics.ao-ph",
     "kw": "ocean circulation"},
    {"field": "seismology", "count": 1, "cat": "physics.geo-ph", "kw": "earthquake"},
    {"field": "agriculture", "count": 1, "cat": "q-bio.PE", "kw": "agriculture"},
    {"field": "finance", "count": 1, "cat": "q-fin.CP", "kw": "trading"},
    {"field": "social-networks", "count": 1, "cat": "cs.SI", "kw": "social networks"},
    {"field": "databases", "count": 2, "cat": "cs.DB", "kw": "query optimization"},
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
    have = {(p["field"], p["arxiv_id"]) for p in manifest["papers"]}

    for spec in SPECS:
        need = spec["count"] - sum(1 for p in manifest["papers"]
                                   if p["field"] == spec["field"])
        if need <= 0:
            print(f"[skip] {spec['field']} complete")
            continue
        if spec.get("arxiv_id"):
            entries = api_entries("https://export.arxiv.org/api/query?id_list="
                                  + urllib.parse.quote(spec["arxiv_id"], safe=""))
        else:
            entries = []
        if len(entries) < need and spec.get("cat"):
            entries += api_entries(
                "https://export.arxiv.org/api/query?search_query="
                f"cat:{spec['cat']}+AND+all:{urllib.parse.quote(spec['kw'])}"
                f"&sortBy=relevance&start=0&max_results={need + 2}")
        fresh = [e for e in entries if e["id"]
                 and (spec["field"], e["id"]) not in have][:need]
        if not fresh:
            print(f"[FAIL] no fresh arXiv entries for {spec['field']}")
            return 1
        for e in fresh:
            blob = fetch(f"https://arxiv.org/pdf/{e['id']}")
            if not blob.startswith(b"%PDF") or len(blob) < MIN_PDF_BYTES:
                print(f"[FAIL] {e['id']} not a valid PDF ({len(blob)} bytes)")
                return 1
            stem = (f"{spec['field']}__{e['id'].split('v')[0].replace('/', '-')}"
                    f"__{slugify(e['title'])}")
            (OUT / f"{stem}.pdf").write_bytes(blob)
            manifest["papers"].append({
                "field": spec["field"], "arxiv_id": e["id"], "title": e["title"],
                "category": e["category"],
                "url": f"https://arxiv.org/pdf/{e['id']}",
                "pdf": f"{stem}.pdf", "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest()})
            have.add((spec["field"], e["id"]))
            print(f"[ok] {spec['field']}: {e['title'][:60]} "
                  f"({len(blob) // 1024} KB)", flush=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False,
                                            indent=1), encoding="utf-8")

    n = len(manifest["papers"])
    fields = len({p["field"] for p in manifest["papers"]})
    print(f"[done] {n} papers across {fields} fields in {OUT}"
          + ("" if n >= TARGET else f" (target {TARGET} — rerun to top up)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
