#!/usr/bin/env python3
"""语料加载 + 结构解析 + 分块器 — DeepRead 论文设置的本地映射.

论文设置(DeepRead arXiv:2602.05014 §4.2):
  - single-pass/ITRG : OpenAI File Search 风格, chunk 800 tokens / overlap 400
  - Search-o1/DeepRead: structure-based chunking, overlap 0
  - RAPTOR           : Collapsed Tree, node ≤800 tokens, 5 层, cluster top-5
token 估计: 英文按 4 chars ≈ 1 token(与 tiktoken 的量级一致, 论文未公开分词器),
本文档 REPRODUCTION-NOTES.md 记录该近似。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
DATA = SUITE / "data"
SCIFACT_DIR = DATA / "standard2" / "scifact"

CHARS_PER_TOKEN = 4


def tokens(s: str) -> int:
    return max(1, len(s) // CHARS_PER_TOKEN)


def cid_of(filename: str) -> str:
    """'Title [31715818].md' → '31715818'."""
    m = re.search(r"\[([^\[\]]+)\]\s*\.md$", filename)
    return m.group(1) if m else Path(filename).stem


def load_corpus() -> list[dict]:
    """返回 [{cid, title, text, path}] — 与 KB-SciFact 入库文档同源同序。"""
    out = []
    for src in sorted(SCIFACT_DIR.glob("*.md")):
        text = src.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        title = ""
        body_start = 0
        if lines and lines[0].lstrip().startswith("#"):
            title = lines[0].lstrip().lstrip("#").strip()
            body_start = 1
        out.append({"cid": cid_of(src.name), "title": title or src.stem,
                    "text": text, "path": src.name})
    return out


def load_queries(limit: int = 0) -> list[dict]:
    qs = [json.loads(l) for l in
          (SCIFACT_DIR / "queries.jsonl").open(encoding="utf-8")]
    return qs[:limit] if limit else qs


# ── 结构解析(DeepRead §3.2): headings=hierarchy, paragraphs=sequence ─────────

@dataclass
class Para:
    doc: str        # cid
    sec: int        # section index (heading-level)
    para: int       # paragraph index within section
    text: str
    coords: str = field(default="")  # "(cid, sec, para)"

    def __post_init__(self) -> None:
        self.coords = f"({self.doc}, sec {self.sec}, para {self.para})"


@dataclass
class Section:
    sec: int
    heading: str
    paras: list[Para]
    n_chars: int


def parse_structure(doc: dict) -> list[Section]:
    """markdown → [Section(sec, heading, paras)] — 段落=空行分隔块, 标题切节。"""
    sections: list[Section] = []
    cur_h, cur_buf = "# " + (doc["title"] or doc["cid"]), []
    sec_idx = -1

    def flush():
        nonlocal sec_idx
        if not cur_buf:
            return
        paras = [p.strip() for p in re.split(r"\n\s*\n", "\n".join(cur_buf)) if p.strip()]
        paras = [p for p in paras if not re.match(r"^\s*#{1,6}\s", p)]
        if paras:
            sec_idx += 1
            sections.append(Section(
                sec_idx, cur_h,
                [Para(doc["cid"], sec_idx, j, t) for j, t in enumerate(paras)],
                sum(len(t) for t in paras)))
    for line in doc["text"].splitlines():
        if re.match(r"^\s*#{1,6}\s", line):
            flush()
            cur_h = line.lstrip().lstrip("#").strip() or cur_h
            cur_buf = []
        else:
            cur_buf.append(line)
    flush()
    if not sections:  # 无正文的退化文档: 整体当一段
        sections.append(Section(0, cur_h,
                                [Para(doc["cid"], 0, 0, doc["text"].strip() or doc["title"])],
                                len(doc["text"])))
    return sections


# ── 分块器 ───────────────────────────────────────────────────────────────────

def chunk_fixed(text: str, max_tokens: int = 800, overlap_tokens: int = 400
                ) -> list[str]:
    """定窗滑块(OpenAI File Search 风格): 800/400 tokens ≈ 3200/1600 chars。"""
    step = max_tokens * CHARS_PER_TOKEN
    ov = overlap_tokens * CHARS_PER_TOKEN
    if len(text) <= step:
        return [text] if text.strip() else []
    out, i = [], 0
    while i < len(text):
        piece = text[i:i + step]
        if piece.strip():
            out.append(piece)
        if i + step >= len(text):
            break
        i += step - ov
    return out


def chunk_structure(text: str, max_tokens: int = 800) -> list[str]:
    """structure-based chunking, overlap 0(论文 §4.2): 按空行段落聚合,
    超 max_tokens 的节内硬切(无重叠)。"""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    out: list[str] = []
    buf, buf_len = [], 0
    limit = max_tokens * CHARS_PER_TOKEN
    for b in blocks:
        bl = len(b)
        if buf and buf_len + bl > limit:
            out.append("\n\n".join(buf))
            buf, buf_len = [], 0
        if bl > limit:  # 单段超限: 硬切, 无重叠
            for i in range(0, bl, limit):
                out.append(b[i:i + limit])
            continue
        buf.append(b)
        buf_len += bl
    if buf:
        out.append("\n\n".join(buf))
    return [c for c in out if c.strip()]
