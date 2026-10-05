#!/usr/bin/env python3
"""优化版逐级检索(Librarian mode B) — 内容驱动 + 全链路可观测.

逐级流程(七层, 每层全程 trace):
  L0  书架分类      kb_list + 平台 classify_kbs 同语义
  L2  描述清单      kb_get_documents 全量描述
  L3  目录信号      词重叠(拆连字符/下划线复合词 + CJK 二元组) + 描述信任 → 读计划
  L4  并行内容读取  单 MCP stdio 连接流水线并发(窗口 8), 全文 20k / 头部 600
  L5  内容判卷      平台 run_manifest(分块→Laya 逐段→yes 全收, fail-closed)
  L5b 内容探查补召  零信号未读文档: 头部 600 字符 → Laya 评分 ≥ 保留线(global_best
                    - 0.05) → 补读全文 → 再判(与最终保留同一把尺子)
  L6  内容驱动保留  retain_docs(相对截断 best-0.05 + overlap 契合 + top-3 地板)
      内容驱动打包  幸存段按 Laya 分数降序去重拼包(旧版按路径字典序 — 噪音挤掉金标的根源)

相对旧 run_mode_b 的实质变化 = L3 分词修正 + L4 并行 + L5b 补召 + L6 保留/打包排序。
yes 全收契约不变: score>=threshold 的段全部幸存并全部落盘(scores 字段), 保留/打包只
决定谁进入最终证据包。头部探查段永不进判卷(只作晋级依据), 晋级后以全文重新判卷。

可观测性: trace.jsonl 记录每层决策、每次 MCP 调用/返回摘要/耗时、每段 Laya 判决、
每次 peek 评分与晋级决定。本地 Laya 经 SDK 只返回结构化分数, 无自由文本思考链;
判卷指令原文(evidence/instance 模板)随 trace 落盘。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIBRARIAN_SCRIPTS = REPO / ".claude" / "skills" / "knowledgebase-librarian" / "scripts"
for p in (str(REPO / "benchmark-suite" / "scripts"), str(LIBRARIAN_SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

import complete_recall as cr  # noqa: E402
import jev_filter  # noqa: E402


class TraceLog:
    """全链路审计日志: 每层决策/每次工具调用/每段判决, jsonl 落盘。"""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.t0 = time.perf_counter()
        path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, tier: str, event: str, **kw) -> None:
        rec = {"t": round(time.perf_counter() - self.t0, 3), "tier": tier,
               "event": event}
        rec.update({k: (v if isinstance(v, (int, float, bool, list)) else str(v)[:220])
                    for k, v in kw.items()})
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class PipelinedMcp:
    """单 stdio 连接上的并发 MCP 客户端: 读线程按 id 分发响应(服务端为 asyncio)。"""

    def __init__(self, repo_root: Path = REPO):
        env = dict(os.environ)
        env.setdefault("PYTHONUTF8", "1")
        if "MCP_AUTH_TOKEN" not in env:
            from lib import auth_token
            env["MCP_AUTH_TOKEN"] = auth_token()
        self.proc = subprocess.Popen(
            ["uv", "run", "--directory", "kb-mcp", "python", "server.py"],
            cwd=str(repo_root), env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1)
        self._futures: dict[int, Future] = {}
        self._lock = threading.Lock()
        self._wlock = threading.Lock()
        self._id = 0
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._initialize()

    def _read_loop(self) -> None:
        for raw in self.proc.stdout:
            line = raw.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            mid = msg.get("id")
            if mid is None:
                continue
            with self._lock:
                fut = self._futures.pop(mid, None)
            if fut is None:
                continue
            if "error" in msg:
                fut.set_exception(RuntimeError(f"MCP error: {msg['error']}"))
            else:
                fut.set_result(msg["result"])

    def _send(self, obj: dict) -> None:
        with self._wlock:
            self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()

    def _initialize(self) -> None:
        with self._lock:
            self._id += 1
            mid = self._id
        fut = Future()
        with self._lock:
            self._futures[mid] = fut
        self._send({"jsonrpc": "2.0", "id": mid, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "librarian-opt", "version": "1.0"}}})
        fut.result(timeout=120)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, name: str, arguments: dict | None = None,
             timeout: float = 300.0) -> dict:
        with self._lock:
            self._id += 1
            mid = self._id
            fut = Future()
            self._futures[mid] = fut
        self._send({"jsonrpc": "2.0", "id": mid, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments or {}}})
        result = fut.result(timeout=timeout)
        if result.get("isError"):
            raise RuntimeError(f"tool {name} error: {json.dumps(result)[:300]}")
        for block in result.get("content", []):
            if block.get("type") == "text":
                try:
                    return json.loads(block["text"])
                except json.JSONDecodeError:
                    return {"raw": block["text"]}
        return {}

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def _terms_opt(value: str) -> set:
    """L3 专用分词: 拆连字符/下划线复合词 + CJK 二元组。

    旧 cr._terms 把 "deep-spatial-learning-with-molecular-vibrati" 当成一个
    token(连字符在字符类里), 目录重叠对这类文档恒为 0 — 2011.07200 漏检的根源。
    """
    text = str(value or "").lower()
    latin: set = set()
    for run in re.findall(r"[a-z0-9][a-z0-9_.\-]{1,}", text):
        for part in re.split(r"[_.\-]+", run):
            part = part.strip(".'")
            if len(part) >= 2 and part not in cr._STOP:
                latin.add(part)
    cjk: set = set()
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if len(run) <= 3:
            cjk.add(run)
        else:
            cjk.update(run[i:i + 2] for i in range(len(run) - 1))
    return latin | cjk


def _overlap(a: set, b: set) -> int:
    """词重叠计数(精确匹配)。前缀信用实测会大面积误伤(optimal-distributed-
    control 之类借 learning/model 前缀混入), 故只留拆词后的精确重叠。"""
    return len(a & b)


def run_tiered(query: str, shelves: list[str], out_dir: Path, *,
               budget: int = 35, head_budget: int = 20, peek_cap: int = 48,
               read_window: int = 8, retain_margin: float = 0.05,
               top_k_floor: int = 3, pack_chars: int = 40_000,
               max_doc_chars: int = 20_000) -> dict:
    """逐级检索主流程 L0→L6, 全程 trace。返回 result dict(保留/逐出/包/审计)。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    tr = TraceLog(out_dir / "trace.jsonl")
    tr.event("L0", "start", query=query, shelves=shelves)
    t: dict[str, float] = {"L0": 0.0, "L2": 0.0, "L3": 0.0, "L4": 0.0,
                           "L5": 0.0, "L5b_peek_read": 0.0, "L5b_judge": 0.0, "L6": 0.0}

    def key_of(d: dict) -> tuple[str, str]:
        return (str(d.get("kb_id")), str(d.get("doc_path")))

    docs_all: list[dict] = []
    chosen: list[dict] = []
    read_docs: list[dict] = []
    peek_docs: list[dict] = []
    promoted: list[dict] = []
    peek_stats = {"peeked": 0, "promoted": 0, "promote_cut": None}
    read_plan: list[tuple[dict, str, str]] = []
    mc = PipelinedMcp()
    try:
        # ── L0: 书架清单与分类(与平台 classify_kbs 同语义) ──
        t["L0"] = time.perf_counter()
        kbs = mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []
        classified = cr.classify_kbs(query, kbs)
        for k in classified:
            tr.event("L0", "kb_classified", kb=str(k.get("name")), status=k.get("catalog_status"),
                     overlap=k.get("query_overlap"))
        chosen = [k for k in classified if str(k.get("name")) in set(shelves)]
        if not chosen:
            chosen = [k for k in classified if k.get("catalog_status") == "relevant"]
        t["L0"] = time.perf_counter() - t["L0"]
        tr.event("L0", "done", seconds=round(t["L0"], 2),
                 chosen=[str(k.get("name")) for k in chosen])

        # ── L2: 候选书架全部文档描述 ──
        t["L2"] = time.perf_counter()
        for k in chosen:
            kb_id = k.get("kb_id") or k.get("name")
            rows = mc.call("kb_get_documents", {"lightweight": True, "kb_id": kb_id},
                           timeout=180).get("catalog") or []
            for d in rows:
                docs_all.append({**d, "kb_id": kb_id, "kb_name": k.get("name")})
            tr.event("L2", "shelf_docs", kb=str(k.get("name")), docs=len(rows))
        t["L2"] = time.perf_counter() - t["L2"]
        tr.event("L2", "done", seconds=round(t["L2"], 2), docs=len(docs_all))

        # ── L3: 目录信号(修正分词的词重叠 + 描述信任) → 读计划 ──
        t["L3"] = time.perf_counter()
        qterms = _terms_opt(query)
        sibs: dict[str, list[str]] = {}
        for d in docs_all:
            sibs.setdefault(str(d.get("kb_id")), []).append(str(d.get("description") or ""))
        for d in docs_all:
            blob = f"{d.get('name', '')} {d.get('description', '')}"
            d["overlap"] = _overlap(qterms, _terms_opt(blob)) if qterms else 0
            trusted, reasons = cr._metadata_trust(str(d.get("description") or ""),
                                                  sibs[str(d.get("kb_id"))])
            d["description_trust"] = "trusted" if trusted else "untrusted"
            d["trust_reasons"] = reasons
        overlaps = sorted((d for d in docs_all if d["overlap"] > 0), key=lambda x: -x["overlap"])
        for d in overlaps:
            if len([1 for _, _, kind in read_plan if kind == "full"]) >= budget:
                break
            read_plan.append((d, f"overlap={d['overlap']}", "full"))
        picked = {key_of(d) for d, _, _ in read_plan}
        stems: set = set()
        for d, _, kind in read_plan:
            if kind == "full":
                m = re.search(r"^(.*) \(part \d+ of \d+\)",
                              str(d.get("doc_path") or "").replace("\\", "/"))
                if m:
                    stems.add(m.group(1))
        for d in docs_all:
            m = re.search(r"^(.*) \(part \d+ of \d+\)",
                          str(d.get("doc_path") or "").replace("\\", "/"))
            if m and m.group(1) in stems and key_of(d) not in picked:
                if len([1 for _, _, kind in read_plan if kind == "full"]) >= budget:
                    break
                read_plan.append((d, "stem_completion", "full"))
                picked.add(key_of(d))
        heads = 0
        for d in docs_all:
            if d["description_trust"] == "untrusted" and key_of(d) not in picked:
                if heads >= head_budget:
                    break
                read_plan.append((d, "untrusted_head", "head"))
                picked.add(key_of(d))
                heads += 1
        t["L3"] = time.perf_counter() - t["L3"]
        for d, reason, kind in read_plan:
            tr.event("L3", "read_planned", doc=str(d.get("doc_path")), reason=reason, kind=kind)
        tr.event("L3", "done", seconds=round(t["L3"], 2), planned=len(read_plan),
                 zero_signal_unscanned=len(docs_all) - len(read_plan))

        # ── L4: 并行内容读取(单连接流水线, 窗口 read_window) ──
        t["L4"] = time.perf_counter()

        def do_read(item: tuple[dict, str, str]) -> dict:
            d, reason, kind = item
            t0 = time.perf_counter()
            r = mc.call("kb_doc_read", {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                                        "max_chars": max_doc_chars if kind == "full" else 600},
                        timeout=180)
            lat = time.perf_counter() - t0
            content = str(r.get("content") or "")
            tr.event("L4", "doc_read", doc=str(d.get("doc_path")), kind=kind,
                     reason=reason, chars=len(content), latency_s=round(lat, 3),
                     truncated=bool(r.get("truncated")))
            return {**d, "content": content, "truncated": bool(r.get("truncated")),
                    "read_kind": kind, "read_reason": reason, "read_s": round(lat, 3)}

        with ThreadPoolExecutor(max_workers=read_window) as pool:
            read_docs = list(pool.map(do_read, read_plan))
        t["L4"] = time.perf_counter() - t["L4"]
        tr.event("L4", "done", seconds=round(t["L4"], 2), reads=len(read_docs),
                 chars=sum(len(d["content"]) for d in read_docs))

        # ── L5b(读取半场): 零信号未读文档头部 600 字符(判卷后评分, 先取回内容) ──
        unseen = [d for d in docs_all if key_of(d) not in picked][:peek_cap]
        if unseen:
            t0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=read_window) as pool:
                peek_docs = list(pool.map(
                    lambda d: {**d, "content": str(mc.call(
                        "kb_doc_read", {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                                        "max_chars": 600}, timeout=180).get("content") or ""),
                        "read_kind": "peek_head", "read_reason": "zero_signal_peek"}, unseen))
            t["L5b_peek_read"] = time.perf_counter() - t0
            peek_stats["peeked"] = len(peek_docs)
            tr.event("L5b", "heads_read", seconds=round(t["L5b_peek_read"], 2),
                     heads=len(peek_docs))
    finally:
        mc.close()

    def judge(docs: list[dict], tag: str) -> dict:
        manifest = {"query": query, "engine": "laya", "threshold": 0.5,
                    "max_segment_chars": 3000, "max_evidence_chars": pack_chars,
                    "knowledge_bases": [{"kb_id": k.get("kb_id") or k.get("name"),
                                         "name": k.get("name"),
                                         "description": k.get("description") or ""}
                                        for k in chosen],
                    "documents": docs}
        run = cr.run_manifest(manifest)
        jev = run["jev"]
        tr.event(tag, "judging_instruction", criterion=jev.get("criterion"),
                 instruction=jev_filter._laya_instruction(query, jev.get("criterion") or "evidence"),
                 threshold=jev.get("threshold"), model=str(jev.get("model")))
        for rec in jev.get("scores") or []:
            tr.event(tag, "segment_verdict", candidate_id=rec.get("candidate_id"),
                     doc=str(rec.get("doc_path")), score=rec.get("score"), kept=rec.get("kept"))
        tr.event(tag, "done", candidates=jev.get("candidate_count"),
                 scored=jev.get("scored_count"), survivors=len(jev.get("survivors") or []),
                 real_engine=jev.get("real_engine"))
        return run

    # ── L5: 内容判卷第一波(平台 run_manifest: 分块→Laya 逐段→yes 全收, fail-closed) ──
    t["L5"] = time.perf_counter()
    run1 = judge(read_docs, "L5")
    jev1 = run1["jev"]
    t["L5"] = time.perf_counter() - t["L5"]
    tr.event("L5", "phase_done", seconds=round(t["L5"], 2))

    # ── L5b: 头部评分与晋级 → 晋级文档补读全文 → 再判(同一把保留线尺子) ──
    jev2 = None
    if peek_docs:
        t0 = time.perf_counter()
        best1 = max((s.get("score") or 0.0) for s in (jev1.get("survivors") or [])) \
            if jev1.get("survivors") else 0.0
        promote_cut = max(0.5, round(best1 - retain_margin, 4))
        peek_stats["promote_cut"] = promote_cut
        crit = jev1.get("criterion") or jev_filter.criterion_for(query)
        passed: list[tuple[float, dict]] = []
        for d in peek_docs:
            segs = cr.segment_document(d, max_chars=3000)
            head_best = None
            for s in segs:
                try:
                    sc, _meta = jev_filter.laya_score(query, s["text"], crit)
                except Exception as exc:  # noqa: BLE001 — fail-closed: 评分失败不晋级
                    tr.event("L5b", "peek_score_error", doc=str(d.get("doc_path")),
                             error=str(exc))
                    break
                head_best = sc if head_best is None else max(head_best, sc)
                if sc >= promote_cut:
                    break
            ok = head_best is not None and head_best >= promote_cut
            tr.event("L5b", "peek_verdict", doc=str(d.get("doc_path")),
                     head_best=head_best, promote_cut=promote_cut, promoted=ok)
            if ok:
                passed.append((head_best, d))
        # 晋级上限: 头部摘要段打分 top-heavy, 不设上限会让无关论文挤占晋级名额
        passed.sort(key=lambda x: -(x[0] or 0.0))
        promoted = [d for _sc, d in passed[:6]]
        for sc, d in passed:
            if all(d is not p for p in promoted):
                tr.event("L5b", "peek_promote_deferred", doc=str(d.get("doc_path")),
                         head_best=sc, reason="promote_cap_6")
        peek_stats["promoted"] = len(promoted)
        t["L5b_judge"] = time.perf_counter() - t0
        if promoted:
            mc = PipelinedMcp()
            try:
                with ThreadPoolExecutor(max_workers=read_window) as pool:
                    promoted = list(pool.map(
                        lambda d: {**d, "content": str(mc.call(
                            "kb_doc_read", {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                                            "max_chars": max_doc_chars},
                            timeout=180).get("content") or ""),
                            "read_kind": "full",
                            "read_reason": f"head_promoted:{d.get('_head_best') or ''}"},
                        promoted))
            finally:
                mc.close()
            tr.event("L5b", "promoted_full_reads", docs=len(promoted))
            t1 = time.perf_counter()
            run2 = judge(promoted, "L5b")
            jev2 = run2["jev"]
            t["L5b_judge"] = round(t["L5b_judge"] + (time.perf_counter() - t1), 2)
        tr.event("L5b", "phase_done", promoted=len(promoted), promote_cut=promote_cut)

    # ── L6: 内容驱动保留(合并两波) + 分数降序打包 ──
    t["L6"] = time.perf_counter()
    survivors = list(jev1.get("survivors") or [])
    score_rows = list(jev1.get("scores") or [])
    if jev2 is not None:
        survivors += list(jev2.get("survivors") or [])
        score_rows += list(jev2.get("scores") or [])
    real_engine = bool(jev1.get("real_engine")) and bool(
        (jev2 or {}).get("real_engine", True))

    doc_best: dict[tuple[str, str], dict] = {}
    doc_segs: dict[tuple[str, str], int] = {}
    for s in survivors:
        k = (str(s.get("kb_id") or ""), str(s.get("doc_path") or ""))
        sc = s.get("score")
        doc_segs[k] = doc_segs.get(k, 0) + 1
        if isinstance(sc, (int, float)):
            best = doc_best.get(k)
            if best is None or sc > best["score"]:
                doc_best[k] = {"score": float(sc)}
    agreed = {key_of(d) for d in docs_all if d.get("overlap", 0) >= 3} & set(doc_best)
    ret = cr.retain_docs(doc_best, threshold=0.5, relative_margin=retain_margin,
                         top_k_floor=top_k_floor, agreed_keys=agreed, max_kept=18)
    kept_keys = set(ret["kept_keys"])
    for k in sorted(doc_best, key=lambda x: -(doc_best[x]["score"])):
        tr.event("L6", "doc_retention", doc=k[1], best_score=doc_best[k]["score"],
                 segments=doc_segs.get(k, 0), kept=k in kept_keys,
                 signal=("agreement+content" if k in agreed else "content"))
    ranked_all = sorted(survivors, key=lambda s: -(s.get("score") or 0.0))
    # 文档轮转打包: 每篇保留文档先贡献自己的最高分段, 再轮转第二/三段 —
    # 防止单篇高分文档霸占预算, 保证高分文档集合的覆盖面。
    by_doc: dict[tuple[str, str], list[dict]] = {}
    for s in ranked_all:
        k = (str(s.get("kb_id") or ""), str(s.get("doc_path") or ""))
        if k in kept_keys:
            by_doc.setdefault(k, []).append(s)
    doc_order = sorted(by_doc, key=lambda k: -(doc_best.get(k, {}).get("score") or 0.0))
    chunks: list[str] = []
    used, pack_rows = 0, []
    seen_fp: set = set()
    round_idx = 0
    while True:
        added = False
        for k in doc_order:
            segs = by_doc.get(k) or []
            if round_idx >= len(segs):
                continue
            s = segs[round_idx]
            fp = str(s.get("text") or "")[:400]
            if fp in seen_fp:
                continue
            seen_fp.add(fp)
            src = str(s.get("doc_path") or s.get("candidate_id"))
            sec = str(s.get("section_path") or "")
            block = f"[{src + (' · ' + sec if sec else '')}]\n{str(s.get('text') or '').strip()}".strip()
            if used + len(block) > pack_chars:
                continue  # 预算尽: 分数降序轮转, 装不下的低分段落选(审计可查)
            chunks.append(("\n\n" if chunks else "") + block)
            used += len(block)
            pack_rows.append({"doc_path": src, "score": s.get("score"),
                              "candidate_id": s.get("candidate_id")})
            added = True
        if not added:
            break
        round_idx += 1
    t["L6"] = time.perf_counter() - t["L6"]
    tr.event("L6", "done", seconds=round(t["L6"], 2), kept_docs=len(kept_keys),
             pack_blocks=len(pack_rows), pack_chars=used)

    evicted = [{"doc_path": k[1], "best_score": doc_best[k]["score"],
                "segments": doc_segs.get(k, 0)}
               for k in doc_best if k not in kept_keys]
    result = {
        "query": query, "shelves": shelves,
        "real_engine": real_engine, "status": jev1.get("status"),
        "criterion": jev1.get("criterion"), "threshold": jev1.get("threshold"),
        "phase_s": {k: round(v, 2) for k, v in t.items()},
        "tier_counts": {"docs_listed": len(docs_all), "read_planned": len(read_plan),
                        "docs_read": len(read_docs),
                        "full_reads": len([d for d in read_docs if d.get("read_kind") == "full"]),
                        "head_reads": len([d for d in read_docs if d.get("read_kind") == "head"]),
                        "peeked_docs": peek_stats["peeked"],
                        "promoted_docs": peek_stats["promoted"],
                        "candidates": jev1.get("candidate_count"),
                        "scored": jev1.get("scored_count") + ((jev2 or {}).get("scored_count") or 0),
                        "survivors_all_yes": len(survivors),
                        "retained_docs": len(kept_keys),
                        "evicted_docs": len(evicted),
                        "pack_blocks": len(pack_rows), "pack_chars": used},
        "retention": ret,
        "evicted": evicted,
        "promote_cut": peek_stats["promote_cut"],
        "pack": "\n\n".join(chunks),
        "pack_rows": pack_rows,
        "scores": score_rows,
        "survivors_summary": [{"doc_path": s.get("doc_path"), "score": s.get("score"),
                               "candidate_id": s.get("candidate_id")} for s in survivors],
    }
    (out_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "pack.txt").write_text(result["pack"], encoding="utf-8")
    return result
