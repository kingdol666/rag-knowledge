# -*- coding: utf-8 -*-
"""多领域中长篇完整文档数据集下载器。

安全约束（Mimosa）：仅允许 http/https；发请求前校验 host——解析全部地址并
拒绝 localhost、环回、私有（RFC1918/link-local）与保留地址。

语料设计：8 个领域中英双语，每篇都是"完整文档"（整部法律全文 / 整回小说 /
整篇论文 PDF / 整章官方文档），支持 解析→入库→书架分组→逐级检索。
外部学术数据集（QuALITY/Qasper）另列，供金标问答评测复用。

运行: uv run --no-sync --directory backend python D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/experiment-redesign-20261101/scripts/download_corpus.py
"""
import ipaddress
import json
import socket
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx

BASE = Path(__file__).resolve().parent
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"
LOG = BASE / "artifacts" / "download_log.json"

BLOCKED_NETS = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
    "172.16.0.0/12", "192.0.0.0/24", "192.168.0.0/16", "198.18.0.0/15",
    "224.0.0.0/4", "240.0.0.0/4", "::1/128", "::/128", "fc00::/7",
    "fe80::/10", "ff00::/8")]


def ssrf_guard(url: str) -> str:
    """仅 http/https + host 解析后必须全部是公网地址。"""
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"scheme not allowed: {p.scheme}")
    host = p.hostname or ""
    infos = socket.getaddrinfo(host, None)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        for net in BLOCKED_NETS:
            if ip in net:
                raise ValueError(f"host resolves to blocked addr: {host} -> {ip}")
    return url


def fetch(cli: httpx.Client, url: str, dest: Path, note: str) -> dict:
    entry = {"url": url, "dest": str(dest), "note": note}
    try:
        ssrf_guard(url)
        r = cli.get(url)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        entry.update(ok=True, bytes=len(r.content),
                     sha_head=__import__("hashlib").sha256(r.content[:4096]).hexdigest()[:16])
        print(f"OK   {note:28s} {len(r.content):>9,} B  {dest.name}")
    except Exception as e:  # noqa: BLE001 — 逐条记录失败供补采
        entry.update(ok=False, error=str(e)[:200])
        print(f"FAIL {note:28s} {e}")
    return entry


WIKI = "https://zh.wikisource.org/w/api.php?action=query&redirects=1&prop=extracts&explaintext=1&format=json&formatversion=2&titles="


