#!/usr/bin/env python3
"""构建语料级抽取式问答集 CorpusClozeQA — 答案保证在库的内容检索基准.

协议: 对已入库 wiki 页面逐句扫描, 抽取含"答案 span"(年份 / 大写实体串)的事实句,
把答案 span 替换为 ____ 得到 cloze 问题; 金答案 = 原 span, 金证据 = 该句, 金文档 = 该页.
所有条目的金答案在对应 KB 的入库正文中逐字存在 → 专门度量"检索到的内容里是否真的有答案".

确定性: shard 按名排序 + 页保持文件序(语料本身按 sha256(title) 稳定采样), 无随机数.
入库门控: 默认只为 checkpoint 页数 == shard 页数的 KB 构建条目(答案确定已入库).

用法:
  python build_content_qa.py                       # 全部已入库齐的 KB, 每 KB 40 条
  python build_content_qa.py --per-kb 60           # 每 KB 60 条
  python build_content_qa.py --include-partial     # 允许未入库齐的 KB(答案可能缺页)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SPLIT_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks" / "kb_split"
RESULTS_DIR = SCRIPTS_DIR.parent / "results"
OUT_PATH = SPLIT_DIR / "contentqa_corpus.jsonl"

YEAR_RE = re.compile(r"\b(1[5-9][0-9]{2}|20[0-2][0-9])\b")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
CONNECTORS = {"of", "the", "and", "de", "van", "von", "di", "del", "la", "le", "da", "du", "der", "al"}
CAP_TOKEN_RE = re.compile(r"^[A-Z][\w''&.\-]*$")
# 句首代词/指示词单独成 span 无意义
SPAN_BLACKLIST = {
    "The", "This", "That", "These", "Those", "There", "Then", "It", "Its",
    "He", "She", "They", "Their", "His", "Her", "As", "In", "On", "At",
    "When", "While", "After", "Before", "During", "However", "Also", "Later",
    "Some", "Most", "Many", "Other", "Another", "Both", "Each", "All", "One",
    "Two", "First", "New", "More", "Early", "Late", "I", "A", "An",
}
SENT_MIN, SENT_MAX = 60, 400
SPAN_MIN, SPAN_MAX = 2, 80


def sentence_spans(sentence: str) -> list[tuple[str, str]]:
    """返回 [(span_text, span_type)]; type ∈ {year, entity}."""
    spans: list[tuple[str, str]] = []
    for m in YEAR_RE.finditer(sentence):
        spans.append((m.group(1), "year"))
    tokens = sentence.split()
    run: list[str] = []
    caps = 0
    for tok in tokens:
        stripped = tok.strip(".,;:!?()[]{}\"'")
        # 词面带标点的 token(括号/引号/逗号)不可作答案一部分 — 断开 run
        clean = stripped == tok
        is_cap = bool(CAP_TOKEN_RE.match(stripped)) and stripped[:1].isupper()
        is_conn = stripped.lower() in CONNECTORS
        if is_cap and clean or (is_conn and clean and run):
            if is_cap:
                caps += 1
            run.append(tok)
        else:
            if caps >= 2:
                text = " ".join(run).strip(".,;:!?()[]{}\"'")
                if SPAN_MIN <= len(text) <= SPAN_MAX:
                    spans.append((text, "entity"))
            run, caps = [], 0
    if caps >= 2:
        text = " ".join(run).strip(".,;:!?()[]{}\"'")
        if SPAN_MIN <= len(text) <= SPAN_MAX:
            spans.append((text, "entity"))
    return spans


def is_prose_sentence(sentence: str) -> bool:
    if not (SENT_MIN <= len(sentence) <= SENT_MAX):
        return False
    if any(ch in sentence for ch in "|\n\t"):
        return False
    if sentence.count(",") > 8:  # 表格残留/枚举堆砌
        return False
    return True


def qa_item_from_page(page: dict, assignments: dict[str, str]) -> dict | None:
    """一页至多产出 1 条 QA(取第一个合格句).

    只接受 golden 页(assignments 中域与 shard 一致) — 干扰页无真实域归属.
    剥离页首标题前缀, 且答案 span 不得位于标题区(否则题面自带答案).
    """
    title = page["title"]
    if assignments.get(title) != page["kb"]:
        return None
    content = page.get("content") or ""
    if content.startswith(title):  # 剥离页首标题前缀, 避免题面自带答案
        content = content[len(title):]
    for sentence in SENT_SPLIT_RE.split(content):
        if not is_prose_sentence(sentence):
            continue
        spans = sentence_spans(sentence)
        if not spans:
            continue
        # 优先 year(数字型答案最客观), 否则最短实体(越短越像"答案")
        spans.sort(key=lambda s: (s[1] != "year", len(s[0])))
        for span_text, span_type in spans:
            if span_text in SPAN_BLACKLIST or not span_text[0].isalnum():
                continue
            if span_text.lower() == title.lower():
                continue
            masked = sentence.replace(span_text, "____", 1)
            if masked == sentence or "____" not in masked:
                continue
            return {
                "question": masked,
                "answers": [span_text],
                "gold_title": title,
                "gold_kb": page["kb"],
                "evidence_sentence": sentence,
                "span_type": span_type,
            }
    return None


def eligible_kbs(include_partial: bool) -> dict[str, int]:
    """{kb: 可用页数上限} — checkpoint 页数(已入库), partial 默认排除."""
    out: dict[str, int] = {}
    for shard in sorted(SPLIT_DIR.glob("pages_KB-*.jsonl")):
        kb = shard.stem.replace("pages_", "")
        ckpt = RESULTS_DIR / f"checkpoint-{kb}.jsonl"
        n_shard = sum(1 for _ in shard.open(encoding="utf-8"))
        n_done = sum(1 for _ in ckpt.open(encoding="utf-8")) if ckpt.exists() else 0
        if include_partial or n_done >= n_shard:
            out[kb] = min(n_shard, n_done) if include_partial else n_shard
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-kb", type=int, default=40)
    ap.add_argument("--include-partial", action="store_true")
    args = ap.parse_args()

    kbs = eligible_kbs(args.include_partial)
    print(f"eligible KBs: {len(kbs)} -> {sorted(kbs)}")
    assignments = {}
    assign_path = SPLIT_DIR / "kb_assignments.json"
    if assign_path.exists():
        with assign_path.open(encoding="utf-8") as fh:
            assignments = json.load(fh)

    items: list[dict] = []
    seen_spans: set[str] = set()
    for kb in sorted(kbs):
        got = 0
        shard = SPLIT_DIR / f"pages_{kb}.jsonl"
        with shard.open(encoding="utf-8") as fh:
            for line in fh:
                if got >= args.per_kb:
                    break
                page = json.loads(line)
                item = qa_item_from_page(page, assignments)
                if not item:
                    continue
                span_key = item["answers"][0].lower()
                if span_key in seen_spans:
                    continue
                seen_spans.add(span_key)
                got += 1
                item["qid"] = f"cqa-{kb}-{got:04d}"
                items.append(item)
        print(f"  {kb}: {got} items")

    with OUT_PATH.open("w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")

    n_year = sum(1 for i in items if i["span_type"] == "year")
    print(f"total {len(items)} items ({n_year} year, {len(items)-n_year} entity) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
