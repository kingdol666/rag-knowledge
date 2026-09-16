#!/usr/bin/env python3
"""复现自检 — 校验 algorithms 项目能否复现 DeepRead Table 1 全部 8 个算法。

做三件事(全部只读, 不产生任何新的 LLM 调用):
  1. 静态: 语料(148 篇 SciFact) / 冻结查询(30 条) / 算法注册表(8 个) / 缓存完整性;
  2. 在线: 启动的 api_server(127.0.0.1:8790) 对每个算法各答 1 题, 校验返回指标;
  3. 一致性: 把在线结果的检索层指标与论文数据快照
     (docs/paper/cikm/data-snapshot/deepread_matrix.json) 逐字段核对。

用法:
    python verify_reproduction.py            # 每个算法查 1 题(sf-001)
    python verify_reproduction.py --qid sf-003 --limit 3
退出码 0 = 全部通过。
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent
ROOT = SUITE.parent
SNAPSHOT = ROOT / "docs" / "paper" / "cikm" / "data-snapshot" / "deepread_matrix.json"
API = "http://127.0.0.1:8790"

# Windows 控制台默认 GBK, 中文/勾叉会炸; 统一改 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

METRIC_KEYS = ["recall@1", "hit@1", "recall@5", "hit@5", "recall@10",
               "hit@10", "ndcg@10", "precision@5", "mrr"]


def _guard(url: str) -> None:
    """预检请求目标: 仅允许本机 API 基址(SSRF 加固, 请求前显式校验)。"""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"blocked scheme: {parts.scheme!r} ({url})")
    if (parts.hostname or "").lower() not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError(f"blocked non-loopback host: {parts.hostname!r} ({url})")


def _get(path: str) -> dict:
    url = API + path
    _guard(url)
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310
        return json.loads(r.read().decode("utf-8"))


def _post(path: str, payload: dict, timeout: int = 900) -> dict:
    url = API + path
    _guard(url)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qid", default="sf-001")
    ap.add_argument("--limit", type=int, default=1, help="每个算法检查的题目数")
    args = ap.parse_args()

    failures: list[str] = []
    print("=" * 74)
    print("Step 1 — 静态自检")
    print("=" * 74)

    sys.path.insert(0, str(HERE))
    from corpus import load_corpus, load_queries  # noqa: E402
    from methods import METHODS  # noqa: E402
    from run_matrix import METHOD_ORDER  # noqa: E402

    corpus = load_corpus()
    queries = load_queries()
    print(f"  语料      : {len(corpus)} 篇 (expect 148)")
    print(f"  冻结查询  : {len(queries)} 条 (expect 30)")
    print(f"  算法注册表: {len(METHOD_ORDER)} 个 -> {', '.join(METHOD_ORDER)}")
    if len(corpus) != 148:
        failures.append(f"corpus {len(corpus)} != 148")
    if len(queries) != 30:
        failures.append(f"queries {len(queries)} != 30")
    if len(METHOD_ORDER) != 8:
        failures.append(f"methods {len(METHOD_ORDER)} != 8")
    missing_impl = [m for m in METHOD_ORDER if m not in METHODS]
    if missing_impl:
        failures.append(f"未实现的方法: {missing_impl}")

    cache = HERE / "cache"
    for kind in ("ev", "ans", "judge"):
        got = len(list(cache.glob(f"{kind}_*_*.json")))
        print(f"  缓存 {kind}_*: {got} 个")
        if got < 8 * 30:
            failures.append(f"cache {kind} 不完整: {got} < 240")

    print()
    print("=" * 74)
    print("Step 2 — 在线自检 (api_server 127.0.0.1:8790)")
    print("=" * 74)
    try:
        health = _get("/health")
    except (urllib.error.URLError, OSError) as exc:
        print(f"  ✗ api_server 不可达: {exc}")
        print("    先运行: python api_server.py &")
        return 2
    print(f"  /health  : {health['status']} | methods={len(health['methods'])} "
          f"| queries={health['queries']} | corpus={health['corpus']}")
    if health["status"] != "ok":
        failures.append("health != ok")
    methods_api = _get("/methods")
    print(f"  /methods : {len(methods_api['methods'])} 个算法, "
          f"{len(methods_api['paper_mapping'])} 条论文对应")
    questions = _get("/questions")
    qlist = questions.get("queries") or questions.get("questions") or []
    print(f"  /questions: {len(qlist)} 条")

    qids = [args.qid] + [q["qid"] for q in queries
                         if q["qid"] != args.qid][: max(0, args.limit - 1)]
    qids = qids[: args.limit]
    print(f"  检查题目: {qids}")

    live: dict[str, dict] = {}
    for m in METHOD_ORDER:
        row = {}
        for qid in qids:
            try:
                res = _post("/ask", {"method": m, "qid": qid, "judge": False})
            except (urllib.error.URLError, OSError) as exc:
                failures.append(f"{m}/{qid} 调用失败: {exc}")
                print(f"  ✗ {m:<17} {qid}  调用失败: {exc}")
                continue
            row[qid] = res
            n_ev = len(res.get("evidence_sources") or res.get("evidence") or [])
            ans = res.get("answer") or ""
            ans = ans if isinstance(ans, str) else json.dumps(ans, ensure_ascii=False)
            print(f"  ✓ {m:<17} {qid}  ndcg@10={res['metrics'].get('ndcg@10')} "
                  f"hit@1={res['metrics'].get('hit@1')} evidence={n_ev} "
                  f"answer={len(ans)}ch")
            if not ans.strip():
                failures.append(f"{m}/{qid} 回答为空")
            if not res.get("metrics"):
                failures.append(f"{m}/{qid} 无检索指标")
        live[m] = row

    print()
    print("=" * 74)
    print("Step 3 — 与论文数据快照一致性核对")
    print("=" * 74)
    if not SNAPSHOT.exists():
        print(f"  ! 快照不存在: {SNAPSHOT} — 跳过")
        failures.append("snapshot missing")
    else:
        snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        rrows = snap.get("retrieval_rows") or {}
        n_rows = sum(len(v) for v in rrows.values())
        print(f"  快照: {SNAPSHOT.name} ({SNAPSHOT.stat().st_size} bytes, "
              f"{len(rrows)} 方法 × {n_rows} 条检索行)")
        index = {(m, r.get("qid")): r for m, rows_ in rrows.items() for r in rows_}
        checked = agree = 0
        for m, row in live.items():
            for qid, res in row.items():
                ref = index.get((m, qid))
                if not ref:
                    continue
                for k in METRIC_KEYS:
                    if k not in ref or k not in res["metrics"]:
                        continue
                    checked += 1
                    a, b = float(ref[k]), float(res["metrics"][k])
                    if abs(a - b) <= 1e-9:
                        agree += 1
                    else:
                        failures.append(f"{m}/{qid} {k}: snapshot={a} live={b}")
        if checked:
            pct = 100.0 * agree / checked
            print(f"  指标逐字段核对: {agree}/{checked} 一致 ({pct:.1f}%)")
            if agree != checked:
                failures.append(f"指标不一致 {checked - agree}/{checked}")
        else:
            print("  ! 快照中没有可对比的 (method,qid) 行")

    print()
    print("=" * 74)
    if failures:
        print(f"✗ 复现自检未通过 — {len(failures)} 个问题:")
        for f in failures[:40]:
            print(f"    - {f}")
        return 1
    print("✓ 复现自检全部通过 — 8 个算法均可复现、可作答、指标与论文快照一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
