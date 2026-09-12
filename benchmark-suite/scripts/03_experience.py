#!/usr/bin/env python3
"""模块 C — 冥想(经验自动总结)基准.

流程(全部真实链路):
  1. 触发冥想: POST /api/v1/meditation/run {kb_id, trigger, harness=omp}
     → harness Agent 从知识库文档综合信号 → 自动撰写经验写入 KB 经验区
  2. 读取经验: GET /api/v1/experience/{kb_id}
  3. 子 Agent 评价: omp 一次性运行, 对每条经验按 0-10 rubric 打分
     (接地面: 内容是否源自库内事实; 结构完整性; 可复用性), 输出 JSON
指标: run_success / coverage(有经验产出的 KB 占比) / n_experiences /
      judge_score_mean(子Agent 评价) / grounded_ratio(判定有据比例)
输出: results/module_c_experience_r{1,2}.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import BACKEND, REPO, RESULTS, env_fingerprint, http_get, http_post, mean, now_iso  # noqa: E402

ROUND = sys.argv[1] if len(sys.argv) > 1 else "1"
TARGET_KBS = (sys.argv[2].split(",") if len(sys.argv) > 2 else ["KB-Demo-EN", "KB-Demo-ZH"])
HARNESS = "omp"


def run_meditation(kb_id: str) -> dict:
    return http_post(f"{BACKEND}/api/v1/meditation/run",
                     {"kb_id": kb_id, "trigger": "benchmark", "harness": HARNESS},
                     timeout=900)


def list_experiences(kb_id: str) -> list[dict]:
    d = http_get(f"{BACKEND}/api/v1/experience/{kb_id}", timeout=120)
    return (d.get("experiences") or d.get("data") or d.get("items") or [])


def list_and_approve_drafts(kb_id: str) -> tuple[int, int]:
    """列出冥想产出的草稿并逐个审批发布(系统设计的人工确认环节, 基准中自动化)。

    返回 (草稿数, 成功发布数)。
    """
    drafts = http_get(f"{BACKEND}/api/v1/experience/{kb_id}/drafts",
                      timeout=120)
    items = drafts.get("drafts") or []
    approved = 0
    for d in items:
        did = d.get("draft_id") or d.get("id")
        if not did:
            continue
        try:
            r = http_post(f"{BACKEND}/api/v1/experience/{kb_id}/drafts/{did}/approve",
                          {}, timeout=120)
            if r.get("success", True):
                approved += 1
        except Exception as e:  # noqa: BLE001
            print(f"  approve failed {did}: {str(e)[:80]}")
    return len(items), approved


JUDGE_PROMPT = """You are a strict reviewer of an auto-generated "experience" entry
( distilled operational knowledge ) for a knowledge-base system. Score it 0-10.
Rubric: grounded in real facts (not hallucinated) = up to 4 points; clear structure
(title/scenario/category present and coherent) = up to 3 points; reusable for
future retrieval tasks = up to 3 points. Reply with ONLY a JSON object:
{"score": <0-10>, "grounded": true/false, "issues": "<one short sentence>"}

EXPERIENCE:
{experience}
"""


def judge_experience(exp: dict, run_tag: str) -> dict:
    body = json.dumps({k: exp.get(k) for k in
                       ("title", "scenario", "category", "content", "symptom",
                        "resolution", "tags") if exp.get(k)},
                      ensure_ascii=False, indent=1)
    if len(body) > 6000:
        body = body[:6000]
    prompt = JUDGE_PROMPT.replace("{experience}", body)
    try:
        proc = subprocess.run(
            ["omp", "-p", prompt, "--auto-approve", "--no-session",
             "--max-time", "300"],
            cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=360)
        out = proc.stdout or ""
        m = re.search(r"\{[^{}]*\}", out, re.S)
        if m:
            d = json.loads(m.group(0))
            d["score"] = max(0, min(10, float(d.get("score", 0))))
            d["grounded"] = bool(d.get("grounded"))
            return d
        (RESULTS / f"judge-{run_tag}.txt").write_text(
            f"=== stdout ===\n{out[:3000]}", encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        (RESULTS / f"judge-{run_tag}.txt").write_text(str(e)[:500],
                                                      encoding="utf-8")
    return {"score": None, "grounded": None, "issues": "judge failed"}


def main() -> int:
    per_kb = {}
    samples = {}
    for kb_id in TARGET_KBS:
        print(f"== {kb_id} ==", flush=True)
        run_err = None
        try:
            run_meditation(kb_id)
        except Exception as e:  # noqa: BLE001
            run_err = str(e)[:150]
        time.sleep(5)
        try:
            n_drafts, n_approved = list_and_approve_drafts(kb_id)
            print(f"  drafts={n_drafts} approved={n_approved}", flush=True)
        except Exception as e:  # noqa: BLE001
            n_drafts = n_approved = 0
            print(f"  draft flow error: {str(e)[:100]}")
        time.sleep(3)
        try:
            exps = list_experiences(kb_id)
        except Exception:  # noqa: BLE001
            exps = []
        print(f"  experiences: {len(exps)}", flush=True)

        judged = []
        for i, e in enumerate(exps[:8]):
            d = judge_experience(e, f"r{ROUND}-{kb_id}-{i}")
            judged.append(d)
            print(f"  judge[{i}] score={d.get('score')} grounded={d.get('grounded')}",
                  flush=True)
        scores = [d["score"] for d in judged if d.get("score") is not None]
        grounded = [d["grounded"] for d in judged if d.get("grounded") is not None]
        per_kb[kb_id] = {
            "run_success": run_err is None,
            "run_error": run_err,
            "n_drafts": n_drafts,
            "n_approved": n_approved,
            "n_experiences": len(exps),
            "judge_score_mean": mean(scores),
            "grounded_ratio": mean([1 if g else 0 for g in grounded]),
        }
        samples[kb_id] = {
            "titles": [e.get("title") for e in exps[:8]],
            "judged": judged,
        }

    covered = sum(1 for v in per_kb.values() if v["n_experiences"] > 0)
    summary = {
        "round": ROUND,
        "n_kbs": len(TARGET_KBS),
        "run_success_rate": mean([1 if v["run_success"] else 0
                                  for v in per_kb.values()]) or 0,
        "kb_coverage": round(covered / len(TARGET_KBS), 4),
        "total_experiences": sum(v["n_experiences"] for v in per_kb.values()),
        "judge_score_mean": mean([v["judge_score_mean"] for v in per_kb.values()
                                  if v["judge_score_mean"] is not None]),
        "grounded_ratio": mean([v["grounded_ratio"] for v in per_kb.values()
                                if v["grounded_ratio"] is not None]),
        "env": env_fingerprint(),
        "generated": now_iso(),
    }
    suffix = "_std" if "Std" in TARGET_KBS[0] else ""
    out = RESULTS / f"module_c_experience{suffix}_r{ROUND}.json"
    out.write_text(json.dumps({"summary": summary, "per_kb": per_kb,
                               "samples": samples},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
