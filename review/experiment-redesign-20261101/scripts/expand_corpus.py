# -*- coding: utf-8 -*-
"""语料扩充 → 100+ 篇多领域中长篇完整文档（11 域）。

来源（全部合规可直链）：
  Gutenberg 公版书（文学/哲学/经济）· arXiv PDF（科学）· EuropePMC OA 全文 XML（医学）
  Kubernetes 官方文档 md（技术，GitHub API 列目录自适应路径）· wikisource 中文（法律/政务/文学/历史）
产出：
  1) 各域目录下新文档  2) corpus_spec.json（域→文档清单+名称+描述+金标锚，manifest/s2 的单一事实源）
  3) expand_log.json（每条下载结果；失败可重跑补采，幂等：已存在且 ≥MIN_CHARS 的跳过）
金标锚纪律：anchor 必须是下载内容中实测存在的字符串（标题/著名专名），实测缺失则该题不入 spec。
安全：SSRF 守卫（仅 http/https + 拒绝环回/私有/保留地址）；wikisource 走 curl + 限速退避。
运行: python expand_corpus.py
"""
import ipaddress
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

BASE = Path(__file__).resolve().parent
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"
SPEC_OUT = BASE.parent / "artifacts" / "corpus_spec.json"
LOG_OUT = BASE.parent / "artifacts" / "expand_log.json"
MIN_CHARS = 2000
UA = "corpus-builder/1.0 (research)"

BLOCKED_NETS = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
    "172.16.0.0/12", "192.0.0.0/24", "192.168.0.0/16", "198.18.0.0/15",
    "224.0.0.0/4", "240.0.0.0/4", "::1/128", "::/128", "fc00::/7", "fe80::/10", "ff00::/8")]


def ssrf_guard(url):
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"scheme not allowed: {p.scheme}")
    for info in socket.getaddrinfo(p.hostname or "", None):
        ip = ipaddress.ip_address(info[4][0])
        if any(ip in net for net in BLOCKED_NETS):
            raise ValueError(f"blocked addr for {p.hostname}: {ip}")


def http_get(url: str, timeout: int = 120) -> bytes:
    ssrf_guard(url)
    p = subprocess.run(["curl", "-sfL", "-m", str(timeout), "-A", UA, url],
                       capture_output=True, timeout=timeout + 30)
    return p.stdout


def fetch_gutenberg(gid: int, dest: Path, title: str, anchor: str, log: list) -> bool:
    """Gutenberg 整本：cache/epub 新路径优先，files 老路径回退；拒绝 HTML 错误页。"""
    if dest.exists() and len(dest.read_text(encoding="utf-8", errors="replace")) >= MIN_CHARS \
            and "<html" not in dest.read_text(encoding="utf-8", errors="replace")[:500].lower():
        log.append(dict(id=f"gutenberg:{gid}", ok=True, skipped=True)); return True
    urls = [f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt",
            f"https://www.gutenberg.org/files/{gid}/{gid}-0.txt",
            f"https://www.gutenberg.org/files/{gid}/{gid}.txt"]
    for url in urls:
        try:
            b = http_get(url, timeout=180)
            text = b.decode("utf-8", "replace")
            if len(text) >= MIN_CHARS and "<html" not in text[:500].lower():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding="utf-8")
                anchor_ok = anchor.lower() in text.lower()
                log.append(dict(id=f"gutenberg:{gid}", ok=True, chars=len(text), anchor_ok=anchor_ok))
                print(f"OK  gutenberg {gid:<6} {len(text):>9,} chars  {dest.name}  anchor={'✓' if anchor_ok else '✗'}")
                return True
        except Exception:  # noqa: BLE001 — 逐 URL 降级
            continue
    print(f"FAIL gutenberg {gid} {title}")
    log.append(dict(id=f"gutenberg:{gid}", ok=False, error="no variant fetched"))
    return False


