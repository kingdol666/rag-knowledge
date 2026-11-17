# -*- coding: utf-8 -*-
"""路由层归因实验：内容归纳版目录卡 vs 来源标签版目录卡。

用户假设：A0 失败主因 = 目录卡是"来源/格式标签"而非"内容归纳"。
验证：同机制、同题集，仅替换目录卡为按实际文档主题撰写的内容归纳版（中英双语、
每库覆盖其真实文档的关键词），重跑 70 题路由 → 路由正确率对比；
并对原 32 道误路由 gold 题补跑 A0 全链（search→judge）看 gold 恢复。

运行: uv run --no-sync --directory kb-mcp python .../s8_route_v2.py
产出: artifacts/s8_route_v2.json
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client

ROOT = Path(r'D:/codes/ClaudeGPT/rag_project/rag-knowledge')
BASE = ROOT / 'review/experiment-redesign-20261101'
ART = BASE / 'artifacts'
SSE_URL = "http://127.0.0.1:8000/sse"

# 内容归纳版目录卡：基于每库真实文档清单的主题归纳（中英双语关键词，均衡长度）
ENRICHED = {
    "law-zh": "中国法律法规全文库：个人信息保护法（同意与撤回、敏感个人信息、自动化决策）、数据安全法（重要数据目录、数据安全审查）、网络安全法（等级保护制度、关键信息基础设施）、反垄断法、专利法、商标法、著作权法、电子商务法、反不正当竞争法、消费者权益保护法、食品安全法、密码法",
    "gov-zh": "中国政府政策文件全文：2020-2025 年国务院政府工作报告（GDP 增长目标 5%左右、新质生产力、产业政策、民生保障）、十四五规划纲要（2035 年远景目标、人均国内生产总值达到中等发达国家水平、科技自立自强、数字中国）",
    "literature-zh": "中国古典文学《红楼梦》前十二回全文（繁体原文）：甄士隐梦幻识通灵、贾雨村风尘怀闺秀、赠银五十两、林黛玉抛父进京都、贾宝玉初见赠字颦颦、太虚幻境千红一窟、护官符、元妃省亲",
    "literature-en": "English classic novels, full texts: Pride and Prejudice (Mr Bennet, Darcy, Elizabeth, Longbourn entail, four or five thousand a year), Moby Dick (Ishmael, Captain Ahab, the white whale, Spouter-Inn), Frankenstein, Jane Eyre, Alice's Adventures in Wonderland, Sherlock Holmes, Treasure Island, The Time Machine, Dracula, The Great Gatsby, The Metamorphosis (Gregor), The War of the Worlds, A Tale of Two Cities (It was the best of times), Great Expectations (Pip), The Picture of Dorian Gray, Huckleberry Finn, The Odyssey, Sense and Sensibility, Anna Karenina",
    "science-en": "AI and machine learning research papers (full PDFs): Attention Is All You Need (Transformer multi-head self-attention), BERT (masked language model, next sentence prediction), ResNet (deep residual learning for image recognition), GAN (generative adversarial networks), VAE (auto-encoding variational Bayes), word2vec word representations, CLIP (natural language supervision), DDPM denoising diffusion, T5 text-to-text transfer learning, RoBERTa, Swin Transformer, GPT-3 few-shot learners, InstructGPT (training with human feedback), LLaMA open foundation models, RAG retrieval-augmented generation (Lewis 2020)",
    "medicine-en": "Medical open-access review articles (full text): sepsis biomarkers (procalcitonin, CRP, presepsin), COVID-19 post-acute sequelae (long COVID), diabetes mellitus management (glucose), cancer immunotherapy, Alzheimer disease biomarkers, cardiovascular imaging, gut microbiome, mRNA vaccines, obesity pharmacotherapy, telemedicine outcomes, CRISPR gene editing, tuberculosis treatment, malaria vaccine, asthma biologics, stroke thrombolysis",
    "tech-en": "Kubernetes official documentation chapters: nodes (kubelet, container runtime, node status), controllers and reconciliation, cloud-controller-manager, cluster components (control plane), Pod Security Standards (Privileged / Baseline / Restricted profiles), storage classes and dynamic provisioning, ephemeral volumes, projected volumes, service accounts, security checklist, secrets good practices, pod management",
    "history-zh": "《史记》完整篇目（繁体原文）：项羽本纪（垓下之围、力拔山兮气盖世、乌江自刎）、高祖本纪、吕太后本纪、孔子世家、萧相国世家（萧何）、留侯世家（张良）、淮阴侯列传（韩信）、李将军列传（李广）、货殖列传、陈涉世家（燕雀安知鸿鹄之志、大泽乡起义、傭耕壟上）",
    "philosophy-en": "Western philosophy classics, full texts: Marcus Aurelius Meditations (Stoicism), Plato The Republic (justice, the ideal state), Machiavelli The Prince (principalities, power), Nietzsche Thus Spoke Zarathustra and Beyond Good and Evil, Sun Tzu The Art of War (military strategy), Thoreau Walden, Thomas Paine Common Sense",
    "economics-en": "Economics classics, full texts: Adam Smith The Wealth of Nations (division of labour, markets), Veblen The Theory of the Leisure Class (conspicuous consumption), John Stuart Mill On Liberty, Malthus An Essay on the Principle of Population",
}


def cj(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content]}


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    spec = json.loads((ART / "corpus_spec_final.json").read_text(encoding="utf-8"))
    questions = [json.loads(l) for l in
                 (ART / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    questions = [q for q in questions if not q.get("needs_expansion")]
    kb_slug = {m["slug"]: m for m in spec}
    slug_by_name = {}

    async with sse_client(SSE_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            dl = cj(await s.call_tool("kb_list", {"lightweight": True}))
            kb_id_by_slug = {}
            for m in spec:
                for k in (dl.get("catalog") or []):
                    if k.get("name") == m["kb_name"]:
                        kb_id_by_slug[m["slug"]] = k["kb_id"]

            # ── 内容归纳版目录卡 ──
            d = cj(await s.call_tool("kb_create", {
                "name": f"路由目录卡-内容归纳-{time.strftime('%H%M%S')}",
                "description": "内容归纳版目录卡（按各库真实文档主题归纳，中英双语；实验后删除）"}))
            ckb = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
            for slug, desc in ENRICHED.items():
                nm = kb_slug[slug]["kb_name"]
                cj(await s.call_tool("kb_doc_create", {
                    "kb_id": ckb, "name": f"{slug}.md",
                    "content": f"# {nm}\n\n{desc}", "description": desc}))
            rr = cj(await s.call_tool("kb_reindex", {"kb_id": ckb}))
            rt = rr.get("task_id")
            if rt:
                for _ in range(30):
                    await asyncio.sleep(2)
                    ts_ = cj(await s.call_tool("kb_task_status", {"task_id": rt}))
                    if str(ts_.get("status", "")).lower() in ("done", "completed", "success", "finished"):
                        break
            for _ in range(15):
                await asyncio.sleep(2)
                pd = cj(await s.call_tool("kb_search_vector", {
                    "query": "法律 数据安全", "kb_id": ckb, "top_k": 2, "score_threshold": 0.2}))
                if pd.get("results"):
                    break

            # ── 全量重路由 ──
            results = []
            for q in questions:
                rd = cj(await s.call_tool("kb_search_vector", {
                    "query": q["question"], "kb_id": ckb,
                    "top_k": 2, "score_threshold": 0.2, "slim": True}))
                rh = rd.get("results") or []
                route = Path(str(rh[0].get("doc_path") or "?")).stem.replace(".md", "") if rh else ""
                ok = (route == q.get("domain")) if q.get("domain") else None
                results.append(dict(qid=q["id"], question=q["question"][:40],
                                    route=route, correct=ok))
                print(f"{q['id'][:26]:26s} -> {route:14s} correct={ok}", flush=True)

            gold_rows = [r for r in results if r["correct"] is not None]
            acc = sum(1 for r in gold_rows if r["correct"])
            print(f"\n=== 内容归纳版路由正确率: {acc}/{len(gold_rows)} = {acc/max(len(gold_rows),1)*100:.0f}%  （旧来源标签版 52%）")

            # ── 对旧版误路由的 gold 题补跑 A0 全链（search→judge）──
            old_rows = [json.loads(l) for l in
                        open(ART / "s4_checkpoint.jsonl", encoding="utf-8")]
            old_a0 = {r["qid"]: r for r in old_rows if r["arm"] == "A0"}
            prev_wrong = [q for q in questions
                          if q["id"] in old_a0 and old_a0[q["id"]].get("route_correct") is False
                          and q.get("kind") == "gold"]
            print(f"补跑原误路由 gold 题: {len(prev_wrong)}", flush=True)
            recovered = 0
            detail = []
            for q in prev_wrong:
                rd = cj(await s.call_tool("kb_search_vector", {
                    "query": q["question"], "kb_id": kb_id_by_slug.get(q.get("domain"), ""),
                    "top_k": 30, "score_threshold": 0.35, "balance_kbs": True, "slim": True}))
                hits = rd.get("results") or []
                best = {}
                for h in hits:
                    dp = (h.get("doc_path") or h.get("path") or "?").replace("\\", "/")
                    sc = h.get("score", 0) or 0
                    if dp not in best or sc > best[dp][0]:
                        best[dp] = (sc, h.get("content", ""))
                ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:6]
                refs = json.dumps([{"kb_id": kb_id_by_slug.get(q.get("domain"), ""), "doc_path": dp}
                                   for dp, _ in ranked], ensure_ascii=False)
                jd = cj(await s.call_tool("kb_laya_judge", {
                    "query": q["question"], "documents": refs,
                    "criterion": "auto", "include_text": False}))
                pack = jd.get("evidence_pack") or ""
                gold_hit = bool(q.get("gold_evidence")) and q["gold_evidence"] in pack
                recovered += bool(gold_hit)
                detail.append(dict(qid=q["id"], route=q.get("domain"),
                                   gold_hit=gold_hit, pack_bytes=len(pack.encode('utf-8'))))
                print(f"  recheck {q['id'][:30]:30s} gold={gold_hit} pack={len(pack.encode('utf-8'))}B", flush=True)

            out = dict(
                enriched_route_acc=f"{acc}/{len(gold_rows)}",
                old_route_acc="34/66 (52%)",
                prev_wrong_n=len(prev_wrong), recovered=recovered, detail=detail,
                per_q=results)
            (ART / "s8_route_v2.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            if ckb:
                cj(await s.call_tool("kb_delete", {"kb_id": ckb}))
                print("catalog v2 deleted", flush=True)
            print(f"=== 误路由题 gold 恢复: {recovered}/{len(prev_wrong)}")


if __name__ == "__main__":
    asyncio.run(main())
