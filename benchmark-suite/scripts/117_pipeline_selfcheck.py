#!/usr/bin/env python3
"""PIPELINE 自检 — 验证 V2 全链路"能执行、数据流转完整、指标与功能对应"。

五类检查：
  1) 文件齐全：V2 用到的每个脚本/模块/PIPELINE 章节都在；
  2) 模块可导入：chat_tracks 的答案键隔离断言、baselines、runner、
     compare_report、compare_html、monitor 全部 import 成功；
  3) 题集合法：若存在 data/papers/qa_v2.json，用 112 的 validate 校验；
  4) 阶段契约：生产者产出的文件名 ↔ 消费者读取的文件名逐条对齐（静态断言）；
  5) 端到端 dry-run：用占位数据把「runner → compare_report → compare_html → 116」
     真跑一遍，确认产物齐全（**不调用任何 API**）。

用法（在 benchmark-suite/ 下）
    python scripts/117_pipeline_selfcheck.py
    python scripts/117_pipeline_selfcheck.py --questions data/papers/qa_v2.json
    python scripts/117_pipeline_selfcheck.py --no-chain      # 只做静态检查

退出码：0 全通过（允许 warn）；1 有 fail。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "experiments"))

OK, WARN, FAIL = "ok", "warn", "fail"
results: list[tuple[str, str, str]] = []


def add(status: str, name: str, detail: str = "") -> None:
    results.append((status, name, detail))


# ── 1. files ────────────────────────────────────────────────────────────────
REQUIRED = [
    "PIPELINE.md", "exp.py", "EXPERIMENT-DESIGN-V2.md",
    "experiments/chat_tracks.py", "experiments/baselines.py",
    "experiments/runner.py", "experiments/compare_report.py",
    "experiments/compare_html.py", "experiments/monitor.py",
    "scripts/lib.py", "scripts/110_stratified_grade.py",
    "scripts/112_question_set.py", "scripts/113_baselines.py",
    "scripts/114_pool_qrels.py", "scripts/115_stats.py",
    "scripts/116_experiment_report.py",
    "data/corpus_md",
]


def check_files() -> None:
    for rel in REQUIRED:
        p = SUITE / rel
        add(OK if p.exists() else FAIL, f"file: {rel}",
            "" if p.exists() else "缺失")


def check_corpus() -> None:
    md = sorted((SUITE / "data" / "corpus_md").glob("*.md"))
    add(OK if len(md) >= 50 else WARN, "corpus_md 文档数", f"{len(md)} 篇")
    q = SUITE / "data" / "papers" / "qa_questions_r2.json"
    if q.exists():
        add(OK, "题集 qa_questions_r2.json", "存在（可作冒烟题集）")


# ── 2. imports ──────────────────────────────────────────────────────────────
def check_imports() -> None:
    for mod in ("chat_tracks", "baselines", "runner", "compare_report",
                "compare_html", "monitor"):
        try:
            __import__(mod)
            add(OK, f"import: {mod}")
        except Exception as e:  # noqa: BLE001
            add(FAIL, f"import: {mod}", f"{type(e).__name__}: {e}")
    try:
        import chat_tracks as ct
        # leak-guard: file-tool tracks must not sit at the repo root
        leak = [t for t, s in ct.TRACKS.items()
                if set(s["allowed_tools"]) & {"Read", "Grep", "Glob"}
                and Path(s["cwd"]).resolve() == ct.REPO.resolve()]
        add(OK if not leak else FAIL, "答案键隔离（无泄漏轨）",
            f"leak={leak}" if leak else f"prompt_version={ct.PROMPT_VERSION}")
    except Exception as e:  # noqa: BLE001
        add(FAIL, "答案键隔离检查", f"{type(e).__name__}: {e}")


# ── 3. question set ─────────────────────────────────────────────────────────
def check_questions(path: str) -> None:
    p = SUITE / path
    if not p.exists():
        add(WARN, "题集校验", f"{path} 不存在（用 112 --skeleton 生成后再填）")
        return
    try:
        spec = importlib.util.spec_from_file_location(
            "qs112", SUITE / "scripts" / "112_question_set.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        errs = m.validate(json.loads(p.read_text(encoding="utf-8")),
                          strict_quota=False)
        add(OK if not errs else FAIL, "题集校验",
            f"{len(errs)} 个错误: {errs[:3]}" if errs else "结构合法")
    except Exception as e:  # noqa: BLE001
        add(FAIL, "题集校验", f"{type(e).__name__}: {e}")


# ── 4. stage contract (producer → consumer filenames) ───────────────────────
def check_contract() -> None:
    # producer writes these; consumers must look for the same names
    produced = {"run_manifest.json", "track_*.json", "SUMMARY.md",
                "baselines.json", "COMPARE.md", "COMPARE.html", "monitor.json",
                "judge.json", "qrels_pool.json", "qrels_scores.json",
                "stats.json", "REPORT.md"}
    readers = {
        "experiments/compare_report.py": ["run_manifest.json", "track_", "baselines.json",
                                          "COMPARE.md", "monitor.json"],
        "scripts/114_pool_qrels.py": ["baselines.json", "track_", "qrels_pool.json",
                                      "qrels_scores.json"],
        "scripts/115_stats.py": ["judge.json"],
        "scripts/116_experiment_report.py": ["baselines.json", "track_", "qrels_scores.json",
                                             "stats.json", "judge.json", "REPORT.md"],
        "scripts/110_stratified_grade.py": ["judge.json"],
    }
    for rel, names in readers.items():
        src = (SUITE / rel).read_text(encoding="utf-8")
        missing = [n for n in names if n.replace("track_", "track_") not in src
                   and n not in src]
        add(OK if not missing else FAIL, f"contract: {Path(rel).name}",
            f"缺 {missing}" if missing else "消费者引用的工件名齐全")
    # canonical run dir must be used by producers
    for rel in ("experiments/runner.py", "scripts/113_baselines.py"):
        src = (SUITE / rel).read_text(encoding="utf-8")
        good = ("new_run_dir" in src) or ("set_run" in src)
        add(OK if good else FAIL, f"run 目录规范: {Path(rel).name}",
            "使用 results/runs/<run_id>/" if good else "未使用规范 run 目录")
    add(OK, "工件集合", f"{len(produced)} 类")


# ── 5. end-to-end dry-run chain ─────────────────────────────────────────────
def dry_run_chain() -> None:
    try:
        import compare_html
        import compare_report
        import runner

        questions = [
            {"qid": "SC01", "question": "self-check placeholder A?"},
            {"qid": "SC02", "question": "self-check placeholder B?"},
        ]
        tracks = ["a2", "bm25", "vector"]
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "run-selfcheck"
            runner.execute(questions, tracks, out, dry_run=True, quiet=True)
            need = ["run_manifest.json"] + \
                   [f"track_{t}_{q['qid']}.json" for q in questions for t in tracks]
            miss = [n for n in need if not (out / n).exists()]
            add(OK if not miss else FAIL, "chain: runner(dry-run)",
                f"缺 {miss[:3]}" if miss else f"{len(need)} 个单元落盘")

            md, payload = compare_report.build(out, {"questions": questions})
            (out / "COMPARE.md").write_text(md, encoding="utf-8")
            (out / "monitor.json").write_text(json.dumps(payload, ensure_ascii=False),
                                              encoding="utf-8")
            ok = (out / "COMPARE.md").exists() and (out / "monitor.json").exists()
            bad = [c["check"] for c in payload.get("self_checks", []) if not c["ok"]]
            add(OK if ok and not bad else FAIL, "chain: compare_report",
                f"自检失败 {bad}" if bad else
                f"{len(payload.get('self_checks', []))} 项自检通过")

            (out / "COMPARE.html").write_text(compare_html.render(payload),
                                              encoding="utf-8")
            html_ok = (out / "COMPARE.html").read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
            add(OK if html_ok else FAIL, "chain: compare_html",
                "COMPARE.html 生成" if html_ok else "HTML 异常")

            import subprocess
            r = subprocess.run([sys.executable, str(SUITE / "scripts" / "116_experiment_report.py"),
                                "--run", str(out)], capture_output=True, text=True)
            add(OK if r.returncode == 0 and (out / "REPORT.md").exists() else FAIL,
                "chain: 116_report", (r.stdout or r.stderr).strip().splitlines()[-1]
                if (r.stdout or r.stderr) else "")
    except Exception as e:  # noqa: BLE001
        add(FAIL, "chain: dry-run", f"{type(e).__name__}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="data/papers/qa_v2.json")
    ap.add_argument("--no-chain", action="store_true")
    args = ap.parse_args()

    check_files()
    check_corpus()
    check_imports()
    check_questions(args.questions)
    check_contract()
    if not args.no_chain:
        dry_run_chain()

    icon = {OK: "✓", WARN: "!", FAIL: "✗"}
    print("PIPELINE 自检\n" + "=" * 68)
    for st, name, detail in results:
        print(f"  {icon[st]} {name:<34} {detail}")
    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    n_warn = sum(1 for s, _, _ in results if s == WARN)
    print("=" * 68)
    print(f"共 {len(results)} 项 · 通过 {len(results) - n_fail - n_warn} · "
          f"警告 {n_warn} · 失败 {n_fail}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
