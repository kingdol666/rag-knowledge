"""Large-document splitter — 把超大文档拆成可检索的小文档（入库规范化层）。

设计（维持平台「文档入库 → 分块向量化 → 多 KB 检索」的既有思路）：
- 拆分发生在 **文档级**（写盘层），拆出的每个 part 是独立文档 → 向量分块、
  BM25 关键词窗口、图谱节点、检索返回粒度全部自然受益；
- 拆分策略：Markdown 标题感知（##/### 段落）优先，超长段落再按段落/句子窗口切分；
  每个 part 带上下文头（源标题 + part i/N + 所在章节路径），保证被单独检索到时语义自洽；
- 参数与检索栈对齐：part 上限 ≤ `max_chars`（默认 10000），小于 BM25 关键词窗口
  （默认 12000），因此拆分后的 part 不会再被关键词索引截断；
- 纯函数、无 I/O，便于单测与跨层复用（HTTP 端点在 routes/documents.py）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

DEFAULT_MAX_CHARS = 10_000
DEFAULT_OVERLAP_CHARS = 400
# 低于该长度的文档永不拆分（避免碎文档爆炸）
MIN_SPLIT_CHARS = 12_000

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)


@dataclass
class SplitPart:
    """一个可独立入库的文档片段。"""
    title: str            # 片段标题（含 part 序号）
    content: str          # 片段正文（含上下文头）
    part_index: int       # 1-based
    part_count: int
    source_title: str
    start_char: int
    end_char: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title, "content": self.content,
            "part_index": self.part_index, "part_count": self.part_count,
            "source_title": self.source_title,
            "start_char": self.start_char, "end_char": self.end_char,
            "chars": len(self.content),
        }


def should_split(content: str, max_chars: int = DEFAULT_MAX_CHARS) -> bool:
    """是否需要拆分：超过 max_chars 且超过硬下限。"""
    return len(content or "") > max(max_chars, MIN_SPLIT_CHARS)


def _sections(content: str) -> list[tuple[str, str]]:
    """按 Markdown 标题切段 → [(章节路径, 正文), ...]（无标题时为单段）。"""
    matches = list(_HEADING_RE.finditer(content))
    if not matches:
        return [("", content)]

    sections: list[tuple[str, str]] = []
    # 标题前的前言
    if matches[0].start() > 0:
        sections.append(("", content[: matches[0].start()]))

    stack: list[tuple[int, str]] = []
    for i, m in enumerate(matches):
        level, heading = len(m.group(1)), m.group(2).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[m.end(): end]
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, heading))
        path = " > ".join(h for _, h in stack if h)
        sections.append((path, f"{m.group(0)}\n{body}".strip()))
    return sections


def _hard_window(text: str, max_chars: int, overlap: int) -> list[str]:
    """无句读/无段落边界的超长串：按固定窗口硬切（带重叠）。"""
    step = max(1, max_chars - (overlap or 0))
    return [text[i: i + max_chars] for i in range(0, len(text), step)] or [text]


def _window_split(text: str, max_chars: int, overlap: int) -> list[str]:
    """超长段落按空行段落打包；单段仍超限时按句子切，句子本身超限再硬切。"""
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            # 单段超限：先冲刷当前，再按句/硬窗口切
            if current:
                chunks.append(current)
                current = ""
            pieces = re.split(r"(?<=[。！？.!?])\s*", para)
            buf = ""
            for piece in pieces:
                if len(piece) > max_chars:
                    # 句子本身超限（无标点长串）→ 硬窗口切
                    if buf:
                        chunks.append(buf)
                        buf = ""
                    chunks.extend(_hard_window(piece, max_chars, overlap))
                    continue
                if len(buf) + len(piece) > max_chars and buf:
                    chunks.append(buf)
                    buf = buf[-overlap:] if overlap else ""
                buf += piece
            if buf.strip():
                chunks.append(buf)
            continue
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current.strip():
        chunks.append(current)
    return chunks or [text]


def split_document(
    content: str,
    title: str = "",
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[SplitPart]:
    """把文档拆成 ≤max_chars 的片段（标题感知 + 段落窗口 + 上下文头）。

    返回 [SplitPart]；不满足拆分条件时返回单元素列表（part_count=1）。
    """
    content = content or ""
    title = (title or "").strip() or "untitled"
    if not should_split(content, max_chars):
        return [SplitPart(title=title, content=content, part_index=1, part_count=1,
                          source_title=title, start_char=0, end_char=len(content))]

    # 1) 标题感知聚合：把 section 打包到 ≤max_chars
    raw_parts: list[tuple[str, str, int, int]] = []  # (章节路径, 正文, start, end)
    for path, body in _sections(content):
        start = content.find(body)
        start = start if start >= 0 else 0
        for piece in _window_split(body, max_chars, overlap_chars):
            raw_parts.append((path, piece, start, start + len(piece)))

    total = len(raw_parts)
    parts: list[SplitPart] = []
    for idx, (path, body, start, end) in enumerate(raw_parts, 1):
        header = [f"# {title}（第 {idx}/{total} 部分）"]
        if path:
            header.append(f"章节: {path}")
        header.append("")
        part_title = f"{title} (part {idx})" + (f" — {path.split(' > ')[-1][:40]}" if path else "")
        parts.append(SplitPart(
            title=part_title,
            content="\n".join(header) + body,
            part_index=idx, part_count=total, source_title=title,
            start_char=start, end_char=end,
        ))
    return parts


def plan_split(content: str, title: str, cfg: dict | None = None) -> dict[str, Any]:
    """按配置规划拆分（供 API/写盘层调用）：返回
    {split: bool, reason: str, part_count: int, parts: [...]}"""
    cfg = cfg or {}
    max_chars = int(cfg.get("max_chars", DEFAULT_MAX_CHARS) or DEFAULT_MAX_CHARS)
    overlap = int(cfg.get("overlap_chars", DEFAULT_OVERLAP_CHARS) or DEFAULT_OVERLAP_CHARS)
    auto = bool(cfg.get("auto_split", True))
    content = content or ""
    if not auto:
        return {"split": False, "reason": "auto_split_disabled", "part_count": 1,
                "parts": [SplitPart(title=title or "untitled", content=content, part_index=1,
                                    part_count=1, source_title=title or "untitled",
                                    start_char=0, end_char=len(content)).to_dict()]}
    if not should_split(content, max_chars):
        return {"split": False, "reason": f"shorter_than_{max(max_chars, MIN_SPLIT_CHARS)}",
                "part_count": 1,
                "parts": [SplitPart(title=title or "untitled", content=content, part_index=1,
                                    part_count=1, source_title=title or "untitled",
                                    start_char=0, end_char=len(content)).to_dict()]}
    parts = split_document(content, title, max_chars=max_chars, overlap_chars=overlap)
    return {"split": len(parts) > 1, "reason": "oversized_or_multi_section",
            "part_count": len(parts), "parts": [p.to_dict() for p in parts]}
