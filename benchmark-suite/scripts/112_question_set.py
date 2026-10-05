#!/usr/bin/env python3
"""题集构建与校验 — 分层六类题集（V2 实验的 P0-4 修法）。

用法（在 benchmark-suite/ 下）
    python scripts/112_question_set.py --validate data/papers/qa_v2.json
    python scripts/112_question_set.py --stats    data/papers/qa_v2.json
    python scripts/112_question_set.py --skeleton --out data/papers/qa_v2.json

题集 schema
-----------
{
  "version": "2026-09-24",
  "meta": {"designed_by": "...", "grounding": "...", "leakage_control": "..."},
  "questions": [
    {"qid": "V2-001",
     "stratum": "single|multihop|crosskb|distractor|unanswerable|outofcorpus",
     "question": "...",
     "gold_docs": ["2409.13934", ...],      # 应拒答层必须为空
     "gold_points": ["要点1", "要点2", ...], # 语义要点 rubric（非逐字关键词）
     "gold_keywords": ["..."],              # 可选，仅作 L1 回归层
     "arxiv_id": "2409.13934"}              # 单文档题可给
  ]
}

分层配额（80 题）
    single 20 · multihop 15 · crosskb 10 · distractor 15 · unanswerable 12 · outofcorpus 8

防泄漏规程（写进 meta 并由本脚本校验）
  1. 出题者只看标题 + 摘要首句，禁看正文（--skeleton 只导出这两项）；
  2. gold_points 是语义要点，不是逐字关键词；
  3. 3 名人类各改写/复核 1/3，meta 记录复核人；
  4. 冻结后公开（Zenodo DOI）。

退出码：校验失败 → 1；成功 → 0。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
CORPUS = SUITE / "data" / "corpus_md"

ANSWERABLE = ("single", "multihop", "crosskb", "distractor")
REFUSAL = ("unanswerable", "outofcorpus")
STRATA = ANSWERABLE + REFUSAL

QUOTA = {"single": 20, "multihop": 15, "crosskb": 10,
         "distractor": 15, "unanswerable": 12, "outofcorpus": 8}


def _load(path: str) -> dict:
    return json.loads((SUITE / path).read_text(encoding="utf-8"))


def validate(doc: dict, strict_quota: bool = False) -> list[str]:
    errs: list[str] = []
    qs = doc.get("questions") or []
    if not isinstance(qs, list) or not qs:
        return ["questions 为空"]
    meta = doc.get("meta") or {}
    if not meta:
        errs.append("meta 缺失（出题人/依据/防泄漏声明）——溯源链会断")
    seen: set[str] = set()
    counts: dict[str, int] = {}
    for i, q in enumerate(qs, 1):
        tag = q.get("qid") or f"#{i}"
        if not q.get("qid"):
            errs.append(f"{tag}: 缺 qid")
        if q.get("qid") in seen:
            errs.append(f"{tag}: qid 重复")
        seen.add(q.get("qid"))
        s = q.get("stratum")
        if s not in STRATA:
            errs.append(f"{tag}: stratum 非法 {s!r}（应为 {STRATA}）")
            continue
        counts[s] = counts.get(s, 0) + 1
        if not str(q.get("question") or "").strip():
            errs.append(f"{tag}: question 为空")
        pts = q.get("gold_points") or []
        if len(pts) < 1:
            errs.append(f"{tag}: gold_points 缺失（应为语义要点 rubric）")
        gd = q.get("gold_docs") or []
        if s in ANSWERABLE and not gd and not q.get("arxiv_id"):
            errs.append(f"{tag}: 可答层必须有 gold_docs 或 arxiv_id")
        if s in REFUSAL and gd:
            errs.append(f"{tag}: 应拒答层不应有 gold_docs（该题在库内无解）")
        if s == "multihop" and len(gd) < 2 and not q.get("arxiv_id"):
            errs.append(f"{tag}: multihop 应跨 ≥2 篇（gold_docs 至少 2 个）")
    quota = QUOTA
    if isinstance(meta.get("quota"), dict) and meta["quota"]:
        quota = meta["quota"]
    for s, want in quota.items():
        got = counts.get(s, 0)
        if got != want:
            msg = f"分层配额: {s} = {got}，期望 {want}"
            if strict_quota:
                errs.append(msg)
            else:
                print(f"[warn] {msg}")
    print(f"[validate] {len(qs)} 题 · " +
          " ".join(f"{s}={counts.get(s, 0)}" for s in STRATA))
    return errs


def stats(path: str) -> None:
    doc = _load(path)
    qs = doc["questions"]
    print(f"题集: {path} · version={doc.get('version')} · n={len(qs)}")
    print(f"{'stratum':<14}{'n':>4}  {'gold_docs>0':>12}  {'gold_points(avg)':>16}")
    for s in STRATA:
        sub = [q for q in qs if q.get("stratum") == s]
        if not sub:
            continue
        gd = sum(1 for q in sub if q.get("gold_docs"))
        avg = sum(len(q.get("gold_points") or []) for q in sub) / len(sub)
        print(f"{s:<14}{len(sub):>4}  {gd:>12}  {avg:>16.1f}")
    nkw = sum(1 for q in qs if q.get("gold_keywords"))
    print(f"含逐字关键词的题: {nkw}/{len(qs)}（应尽量少——语义要点才是主口径）")


def _title_and_first_sentence(p: Path) -> tuple[str, str]:
    """只读标题 + 摘要首句（防泄漏：出题者不得看正文）。"""
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    title, body, started = p.stem, [], False
    for ln in lines:
        if re.match(r"^\s*#{1,6}\s", ln):
            if not started:
                title = ln.lstrip().lstrip("#").strip() or title
            continue
        if ln.strip():
            started = True
            body.append(ln.strip())
        if started and len(" ".join(body)) > 240:
            break
    first = " ".join(body)
    m = re.search(r"(.+?[.!?])\s", first + " ")
    return title, (m.group(1) if m else first)[:300]


def skeleton(out: str, per_stratum: dict[str, int]) -> None:
    docs = sorted(CORPUS.glob("*.md"))
    if not docs:
        print(f"[skeleton] 语料目录为空: {CORPUS}")
        sys.exit(1)
    picks = [(p.name, *(_title_and_first_sentence(p))) for p in docs]
    questions, idx, di = [], 0, 0
    for s in STRATA:
        for _ in range(per_stratum.get(s, 0)):
            idx += 1
            name, title, first = picks[di % len(picks)]
            di += 1
            src = name.split("__")[1] if "__" in name else name[:-3]
            questions.append({
                "qid": f"V2-{idx:03d}",
                "stratum": s,
                "question": "",
                "gold_docs": [] if s in REFUSAL else [src],
                "gold_points": [],
                "gold_keywords": [],
                "candidate_source": src,
                "candidate_title": title,
                "abstract_first_sentence": first,
            })
    doc = {
        "version": "2026-09-24",
        "meta": {
            "designed_by": "<填写出题人>",
            "grounding": "出题者只看 candidate_title + abstract_first_sentence；"
                         "禁看正文",
            "leakage_control": "gold_points 为语义要点 rubric；3 人各复核 1/3；"
                               "冻结后公开 DOI",
            "status": "SKELETON — 需人工/Agent 填写 question 与 gold_points",
        },
        "questions": questions,
    }
    (SUITE / out).write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    print(f"[skeleton] 生成 {len(questions)} 个槽位 → {out}")
    print("下一步：按 abstract_first_sentence 填写 question 与 3-5 条 gold_points，"
          "再跑 --validate。")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", metavar="FILE")
    ap.add_argument("--stats", metavar="FILE")
    ap.add_argument("--skeleton", action="store_true")
    ap.add_argument("--out", default="data/papers/qa_v2.json")
    ap.add_argument("--strict-quota", action="store_true",
                    help="分层配额不等即报错（默认仅 warn）")
    args = ap.parse_args()

    if args.stats:
        stats(args.stats)
        return 0
    if args.skeleton:
        skeleton(args.out, QUOTA)
        return 0
    if args.validate:
        errs = validate(_load(args.validate), strict_quota=args.strict_quota)
        if errs:
            print(f"[validate] {len(errs)} 个错误:")
            for e in errs:
                print(f"  - {e}")
            return 1
        print("[validate] OK")
        return 0
    ap.error("指定 --validate / --stats / --skeleton 之一")


if __name__ == "__main__":
    sys.exit(main())