def wiki(cli: httpx.Client, title: str, dest: Path, note: str) -> dict:
    url = WIKI + quote(title)
    e = {"url": url, "dest": str(dest), "note": note, "kind": "wikisource-extract"}
    try:
        ssrf_guard(url)
        r = cli.get(url)
        r.raise_for_status()
        pages = (r.json().get("query") or {}).get("pages") or []
        text = pages[0].get("extract", "") if pages else ""
        if len(text) < 2000:
            raise ValueError(f"extract too short: {len(text)} chars (title miss?)")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        e.update(ok=True, bytes=len(text.encode("utf-8")))
        print(f"OK   {note:28s} {len(text.encode('utf-8')):>9,} B  {dest.name}")
    except Exception as ex:  # noqa: BLE001
        e.update(ok=False, error=str(ex)[:200])
        print(f"FAIL {note:28s} {ex}")
    return e


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cli = httpx.Client(trust_env=False, timeout=120, follow_redirects=True,
                       headers={"User-Agent": "corpus-builder/1.0 (research; contact: local)"})
    log: list[dict] = []

    # ── 文学-EN：整本公版小说（Gutenberg） ──
    log.append(fetch(cli, "https://www.gutenberg.org/files/1342/1342-0.txt",
                     CORPUS / "literature-en" / "pride_and_prejudice_full.txt", "PridePrejudice全本"))
    log.append(fetch(cli, "https://www.gutenberg.org/files/2701/2701-0.txt",
                     CORPUS / "literature-en" / "moby_dick_full.txt", "MobyDick全本"))

    # ── 文学-ZH：红楼梦前五回（完整回目单元） ──
    for i in (1, 2, 3, 4, 5):
        log.append(wiki(cli, f"紅樓夢/第{'一二三四五'[i-1]}回",
                        CORPUS / "literature-zh" / f"hongloumeng_hui{i:02d}.txt", f"红楼梦第{i}回"))

    # ── 法律-ZH：三部数据/安全类法律全文 ──
    for title, fn in [("中华人民共和国个人信息保护法", "pipl_full.txt"),
                      ("中华人民共和国数据安全法", "dsl_full.txt"),
                      ("中华人民共和国网络安全法", "csl_full.txt")]:
        log.append(wiki(cli, title, CORPUS / "law-zh" / fn, title[:14] + "全文"))

    # ── 政务-ZH：政府工作报告 2024 全文 ──
    log.append(wiki(cli, "政府工作报告 (2024年)",
                    CORPUS / "gov-zh" / "gov_work_report_2024.txt", "政府工作报告2024"))
    log.append(wiki(cli, "中华人民共和国国民经济和社会发展第十四个五年规划和2035年远景目标纲要",
                    CORPUS / "gov-zh" / "14th_five_year_plan.txt", "十四五规划纲要全文"))

    # ── 历史-ZH：史记完整篇目两卷 ──
    for juan, name in [("卷007", "xiangyu_benji"), ("卷048", "chanshe_shijia")]:
        log.append(wiki(cli, f"史記/{juan}", CORPUS / "history-zh" / f"shiji_{name}.txt", f"史记{juan}"))

    # ── 科学-EN：三篇完整论文 PDF（arXiv） ──
    for ax, name in [("1706.03762", "attention_is_all_you_need"),
                     ("1810.04805", "bert_pretraining"),
                     ("2005.11401", "rag_lewis2020")]:
        log.append(fetch(cli, f"https://arxiv.org/pdf/{ax}",
                         CORPUS / "science-en" / f"{name}.pdf", f"arXiv:{ax}"))

    # ── 医学-EN：EuropePMC OA 全文（搜索 API 取开放获取长文） ──
    for topic, fn in [("sepsis biomarkers review", "sepsis_biomarkers_oa.xml"),
                      ("COVID-19 long-term sequelae", "covid_sequelae_oa.xml")]:
        try:
            q = quote(f'({topic}) AND OPEN_ACCESS:y AND SRC:PPM')
            u = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
                 + q + "&format=json&pageSize=5&sort=P_PDATE_D desc")
            ssrf_guard(u)
            hits = cli.get(u).json().get("resultList", {}).get("result", [])
            pick = next((h for h in hits if h.get("isOpenAccess") == "Y" and h.get("pmcid")), None)
            if not pick:
                raise ValueError("no OA hit")
            pu = (f"https://www.ebi.ac.uk/europepmc/webservices/rest/"
                  f"{pick['pmcid']}/fullTextXML")
            ssrf_guard(pu)
            r = cli.get(pu)
            r.raise_for_status()
            d = CORPUS / "medicine-en" / fn
            d.write_bytes(r.content)
            e = {"url": pu, "dest": str(d), "note": f"PMC:{pick['pmcid']} {topic}",
                 "ok": True, "bytes": len(r.content), "pmcid": pick["pmcid"],
                 "title": pick.get("title", "")[:160]}
            log.append(e)
            print(f"OK   PMC:{pick['pmcid']:15s} {len(r.content):>9,} B  {fn}")
        except Exception as ex:  # noqa: BLE001
            log.append({"note": f"PMC {topic}", "ok": False, "error": str(ex)[:200]})
            print(f"FAIL PMC {topic:28s} {ex}")

    # ── 技术-EN：Kubernetes 官方文档完整章节（markdown 源文件） ──
    for path, fn in [
        ("concepts/overview/components.md", "k8s_components.md"),
        ("concepts/architecture/cloud-controller-manager.md", "k8s_ccm.md"),
        ("concepts/workloads/pods/pod.md", "k8s_pods.md"),
        ("concepts/security/pod-security-standards.md", "k8s_pss.md"),
    ]:
        log.append(fetch(cli, f"https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/{path}",
                         CORPUS / "tech-en" / fn, fn))

    # ── 外部学术数据集：Qasper（完整科研论文+问答+证据标注） ──
    log.append(fetch(cli, "https://ai2-public-datasets.s3.amazonaws.com/qasper/qasper-dev-v1.json",
                     CORPUS / "external-datasets" / "qasper-dev-v1.json", "Qasper-dev(完整论文QA)"))
    log.append(fetch(cli, "https://ai2-public-datasets.s3.amazonaws.com/qasper/qasper-train-v1.json",
                     CORPUS / "external-datasets" / "qasper-train-v1.json", "Qasper-train"))

    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for e in log if e.get("ok"))
    print(f"\n=== {ok}/{len(log)} downloaded; log → {LOG}")


if __name__ == "__main__":
    main()
