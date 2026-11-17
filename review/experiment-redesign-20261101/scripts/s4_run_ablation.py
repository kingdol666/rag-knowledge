# -*- coding: utf-8 -*-
"""Stage 4 — 消融实验执行器（机械臂；A1-readall 另有真实 agent 执行模式）。

臂：A0（逐级全开：描述路由→库内宽网→判卷）· A1-readall（逐篇通读，不启动检索）
    A1b（全局向量直搜）· A2（无证据门）· A3（无描述层，需 --prepare-a3 建对照库）
    优化轮新增：A0f（导航同 A0，判卷全窗口：自行取全卷 250K + inline content，
    根修参考模式 server 40K 抓取截断）· A0h（A0f + slim=False 全文 chunk top-8
    ∪ 判卷包，总帽 60K）· PD（精确逐文档：无导航，十库定向并集 top-6 → A0f 同款判卷）
复现纪律：A0 路由 = **描述路由器**（问题×库描述 bigram 重合度）——不使用金标 domain 字段
（防先验泄漏）；route_correct 单独记录作为 H3（描述层路由质量）数据。

trace 字段：calls / tool_seconds / bytes_ingested / llm_digest_seconds(=bytes÷rate) /
gold_hit / evidence_focus(证据字节÷全库字节) / first_hit_read_index(readall) /
is_refusal / route_slug+route_correct(A0/A0f/A0h) / distractor_docs(非金标域候选数) /
survivors / judge_mode(A0f/A0h/PD=inline_content 全窗口方案)。

用法（kb-mcp venv）:
  s4_run_ablation.py --questions artifacts/questions.jsonl --arms A0,A1-readall,A1b,A2 [--limit N]
  s4_run_ablation.py --prepare-a3                 # 构建无描述层对照库（A3 前置）
  s4_run_ablation.py --arms A3 --questions ...    # 在对照库上跑 A3
  s4_run_ablation.py --kb-prefix MD语料-          # 复用 S2 已建库（默认，避免重复解析 PDF）
"""
import asyncio
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts"
KBMCP_DIR = BASE.parents[2] / "kb-mcp"
STDIO_CMD = ["uv", "run", "--no-sync", "--directory", str(KBMCP_DIR), "python", str(KBMCP_DIR / "server.py")]
DEFAULT_DIGEST_RATE = 4000  # chars/s —— 735k tokens≈10min 的等效速率（--digest-rate 可调）

# ── 优化轮新臂（A0f/A0h/PD）常量 ─────────────────────────────────────────────
# A0f 判卷全窗口方案（已核验 kb-mcp/server.py kb_laya_judge）：
#   参考模式的 server 端 kb_doc_read 硬编码 max_chars=40000（~:3205）＝窗口截断主因；
#   但 documents 条目带 content 时跳过 server 抓取（legacy 模式，content given = no fetch），
#   且 max_evidence_chars 本就是工具参数（默认 40000）→ 无需改 server：
#   判卷前自行 kb_doc_read(max_chars=250000, limit=100000) 取全卷，inline 传入。
FULL_VIS_CHARS = 250000    # kb_doc_read 读窗（>60K 分卷上限 → 全卷可见）
FULL_VIS_LINES = 100000    # 行数上限（默认 200 行会截掉长行文档）
FULL_VIS_EVIDENCE_CHARS = 250000  # 传给 kb_laya_judge 的 evidence_pack 上限
UNION_CAP_CHARS = 60000    # A0h 判卷包 ∪ 分块窗口 的总字符帽
CHUNK_TOP_K = 10           # A0h slim=False 分块检索 top_k
CHUNK_UNION_N = 8          # A0h 并入证据的分块数
JUDGE_MODE_TAG = "inline_content(max_chars=250000,limit=100000,max_evidence_chars=250000)"

# --capture-responses：旁路捕获各臂对问题的回复（证据）原文（论文 HTML 报告数据源）。
CAPTURE_ON = False
CAPTURE: dict = {}
_last_response_text: dict = {}


def cj(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content]}


def kb_spec():
    """单一事实源：优先数据驱动 spec（10 域 138 篇），回退旧 KB_SPECS。
    provenance/ 为终局归档位置（final_bench 复现即用此份）；旧 artifacts/ 根路径保留兼容。"""
    for spec_file in (BASE.parent / "artifacts" / "provenance" / "corpus_spec_final.json",
                      BASE.parent / "artifacts" / "corpus_spec_final.json"):
        if spec_file.exists():
            spec = json.loads(spec_file.read_text(encoding="utf-8"))
            return [dict(slug=m["slug"], name=m["kb_name"], description=m["kb_desc"],
                         docs=[(d["file"], d["name"], d["desc"]) for d in m["docs"]])
                    for m in spec]
    sys.path.insert(0, str(BASE))
    from s2_ingest_corpus import KB_SPECS
    return KB_SPECS


