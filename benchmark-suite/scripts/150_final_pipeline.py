#!/usr/bin/env python3
r"""150_final_pipeline.py — 论文终测一键流水线（gate → run → grade → assert）.

为什么有这个脚本（2026-10-13 新增）
-----------------------------------
论文（paper_demo/tex）的实验数字来自**两个不同时代的通道**，此前没有任何
单一入口能一次性跑完并自证：

  * `exp_r2_grade.json` / `R2-EXP-3TRACK-REPORT.md` ← `scripts/107_exp_grade.py`
    （三轨 a2/b/c，确定性判分）；
  * `r2_pipeline_100.json` ← `scripts/108_pipeline_evidence.py`
    （100 篇语料 / 322 parts / 33 存储单元 / 4,528 chunks 的入库-整理证据）；
  * 论文里的 `cited`（part/section/table 引用数）此前**只存在于 `main.tex`
    注释里的一段临时正则**，仓库无脚本可复算——本脚本把它固化为
    `scripts/107_exp_grade.py` 的第三项判分（见 `_paper_numbers.py`）。

本脚本把上面三段合成**一条可复现命令**，并在每一步 fail-closed：

  Gate 0 平台      backend/web/token 三通（token 过期自动刷新）
  Gate 1 kb-mcp    **stdio 工具面真实可初始化**（论文复现最脆的一环：
                   平台轨若挂不上 MCP，会静默退化为"无工具凭记忆作答"）
  Gate 2 语料      100 篇 corpus_md + 5 门类库 + Corpus-Chunks800（4,528 chunks）
  Gate 3 题集      qa_questions_r2.json / qa_questions.json 字段完整性
  Stage run        三轨 a2,b,c 真实执行（chat API，harness=claude）
  Stage scan       哨兵扫描 KB_TOOLS_NOT_READY / KB_NO_RETRIEVAL / 空答 → 报告
  Stage grade      107 确定性判分（gold 证据 + ≥60% 关键词 + 引用标记）
  Stage assert     _paper_numbers.py：运行产物 ↔ 论文 \NUM* 宏 + 硬编码数字逐条对账

用法（在 benchmark-suite/ 下）
    python scripts/150_final_pipeline.py                 # 全流程（真实执行，约 1-2h）
    python scripts/150_final_pipeline.py --check         # 只跑 Gate 0-3（不跑实验）
    python scripts/150_final_pipeline.py --skip-run --run <run_id>   # 只判分+对账
    python scripts/150_final_pipeline.py --retry-sentinel --run <run_id>
    python scripts/150_final_pipeline.py --assert-only --run <run_id>

完整跑一轮论文终测的推荐顺序（前置 = 语料，本脚本 = 实验）：
    1) python scripts/150_final_pipeline.py --check        # 先看 Gate（1 分钟内）
    2) （若 Gate 2 报密索引为空）
       python scripts/106_exp_corpus_r2.py --dry-run        # 只读盘点
       python scripts/106_exp_corpus_r2.py --reuse-export   # 复用已核验导出 + 重建索引
    3) python scripts/150_final_pipeline.py                # 三轨真实执行 + 判分 + 对账
    4) python scripts/108_pipeline_evidence.py             # 入库/整理证据（Table 1 那一半）

退出码：0 全过；1 有 fail（Gate/对账/哨兵任一失败）。
产出：results/final_run.json（本轮完整状态）+ results/paper_numbers.json
      （论文数字对账表，供 `scripts/117_pipeline_selfcheck.py` 与投稿前复核）。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"
RUNS = RESULTS / "runs"
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "experiments"))

OK, WARN, FAIL, SKIP = "ok", "warn", "fail", "skip"
_STATE: dict = {"gates": [], "stages": []}


def log(name: str, status: str, detail: str = "") -> None:
    icon = {OK: "✓", WARN: "!", FAIL: "✗", SKIP: "·"}[status]
    print(f"  {icon} {name:<30} {detail}", flush=True)


def gate(name: str, status: str, detail: str = "") -> None:
    _STATE["gates"].append({"name": name, "status": status, "detail": detail})
    log(name, status, detail)


def stage(name: str, status: str, detail: str = "") -> None:
    _STATE["stages"].append({"name": name, "status": status, "detail": detail})
    log(name, status, detail)


def section(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


# ── Gate 0 — 平台 ───────────────────────────────────────────────────────────
def gate_platform() -> bool:
    from lib import BACKEND, WEB, check_token

    ok_all = True
    try:
        ok, state = check_token(WEB)
    except Exception as e:  # noqa: BLE001
        ok, state = False, f"error:{type(e).__name__}"
    gate("token", OK if ok else FAIL, state)
    ok_all &= ok

    for label, url in (("backend", f"{BACKEND}/api/v1/health"), ("web", f"{WEB}/")):
        try:
            with urllib.request.urlopen(url, timeout=6) as r:  # noqa: S310
                good = r.status < 500
        except Exception as e:  # noqa: BLE001
            good = False
            gate(label, FAIL, f"{url} → {type(e).__name__}")
        else:
            gate(label, OK if good else FAIL, url)
        ok_all &= good
    return ok_all


# ── Gate 1 — kb-mcp stdio 工具面（论文复现的红线） ──────────────────────────
def gate_mcp() -> bool:
    from lib import McpClient

    t0 = time.perf_counter()
    mc = None
    try:
        mc = McpClient()
        tools = mc.call("kb_list", {"lightweight": True}, timeout=180)
        names = [k.get("name") for k in (tools.get("catalog") or [])]
        dt = round(time.perf_counter() - t0, 1)
        gate("kb-mcp stdio 工具面", OK if names else FAIL,
             f"{len(names)} KB · 初始化 {dt}s")
        _STATE["kb_names"] = names
        return bool(names)
    except Exception as e:  # noqa: BLE001
        gate("kb-mcp stdio 工具面", FAIL, f"{type(e).__name__}: {str(e)[:160]}")
        return False
    finally:
        if mc:
            mc.close()


def _mcp_client():
    from lib import McpClient
    return McpClient()


# ── Gate 2 — 语料 ───────────────────────────────────────────────────────────
CATEGORIES = ("计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
              "工程与能源", "经济与社会")


def gate_corpus() -> bool:
    """论文语料门：100 篇导出 + 五门类库 322 docs + 密索引真的可检索。

    为什么查密度索引的 live probe：`Corpus-Chunks800` 的 doc_count 恒为 0
    （index_kb.build_kb 走 kb_index_document 直传 content，不落 tree-fs），
    所以 doc_count 不能当健康指标；2026-10-13 就是这样漏掉了一次真实损坏——
    集合被清空、检索恒返回空，而 doc_count 看起来"正常"。唯一可信的判据是
    真发一次 kb_search_vector 看有没有命中。
    """
    ok = True
    md = sorted((SUITE / "data" / "corpus_md").glob("*.md"))
    gate("corpus_md 100 篇", OK if len(md) >= 100 else FAIL, f"{len(md)} 篇")
    ok &= len(md) >= 100

    # manifest ↔ 导出目录对账：导出残缺则 Track B/C 的证据面是假的
    try:
        man = json.loads((SUITE / "data" / "papers" / "manifest.json")
                         .read_text(encoding="utf-8"))
        slugs = {Path(str(p.get("pdf", ""))).stem for p in man.get("papers", [])}
        missing = sorted(slugs - {p.stem for p in md})
        gate("manifest ↔ corpus_md", OK if not missing else FAIL,
             f"{len(slugs)} 篇 · 缺导出 {len(missing)}"
             + (f": {missing[:3]}" if missing else ""))
        ok &= not missing
    except Exception as e:  # noqa: BLE001
        gate("manifest ↔ corpus_md", FAIL, f"{type(e).__name__}: {str(e)[:120]}")
        ok = False

    try:
        mc = _mcp_client()
        try:
            kb = mc.call("kb_list", {"lightweight": True}, timeout=180)
            cat = {k.get("name"): k for k in (kb.get("catalog") or [])}
            dist = {c: (cat.get(c) or {}).get("doc_count") for c in CATEGORIES}
            tot_docs = sum(int(v or 0) for v in dist.values())
            gate("五门类库 322 docs（论文 Table 1）", OK if tot_docs >= 322 else FAIL,
                 f"{tot_docs} docs · " + " · ".join(f"{c[:6]}={v}" for c, v in dist.items()))
            ok &= tot_docs >= 322

            # 密索引：live probe（c 臂 / vector·rrf baseline 的证据面）
            chunks = cat.get("Corpus-Chunks800")
            hits = 0
            if chunks:
                p = mc.call("kb_search_vector",
                            {"query": "probe study", "kb_id": "Corpus-Chunks800",
                             "top_k": 3}, timeout=300)
                hits = len(p.get("results") or [])
            gate("Corpus-Chunks800 可检索（live probe）",
                 OK if hits else FAIL,
                 f"probe hits={hits}"
                 + ("" if hits else " → 密索引为空：c 臂/baseline 无证据，"
                                    "先跑 python scripts/106_exp_corpus_r2.py 重建"))
            ok &= bool(hits)

            stats = mc.call("kb_search_stats", {}, timeout=300).get("stats") or {}
            cols = stats.get("collections") or []
            tot = sum(int(c.get("chunk_count") or c.get("count") or 0) for c in cols)
            gate("全库 chunks（信息项）", OK if tot else WARN,
                 f"{tot} chunks · {len(cols)} collections")
            _STATE["corpus"] = {
                "corpus_md": len(md), "category_docs": tot_docs,
                "chunks800_probe_hits": hits, "total_chunks": tot,
                "chunks800_doc_count": (chunks or {}).get("doc_count")}
        finally:
            mc.close()
    except Exception as e:  # noqa: BLE001
        gate("语料探活", FAIL, f"{type(e).__name__}: {str(e)[:160]}")
        ok = False
    return ok


# ── Gate 3 — 题集 ───────────────────────────────────────────────────────────
def gate_questions(qfile: str) -> bool:
    p = SUITE / qfile
    if not p.exists():
        gate("题集", FAIL, f"{qfile} 不存在")
        return False
    qs = json.loads(p.read_text(encoding="utf-8"))["questions"]
    miss = [q.get("qid") for q in qs
            if not (q.get("arxiv_id") and q.get("gold_keywords"))]
    n_kw = [len(q.get("gold_keywords") or []) for q in qs]
    gate("题集", OK if not miss else FAIL,
         f"{qfile} · {len(qs)} 题 · 关键词/题 {min(n_kw)}-{max(n_kw)}"
         + (f" · 缺字段 {miss}" if miss else ""))
    return not miss


# ── Stage run — 三轨真实执行 ────────────────────────────────────────────────
def stage_run(run_dir: Path | None, qfile: str, tracks: str, max_turns: int,
              limit: int, retry_sentinel: bool) -> Path | None:
    section("Stage run — 三轨真实执行（chat API，harness=claude）")
    if run_dir and retry_sentinel:
        n = reset_sentinel(run_dir)
        stage("哨兵单元重置", OK if n else SKIP, f"{n} 个失败单元标记为待重跑")
    cmd = [sys.executable, str(SUITE / "experiments" / "runner.py"),
           "--questions", qfile, "--tracks", tracks, "--limit", str(limit),
           "--max-turns", str(max_turns)]
    if run_dir:
        cmd += ["--out-dir", str(run_dir)]
    t0 = time.perf_counter()
    print("  $ " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=str(SUITE))
    dt = round(time.perf_counter() - t0, 1)
    if r.returncode != 0:
        stage("三轨执行", FAIL, f"exit {r.returncode} · {dt}s")
        return None
    target = run_dir or newest_run()
    stage("三轨执行", OK, f"{target.name} · {dt}s")
    return target


def newest_run() -> Path | None:
    cands = [d for d in RUNS.glob("run-*") if d.is_dir()
             and not d.name.startswith(".") and "chatmodes" not in d.name]
    return max(cands, key=lambda d: (d.stat().st_mtime, d.name)) if cands else None


# ── Stage scan — 哨兵扫描 / 失败单元重置 ────────────────────────────────────
SENTINELS = ("KB_TOOLS_NOT_READY", "KB_NO_RETRIEVAL")


def scan_cells(run_dir: Path) -> dict:
    """逐单元扫描：哨兵 / 空答 / error / 零工具。返回分类统计。"""
    buckets: dict[str, list[str]] = {k: [] for k in
                                     ("sentinel", "empty", "error", "zero_tools")}
    cells = sorted(run_dir.glob("track_*.json"))
    for f in cells:
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            buckets["error"].append(f.name)
            continue
        ans = str(r.get("answer") or "")
        if any(s in ans for s in SENTINELS):
            buckets["sentinel"].append(f.name)
        elif r.get("error") or r.get("is_error"):
            buckets["error"].append(f.name)
        elif not ans.strip():
            buckets["empty"].append(f.name)
        elif ((r.get("tool_call_count") or 0) == 0
              and str(r.get("track")) in ("a", "a2")):
            # 平台轨无工具面调用 = 无效数据（b/c 轨允许零工具如实拒答）
            buckets["zero_tools"].append(f.name)
    return {"cells": len(cells), **{k: v for k, v in buckets.items()},
            "bad": sum(len(v) for v in buckets.values())}


def reset_sentinel(run_dir: Path) -> int:
    s = scan_cells(run_dir)
    bad = set(s["sentinel"]) | set(s["empty"]) | set(s["error"])
    for name in bad:
        try:
            (run_dir / name).unlink()
        except OSError:
            pass
    return len(bad)


def stage_scan(run_dir: Path) -> bool:
    section("Stage scan — 哨兵扫描（平台轨工具面失败 = 无效数据）")
    s = scan_cells(run_dir)
    stage("单元数", OK if s["cells"] else FAIL, f"{s['cells']} cells in {run_dir.name}")
    clean = s["bad"] == 0
    stage("哨兵/空答/error", OK if clean else FAIL,
          f"sentinel={len(s['sentinel'])} empty={len(s['empty'])} "
          f"error={len(s['error'])}")
    if s["zero_tools"]:
        stage("a2 零工具单元", WARN,
              f"{len(s['zero_tools'])}: {', '.join(n.split('_')[-1] for n in s['zero_tools'])}")
    _STATE["scan"] = s
    return clean


# ── Stage grade — 107 确定性判分 ────────────────────────────────────────────
def stage_grade(run_dir: Path, qfile: str) -> bool:
    section("Stage grade — 确定性判分（gold 证据 + ≥60% 关键词 + 引用标记）")
    cmd = [sys.executable, str(SUITE / "scripts" / "107_exp_grade.py"),
           "--run", run_dir.name, "--qfile", qfile]
    r = subprocess.run(cmd, cwd=str(SUITE), capture_output=True, text=True)
    out = (r.stdout or "").strip().splitlines()
    if r.returncode != 0:
        stage("107 判分", FAIL, (r.stderr or "").strip()[:200])
        return False
    stage("107 判分", OK, out[0] if out else "")
    return True


def _finding(run_dir: Path) -> str:
    """运行器写盘的「发现文件」：agent 轨是 track_*.json；老式检索臂是 arm_*.json。"""
    if list(run_dir.glob("track_*.json")):
        return "track_*.json"
    if list(run_dir.glob("arm_*.json")):
        return "arm_*.json"
    return ""


def paper_numbers_for(run_dir: Path) -> tuple[dict, list]:
    """对账一个 run 目录：自动挑与 run 题号匹配的题集，再与论文数字逐条比较。"""
    import _paper_numbers as pn

    g = pn.grade_run(run_dir, pn.pick_qfile(run_dir))
    return g, pn.compare(pn.paper_values(), g["grades"], run_dir, rows=g["rows"])


# ── Stage assert — 论文数字对账 ─────────────────────────────────────────────
def stage_assert(run_dir: Path) -> bool:
    section("Stage assert — 运行产物 ↔ 论文数字（\\NUM* 宏 + 表格硬编码）")
    import _paper_numbers as pn

    if not _finding(run_dir):
        stage("发现文件", FAIL, f"{run_dir.name} 内既无 track_*.json 也无 arm_*.json")
        return False
    qf = pn.pick_qfile(run_dir)
    rows = pn.grade_run(run_dir, qf)
    paper = pn.paper_values()
    checks = pn.compare(paper, rows["grades"], run_dir, rows=rows["rows"])
    (RESULTS / "paper_numbers.json").write_text(
        json.dumps({"run_dir": run_dir.name, "finding": _finding(run_dir),
                    "question_file": qf.name, "paper": paper,
                    "observed": rows["grades"],
                    "citation_definition": pn.CITE_DEF,
                    "citation_definition_dense": pn.CITE_DEF_DENSE,
                    "checks": checks}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    n_fail = 0
    for c in checks:
        st = OK if c["ok"] else FAIL
        n_fail += 0 if c["ok"] else 1
        log(f"{c['claim']:<22}", st,
            f"论文 {c['paper']} · 实测 {c['observed']} {c['detail']}".strip())
    stage("论文数字对账", OK if not n_fail else FAIL, f"{len(checks) - n_fail}/{len(checks)} 条一致")
    _STATE["checks"] = checks
    return not n_fail


# ── main ────────────────────────────────────────────────────────────────────
def resolve_run_arg(arg: str) -> Path | None:
    """`--run` 同时接受「目录名 / 相对路径 / 绝对路径」（与 107 的 --run 口径一致）。

    历史坑：只按 `RUNS / args.run` 拼接时，`--run results\\runs\\run-xxx` 会拼成
    `results/runs/results/runs/run-xxx`，然后报「results/runs/ 下没有可用 run」——
    对账命令明明写对了却跑不动。
    """
    if not arg:
        return None
    for cand in (RUNS / arg, RESULTS / arg, SUITE / arg, Path(arg)):
        try:
            if cand.is_dir():
                return cand.resolve()
        except OSError:
            continue
    return RUNS / arg  # 交给后面的存在性检查报错


def main() -> int:
    ap = argparse.ArgumentParser(
        description="论文终测一键流水线（gate → run → grade → assert）")
    ap.add_argument("--run", default="", help="指定已有 run 目录名（默认最新）")
    ap.add_argument("--questions", default="data/papers/qa_questions.json",
                    help="题集（论文口径 = qa_questions.json；快速冒烟用 qa_questions_r2.json）")
    ap.add_argument("--tracks", default="a2,b,c")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--check", action="store_true", help="只跑 Gate，不执行实验")
    ap.add_argument("--skip-run", action="store_true", help="跳过 run，直接判分+对账")
    ap.add_argument("--assert-only", action="store_true", help="只对账")
    ap.add_argument("--retry-sentinel", action="store_true",
                    help="重跑哨兵/空答/error 单元（配套 --run 或新轮次前清场）")
    args = ap.parse_args()

    t0 = time.perf_counter()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"论文终测流水线 · {stamp}\nbenchmark-suite: {SUITE}")

    run_dir = resolve_run_arg(args.run)

    if not args.assert_only:
        section("Gate 0 — 平台就绪")
        g0 = gate_platform()
        section("Gate 1 — kb-mcp stdio 工具面")
        g1 = gate_mcp()
        section("Gate 2 — 语料（100 篇 / 五门类库 / Chunks800）")
        g2 = gate_corpus()
        section("Gate 3 — 题集")
        g3 = gate_questions(args.questions)

        if g1 and not (g0 and g2 and g3):
            print("\n[!] Gate 1 通过但其他 Gate 未过 —— 平台轨可跑，语料/平台需先修")
        if not (g0 and g1):
            print("\n[✗] Gate 0/1 未过：先 `ragctl up` 并用 "
                  "`uv run --directory kb-mcp python server.py` 手动验一次 kb-mcp，"
                  "否则平台轨 (a2) 会静默退化 —— 这正是 2026-09-30 轮 BQ03/BQ10 "
                  "两次 grounding 失败的原因。")
            _STATE.update({"started_utc": stamp, "seconds": round(time.perf_counter() - t0, 1),
                           "verdict": "gates_failed"})
            (RESULTS / "final_run.json").write_text(
                json.dumps(_STATE, ensure_ascii=False, indent=1), encoding="utf-8")
            return 1
        if args.check:
            print("\n[ok] --check 完成（未执行实验）")
            _STATE.update({"started_utc": stamp, "verdict": "gates_only",
                           "seconds": round(time.perf_counter() - t0, 1)})
            (RESULTS / "final_run.json").write_text(
                json.dumps(_STATE, ensure_ascii=False, indent=1), encoding="utf-8")
            return 0

    if not args.assert_only and not args.skip_run:
        run_dir = stage_run(run_dir, args.questions, args.tracks, args.max_turns,
                            args.limit, args.retry_sentinel)
        if run_dir is None:
            return 1
    if run_dir is None:
        run_dir = newest_run()
    if run_dir is None or not run_dir.exists():
        stage("定位 run 目录", FAIL, "results/runs/ 下没有可用 run")
        return 1
    print(f"\n[run] {run_dir}")

    ok_scan = ok_grade = ok_assert = True
    if not args.assert_only:
        ok_scan = stage_scan(run_dir)
        ok_grade = stage_grade(run_dir, args.questions)
        if not ok_grade:
            return 1
    ok_assert = stage_assert(run_dir)

    verdict = "pass" if (ok_scan and ok_grade and ok_assert) else "fail"
    print(f"\n===== 结论: {verdict} =====")
    if not ok_scan:
        print("  哨兵单元存在 → 平台轨工具面不稳定：先修 kb-mcp 挂载再重跑"
              "（`--retry-sentinel` 可只重跑失败单元）")
    if not ok_assert:
        print("  对账有差异 → 见 results/paper_numbers.json；"
              "要么重跑，要么按实测更新论文宏并注明")
    _STATE.update({"run_dir": run_dir.name, "question_file": args.questions,
                   "started_utc": stamp, "verdict": verdict,
                   "seconds": round(time.perf_counter() - t0, 1)})
    (RESULTS / "final_run.json").write_text(
        json.dumps(_STATE, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n产出: results/final_run.json · results/paper_numbers.json · "
          f"{run_dir.name}/SUMMARY.md · results/exp_r2_grade.json")
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
