# -*- coding: utf-8 -*-
"""Stage 2 — 全量语料入库（8 KB，域=KB、主题=分组、描述=逐文档）。

行为：
  · 文本文档（.txt/.md/.xml）> SPLIT_CHARS(28_000) 自动分卷 "(part i of n)"（同生产库惯例）；
  · PDF 走 MinerU 解析链：parse_doc_batch → parse_task_status 轮询 → kb_doc_save_parsed(手动模式)；
  · 每库 kb_reindex；产物 artifacts/s2_ingest_report.json（kb_id/文档路径/解析字符数/分卷数）。
  · --dry-run 只列计划不执行。
运行: uv run --no-sync --directory kb-mcp python .../s2_ingest_corpus.py [--dry-run]
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
CORPUS = BASE.parents[2] / "corpus" / "multi-domain-docs-20261101"
SSE_URL = "http://127.0.0.1:8000/sse"
SPLIT_CHARS = 28_000
POLL_TIMEOUT = 600

KB_SPECS = [
    dict(slug="law-zh", name="MD语料-法律-中文", desc="数据与隐私法律全文：个保法/数安法/网安法",
         docs=[("law-zh/pipl_full.txt", "个人信息保护法.md", "个人信息处理规则：同意与撤回、敏感个人信息、自动化决策、处理者义务、法律责任"),
               ("law-zh/dsl_full.txt", "数据安全法.md", "数据安全制度：重要数据目录、数据安全审查、风险监测、政务数据安全开放"),
               ("law-zh/csl_full.txt", "网络安全法.md", "网络运行安全：等级保护制度、关键信息基础设施、网络信息安全与监测预警")]),
    dict(slug="gov-zh", name="MD语料-政务-中文", desc="国务院政府工作报告与五年规划纲要全文",
         docs=[("gov-zh/gov_work_report_2024.txt", "政府工作报告2024.md", "2024 年国务院政府工作报告全文：发展目标、新质生产力、民生与安全"),
               ("gov-zh/14th_five_year_plan.txt", "十四五规划纲要.md", "十四五规划纲要全文：2035 远景目标、科技自立自强、数字中国、区域协调")]),
    dict(slug="literature-zh", name="MD语料-文学-中文", desc="红楼梦早期回目（维基文库繁体）",
         docs=[(f"literature-zh/hongloumeng_hui{i:02d}.txt", f"红楼梦第{i:02d}回.md",
                d) for i, d in [
                   (1, "第一回：甄士隐梦幻识通灵，贾雨村风尘怀闺秀；通灵宝玉缘起、士隐赠银"),
                   (2, "第二回：贾夫人仙逝扬州城，冷子兴演说荣国府；贾府人物谱系"),
                   (3, "第三回：林黛玉抛父进京都；宝黛初会、宝玉赠字颦颦"),
                   (4, "第四回：薄命女偏逢薄命郎；葫芦僧判断葫芦案、护官符"),
                   (5, "第五回：贾宝玉神游太虚境；金陵十二钗判词、千红一窟茶")]]),
    dict(slug="literature-en", name="MD语料-文学-英文", desc="Gutenberg 公版整本小说",
         docs=[("literature-en/pride_and_prejudice_full.txt", "pride_and_prejudice.md",
                "Pride and Prejudice (full novel): Bennet family, Darcy and Elizabeth, entail of Longbourn"),
               ("literature-en/moby_dick_full.txt", "moby_dick.md",
                "Moby-Dick (full novel): Ishmael, Ahab, the Pequod, the white whale")]),
    dict(slug="science-en", name="MD语料-科学-英文", desc="完整论文 PDF（MinerU 解析链入库）",
         docs=[("science-en/attention_is_all_you_need.pdf", "attention_is_all_you_need.md",
                "Transformer (Vaswani 2017): multi-head self-attention, positional encoding, WMT14 SOTA"),
               ("science-en/bert_pretraining.pdf", "bert.md",
                "BERT (Devlin 2018): masked language model + next sentence prediction pretraining"),
               ("science-en/rag_lewis2020.pdf", "rag_lewis2020.md",
                "RAG (Lewis 2020): parametric memory + non-parametric retrieval hybrid generation")]),
    dict(slug="medicine-en", name="MD语料-医学-英文", desc="EuropePMC 开放获取综述全文（JATS XML）",
         docs=[("medicine-en/sepsis_biomarkers_review_oa.xml", "sepsis_biomarkers_review.md",
                "Sepsis biomarkers review: procalcitonin, CRP, presepsin, diagnostic performance"),
               ("medicine-en/covid_sequelae_review_oa.xml", "covid_sequelae_review.md",
                "Post-COVID condition review: long-term sequelae, persistent symptoms, organ involvement")]),
    dict(slug="tech-en", name="MD语料-技术-英文", desc="Kubernetes 官方文档完整章节",
         docs=[("tech-en/k8s_nodes.md", "k8s_nodes.md", "Kubernetes node anatomy: kubelet, container runtime, node status/management"),
               ("tech-en/k8s_cloud_controller.md", "k8s_cloud_controller.md", "cloud-controller-manager: cloud provider integration, node/lifecycle/route controllers"),
               ("tech-en/k8s_controller.md", "k8s_controller.md", "Kubernetes controllers: reconciliation loop, controller-manager patterns"),
               ("tech-en/k8s_components.md", "k8s_components.md", "Cluster components: control plane vs node components"),
               ("tech-en/k8s_pss.md", "k8s_pss.md", "Pod Security Standards: Privileged / Baseline / Restricted profiles")]),
    dict(slug="history-zh", name="MD语料-历史-中文", desc="史记完整篇目（维基文库繁体）",
         docs=[("history-zh/shiji_xiangyu_benji.txt", "史记项羽本纪.md", "项羽本纪：巨鹿之战、垓下之围、力拔山兮氣蓋世、乌江自刎"),
               ("history-zh/shiji_chanshe_shijia.txt", "史记陈涉世家.md", "陈涉世家：傭耕壟上、大泽乡起义、燕雀安知鸿鹄之志")]),
]


def cj(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content]}


def plan_actions():
    """列出计划动作（--dry-run 用）：入库分卷预估 + PDF 解析清单。"""
    plans = []
    for spec in KB_SPECS:
        for fp, name, desc in spec["docs"]:
            p = CORPUS / fp
            if not p.exists():
                plans.append(dict(kb=spec["slug"], file=fp, action="SKIP-MISSING"))
                continue
            if p.suffix.lower() == ".pdf":
                plans.append(dict(kb=spec["slug"], file=fp, action="parse_doc_batch->save_parsed"))
                continue
            n = len((p.read_text(encoding="utf-8", errors="replace")).encode("utf-8"))
            parts = max(1, -(-n // SPLIT_CHARS))
            plans.append(dict(kb=spec["slug"], file=fp, bytes=n,
                              action="kb_doc_create" if parts == 1 else f"split into {parts} parts"))
    return plans


async def run(dry: bool):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ART.mkdir(parents=True, exist_ok=True)
    if dry:
        plans = plan_actions()
        (ART / "s2_dryrun_plan.json").write_text(
            json.dumps(plans, ensure_ascii=False, indent=2), encoding="utf-8")
        for x in plans:
            print(f"{x['action']:34s} {x['kb']:14s} {Path(x['file']).name}")
        print(f"\n{len(plans)} planned actions → artifacts/s2_dryrun_plan.json")
        return
    report = dict(kbs={}, pdf_tasks=[], started=time.strftime("%Y-%m-%d %H:%M:%S"))
    async with sse_client(SSE_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            pdfs_all = []
            for spec in KB_SPECS:
                d = cj(await s.call_tool("kb_create", {"name": spec["name"], "description": spec["desc"]}))
                kb_id = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
                entry = dict(kb_id=kb_id, docs=[], parts=0)
                text_files = [x for x in spec["docs"] if not x[0].lower().endswith(".pdf")]
                pdf_files = [x for x in spec["docs"] if x[0].lower().endswith(".pdf")]
                for fp, name, desc in text_files:
                    p = CORPUS / fp
                    if not p.exists():
                        entry["docs"].append(dict(file=fp, ok=False, error="missing")); continue
                    content = p.read_text(encoding="utf-8", errors="replace")
                    n = len(content.encode("utf-8"))
                    if n <= SPLIT_CHARS:
                        dd = cj(await s.call_tool("kb_doc_create", {
                            "kb_id": kb_id, "name": name, "content": content, "description": desc}))
                        ok = bool(dd.get("success") or dd.get("files"))
                        entry["docs"].append(dict(file=fp, name=name, ok=ok, bytes=n))
                        entry["parts"] += 1
                    else:  # 分卷（同生产库 " (part i of n)" 惯例），每卷共享同一描述
                        chunks = [content[i:i + SPLIT_CHARS] for i in range(0, len(content), SPLIT_CHARS)]
                        total = len(chunks)
                        stem = Path(name).stem
                        for i, ch in enumerate(chunks, start=1):
                            part_name = f"{stem} (part {i} of {total}).md"
                            dd = cj(await s.call_tool("kb_doc_create", {
                                "kb_id": kb_id, "name": part_name, "content": ch,
                                "description": f"[{i}/{total}] {desc}"}))
                            entry["docs"].append(dict(file=fp, name=part_name,
                                                      ok=bool(dd.get("success") or dd.get("files")),
                                                      bytes=len(ch.encode("utf-8"))))
                        entry["parts"] += total
                pdfs_all += [(spec["name"], kb_id, fp, name, desc) for fp, name, desc in pdf_files]
                rr = cj(await s.call_tool("kb_reindex", {"kb_id": kb_id}))
                entry["reindex_ok"] = bool(rr.get("success", False))
                report["kbs"][spec["name"]] = entry
                print(f"ingest {spec['slug']:14s} kb={kb_id[:8]} parts={entry['parts']} "
                      f"reindex={entry['reindex_ok']}", flush=True)
            # PDF 解析链（批量提交 → 轮询 → 逐件 save_parsed）
            if pdfs_all:
                paths = [str(CORPUS / fp) for _, _, fp, _, _ in pdfs_all]
                d = cj(await s.call_tool("parse_doc_batch", {"file_paths": paths, "use_ocr": True}))
                task_id = d.get("task_id", "")
                report["pdf_tasks"].append(task_id)
                print(f"pdf parse task={task_id} files={len(paths)}", flush=True)
                md_by_src, done = {}, False
                for _ in range(int(POLL_TIMEOUT / 4)):
                    await asyncio.sleep(4)
                    d = cj(await s.call_tool("parse_task_status", {"task_id": task_id}))
                    st = str(d.get("status", "")).lower()
                    if st in ("done", "completed", "success", "finished", "error", "failed"):
                        done = st in ("done", "completed", "success", "finished")
                        res = d.get("result") if isinstance(d.get("result"), dict) else {}
                        for r_ in res.get("results") or d.get("results") or []:
                            src = r_.get("source_filename") or ""
                            md_by_src[src] = r_.get("markdown_path") or ""
                        break
                for spec_name, kb_id, fp, name, desc in pdfs_all:
                    src = Path(fp).name
                    md = md_by_src.get(src, "")
                    ok = False
                    if done and md:
                        dd = cj(await s.call_tool("kb_doc_save_parsed", {
                            "parent_id": report["kbs"][spec_name]["kb_id"],
                            "markdown_path": md, "source_filename": src, "description": desc}))
                        files = dd.get("files") or []
                        ok = bool(dd.get("success") and files)
                        if files:
                            report["kbs"][spec_name]["docs"].append(
                                dict(file=fp, name=files[0].get("name"), path=files[0].get("path"),
                                     ok=True, parsed_chars=len((Path(md).read_text(encoding='utf-8', errors='replace')))))
                    if not ok:
                        report["kbs"][spec_name]["docs"].append(dict(file=fp, ok=False, error="parse/save failed"))
                    print(f"pdf {src} saved={ok} chars={report['kbs'][spec_name]['docs'][-1].get('parsed_chars')}", flush=True)
                # PDF 落库后重建对应库索引
                for spec_name in {sn for sn, _, _, _, _ in pdfs_all}:
                    cj(await s.call_tool("kb_reindex", {"kb_id": report["kbs"][spec_name]["kb_id"]}))
    (ART / "s2_ingest_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(e["parts"] for e in report["kbs"].values())
    bad = [d for e in report["kbs"].values() for d in e["docs"] if not d.get("ok")]
    print(f"\n=== S2 done: KBs={len(report['kbs'])} parts={total} failures={len(bad)}")
    if bad:
        print(json.dumps(bad, ensure_ascii=False)[:600])


if __name__ == "__main__":
    asyncio.run(run(dry="--dry-run" in sys.argv))
