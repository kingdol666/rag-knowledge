#!/usr/bin/env python3
"""MCP 集成基准评测 — 通过 kb-mcp MCP 协议（stdio）按 knowledgebase-search skill 规程测试.

与 run_domain_eval.py (HTTP 直调) 的区别: 本脚本启动真正的 kb-mcp MCP 服务器
（.zcode/mcp.json 同款命令: uv run --directory kb-mcp python server.py），
用 JSON-RPC tools/call 驱动 —— 验证的是 Agent 实际使用的 MCP 工具层。

流程 = knowledgebase-search SKILL.md 的 QDCVR 规程:
  Pre-Flight  kb_project_status            (skill 强制门)
  Step 1      kb_list(lightweight=true)    选库上下文
  Step 2      kb_search_two_stage          (balance_kbs=True, skill 默认)
  Step 2.5    硬阈值 0.35 + 文档级去重     (skill 铁律, 两种口径都报)
  Step 3      kb_doc_read 内容验证抽样     (0-8 rubric, top-1 抽检)

用法:
  python run_mcp_eval.py                    # 领域 50 查询 × skill/raw 双口径
  python run_mcp_eval.py --track1 20        # 追加 FlashRAG hotpotqa 冒烟(经 MCP)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SCRIPTS_DIR))
from bench_http import validated_url  # noqa: E402

QUERIES_FILE = REPO_ROOT / "docs" / "paper" / "benchmark" / "datasets" / "queries.json"
BENCH_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks"
RESULTS_DIR = SCRIPTS_DIR.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLD = 0.35  # skill Step 2.5 硬阈值


class McpClient:
    """最小 MCP stdio 客户端: initialize → tools/list → tools/call."""

    def __init__(self, repo_root: Path):
        env = dict(os.environ)
        env.setdefault("PYTHONUTF8", "1")
        token_path = repo_root / ".env"
        if "MCP_AUTH_TOKEN" not in env and token_path.exists():
            for line in token_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("MCP_AUTH_TOKEN="):
                    env["MCP_AUTH_TOKEN"] = line.split("=", 1)[1].strip()
        self.proc = subprocess.Popen(
            ["uv", "run", "--directory", "kb-mcp", "python", "server.py"],
            cwd=str(repo_root), env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1)
        self._id = 0
        self._initialize()

    def _send(self, obj: dict) -> None:
        assert self.proc.stdin
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _recv(self, want_id: int, timeout: float = 120.0) -> dict:
        assert self.proc.stdout
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want_id:
                if "error" in msg:
                    raise RuntimeError(f"MCP error: {msg['error']}")
                return msg["result"]
        raise TimeoutError(f"MCP 响应超时 (id={want_id})")

    def _initialize(self) -> None:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "qdcvr-bench", "version": "1.0"}}})
        self._recv(self._id)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def list_tools(self) -> list[dict]:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": "tools/list"})
        return self._recv(self._id).get("tools", [])

    def call(self, name: str, arguments: dict | None = None, timeout: float = 120.0) -> dict:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments or {}}})
        result = self._recv(self._id, timeout)
        if result.get("isError"):
            raise RuntimeError(f"tool {name} error: {json.dumps(result)[:300]}")
        for block in result.get("content", []):
            if block.get("type") == "text":
                text = block["text"]
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"raw": text}
        return {}

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def step25_dedup_threshold(results: list[dict], threshold: float = THRESHOLD) -> list[dict]:
    """skill Step 2.5: 硬阈值丢弃 + 文档级去重(同文档留最高分)。"""
    best_by_doc: dict[str, dict] = {}
    for r in results:
        if float(r.get("score", 0)) < threshold:
            continue
        dp = str(r.get("doc_path", ""))
        if dp not in best_by_doc or float(r["score"]) > float(best_by_doc[dp]["score"]):
            best_by_doc[dp] = r
    return sorted(best_by_doc.values(), key=lambda r: -float(r["score"]))


def eval_top(results: list[dict], golden_frags: set[str], golden_kb: str) -> dict:
    top5 = results[:5]
    hits = [1 if any(f in str(r.get("doc_path", "")).lower() for f in golden_frags) else 0
            for r in top5]
    hits += [0] * (5 - len(hits))
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits))
    idcg = sum(1 / math.log2(i + 2) for i in range(min(sum(hits), 5))) or 1.0
    rr = next((1.0 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
    kb_ids = [str(r.get("kb_id", "")) for r in top5]
    return {"p1": hits[0], "p5": sum(hits) / 5, "mrr": rr,
            "ndcg5": dcg / idcg, "routing": int(golden_kb in kb_ids) if golden_kb else 0,
            "fpr": (sum(1 for k in kb_ids if k and k != golden_kb) / 5) if golden_kb else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track1", type=int, default=0,
                    help="追加 FlashRAG 数据集冒烟条数(经 MCP, golden 标记在当前语料必然 0 命中, 仅验证链路)")
    ap.add_argument("--track1-dataset", default="hotpotqa")
    args = ap.parse_args()

    print("启动 kb-mcp MCP 服务器 (stdio) ...", flush=True)
    client = McpClient(REPO_ROOT)
    report: dict = {"timestamp": datetime.now(timezone.utc).isoformat(),
                    "transport": "MCP stdio (uv run --directory kb-mcp python server.py)",
                    "skill": "knowledgebase-search QDCVR 六步规程"}

    # ── Pre-Flight: kb_project_status (skill 强制门) ──
    status = client.call("kb_project_status", {"scope": "runtime"})
    report["preflight_kb_project_status"] = {k: status.get(k) for k in
                                             list(status)[:8]}
    print(f"Pre-Flight kb_project_status: {json.dumps(report['preflight_kb_project_status'], ensure_ascii=False)[:220]}")

    # ── 工具清单核验 ──
    tools = {t["name"] for t in client.list_tools()}
    required = ["backend_status", "kb_list", "kb_search_two_stage",
                "kb_search_vector", "kb_search_stats", "kb_doc_read"]
    missing = [t for t in required if t not in tools]
    report["mcp_tools_total"] = len(tools)
    report["mcp_tools_missing"] = missing
    print(f"MCP 工具数: {len(tools)}, 缺失: {missing or '无'}")

    # ── Step 1: kb_list 选库上下文 ──
    kb_list = client.call("kb_list", {"lightweight": True})
    kbs = (kb_list if isinstance(kb_list, list)
           else kb_list.get("catalog") or kb_list.get("kbs") or kb_list.get("results") or [])
    report["kb_count_via_mcp"] = len(kbs)
    print(f"Step 1 kb_list(lightweight): {report['kb_count_via_mcp']} KB")

    # ── Step 2-2.5: 领域 50 查询 × {skill(threshold+dedup), raw} 双口径 ──
    samples = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
    # KB 名 → uuid (MCP kb_list catalog: {kb_id, name, path, ...})
    name2uuid = {}
    for kb in kbs:
        nm = kb.get("name") or kb.get("path")
        uid = kb.get("kb_id") or kb.get("id")
        if nm and uid:
            name2uuid[nm] = uid

    def run_mode(mode: str) -> tuple[list[dict], list[float]]:
        per_q, lats = [], []
        for i, s in enumerate(samples):
            import time as _t
            t0 = _t.perf_counter()
            resp = client.call("kb_search_two_stage",
                               {"query": s["query"], "kb_id": "",
                                "balance_kbs": True, "top_k": 20})
            lats.append((_t.perf_counter() - t0) * 1000)
            results = (resp.get("stage2", {}).get("results")
                       or resp.get("results") or [])
            if mode == "skill":
                results = step25_dedup_threshold(results)
            golden_frags = {d.lower().removesuffix(".md") for d in s.get("relevant_docs", [])}
            golden_kb = name2uuid.get(s.get("expected_kb", ""), "")
            m = eval_top(results, golden_frags, golden_kb)
            m["qid"] = s["qid"]
            per_q.append(m)
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(samples)}] {mode} MRR="
                      f"{statistics.mean(x['mrr'] for x in per_q):.3f}", flush=True)
        return per_q, lats

    print(f"\nStep 2-2.5 领域集 {len(samples)} 查询 × 2 口径 (经 MCP tools/call):", flush=True)
    report["domain"] = {}
    per_mode_scores: dict[str, list[float]] = {}
    for mode in ("skill", "raw"):
        per_q, lats = run_mode(mode)
        per_mode_scores[mode] = [x["ndcg5"] for x in per_q]
        agg = {k: round(statistics.mean(x[k] for x in per_q), 4)
               for k in ["p1", "p5", "mrr", "ndcg5", "routing", "fpr"]}
        agg["latency_ms"] = round(statistics.mean(lats), 1)
        report["domain"][mode] = agg
        print(f"  [{mode}] {json.dumps(agg)}")

    # skill 口径 vs raw 口径 配对检验（Step 2.5 门控的贡献）
    a, b = per_mode_scores["skill"], per_mode_scores["raw"]
    diffs = [x - y for x, y in zip(a, b)]
    sd = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
    if sd:
        t = statistics.mean(diffs) / (sd / math.sqrt(len(diffs)))
        from math import erf
        p = 2 * (1 - 0.5 * (1 + erf(abs(t) / math.sqrt(2))))
    else:
        t, p = 0.0, 1.0
    report["domain"]["skill_vs_raw_ttest"] = {"t": round(t, 4), "p": round(p, 6)}

    # ── Step 3 抽检: kb_doc_read 内容验证 (前 3 个 skill 口径命中查询) ──
    print("\nStep 3 内容验证抽检 (kb_doc_read + 0-8 rubric, top-1):", flush=True)
    checks = []
    for s in samples[:3]:
        resp = client.call("kb_search_two_stage",
                           {"query": s["query"], "kb_id": "", "balance_kbs": True, "top_k": 20})
        results = step25_dedup_threshold(
            resp.get("stage2", {}).get("results") or resp.get("results") or [])
        if not results:
            checks.append({"qid": s["qid"], "top1": None})
            continue
        top1 = results[0]
        golden_frags = {d.lower().removesuffix(".md") for d in s.get("relevant_docs", [])}
        content_hit = any(f in str(top1.get("doc_path", "")).lower() for f in golden_frags)
        # 0-8 rubric 启发式(词面版, 与 run_verifier_eval 同构)
        from run_verifier_eval import content_score_0_8
        score = content_score_0_8(s["query"], str(top1.get("content", ""))[:1500])
        checks.append({"qid": s["qid"], "top1_doc": top1.get("doc_path"),
                       "top1_score": round(float(top1.get("score", 0)), 3),
                       "golden_hit": content_hit, "content_score_0_8": score,
                       "quick_exit": score >= 6})
    report["step3_content_check"] = checks
    for c in checks:
        print(f"  {c['qid']}: top1={str(c.get('top1_doc'))[:60]} "
              f"golden_hit={c.get('golden_hit')} score={c.get('content_score_0_8')} "
              f"快速退出={c.get('quick_exit')}")

    # ── 可选: Track 1 数据集经 MCP 链路冒烟 ──
    if args.track1:
        ds_path = BENCH_DIR / f"{args.track1_dataset}.jsonl"
        ds_samples = [json.loads(l) for l in ds_path.open(encoding="utf-8") if l.strip()][:args.track1]
        print(f"\nTrack1 冒烟: {args.track1_dataset} × {len(ds_samples)} 查询 (经 MCP):", flush=True)
        lat, ok = [], 0
        for s in ds_samples:
            t0 = time.perf_counter()
            resp = client.call("kb_search_two_stage",
                               {"query": s["question"], "kb_id": "",
                                "balance_kbs": True, "top_k": 5})
            lat.append((time.perf_counter() - t0) * 1000)
            if (resp.get("stage2", {}).get("results") or resp.get("results")) is not None:
                ok += 1
        report["track1_smoke"] = {"dataset": args.track1_dataset, "n": len(ds_samples),
                                  "tool_ok": ok,
                                  "latency_ms": round(statistics.mean(lat), 1)}
        print(f"  tool_ok={ok}/{len(ds_samples)}, avg {report['track1_smoke']['latency_ms']}ms"
              f"（当前库无 wiki 语料, 检索 0 命中是预期; 语料入库后由 run_eval.py 出正式分）")

    client.close()
    out = RESULTS_DIR / "eval-mcp-domain40.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