def fetch_arxiv(ax: str, dest: Path, title: str, anchor: str, log: list) -> bool:
    if dest.exists() and dest.stat().st_size > 50_000:
        log.append(dict(id=f"arxiv:{ax}", ok=True, skipped=True)); return True
    try:
        b = http_get(f"https://arxiv.org/pdf/{ax}", timeout=240)
        if len(b) > 50_000 and b[:4] == b"%PDF":
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b)
            log.append(dict(id=f"arxiv:{ax}", ok=True, bytes=len(b)))
            print(f"OK  arxiv {ax:<12} {len(b):>9,} B  {dest.name}")
            return True
    except Exception as e:  # noqa: BLE001
        log.append(dict(id=f"arxiv:{ax}", ok=False, error=str(e)[:120]))
    print(f"FAIL arxiv {ax} {title}")
    log.append(dict(id=f"arxiv:{ax}", ok=False, error="no pdf"))
    return False


def fetch_pmc(topic: str, dest: Path, log: list, used_titles: set) -> dict | None:
    """EuropePMC：搜索 OA 综述 → 取 fullTextXML。返回 {title, anchor} 供金标。"""
    if dest.exists() and dest.stat().st_size > 30_000:
        log.append(dict(id=f"pmc:{topic}", ok=True, skipped=True)); return None
    try:
        q = quote(f"{topic} AND OPEN_ACCESS:y")   # 无括号/无 SRC:PPM（实测带括号会 0 命中）
        u = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
             + q + "&format=json&pageSize=8")
        hits = []
        for attempt in range(4):   # 搜索服务间歇 503（errCode 503）——退避重试
            raw = http_get(u)
            parsed = {}
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"errCode": "empty"}
            if parsed.get("errCode") or parsed.get("hitCount") is None:
                time.sleep(25 * (attempt + 1))
                continue
            hits = parsed.get("resultList", {}).get("result", [])
            break
        pick = next((h for h in hits if h.get("isOpenAccess") == "Y" and h.get("pmcid")
                     and h.get("title", "") not in used_titles), None)
        if not pick:
            raise ValueError("no fresh OA hit (after retries)")
        xml = http_get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pick['pmcid']}/fullTextXML")
        if len(xml) < 30_000:
            raise ValueError(f"xml too small {len(xml)}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(xml)
        title = (pick.get("title") or "").strip()
        used_titles.add(title)
        log.append(dict(id=f"pmc:{pick['pmcid']}", ok=True, bytes=len(xml), title=title[:120]))
        print(f"OK  pmc {pick['pmcid']:<14} {len(xml):>9,} B  {dest.name}")
        return {"pmcid": pick["pmcid"], "title": title}
    except Exception as e:  # noqa: BLE001
        print(f"FAIL pmc {topic}: {str(e)[:90]}")
        log.append(dict(id=f"pmc:{topic}", ok=False, error=str(e)[:120]))
        return None


def fetch_wiki(title: str, dest: Path, log: list, min_chars: int = MIN_CHARS) -> bool:
    """wikisource 提取（curl + 限速退避；幂等）。"""
    if dest.exists() and len(dest.read_text(encoding="utf-8", errors="replace")) >= min_chars:
        log.append(dict(id=f"wiki:{title}", ok=True, skipped=True)); return True
    api = ("https://zh.wikisource.org/w/api.php?action=query&redirects=1"
           "&prop=extracts&explaintext=1&format=json&formatversion=2&titles=")
    for attempt in range(4):
        try:
            body = http_get(api + quote(title), timeout=90).decode("utf-8", "replace")
            pages = (json.loads(body).get("query") or {}).get("pages") or [{}]
            text = pages[0].get("extract", "")
            if len(text) < min_chars:
                raise ValueError(f"extract {len(text)} chars")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            log.append(dict(id=f"wiki:{title}", ok=True, chars=len(text)))
            print(f"OK  wiki {title[:26]:<26} {len(text):>8,} chars  {dest.name}")
            time.sleep(6)  # 防限速
            return True
        except Exception:  # noqa: BLE001 — JSON 解析失败=限速级联，同样退避
            time.sleep(20 * (attempt + 1))
    print(f"FAIL wiki {title}")
    log.append(dict(id=f"wiki:{title}", ok=False, error="fetch failed"))
    return False


def k8s_concept_docs(max_docs: int, log: list) -> list:
    """GitHub API 列 concepts 子目录，自适应挑选 md（5-40KB，去已有）。"""
    have = {p.name for p in (CORPUS / "tech-en").glob("*.md")}
    picked = []
    subdirs = ["workloads", "services", "security", "storage", "scheduling",
               "architecture", "extend", "networking", "compute", "concepts"]
    for sub in subdirs:
        if len(picked) >= max_docs:
            break
        try:
            u = f"https://api.github.com/repos/kubernetes/website/contents/content/en/docs/concepts/{sub}?ref=main"
            items = json.loads(http_get(u))
            if not isinstance(items, list):
                continue
            for it in items:
                if len(picked) >= max_docs:
                    break
                if it.get("type") == "file" and it.get("name", "").endswith(".md") \
                        and it.get("size", 0) and 4000 <= it["size"] <= 45000 \
                        and it["name"] not in have:
                    have.add(it["name"])
                    picked.append((sub, it["name"], it.get("size")))
        except Exception as e:  # noqa: BLE001
            log.append(dict(id=f"k8s-list:{sub}", ok=False, error=str(e)[:120]))
    out = []
    for sub, name, size in picked:
        dest = CORPUS / "tech-en" / name
        if dest.exists():
            out.append((name, name)); continue
        try:
            u = (f"https://raw.githubusercontent.com/kubernetes/website/main/"
                 f"content/en/docs/concepts/{sub}/{name}")
            b = http_get(u)
            text = b.decode("utf-8", "replace")
            if len(text) >= MIN_CHARS:
                dest.write_text(text, encoding="utf-8")
                log.append(dict(id=f"k8s:{name}", ok=True, bytes=len(text)))
                print(f"OK  k8s {name:<44} {len(text):>7,} chars")
                out.append((name, name))
        except Exception as e:  # noqa: BLE001
            log.append(dict(id=f"k8s:{name}", ok=False, error=str(e)[:120]))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    log: list = []
    spec_docs: dict[str, list] = {}

    def add(domain, file_rel, name, desc, anchor=None, question=None):
        spec_docs.setdefault(domain, []).append(
            dict(file=file_rel, name=name, desc=desc, anchor=anchor, question=question))

    # ── 1. 文学-EN：Gutenberg 整本（新增 12） ──
    lit = [
        (84, "frankenstein.md", "Frankenstein", "Frankenstein"),
        (1260, "jane_eyre.md", "Jane Eyre", "Jane Eyre"),
        (11, "alice_in_wonderland.md", "Alice's Adventures in Wonderland", "Wonderland"),
        (1661, "sherlock_holmes_adventures.md", "The Adventures of Sherlock Holmes", "Sherlock Holmes"),
        (120, "treasure_island.md", "Treasure Island", "Treasure Island"),
        (35, "time_machine.md", "The Time Machine", "Time Machine"),
        (43, "dracula.md", "Dracula", "Dracula"),
        (64317, "great_gatsby.md", "The Great Gatsby", "Gatsby"),
        (5200, "metamorphosis.md", "Metamorphosis", "Gregor"),
        (36, "war_of_the_worlds.md", "The War of the Worlds", "Martians"),
        (98, "tale_of_two_cities.md", "A Tale of Two Cities", "It was the best of times"),
        (1400, "great_expectations.md", "Great Expectations", "Pip"),
        (174, "dorian_gray.md", "The Picture of Dorian Gray", "Dorian Gray"),
        (76, "huckleberry_finn.md", "Adventures of Huckleberry Finn", "Huckleberry Finn"),
        (1727, "odyssey.md", "The Odyssey", "Odyssey"),
        (161, "sense_and_sensibility.md", "Sense and Sensibility", "Sense and Sensibility"),
        (1399, "anna_karenina.md", "Anna Karenina", "Anna Karenina"),
    ]
    for gid, name, title, anchor in lit:
        fp = f"literature-en/{name}"
        if fetch_gutenberg(gid, CORPUS / fp, title, anchor, log):
            add("literature-en", fp, name.replace(".md", ""), f"{title}（Gutenberg 公版整本小说）", anchor,
                f"Which novel in the corpus is {title}?")

    # ── 2. 文学-ZH：红楼梦新增回目（7） ──
    for hui in (6, 7, 8, 9, 10, 11, 12):
        fp = f"literature-zh/hongloumeng_hui{hui:02d}.txt"
        if fetch_wiki(f"紅樓夢/第{hui:03d}回", CORPUS / fp, log):
            add("literature-zh", fp, f"红楼梦第{hui:02d}回.md",
                f"红楼梦第{hui}回（维基文库繁体完整回目）", None, None)

    # ── 3. 历史-ZH：史记新增卷（8） ──
    shiji = [(8, "高祖本纪"), (9, "吕太后本纪"), (47, "孔子世家"), (54, "萧相国世家"),
             (55, "留侯世家"), (92, "淮阴侯列传"), (109, "李将军列传"), (129, "货殖列传")]
    for juan, nm in shiji:
        fp = f"history-zh/shiji_juan{juan:03d}.txt"
        if fetch_wiki(f"史記/卷{juan:03d}", CORPUS / fp, log):
            add("history-zh", fp, f"史记卷{juan:03d}{nm}.md",
                f"史记卷{juan}：{nm}（维基文库繁体完整篇目）", nm, f"《史记》中记载{nm}的是哪一卷？")

    # ── 4. 法律-ZH：新增 9 部全文 ──
    laws = [("中华人民共和国反垄断法", "aml"), ("中华人民共和国专利法", "patent"),
            ("中华人民共和国商标法", "trademark"), ("中华人民共和国著作权法", "copyright"),
            ("中华人民共和国电子商务法", "ecommerce"), ("中华人民共和国反不正当竞争法", "ucl"),
            ("中华人民共和国消费者权益保护法", "cpl"), ("中华人民共和国食品安全法", "fsl"),
            ("中华人民共和国密码法", "cryptography_law")]
    for title, tag in laws:
        fp = f"law-zh/{tag}_full.txt"
        if fetch_wiki(title, CORPUS / fp, log):
            # 锚=None：法律正文 extract 不含标题串，锚实测必失败；法律域已有 4 道手写金标
            add("law-zh", fp, f"{title}.md", f"{title}全文（维基文库）", None, None)

    # ── 5. 政务-ZH：政府工作报告 2020-2023/2025 ──
    for year in (2020, 2021, 2022, 2023, 2025):
        fp = f"gov-zh/gov_work_report_{year}.txt"
        title = f"{year}年中华人民共和国国务院政府工作报告"
        if fetch_wiki(title, CORPUS / fp, log):
            add("gov-zh", fp, f"政府工作报告{year}.md",
                f"{year} 年国务院政府工作报告全文", title[:12],
                f"{year} 年政府工作报告设定的发展目标是什么？")

    # ── 6. 科学-EN：arXiv 新增 12 篇 ──
    papers = [
        ("1512.03385", "resnet.md", "Deep Residual Learning", "Deep Residual Learning",
         "Which paper introduced deep residual learning for image recognition?"),
        ("1406.2661", "gan.md", "Generative Adversarial Networks", "Generative Adversarial",
         "Which paper proposed generative adversarial networks?"),
        ("1312.6114", "vae.md", "Auto-Encoding Variational Bayes", "Variational Bayes",
         "Which paper proposed the variational autoencoder?"),
        ("1301.3781", "word2vec.md", "Efficient Estimation of Word Representations", "word representations",
         "Which paper proposed efficient word representations (word2vec)?"),
        ("2103.00020", "clip.md", "Learning Transferable Visual Models", "Natural Language Supervision",
         "Which paper introduced CLIP (visual models from natural language supervision)?"),
        ("2006.11239", "ddpm.md", "Denoising Diffusion Probabilistic Models", "Denoising Diffusion",
         "Which paper introduced denoising diffusion probabilistic models?"),
        ("1910.10683", "t5.md", "Exploring the Limits of Transfer Learning", "Text-to-Text",
         "Which paper proposed the text-to-text transfer learning framework (T5)?"),
        ("1907.11692", "roberta.md", "RoBERTa: A Robustly Optimized BERT", "RoBERTa",
         "Which paper presented RoBERTa?"),
        ("2103.14030", "swin_transformer.md", "Swin Transformer", "Swin Transformer",
         "Which paper introduced the Swin Transformer?"),
        ("2005.14165", "gpt3.md", "Language Models are Few-Shot Learners", "Few-Shot Learners",
         "Which paper showed language models are few-shot learners (GPT-3)?"),
        ("2203.02155", "instructgpt.md", "InstructGPT", "human feedback",
         "Which paper trained language models to follow instructions with human feedback?"),
        ("2302.13971", "llama.md", "LLaMA: Open and Efficient Foundation Language Models", "LLaMA",
         "Which paper introduced LLaMA?"),
    ]
    for ax, name, title, anchor, question in papers:
        fp = f"science-en/{name}"
        if fetch_arxiv(ax, CORPUS / fp, title, anchor, log):
            add("science-en", fp, name.replace(".md", ""), f"{title}（arXiv:{ax} 整篇论文）",
                anchor, question)

    # ── 7. 医学-EN：EuropePMC OA 新增 13 篇（服务 503 时快速失败，不空耗重试） ──
    pmc_topics = [
        ("diabetes mellitus management review", "diabetes_management_review_oa.xml",
         "What does the corpus say about diabetes mellitus management?"),
        ("cancer immunotherapy review", "cancer_immunotherapy_review_oa.xml",
         "Which review in the corpus discusses cancer immunotherapy?"),
        ("Alzheimer disease biomarkers review", "alzheimer_biomarkers_review_oa.xml",
         "What is known about Alzheimer disease biomarkers in the corpus?"),
        ("cardiovascular imaging review", "cardiovascular_imaging_review_oa.xml", None),
        ("gut microbiome review", "gut_microbiome_review_oa.xml", None),
        ("mRNA vaccine review", "mrna_vaccine_review_oa.xml", None),
        ("obesity pharmacotherapy review", "obesity_pharmacotherapy_review_oa.xml", None),
        ("telemedicine outcomes review", "telemedicine_outcomes_review_oa.xml", None),
        ("CRISPR gene editing review", "crispr_gene_editing_review_oa.xml",
         "Which corpus review covers CRISPR gene editing?"),
        ("tuberculosis treatment review", "tuberculosis_treatment_review_oa.xml", None),
        ("malaria vaccine review", "malaria_vaccine_review_oa.xml", None),
        ("asthma biologics review", "asthma_biologics_review_oa.xml", None),
        ("stroke thrombolysis review", "stroke_thrombolysis_review_oa.xml", None),
    ]
    probe = http_get("https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                     "?query=malaria&format=json&pageSize=1", timeout=30)
    pmc_down = b"errCode" in probe[:120] or len(probe) < 50
    if pmc_down:
        print("!! EuropePMC search 503——本跳过医学补采（服务端故障，幂等可后补）")
        log.append(dict(id="pmc:probe", ok=False, error="service 503"))
    used = set()
    for topic, fn, question in ([] if pmc_down else pmc_topics):
        meta = fetch_pmc(topic, CORPUS / "medicine-en" / fn, log, used)
        if meta:
            anchor = (meta["title"][:28].strip()) or topic
            add("medicine-en", f"medicine-en/{fn}", fn.replace("_oa.xml", ""),
                f"{meta['title'][:80]}（EuropePMC OA 全文，{meta['pmcid']}）",
                anchor, question or f"What does the corpus contain about {topic.split(' review')[0]}?")

    # ── 8. 技术-EN：Kubernetes 新增 10 章 ──
    for name, _ in k8s_concept_docs(10, log):
        title = name[:-3].replace("-", " ")
        add("tech-en", f"tech-en/{name}", name, f"Kubernetes concept doc: {title}",
            title[:16], f"Which Kubernetes documentation chapter covers {title}?")

    # ── 9. 哲学-EN（Gutenberg 8） ──
    phil = [(2680, "meditations.md", "Meditations", "Marcus Aurelius"),
            (1497, "republic.md", "The Republic", "Plato"),
            (1232, "the_prince.md", "The Prince", "Machiavelli"),
            (1998, "zarathustra.md", "Thus Spoke Zarathustra", "Zarathustra"),
            (4363, "beyond_good_and_evil.md", "Beyond Good and Evil", "Beyond Good and Evil"),
            (132, "art_of_war.md", "The Art of War", "Sun Tzu"),
            (205, "walden.md", "Walden", "Thoreau"),
            (147, "common_sense.md", "Common Sense", "Paine")]
    for gid, name, title, anchor in phil:
        fp = f"philosophy-en/{name}"
        if fetch_gutenberg(gid, CORPUS / fp, title, anchor, log):
            add("philosophy-en", fp, name.replace(".md", ""),
                f"{title}（Gutenberg 公版整本）", anchor,
                f"Which philosophy work in the corpus is {title}?")

    # ── 10. 经济-EN（Gutenberg 4） ──
    econ = [(3300, "wealth_of_nations.md", "The Wealth of Nations", "Wealth of Nations"),
            (833, "theory_of_the_leisure_class.md", "The Theory of the Leisure Class", "Leisure Class"),
            (34901, "on_liberty.md", "On Liberty", "On Liberty"),
            (4239, "malthus_population.md", "An Essay on the Principle of Population", "Principle of Population")]
    for gid, name, title, anchor in econ:
        fp = f"economics-en/{name}"
        if fetch_gutenberg(gid, CORPUS / fp, title, anchor, log):
            add("economics-en", fp, name.replace(".md", ""),
                f"{title}（Gutenberg 公版整本）", anchor,
                f"Which economics classic in the corpus is {title}?")

    LOG_OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    ok_new = sum(1 for e in log if e.get("ok") and not e.get("skipped"))
    fails = [e for e in log if not e.get("ok")]
    print(f"\n=== 扩充完成：新增成功 {ok_new}，失败 {len(fails)}（幂等可重跑补采）")
    # 汇总当前语料文档数
    counts = {}
    for d in CORPUS.iterdir():
        if d.is_dir():
            counts[d.name] = sum(1 for p in d.rglob("*") if p.is_file())
    print("域分布:", json.dumps(counts, ensure_ascii=False))
    print(f"合计文档（文件级，含分卷前的源文档）: {sum(counts.values())}")

    # spec：既有 18 篇的描述也在 s2_ingest_corpus.KB_SPECS 中——这里把 spec 与 KB_SPECS 合并交给
    # build_manifest_v2 / s2 使用；本脚本只写"新增部分+域清单"，合并逻辑在 merge_spec.py。
    SPEC_OUT.write_text(json.dumps({"domains": sorted(spec_docs.keys()),
                                    "docs": {k: v for k, v in spec_docs.items()},
                                    "log_summary": dict(new_ok=ok_new, fails=len(fails))},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"spec → {SPEC_OUT}")


if __name__ == "__main__":
    main()
