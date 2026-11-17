# -*- coding: utf-8 -*-
"""生成语料 manifest + 金标问题（证据行由脚本在原文中实测命中，不凭记忆编造）。

金标问题集设计：
  每篇文档 2 题（per-doc 单文档证据题）+ 跨域路由题若干（catalog 层用）。
  每题 {id, domain, doc, question(改写前口语), keywords, evidence_substr}——
  evidence_substr 必须在下载文本中 grep 命中，否则 manifest 构建即失败（防编造）。

运行: python D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/experiment-redesign-20261101/scripts/build_manifest.py
"""
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"

# 金标证据串（构建时会逐一在原文中验证；路径/全文版本相关，宁短勿长）
GOLD = [
    # ── 法律-ZH：个保法 ──
    dict(id="L-pipl-1", domain="law-zh", doc="law-zh/pipl_full.txt",
         question="我在 App 上注册时被强制同意提供通讯录，这种“不得过度收集”的原则写在第几条？",
         keywords=["个人信息保护法", "最小范围"], evidence_substr="处理个人信息应当具有明确、合理的目的"),
    dict(id="L-pipl-2", domain="law-zh", doc="law-zh/pipl_full.txt",
         question="个人有权撤回同意吗？撤回之后处理者怎么办？",
         keywords=["撤回同意", "便捷方式"], evidence_substr="基于个人同意处理个人信息的，个人有权撤回其同意"),
    # ── 法律-ZH：数安法 ──
    dict(id="L-dsl-1", domain="law-zh", doc="law-zh/dsl_full.txt",
         question="数据安全法里“重要数据”的目录由谁来制定？",
         keywords=["重要数据目录", "国家数据安全工作协调机制"], evidence_substr="国家数据安全工作协调机制统筹协调有关部门制定重要数据目录"),
    # ── 法律-ZH：网安法 ──
    dict(id="L-csl-1", domain="law-zh", doc="law-zh/csl_full.txt",
         question="网络安全等级保护制度的第几条规定的？关键信息基础设施运营者的额外义务有哪些？",
         keywords=["等级保护制度", "关键信息基础设施"], evidence_substr="国家实行网络安全等级保护制度"),
    # ── 政务-ZH：政府工作报告 ──
    dict(id="G-gwr-1", domain="gov-zh", doc="gov-zh/gov_work_report_2024.txt",
         question="2024 年政府工作报告设定的 GDP 增长目标是多少？",
         keywords=["国内生产总值增长", "5%左右"], evidence_substr="国内生产总值增长5%左右"),
    dict(id="G-gwr-2", domain="gov-zh", doc="gov-zh/gov_work_report_2024.txt",
         question="报告里关于“新质生产力”要推进哪些具体产业方向？",
         keywords=["新质生产力"], evidence_substr="大力推进现代化产业体系建设，加快发展新质生产力"),
    # ── 政务-ZH：十四五规划 ──
    dict(id="G-fyp-1", domain="gov-zh", doc="gov-zh/14th_five_year_plan.txt",
         question="十四五规划提出的 2035 年人均 GDP 达到什么水平的目标？",
         keywords=["人均国内生产总值达到中等发达国家水平"], evidence_substr="人均国内生产总值达到中等发达国家水平"),
    # ── 文学-ZH：红楼梦（wikisource 提取为繁体，证据串用繁体） ──
    dict(id="F-hlm-1", domain="literature-zh", doc="literature-zh/hongloumeng_hui01.txt",
         question="甄士隐资助贾雨村进京赶考时给了多少银子和衣物？",
         keywords=["五十兩白銀", "兩套冬衣"], evidence_substr="五十兩白銀，并兩套冬衣"),
    dict(id="F-hlm-2", domain="literature-zh", doc="literature-zh/hongloumeng_hui03.txt",
         question="林黛玉进贾府时，宝玉送给她什么字（表字）？",
         keywords=["顰顰"], evidence_substr="莫若『顰顰』二字极妙"),
    dict(id="F-hlm-3", domain="literature-zh", doc="literature-zh/hongloumeng_hui05.txt",
         question="贾宝玉梦游太虚幻境时喝的茶叫什么名字？",
         keywords=["千紅一窟"], evidence_substr="此茶名曰『千紅一窟』"),
    # ── 文学-EN ──
    dict(id="F-pp-1", domain="literature-en", doc="literature-en/pride_and_prejudice_full.txt",
         question="What yearly income does Mrs Bennet attribute to the single man at the beginning?",
         keywords=["four or five thousand a year"], evidence_substr="four or five thousand a year"),
    dict(id="F-md-1", domain="literature-en", doc="literature-en/moby_dick_full.txt",
         question="What does Ishmael use as his substitute for a pillow at the Spouter-Inn?",
         keywords=["whale line", "harpoon"], evidence_substr="cannon-ball"),
    # ── 历史-ZH：史记（繁体） ──
    dict(id="H-sj-1", domain="history-zh", doc="history-zh/shiji_xiangyu_benji.txt",
         question="项羽垓下之围时作的绝命诗首句是什么？",
         keywords=["力拔山兮氣蓋世"], evidence_substr="力拔山兮氣蓋世"),
    dict(id="H-sj-2", domain="history-zh", doc="history-zh/shiji_chanshe_shijia.txt",
         question="陈胜说“燕雀安知鸿鹄之志”时他在做什么营生？",
         keywords=["傭耕", "輟耕之壟上"], evidence_substr="陳涉少時，嘗與人傭耕"),
    # ── 科学-EN（PDF：二进制，evidence 在解析入库后由 parse 管线验证，evidence_hit 记 pending） ──
    dict(id="S-attn-1", domain="science-en", doc="science-en/attention_is_all_you_need.pdf",
         question="What self-attention mechanism does the Transformer use?",
         keywords=["multi-head self-attention"], evidence_substr="Attention Is All You Need",
         evidence_pending="pdf-parse"),
    dict(id="S-bert-1", domain="science-en", doc="science-en/bert_pretraining.pdf",
         question="What are the two pretraining strategies of BERT?",
         keywords=["masked language model", "next sentence prediction"], evidence_substr="Masked Language Model",
         evidence_pending="pdf-parse"),
    # ── 技术-EN ──
    dict(id="T-k8s-1", domain="tech-en", doc="tech-en/k8s_nodes.md",
         question="What are the two main components running on a Kubernetes node?",
         keywords=["kubelet", "container runtime"], evidence_substr="container runtime"),
    dict(id="T-k8s-2", domain="tech-en", doc="tech-en/k8s_pss.md",
         question="What are the three Pod Security Standards profiles?",
         keywords=["Privileged", "Baseline", "Restricted"], evidence_substr="Baseline"),
    # ── 医学-EN（XML 全文） ──
    dict(id="M-sep-1", domain="medicine-en", doc="medicine-en/sepsis_biomarkers_review_oa.xml",
         question="Which sepsis biomarker does the review highlight as most established for diagnosis?",
         keywords=["procalcitonin", "PCT"], evidence_substr="procalcitonin"),
    dict(id="M-covid-1", domain="medicine-en", doc="medicine-en/covid_sequelae_review_oa.xml",
         question="What is the formal term for long-term symptoms after COVID-19?",
         keywords=["post-acute sequelae"], evidence_substr="post-acute sequelae"),
]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    docs = []
    golds = []
    failures = []
    seen_docs = {}
    for g in GOLD:
        p = CORPUS / g["doc"]
        if not p.exists():
            failures.append({**g, "error": "doc missing"})
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if g.get("evidence_pending"):
            hit = None  # PDF 二进制：入库解析后由管线验证
        else:
            hit = g["evidence_substr"] in text
        info = seen_docs.get(g["doc"])
        if info is None:
            b = p.stat().st_size
            info = seen_docs[g["doc"]] = dict(
                path=g["doc"], domain=g["domain"], bytes=b,
                sha256_head=hashlib.sha256(p.read_bytes()[:65536]).hexdigest()[:16])
            docs.append(info)
        if hit is False:
            failures.append({**g, "error": "evidence_substr NOT found in text"})
        golds.append({**g, "evidence_hit": hit, "doc_bytes": info["bytes"]})

    manifest = dict(
        name="multi-domain-complete-docs-20261101",
        design="8 域中英双语·完整文档（整部法律/整回小说/整篇论文/整章官方文档），支持解析入库+书架分组+逐级检索",
        corpus_root=str(CORPUS),
        docs=docs,
        gold_questions=golds,
        external=dict(
            qasper="external-datasets/qasper/（1585 篇完整 NLP 论文全文 + 5049 问答 + evidence 段落标注；dev 11MB/train 32MB）",
            usage="消融与基线的现成金标源：qasper-dev 抽样 20-40 题（answerable + unanswerable 混合）",
        ),
    )
    out = BASE.parent / "artifacts" / "manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"docs={len(docs)} gold_questions={len(golds)} evidence_failures={len(failures)}")
    for f in failures:
        print("  FAIL:", f["id"], f["error"][:80])
    print(f"manifest → {out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
