# -*- coding: utf-8 -*-
"""US-10/11 演示驱动：经 /api/kb/agent/chat 驱动指定 harness 完成解析入库/检索任务。

用法:
  python demo_driver.py --task ingest_omp   --harness omp
  python demo_driver.py --task retrieve_omp    --harness omp
  python demo_driver.py --task retrieve_claude --harness claude
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
WEB = "http://127.0.0.1:6789"
PDF = str((BASE / "deepseek_r1.pdf").resolve())
KB = "演示-R1论文-20261112"
TOKEN = ""
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
H = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

QUESTIONS = [
    ("Q1", "DeepSeek-R1 在 AIME 2024 上的 pass@1 成绩是多少？MATH-500 呢？"),
    ("Q2", "DeepSeek-R1 的强化学习框架用的是什么算法？为什么不用神经网络奖励模型？"),
    ("Q3", "DeepSeek-R1-Zero 是纯强化学习训练的吗？它有什么可读性方面的问题？"),
    ("Q4-ood", "DeepSeek-R1 的训练总共花了多少美元的电费？"),
]

RETRIEVE_TMPL = (
    "基于知识库「演示-R1论文-20261112」（其中是 DeepSeek-R1 论文, arXiv 2501.12948）回答以下问题。"
    "按 QDCVR：改写 → kb_search_vector → kb_laya_judge → kb_doc_read 逐字核验。"
    "每个答案给出 doc_path + 逐字引用关键句 + 可信度；检索不到的如实报告未找到，禁止编造。不要读大文件，直奔主线。\n{qs}")

TASKS = {
    "ingest": (
        f"请把本地论文 PDF 解析并入库到知识库。PDF 绝对路径：{PDF}\n"
        f"知识库「{KB}」可能已存在（id 2f63d95f-e3e1-4242-bfdf-9191a3c535a3，当前 0 文档）——存在就直接用，不要重建。\n"
        f"时间预算紧张（回合上限 10 分钟），请直奔主线，不要读大文件：\n"
        f"1) 解析 PDF（MinerU parse_doc 有缓存则直接命中；解析后跳过深度质检，只确认字符数>100000 且无乱码即可）；\n"
        f"2) 入库到「{KB}」：60K 结构感知分卷，每卷写一句内容归纳描述；\n"
        f"3) 每卷显式 index，确认 chunks>=1；\n"
        f"4) 回查：关键词 'GRPO' 与向量检索各一次确认命中；\n"
        f"5) 报告：文档清单（名称/字数）、chunks 数、回查结果。只操作「{KB}」。"),
    "retrieve": (
        "基于知识库「%KB%」回答下面的问题（这是该库中唯一一篇论文 DeepSeek-R1, arXiv 2501.12948）。"
        "按 QDCVR 流程：改写 → kb_search_vector 检索 → kb_laya_judge 判卷 → kb_doc_read 逐字核验。"
        "每个答案必须：给出引用文档 doc_path + 逐字引用关键句 + 标注可信度；检索不到的如实说未找到，禁止编造。\n"
        "%QUESTIONS%"),
    "organize": (
        "对知识库「%KB%」做整理：1) 用 kb_get_documents 列出全部卷；2) 给每个卷打上标签 "
        "['DeepSeek-R1','强化学习','推理模型','演示库']；3) 挑第一卷，确认其 description 是内容归纳式描述"
        "（若不是则用 kb_doc_update_meta 补写一句含论文章节范围的描述）；4) 报告操作结果。只允许操作「%KB%」。"),
}


def build_prompt(task):
    tpl = TASKS[task]
    if task == "retrieve":
        qs = "\n".join(f"{qid}. {q}" for qid, q in QUESTIONS)
        return tpl.replace("%KB%", KB).replace("%QUESTIONS%", qs)
    return tpl.replace("%KB%", KB)


def run(harness, task, out_name, max_wait_s=1200):
    cli = httpx.Client(trust_env=False, timeout=120, headers=H)
    prompt = build_prompt(task)
    t0 = time.time()
    r = cli.post(f"{WEB}/api/kb/agent/chat",
                 json={"prompt": prompt, "harness": harness, "permission": "bypassPermissions",
                       "mode": "async", "timeout_ms": 1100000})
    d = r.json() if r.status_code == 200 else {"raw": r.text[:300]}
    tid = d.get("task_id")
    if not tid:
        (BASE / f"{out_name}_submit_err.json").write_text(
            json.dumps({"status": r.status_code, "body": d}, ensure_ascii=False), encoding="utf-8")
        print("SUBMIT FAIL", str(d)[:200])
        return None
    print(f"[{out_name}] submitted task_id={tid}", flush=True)
    final = None
    for _ in range(max_wait_s // 10):
        time.sleep(10)
        t = cli.get(f"{WEB}/api/kb/agent/tasks/{tid}")
        td = t.json() if t.status_code == 200 else {}
        st = td.get("status")
        if st in ("done", "completed", "success", "finished", "error", "failed", "timeout"):
            final = td
            break
    dt = round(time.time() - t0, 1)
    (BASE / f"{out_name}.json").write_text(
        json.dumps({"harness": harness, "task": task, "seconds": dt, "task_id": tid, "final": final},
                   ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    result = (final or {}).get("result") or {}
    reply = result.get("reply", "") if isinstance(result, dict) else ""
    print(f"[{out_name}] {st} {dt}s reply_chars={len(reply)}", flush=True)
    return reply


def run_single_questions(harness, qids, tag):
    """每回合最多 2 题（600s 回合墙内）；omp/claude 双 harness 可并行。"""
    cli = httpx.Client(trust_env=False, timeout=120, headers=H)
    summary = []
    for i in range(0, len(qids), 2):
        batch = qids[i:i + 2]
        qs = "\n".join(f"{qid}. {dict(QUESTIONS)[qid]}" for qid in batch)
        prompt = RETRIEVE_TMPL.format(qs=qs)
        t0 = time.time()
        r = cli.post(f"{WEB}/api/kb/agent/chat",
                     json={"prompt": prompt, "harness": harness, "permission": "bypassPermissions",
                           "mode": "async", "timeout_ms": 1100000})
        d = r.json() if r.status_code == 200 else {"raw": r.text[:200]}
        tid = d.get("task_id")
        if not tid:
            print("submit fail", str(d)[:150])
            continue
        print(f"[{tag}] {harness} batch{batch} task={tid}", flush=True)
        final = None
        for _ in range(75):
            time.sleep(10)
            t = cli.get(f"{WEB}/api/kb/agent/tasks/{tid}")
            td = t.json() if t.status_code == 200 else {}
            if td.get("status") in ("done", "completed", "success", "finished", "error", "failed", "timeout"):
                final = td
                break
        dt = round(time.time() - t0, 1)
        st = (final or {}).get("status")
        (BASE / f"retrieve_{harness}_{batch[0]}.json").write_text(
            json.dumps({"harness": harness, "questions": batch, "seconds": dt,
                        "task_id": tid, "final": final}, ensure_ascii=False, indent=1, default=str),
            encoding="utf-8")
        res = (final or {}).get("result") or {}
        reply = res.get("reply", "") if isinstance(res, dict) else ""
        print(f"[{tag}] {st} {dt}s chars={len(reply)}", flush=True)
        summary.append({"questions": batch, "status": st, "seconds": dt, "reply_chars": len(reply)})
    (BASE / f"retrieve_{harness}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=list(TASKS))
    ap.add_argument("--harness", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--qids", default="", help="逗号分隔，如 Q1,Q2（retrieve 任务分批）")
    args = ap.parse_args()
    if args.task == "retrieve" and args.qids:
        run_single_questions(args.harness, [q.strip() for q in args.qids.split(",")], args.out or args.harness)
    else:
        out = args.out or f"{args.task}_{args.harness}"
        run(args.harness, args.task, out)