def bigrams(s: str) -> Counter:
    s = re.sub(r"\s+", "", s.lower())
    return Counter(s[i:i + 2] for i in range(len(s) - 1))


def dice(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    inter = sum((a & b).values())
    return 2 * inter / (sum(a.values()) + sum(b.values()))


def route_by_description(question: str, catalog: list, slug_by_name: dict) -> str:
    """描述路由器（L0 机械代理）：question 与各库 name+description 的 bigram Dice 取最大。"""
    q = bigrams(question)
    best, best_slug = -1.0, ""
    for k in catalog:
        slug = slug_by_name.get(k.get("name", ""))
        if not slug:
            continue
        score = dice(q, bigrams(f"{k.get('name','')} {k.get('description','')}"))
        if score > best:
            best, best_slug = score, slug
    return best_slug


async def build_corpus(s: "ClientSession", prefix: str, strip_descriptions: bool) -> dict:
    """按 KB_SPECS 建库；strip_descriptions=True 时描述置空（A3 对照）。"""
    from s2_ingest_corpus import CORPUS, SPLIT_CHARS
    kb_ids = {}
    pdfs = []
    for spec in kb_spec():
        name = f"{prefix}-{spec['slug']}"
        d = cj(await s.call_tool("kb_create", {
            "name": name, "description": "" if strip_descriptions else spec["desc"]}))
        kb_id = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
        kb_ids[spec["slug"]] = kb_id
        for fp, dname, desc in spec["docs"]:
            p = CORPUS / fp
            if not p.exists():
                continue
            if fp.lower().endswith(".pdf"):
                pdfs.append((spec["slug"], kb_id, p, dname,
                             "" if strip_descriptions else desc))
                continue
            content = p.read_text(encoding="utf-8", errors="replace")
            if len(content.encode("utf-8")) <= SPLIT_CHARS:
                cj(await s.call_tool("kb_doc_create", {
                    "kb_id": kb_id, "name": dname, "content": content,
                    "description": "" if strip_descriptions else desc}))
            else:
                chunks = [content[i:i + SPLIT_CHARS] for i in range(0, len(content), SPLIT_CHARS)]
                stem = Path(dname).stem
                for i, ch in enumerate(chunks, 1):
                    cj(await s.call_tool("kb_doc_create", {
                        "kb_id": kb_id, "name": f"{stem} (part {i} of {len(chunks)}).md",
                        "content": ch,
                        "description": "" if strip_descriptions else f"[{i}/{len(chunks)}] {desc}"}))
        await s.call_tool("kb_reindex", {"kb_id": kb_id})
    if pdfs:
        d = cj(await s.call_tool("parse_doc_batch", {"file_paths": [str(p) for _, _, p, _, _ in pdfs],
                                                     "use_ocr": True}))
        tid = d.get("task_id", "")
        md_by_src = {}
        for _ in range(150):
            await asyncio.sleep(4)
            d = cj(await s.call_tool("parse_task_status", {"task_id": tid}))
            if str(d.get("status", "")).lower() in ("done", "completed", "success", "finished",
                                                    "error", "failed"):
                res = d.get("result") if isinstance(d.get("result"), dict) else {}
                for r_ in res.get("results") or []:
                    md_by_src[r_.get("source_filename") or ""] = r_.get("markdown_path") or ""
                break
        for slug, kb_id, p, dname, desc in pdfs:
            md = md_by_src.get(p.name, "")
            if md:
                cj(await s.call_tool("kb_doc_save_parsed", {
                    "parent_id": kb_id, "markdown_path": md,
                    "source_filename": p.name, "description": desc}))
        for slug in {sl for sl, _, _, _, _ in pdfs}:
            await s.call_tool("kb_reindex", {"kb_id": kb_ids[slug]})
    return kb_ids


def corpus_bytes_total() -> int:
    from s2_ingest_corpus import CORPUS
    total = 0
    for spec in kb_spec():
        for fp, _, _ in spec["docs"]:
            p = CORPUS / fp
            if p.exists() and not fp.lower().endswith(".pdf"):
                total += len(p.read_text(encoding="utf-8", errors="replace").encode("utf-8"))
    return total


def owner_slug(dp: str, fallback: str) -> str:
    n = dp.lower()
    if "个人信息保护法" in n or "数据安全法" in n or "pipl" in n or "dsl" in n or "csl" in n:
        return "law-zh"
    if "红楼梦" in n or "honglou" in n:
        return "literature-zh"
    if "史记" in n or "shiji" in n:
        return "history-zh"
    if "k8s" in n:
        return "tech-en"
    if "政府工作" in n or "十四五" in n or "five_year" in n or "gov_work" in n:
        return "gov-zh"
    if "pride" in n or "moby" in n:
        return "literature-en"
    if "attention" in n or "bert" in n or "rag_lewis" in n:
        return "science-en"
    if "sepsis" in n or "covid" in n:
        return "medicine-en"
    return fallback


async def route_via_catalog(s: "ClientSession", question: str, route_kb_id: str,
                            catalog: list, slug_by_name: dict) -> tuple[str, int]:
    """A0/A0f/A0h 共用的 L0 描述路由：对目录卡 KB 做真实语义检索（top1 卡片=路由域），
    空命中回退 bigram 描述路由器。返回 (route_slug, calls)。不用金标 domain。"""
    route, calls = "", 0
    if route_kb_id:
        rd = cj(await s.call_tool("kb_search_vector", {
            "query": question, "kb_id": route_kb_id,
            "top_k": 2, "score_threshold": 0.2, "slim": True}))
        calls += 1
        rhits = rd.get("results") or []
        if rhits:
            top_name = str((rhits[0].get("doc_path") or rhits[0].get("path") or ""))
            route = Path(top_name).stem if top_name.endswith(".md") else top_name
    if not route:
        route = route_by_description(question, catalog, slug_by_name)
    return route, calls


async def fetch_full_doc(s: "ClientSession", kb_id: str, doc_path: str) -> str:
    """全窗口取卷（A0f/A0h/PD）：覆盖参考模式 40K server 抓取的截断盲区。"""
    rd = cj(await s.call_tool("kb_doc_read", {
        "kb_id": kb_id, "doc_path": doc_path,
        "max_chars": FULL_VIS_CHARS, "limit": FULL_VIS_LINES}))
    return rd.get("content") or ""


async def run_arms(arms, questions, kb_ids, kb_ids_a3, digest_rate, catalog, slug_by_name, done=None, ck_path=None):
    active = kb_ids_a3 if "A3" in arms else kb_ids
    kb_id_of = lambda slug: active[slug]  # noqa: E731
    corpus_bytes = corpus_bytes_total()
    traces = {a: [] for a in arms}
    done = done or set()
    route_kb_id = None
    catalog_ts = time.strftime("%H%M%S")
    ck_path = ck_path or (ART / "s4_checkpoint.jsonl")

    async with stdio_client(StdioServerParameters(command=STDIO_CMD[0], args=STDIO_CMD[1:])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()

            # ── 目录卡 KB：每域一张"库描述卡"，A0 路由 = 对目录卡做真实语义检索（忠实描述层导航） ──
            # A3（无描述层消融）：路由卡必须同步剥离描述（name-only），否则 H3 消融不成立；
            # 故 A0 与 A3 禁止同一次调用（路由卡结构互斥）。
            if "A0" in arms or "A3" in arms or "A0f" in arms or "A0h" in arms:
                if "A0" in arms and "A3" in arms:
                    raise SystemExit("A0 与 A3 请分两次调用：A3 路由卡须 name-only（无描述层）")
                no_desc = "A3" in arms
                d = cj(await s.call_tool("kb_create", {
                    "name": f"路由目录卡-{catalog_ts}",
                    "description": "各知识库描述卡（S4 A0 路由层专用，实验后删除）"}))
                ckb = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
                for m in kb_spec():
                    card = f"# {m['name']}" if no_desc else f"# {m['name']}\n\n{m['description']}"
                    cr = cj(await s.call_tool("kb_doc_create", {
                        "kb_id": ckb, "name": f"{m['slug']}.md",
                        "content": card,
                        "description": "" if no_desc else m["description"]}))
                    # 逐卡 kb_index_document（kb_reindex 的异步提交会使集合转入不可查态——实验定罪，
                    # 见 s0h 观察曲线：首卷索引 +180s 稳定，reindex done 后即坏）
                    cpath = ((cr.get("files") or [{}])[0].get("path") or f"路由目录卡-{catalog_ts}/{m['slug']}.md")
                    cj(await s.call_tool("kb_index_document", {"kb_id": ckb, "doc_path": cpath}))
                rr = {"task_id": None}
                rt = rr.get("task_id")
                if rt:  # reindex 是异步任务——轮询到完成（S2 三库断链同根因：异步未等待）
                    for _ in range(30):
                        await asyncio.sleep(2)
                        ts_ = cj(await s.call_tool("kb_task_status", {"task_id": rt}))
                        if str(ts_.get("status", "")).lower() in ("done", "completed", "success", "finished"):
                            break
                # 探针：就绪门必须验证「全部卡片均可检索」——仅 reindex done + 有命中
                # 不足以保证 10 张卡全部向量化提交（实测曾致路由崩到 37.5%，误路由全部
                # 吸向最后入库的 philosophy/economics 两张卡）。
                n_cards = len(kb_spec())
                settled = False
                for _ in range(60):
                    await asyncio.sleep(3)
                    pd = cj(await s.call_tool("kb_search_vector", {
                        "query": "法律 数据安全", "kb_id": ckb, "top_k": 20,
                        "score_threshold": 0.05}))
                    names = {Path(str(h.get("doc_path") or h.get("path") or "")).stem
                             for h in (pd.get("results") or [])}
                    if len(names) >= n_cards:
                        settled = True
                        break
                if not settled:  # 最后兜底：再等一轮让 embedding 队列彻底追平
                    await asyncio.sleep(30)
                route_kb_id = ckb
                print(f"route catalog KB ready: {ckb[:8]} "
                      f"(cards_visible={len(names) if settled else 'partial'})", flush=True)
            for q in questions:
                qid = q["id"]
                gold_ev = q.get("gold_evidence")
                is_refusal = q.get("kind") == "refusal"
                gold_domain = q.get("domain")
                for arm in arms:
                    if (qid, arm) in done:
                        continue
                    t0 = time.time()
                    tr = dict(qid=qid, arm=arm, query=q["question"], is_refusal=is_refusal)
                    calls = 0
                    kb = None  # 当前臂路由/检索焦点库（A0f/A0h 用；PD 无导航）
                    if arm in ("A0", "A3"):
                        # L0 描述路由：对目录卡 KB 做真实语义检索（top1 卡片=路由域），不用金标 domain
                        route = ""
                        if route_kb_id:
                            rd = cj(await s.call_tool("kb_search_vector", {
                                "query": q["question"], "kb_id": route_kb_id,
                                "top_k": 2, "score_threshold": 0.2, "slim": True})); calls += 1
                            rhits = rd.get("results") or []
                            if rhits:
                                top_name = str((rhits[0].get("doc_path") or rhits[0].get("path") or ""))
                                route = Path(top_name).stem if top_name.endswith(".md") else top_name
                        if not route:
                            route = route_by_description(q["question"], catalog, slug_by_name)
                        tr["route_slug"] = route
                        tr["route_correct"] = (route == gold_domain) if gold_domain else None
                        kb = kb_id_of(route) if route else list(active.values())[0]
                        d = cj(await s.call_tool("kb_get_documents", {"kb_id": kb, "lightweight": True})); calls += 1
                        tr["shelf_docs"] = len(d.get("catalog") or [])
                        d = cj(await s.call_tool("kb_search_vector", {
                            "query": q["question"], "kb_id": kb, "top_k": 30,
                            "score_threshold": 0.35, "balance_kbs": True, "slim": True})); calls += 1
                        if not (d.get("results") or []):
                            # skill 契约 Phase 1：0 命中 → 0.30 重试一次（繁简/跨语衰减容忍）
                            d = cj(await s.call_tool("kb_search_vector", {
                                "query": q["question"], "kb_id": kb, "top_k": 30,
                                "score_threshold": 0.30, "balance_kbs": True, "slim": True})); calls += 1
                    elif arm in ("A1b", "A2"):
                        # 全局向量=评测十库的并集（逐库定向搜索后合并）——kb_id="" 的
                        # 全平台搜索会召回评测范围外的库（A3 孪生/生产库），已定罪为设计缺陷
                        d = {"results": []}
                        for _slug in active:
                            ds = cj(await s.call_tool("kb_search_vector", {
                                "query": q["question"], "kb_id": kb_id_of(_slug),
                                "top_k": 30, "score_threshold": 0.35, "slim": True})); calls += 1
                            for h in (ds.get("results") or []):
                                h["_src"] = _slug
                                d["results"].append(h)
                        d["results"].sort(key=lambda h: -(h.get("score", 0) or 0))
                        d["results"] = d["results"][:30]
                    elif arm in ("A0f", "A0h"):
                        # 优化臂：与 A0 完全一致的导航（目录卡路由→书架→库内宽网 top_k=30
                        # @0.35，0 命中 → 0.30 重试一次）；差别仅在判卷层（见下）
                        route, rcalls = await route_via_catalog(
                            s, q["question"], route_kb_id, catalog, slug_by_name)
                        calls += rcalls
                        tr["route_slug"] = route
                        tr["route_correct"] = (route == gold_domain) if gold_domain else None
                        kb = kb_id_of(route) if route else list(active.values())[0]
                        d = cj(await s.call_tool("kb_get_documents", {"kb_id": kb, "lightweight": True})); calls += 1
                        tr["shelf_docs"] = len(d.get("catalog") or [])
                        d = cj(await s.call_tool("kb_search_vector", {
                            "query": q["question"], "kb_id": kb, "top_k": 30,
                            "score_threshold": 0.35, "balance_kbs": True, "slim": True})); calls += 1
                        if not (d.get("results") or []):
                            d = cj(await s.call_tool("kb_search_vector", {
                                "query": q["question"], "kb_id": kb, "top_k": 30,
                                "score_threshold": 0.30, "balance_kbs": True, "slim": True})); calls += 1
                    elif arm == "PD":
                        # 精确逐文档检索：无导航层，十库逐一定向检索 → 按 doc_path 并集
                        d = {"results": []}
                        for _slug in active:
                            ds = cj(await s.call_tool("kb_search_vector", {
                                "query": q["question"], "kb_id": kb_id_of(_slug),
                                "top_k": 30, "score_threshold": 0.35, "slim": True})); calls += 1
                            for h in (ds.get("results") or []):
                                h["_src_kb"] = kb_id_of(_slug)
                                d["results"].append(h)
                    if arm in ("A0f", "A0h", "PD"):
                        # 全窗口判卷（A0f/PD 同体；A0h 在此之上做分块窗口并集）：
                        # 不用参考模式的 server 40K 抓取（截断盲区根因），改为自行
                        # kb_doc_read(max_chars=250000, limit=100000) 取全卷后 inline
                        # 传 content（legacy 模式：content given = no fetch）——零 server 改动。
                        hits = d.get("results") or []
                        best = {}
                        for h in hits:
                            dp = (h.get("doc_path") or h.get("path") or "?").replace("\\", "/")
                            sc = h.get("score", 0) or 0
                            hkb = h.get("_src_kb") or kb
                            key = (hkb, dp)
                            if key not in best or sc > best[key][0]:
                                best[key] = (sc, h.get("content", ""))
                        ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:6]
                        cands = [(k[1], k[0]) for k, _ in ranked]  # [(doc_path, kb_id)]
                        tr["top1"] = cands[0][0] if cands else ""
                        tr["distractor_docs"] = sum(
                            1 for dp, _ in cands
                            if gold_domain and owner_slug(dp, gold_domain) != gold_domain)
                        refs_list, fetched_b = [], 0
                        for dp, dkb in cands:
                            txt = await fetch_full_doc(s, dkb, dp); calls += 1
                            fetched_b += len(txt.encode("utf-8"))
                            refs_list.append({"kb_id": dkb, "doc_path": dp, "content": txt})
                        refs = json.dumps(refs_list, ensure_ascii=False)
                        jd = cj(await s.call_tool("kb_laya_judge", {
                            "query": q["question"], "documents": refs,
                            "criterion": "auto", "include_text": False,
                            "max_evidence_chars": FULL_VIS_EVIDENCE_CHARS})); calls += 1
                        pack = jd.get("evidence_pack") or ""
                        pack_b = len(pack.encode("utf-8"))
                        tr["judge_mode"] = JUDGE_MODE_TAG
                        evidence, ev_b = pack, pack_b
                        _last_response_text[qid] = evidence
                        if arm == "A0h":
                            # 分块窗口并集：slim=False 全文 chunk top-8 ∪ 判卷包，总帽 ~60K
                            # （chunk 优先入包＝新增信号优先；判卷包填剩余预算）
                            dc = cj(await s.call_tool("kb_search_vector", {
                                "query": q["question"], "kb_id": kb, "top_k": CHUNK_TOP_K,
                                "score_threshold": 0.35, "slim": False})); calls += 1
                            chunks, seen_fp = [], set()
                            for h in sorted(dc.get("results") or [],
                                            key=lambda x: -(x.get("score", 0) or 0)):
                                ct = str(h.get("content") or "").strip()
                                if not ct:
                                    continue
                                fp = re.sub(r"\s+", " ", ct)
                                if fp in seen_fp:
                                    continue
                                seen_fp.add(fp)
                                chunks.append(f"[{(h.get('doc_path') or '').replace(chr(92), '/')}#"
                                              f"{h.get('chunk_index', 0)}]\n{ct}")
                                if len(chunks) >= CHUNK_UNION_N:
                                    break
                            chunk_txt = "\n\n".join(chunks)
                            tr["chunk_bytes"] = len(chunk_txt.encode("utf-8"))
                            evidence = chunk_txt[:UNION_CAP_CHARS]
                            if len(chunk_txt) < UNION_CAP_CHARS - 2 and pack:
                                evidence = evidence + "\n\n" + pack[:UNION_CAP_CHARS - len(evidence) - 2]
                            ev_b = len(evidence.encode("utf-8"))
                            _last_response_text[qid] = evidence
                        tr.update(survivors=[x.get("doc_path", "?") for x in (jd.get("survivors") or [])
                                             if isinstance(x, dict)],
                                  pack_bytes=pack_b,
                                  bytes_ingested=fetched_b + pack_b + tr.get("chunk_bytes", 0),
                                  gold_hit=bool(gold_ev) and gold_ev in evidence,
                                  evidence_focus=(ev_b / corpus_bytes) if corpus_bytes else None,
                                  refusal_ok=is_refusal and not jd.get("survivors"))
                    elif arm in ("A0", "A3", "A1b", "A2"):
                        hits = d.get("results") or []
                        best = {}
                        for h in hits:
                            dp = (h.get("doc_path") or h.get("path") or "?").replace("\\", "/")
                            sc = h.get("score", 0) or 0
                            if dp not in best or sc > best[dp][0]:
                                best[dp] = (sc, h.get("content", ""))
                        ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:6]
                        cands = [dp for dp, _ in ranked]
                        tr["top1"] = cands[0] if cands else ""
                        tr["distractor_docs"] = sum(
                            1 for dp in cands
                            if gold_domain and owner_slug(dp, gold_domain) != gold_domain)
                        tr["bytes_ingested"] = sum(len(c[1][1].encode("utf-8")) for c in ranked)
                        if arm == "A2":  # 无证据门：证据=候选 slim 摘要拼接
                            evidence = "\n".join(c[1][1] for c in ranked)
                            _last_response_text[qid] = evidence
                            tr["gold_hit"] = bool(gold_ev) and gold_ev in evidence
                            tr["evidence_focus"] = (tr["bytes_ingested"] / corpus_bytes) if corpus_bytes else None
                            tr["refusal_ok"] = is_refusal and not cands
                        else:
                            default_kb = next(iter(active.values()))
                            refs_list = []
                            for dp in cands:
                                os_ = owner_slug(dp, gold_domain)
                                refs_list.append({"kb_id": kb_id_of(os_) if os_ in active else default_kb,
                                                  "doc_path": dp})
                            refs = json.dumps(refs_list, ensure_ascii=False)
                            jd = cj(await s.call_tool("kb_laya_judge", {
                                "query": q["question"], "documents": refs,
                                "criterion": "auto", "include_text": False})); calls += 1
                            pack = jd.get("evidence_pack") or ""
                            pack_b = len(pack.encode("utf-8"))
                            _last_response_text[qid] = pack
                            tr.update(survivors=[x.get("doc_path", "?") for x in (jd.get("survivors") or [])
                                                 if isinstance(x, dict)],
                                      pack_bytes=pack_b,
                                      bytes_ingested=tr["bytes_ingested"] + pack_b,
                                      gold_hit=bool(gold_ev) and gold_ev in pack,
                                      evidence_focus=(pack_b / corpus_bytes) if corpus_bytes else None,
                                      refusal_ok=is_refusal and not jd.get("survivors"))
                    elif arm == "A1-readall":
                        acc, first_hit, nbytes = [], None, 0
                        # 逐库逐篇通读：不启动任何检索机制（目录/描述/向量/判卷全部关闭）
                        # 目录必须分页取全（page_size≤200，has_more 循环）——readall 臂定义=
                        # 读完全部文档；只取 page1 会静默漏读大库（文学-英文 434 卷只见 200）。
                        for slug in active:
                            kb = kb_id_of(slug)
                            page, shelf = 1, []
                            while True:
                                d = cj(await s.call_tool("kb_get_documents", {
                                    "kb_id": kb, "lightweight": True,
                                    "page": page, "page_size": 200})); calls += 1
                                shelf.extend(d.get("catalog") or [])
                                if not d.get("has_more"):
                                    break
                                page += 1
                            tr.setdefault("shelf_docs_total", 0)
                            tr["shelf_docs_total"] += len(
                                [e for e in shelf if e.get("entry_type") != "sub_kb"])
                            for doc in shelf:
                                dp = doc.get("doc_path") or doc.get("name")
                                if not dp or doc.get("entry_type") == "sub_kb":
                                    continue
                                rd = cj(await s.call_tool("kb_doc_read", {
                                    "kb_id": kb, "doc_path": dp, "max_chars": 60000,
                                    "limit": 100000})); calls += 1  # limit=行数上限：默认 200 行会把短行文档截掉一半以上
                                txt = rd.get("content") or ""
                                nbytes += len(txt.encode("utf-8"))
                                acc.append(txt)
                                if gold_ev and first_hit is None and gold_ev in txt:
                                    first_hit = len(acc)
                        full = "\n".join(acc)
                        tr.update(calls=calls, bytes_ingested=nbytes,
                                  first_hit_read_index=first_hit,
                                  gold_hit=bool(gold_ev) and gold_ev in full,
                                  evidence_focus=nbytes / corpus_bytes if corpus_bytes else None,
                                  refusal_ok=is_refusal,  # 机械口径；真实 agent 版另行测
                                  distractor_docs=None)
                    else:
                        continue
                    tr["calls"] = calls
                    tr["tool_seconds"] = round(time.time() - t0, 1)
                    tr["llm_digest_seconds"] = round(tr["bytes_ingested"] / digest_rate, 1)
                    traces[arm].append(tr)
                    # --capture-responses：把该模式对问题的回复（证据）原文写入旁路字典，
                    # main() 结束时落盘 s4_responses_<HHMMSS>.json（论文 HTML 报告数据源）。
                    # readall 的"回复"=整个语料（24MB/题），只记标记不落原文。
                    if CAPTURE_ON:
                        CAPTURE[arm][qid] = {
                            "question": q["question"],
                            "gold_doc": q.get("gold_doc", ""),
                            "gold_evidence": gold_ev or "",
                            "gold_hit": bool(tr.get("gold_hit")),
                            "is_refusal": bool(is_refusal),
                            "top1": tr.get("top1", ""),
                            "survivors": tr.get("survivors", []),
                            "response_text": ("" if arm == "A1-readall"
                                              else _last_response_text.get(qid, "")),
                            "response_note": ("[readall 模式：回复=全库通读 24.3MB/题，原文不落盘]"
                                              if arm == "A1-readall" else
                                              ("证据窗并集（chunk top-8 ∪ 判卷包）" if arm == "A0h"
                                               else "判卷证据包（fail-closed 段存活合并）" if pack_b else
                                               "候选 slim 摘要拼接（无证据门）" if arm == "A2" else "")),
                        }
                    print(f"[{arm}] {qid} gold={tr.get('gold_hit')} refuse={tr.get('refusal_ok')} "
                          f"calls={calls} tool={tr['tool_seconds']}s "
                          f"digest~{tr['llm_digest_seconds']}s bytes={tr['bytes_ingested']:,}", flush=True)
                    # checkpoint：逐条落盘，崩了不丢（--out 时写入 out 目录，避免与旧臂行混淆）
                    with open(ck_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(tr, ensure_ascii=False) + "\n")
            if route_kb_id:
                cj(await s.call_tool("kb_delete", {"kb_id": route_kb_id}))
                print("route catalog KB deleted (cleanup)", flush=True)
    return traces


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ART.mkdir(parents=True, exist_ok=True)
    argv = sys.argv[1:]
    digest_rate = DEFAULT_DIGEST_RATE
    if "--digest-rate" in argv:
        digest_rate = int(argv[argv.index("--digest-rate") + 1])

    if "--prepare-a3" in argv:
        async with stdio_client(StdioServerParameters(command=STDIO_CMD[0], args=STDIO_CMD[1:])) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                kb_ids_a3 = await build_corpus(s, prefix="A3无描述", strip_descriptions=True)
        (ART / "s4_a3_kbids.json").write_text(json.dumps(kb_ids_a3, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
        print(f"A3 stripped-description KBs ready: {kb_ids_a3}")
        return

    qi = argv.index("--questions") if "--questions" in argv else -1
    qfile = Path(argv[qi + 1]) if qi >= 0 else ART / "questions.jsonl"
    questions = [json.loads(l) for l in qfile.read_text(encoding="utf-8").splitlines() if l.strip()]
    skipped = [q["id"] for q in questions if q.get("needs_expansion")]
    questions = [q for q in questions if not q.get("needs_expansion")]
    # --out <dir>：trace + checkpoint 输出目录（默认 artifacts/；优化轮写入 opt_bench，
    # 与旧臂 checkpoint 行物理隔离——新臂名 A0f/A0h/PD 本身也不与旧行碰撞）
    out_dir = ART
    if "--out" in argv:
        out_dir = Path(argv[argv.index("--out") + 1])
        out_dir.mkdir(parents=True, exist_ok=True)
    # --skip-done：断点续跑——checkpoint 里已有的 (qid, arm) 对直接跳过（崩溃自愈的关键）
    done = set()
    if "--skip-done" in argv:
        ck = out_dir / "s4_checkpoint.jsonl"
        if ck.exists():
            for l in ck.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    t = json.loads(l)
                    done.add((t.get("qid"), t.get("arm")))
        print(f"skip-done: checkpoint has {len(done)} (qid,arm) pairs", flush=True)
    if "--limit" in argv:
        questions = questions[:int(argv[argv.index("--limit") + 1])]
    arms = [a.strip() for a in
            (argv[argv.index("--arms") + 1].split(",") if "--arms" in argv else ["A0", "A1-readall", "A1b"])]
    kb_ids_a3 = None
    if "A3" in arms:
        kb_ids_a3 = json.loads((ART / "s4_a3_kbids.json").read_text(encoding="utf-8"))

    # 复用 S2 已建库（按 KB_SPECS 名称精确匹配），避免重复解析 PDF
    use_prefix = "MD语料-"
    if "--kb-prefix" in argv:
        use_prefix = argv[argv.index("--kb-prefix") + 1]
    slug_by_name = {spec["name"]: spec["slug"] for spec in kb_spec()}
    kb_ids, catalog = {}, []
    async with stdio_client(StdioServerParameters(command=STDIO_CMD[0], args=STDIO_CMD[1:])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            d = cj(await s.call_tool("kb_list", {"lightweight": True}))
            catalog = d.get("catalog") or []
            for k in catalog:
                slug = slug_by_name.get(k.get("name", ""))
                if slug and k.get("name", "").startswith(use_prefix):
                    kb_ids[slug] = k["kb_id"]
    missing = [spec["slug"] for spec in kb_spec() if spec["slug"] not in kb_ids]
    if missing:
        print(f"❌ 语料库缺失（先跑 Stage 2）: {missing}；--kb-prefix={use_prefix}")
        return

    print(f"questions={len(questions)} (skipped needs_expansion: {skipped}) arms={arms} "
          f"kbs={len(kb_ids)} digest_rate={digest_rate} out={out_dir}", flush=True)
    global CAPTURE_ON
    if "--capture-responses" in argv:
        CAPTURE_ON = True
        for a in arms:
            CAPTURE[a] = {}
    traces = await run_arms(arms, questions, kb_ids, kb_ids_a3, digest_rate, catalog, slug_by_name,
                            done, ck_path=out_dir / "s4_checkpoint.jsonl")
    out = out_dir / f"s4_traces_{time.strftime('%H%M%S')}.json"
    out.write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    if CAPTURE_ON:
        resp_path = out_dir / f"s4_responses_{time.strftime('%H%M%S')}.json"
        resp_path.write_text(json.dumps(CAPTURE, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"responses captured → {resp_path} "
              f"({sum(len(v) for v in CAPTURE.values())} rows across {len(CAPTURE)} arms)")
    for arm, rows in traces.items():
        gold = sum(1 for x in rows if x.get("gold_hit"))
        ref = sum(1 for x in rows if x.get("refusal_ok"))
        dig = sum(x.get("llm_digest_seconds", 0) for x in rows)
        rc = [x for x in rows if x.get("route_correct") is not None]
        rcs = f" route_correct={sum(1 for x in rc if x['route_correct'])}/{len(rc)}" if rc else ""
        print(f"=== {arm}: gold={gold} refusal={ref}{rcs} total_digest~{dig:.0f}s → {out}")


if __name__ == "__main__":
    asyncio.run(main())
