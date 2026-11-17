"""Download legally open-access PDFs of Knowledge-Based Systems papers that are
topically / genre-wise close to the HMRS manuscript.

Sources tried, in order:
  1. OpenAlex per-DOI `locations[*].pdf_url` (arXiv, institutional repositories)
  2. OpenAlex `best_oa_location.pdf_url`
  3. Semantic Scholar `openAccessPdf.url`
  4. arXiv id from externalIds / locations
ScienceDirect is deliberately NOT scraped (403 here, and bypassing it is not OK).
Every saved file is verified: %PDF magic, >= 30 KB, and no HTML error body.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "reference" / "kbs"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (HMRS literature review; mailto:lit@example.org)"}

# (filename slug, DOI, tier, why-it-matters)
SHORTLIST = [
    ("SoftwareRefArch_JournalisticKnowledgePlatforms_2023",
     "10.1016/j.knosys.2023.110750", "A",
     "软件参考架构 + 知识平台；与 HMRS 'P1-P5 设计原则 + 模块契约' 的文体最接近"),
    ("RAG_EngineeringDesignKnowledge_2024",
     "10.1016/j.knosys.2024.112410", "B",
     "工程设计知识上的 RAG 部署案例；HMRS 'deployed industrial case study' 的同类文体"),
    ("Survey_LLM_KnowledgeBasedMethods_2025",
     "10.1016/j.knosys.2025.113503", "B",
     "KBS 本刊 LLM×知识方法综述（109 引）；Related Work 定位锚点"),
    ("KnowledgeRetrieval_InContextLearning_SemanticSearch_2025",
     "10.1016/j.knosys.2025.113047", "B",
     "知识检索 + 语义搜索系统；对应 HMRS 三车道召回层"),
    ("XAI_MetaSurvey_2023",
     "10.1016/j.knosys.2023.110273", "B",
     "KBS 高引 XAI 元综述（945 引）；支撑 inspectable evidence 的论证"),
    ("LLM_Oracles_OntologyInstantiation_2025",
     "10.1016/j.knosys.2024.112940", "B",
     "LLM 实例化领域本体；对应内容路由组织与知识层构建"),
    ("PrivateLibrary_CodeGeneration_LLM_2025",
     "10.1016/j.knosys.2025.113934", "B",
     "私有库检索增强代码生成；对应自托管语料 + 库内证据"),
    ("SoftPrompt_DenseRetrieval_2024",
     "10.1016/j.knosys.2024.112758", "B",
     "稠密检索增强；对应 HMRS 的向量召回基线讨论"),
    ("Coordinated_LLM_MultiAgent_QA_2025",
     "10.1016/j.knosys.2025.114627", "A",
     "多智能体协同问答系统；对应 MCP 优先的机器接口与 harness 可插拔"),
    ("TreeQA_LLM_RAG_LogicTree_2025",
     "10.1016/j.knosys.2025.114526", "B",
     "可靠可解释多跳 RAG；与内容验证门的可解释裁决直接对标"),
    ("Building_OpenQA_LowResource_2024",
     "10.1016/j.knosys.2024.112243", "A",
     "构建 OpenQA 系统；系统实现与评测文体的范本"),
    ("FineGrained_StatefulKnowledgeExploration_2025",
     "10.1016/j.knosys.2025.114011", "A",
     "图检索 + LLM 的细粒度知识探索框架；对应 Librarian 分层导航"),
    ("Building_KnowledgeGrounded_Dialogue_2024",
     "10.1016/j.knosys.2024.111943", "A",
     "构建知识接地对话系统；系统设计与开发论文"),
    ("HELIOT_LLM_CDSS_2025",
     "10.1016/j.knosys.2025.114184", "A",
     "LLM 临床决策支持系统；领域知识库 + 可信输出"),
    ("Hallucinations_Observability_DualMemoryKG_2026",
     "10.1016/j.knosys.2026.115469", "B",
     "幻觉治理 + 可观测性 + 双记忆知识图；最贴近 HMRS 诚实弃答与可审计性"),
    ("IntermediateTripleTable_VKG_Architecture_2025",
     "10.1016/j.knosys.2025.113179", "A",
     "虚拟知识图的通用架构；架构型论文范本"),
    ("GOFAI_Meets_GenerativeAI_ExpertSystems_2026",
     "10.1016/j.knosys.2026.116657", "A",
     "用 LLM 开发专家系统；知识系统工程化"),
    ("Optimising_RAG_GrowingWindowChunking_2025",
     "10.1016/j.knosys.2025.114896", "B",
     "RAG 系统分块策略优化；对应 HMRS 语义切分门"),
    ("LLM_HarmonizedDataIngestion_Dataspace_2026",
     "10.1016/j.knosys.2026.115800", "A",
     "异构数据源自动摄取系统；对应 HMRS 九步摄入管线"),
    ("DamageRAG_BenchmarkDiagnose_MultiHopRAG_2026",
     "10.1016/j.knosys.2026.117231", "B",
     "多跳 RAG 的基准 + 诊断；与 HMRS '验证器失效诊断' 的负结果写法同类"),
    ("KG_Orchestra_OpenSource_MultiAgent_Framework_2026",
     "10.1016/j.knosys.2026.117316", "A",
     "开源多智能体框架 + 证据驱动知识图；文体与技术形态双重贴近"),
    ("QueCo_Consensus_UnverifiedEvidence_2026",
     "10.1016/j.knosys.2026.116771", "B",
     "未验证证据上的查询条件共识；对应验证门前的证据不确定性"),
    ("GeneratingKG_MultiAgent_ClaimAttribution_2026",
     "10.1016/j.knosys.2026.116890", "B",
     "多智能体声明抽取 + 归因；对应 per-citation provenance"),
    # ---- batch 2: more system/deployed-IR papers found by full-corpus scan ----
    ("LLM_IR_System_BankSupervisors_2024",
     "10.1016/j.knosys.2024.112914", "A",
     "面向银行监管者的 LLM 检索系统；与 HMRS 同为'部署型 IR 系统'工业案例"),
    ("Practical_PrivacyPreserving_Framework_LLM_Services_2026",
     "10.1016/j.knosys.2026.115347", "A",
     "真实 LLM 服务的实用框架；工程约束与部署设计"),
    ("MSDiagnosis_Benchmark_Framework_MultiStepClinical_2025",
     "10.1016/j.knosys.2025.114524", "A",
     "基准 + 框架 + 多步推理评测；与 HMRS 分层评测设计同源"),
    ("SigOpt_Mulch_IntelligentSystem_AutoML_2023",
     "10.1016/j.knosys.2023.110604", "A",
     "智能系统构建与自动化评测；系统工程文体"),
    ("QueryExpansion_SemanticRelations_RetrievalSystems_2023",
     "10.1016/j.knosys.2023.111183", "B",
     "查询扩展对检索系统的影响评测；对应 HMRS 查询改写层"),
    ("Automating_EngineeringModeling_LLM_Agents_2026",
     "10.1016/j.knosys.2026.115989", "A",
     "工程应用中的 LLM Agent 自动化系统；工业部署视角"),
    ("GeoFuB_OperatorFunction_KnowledgeBase_2025",
     "10.1016/j.knosys.2025.113624", "B",
     "领域知识库自动构建；对应内容路由组织与元数据派生"),
    ("InformationTheoretic_DualMemory_System_2025",
     "10.1016/j.knosys.2025.113913", "B",
     "双记忆系统设计；对应长期记忆/经验层"),
    ("LGMT_ReasoningReliability_Testing_2026",
     "10.1016/j.knosys.2026.116324", "B",
     "LLM 推理可靠性的逻辑接地测试；对应验证器失效诊断"),
    ("FinBloom_KnowledgeGrounding_RealtimeData_2026",
     "10.1016/j.knosys.2026.115559", "B",
     "实时数据知识接地；对应证据新鲜度与来源可追溯"),
    ("Prompting_LLM_KG_LongTailFacts_QA_2025",
     "10.1016/j.knosys.2025.113648", "B",
     "长尾事实问答中的知识图提示；对标跨库检索"),
    ("LLM_Understand_KnowledgeGraphs_2025",
     "10.1016/j.knosys.2025.113060", "B",
     "LLM 与知识图交互能力；支撑知识层设计讨论"),
    ("Enhancing_LLM_Systems_CircuitAnalysis_2026",
     "10.1016/j.knosys.2026.117171", "A",
     "端到端 LLM 系统增强；系统工程方法"),
    # NOT KBS: open design-science precursor of the reference-architecture paper
    ("COMPANION_Developing_SoftwareRefArch_JKP_CEUR2021",
     "", "A",
     "[非 KBS，配套] 同一作者团队的软件参考架构设计科学方法前驱论文（CEUR-WS 开放获取）"),
]

# Forced URLs for items whose OpenAlex OA record is a DOI/ScienceDirect link only,
# or whose preprint lives on a different server.
OVERRIDES = {
    "KG_Orchestra_OpenSource_MultiAgent_Framework_2026": [
        "https://www.biorxiv.org/content/10.64898/2026.02.18.706536v1.full.pdf",
    ],
    "COMPANION_Developing_SoftwareRefArch_JKP_CEUR2021": [
        "https://ceur-ws.org/Vol-2978/saml-paper2.pdf",
    ],
}


def fetch_json(url: str, timeout: int = 40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def oa_candidates(doi: str) -> tuple[list[str], dict]:
    urls: list[str] = []
    meta = {}
    try:
        w = fetch_json("https://api.openalex.org/works/https://doi.org/" +
                       urllib.parse.quote(doi, safe="/"))
        meta = {"title": w.get("title"), "year": w.get("publication_year"),
                "citations": w.get("cited_by_count"),
                "authors": [a["author"]["display_name"]
                            for a in (w.get("authorships") or [])][:8],
                "oa": (w.get("open_access") or {}).get("is_oa")}
        for loc in (w.get("locations") or []):
            u = loc.get("pdf_url")
            if u and u not in urls:
                urls.append(u)
        b = (w.get("best_oa_location") or {}).get("pdf_url")
        if b and b not in urls:
            urls.insert(0, b)
        for loc in (w.get("locations") or []):
            land = loc.get("landing_page_url") or ""
            m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})", land)
            if m:
                u = "https://arxiv.org/pdf/" + m.group(1)
                if u not in urls:
                    urls.append(u)
    except Exception as e:
        meta["openalex_error"] = str(e)[:120]
    try:
        s = fetch_json("https://api.semanticscholar.org/graph/v1/paper/DOI:" +
                       urllib.parse.quote(doi, safe="") +
                       "?fields=title,openAccessPdf,externalIds,year,citationCount")
        p = (s.get("openAccessPdf") or {}).get("url")
        if p and p not in urls:
            urls.append(p)
        ids = s.get("externalIds") or {}
        if ids.get("ArXiv"):
            u = "https://arxiv.org/pdf/" + ids["ArXiv"]
            if u not in urls:
                urls.append(u)
        if not meta.get("citations"):
            meta["citations"] = s.get("citationCount")
    except Exception:
        pass
    # deprioritise ScienceDirect (403 from this host) — but keep as last resort
    urls.sort(key=lambda u: ("sciencedirect.com" in u, "linkinghub" in u))
    return urls, meta


def try_download(url: str, dest: Path) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read(40 * 1024 * 1024)
        if not data.startswith(b"%PDF"):
            return False, f"not a PDF ({r.headers.get('Content-Type')}, {len(data)}B)"
        if len(data) < 30_000:
            return False, f"too small ({len(data)}B)"
        dest.write_bytes(data)
        return True, f"{len(data)}B"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:90]}"


def main():
    manifest = []
    for slug, doi, tier, why in SHORTLIST:
        dest = OUT / f"{tier}_{slug}.pdf"
        urls, meta = oa_candidates(doi) if doi else ([], {"title": why})
        forced = OVERRIDES.get(slug, [])
        urls = forced + [u for u in urls if u not in forced]
        ok, detail, used = False, "", ""
        if dest.exists() and dest.stat().st_size > 30_000 and dest.read_bytes()[:4] == b"%PDF":
            ok, used, detail = True, "cached", f"{dest.stat().st_size}B"
        else:
            for u in urls[:8]:
                good, d = try_download(u, dest)
                if good:
                    ok, used, detail = True, u, d
                    break
                detail = d
        entry = {"file": dest.name if ok else None, "doi": doi, "tier": tier,
                 "title": meta.get("title"), "year": meta.get("year"),
                 "citations": meta.get("citations"), "authors": meta.get("authors"),
                 "is_oa": meta.get("oa"), "why": why,
                 "downloaded": ok, "source_url": used or None,
                 "candidates_tried": len(urls[:8]), "note": None if ok else detail}
        manifest.append(entry)
        flag = "OK  " if ok else "MISS"
        print(f"[{flag}] {tier} {slug[:52]:52s} | {detail[:48]}")
        if ok:
            print(f"        <- {used[:110]}")
        time.sleep(0.25)

    (HERE / "kbs_download_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(e["downloaded"] for e in manifest)
    print(f"\n[done] {n}/{len(manifest)} PDFs saved to {OUT}")


if __name__ == "__main__":
    main()
