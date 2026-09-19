#!/usr/bin/env python3
"""从 arXiv 检索 CIKM Demo 论文(comment 含 CIKM+demo)供风格研读, 下载 PDF.
护栏: https + arXiv host 白名单 + IP 公网校验; XML 拒绝 DOCTYPE/ENTITY;
传输层 curl。输出 paper_demo/reference/ + papers_index.json。"""
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

OUT = Path(__file__).resolve().parent / "reference"
ATOM = "{http://www.w3.org/2005/Atom}"
ALLOWED_HOSTS = {"arxiv.org", "export.arxiv.org", "www.arxiv.org"}
MAX_XML = 512 * 1024
MAX_BODY = 40 * 1024 * 1024

QUERY = ('https://export.arxiv.org/api/query?search_query='
         'co:%22CIKM%22+AND+co:%22demo%22'
         '&sortBy=submittedDate&sortOrder=descending&max_results=20')


def guard(url: str) -> str:
    p = urllib.parse.urlparse(url)
    if p.scheme != "https":
        raise ValueError(url)
    host = (p.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(host)
    for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError(f"non-global ip for {host}")
    return url


def fetch(url: str, timeout: int = 120, max_body: int = MAX_BODY,
          tries: int = 4) -> bytes:
    checked, last = guard(url), None
    for attempt in range(tries):
        time.sleep(3.0 * attempt)
        r = subprocess.run(
            ["curl", "-sSL", "--fail", "--max-redirs", "3",
             "--max-filesize", str(max_body), "--max-time", str(timeout),
             "-A", "cikm-demo-study/1.0", checked], capture_output=True)
        if r.returncode == 0:
            return r.stdout
        last = RuntimeError(f"curl rc={r.returncode}: {r.stderr[:100]}")
    raise last


def entries(query: str) -> list[dict]:
    xml = fetch(query, max_body=MAX_XML).decode("utf-8", errors="replace")
    head = xml[:4096].lstrip().lower()
    if "<!doctype" in head or "<!entity" in head:
        raise ValueError("doctype/entity rejected")
    root = ET.fromstring(xml)
    out = []
    for e in root.findall(f"{ATOM}entry"):
        abs_id = (e.findtext(f"{ATOM}id") or "").strip()
        comment = (e.findtext("{http://arxiv.org/schemas/atom}comment") or "")
        out.append({
            "id": abs_id.rsplit("/abs/", 1)[-1],
            "title": re.sub(r"\s+", " ",
                            (e.findtext(f"{ATOM}title") or "")).strip(),
            "comment": re.sub(r"\s+", " ", comment)[:200],
        })
    return out


def slugify(t: str, n: int = 40) -> str:
    return (re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-").lower()[:n].rstrip("-")
            or "paper")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    es = entries(QUERY)
    picks = [e for e in es if re.search(r"cikm", e["comment"], re.I)
             and re.search(r"demo", e["comment"], re.I)][:6]
    print(f"[search] {len(es)} candidates, {len(picks)} CIKM-demo picks")
    index = []
    for e in picks:
        time.sleep(3)
        try:
            blob = fetch(f"https://arxiv.org/pdf/{e['id']}")
        except Exception as ex:  # noqa: BLE001
            print(f"[fail] {e['id']}: {ex}")
            continue
        if not blob.startswith(b"%PDF"):
            print(f"[fail] {e['id']} not pdf")
            continue
        name = f"cikm-demo__{e['id'].split('v')[0].replace('/', '-')}__{slugify(e['title'])}.pdf"
        (OUT / name).write_bytes(blob)
        index.append({**e, "pdf": name,
                      "sha256": hashlib.sha256(blob).hexdigest()[:16],
                      "bytes": len(blob)})
        print(f"[ok] {e['title'][:60]} ({len(blob)//1024} KB)", flush=True)
    (OUT.parent / "papers_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] {len(index)} demo papers downloaded")
    return 0 if index else 1


if __name__ == "__main__":
    sys.exit(main())
