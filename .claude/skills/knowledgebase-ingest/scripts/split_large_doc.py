#!/usr/bin/env python3
"""split_large_doc.py — knowledgebase-ingest 拆分门禁 (A2.5) 的强制执行脚本。

把「解析后的临时 markdown」按设置的分块上限拆成多个独立 part 文档：
  - 读取设置: config.yml -> ingestion.large_doc.max_chars（可用 --max-chars 覆盖）
  - 传入解析产物路径 -> 标题感知 + 段落窗口拆分（与后端入库规范化层同算法）
  - 每个 part 生成真实内容描述（纯文本摘录，供 A3c 描述门禁直接采用）
  - 默认**删除原临时 md**（--keep-source 保留；--dry-run 只看计划不动文件）
  - stdout 输出单行 JSON，后续 skill 步骤据此执行（不要人工手拆）

用法:
  python split_large_doc.py <parsed.md>                    # 按设置拆分并删原文
  python split_large_doc.py <parsed.md> --dry-run          # 只返回拆分计划
  python split_large_doc.py <parsed.md> --max-chars 2000   # 临时覆盖上限
  python split_large_doc.py <parsed.md> --config D:/path/config.yml
  python split_large_doc.py --selftest                     # 自检算法

退出码: 0 成功（无论是否拆分）；1 参数/IO 错误。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_MAX_CHARS = 10_000
DEFAULT_OVERLAP_CHARS = 400
MIN_MAX_CHARS = 500          # max_chars 防呆下限（与后端一致）
DEFAULT_DESC_CHARS = 120
CONFIG_MAX_CHARS_KEY = "max_chars"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)


# ── config.yml 读取（零依赖：只提取 ingestion.large_doc 三个键） ─────────
def _read_large_doc_config(config_path: Path | None) -> tuple[dict, str]:
    """返回 ({auto_split, max_chars, overlap_chars}, 配置来源说明)。"""
    candidates: list[tuple[Path, str]] = []
    if config_path:
        candidates.append((config_path, "--config 参数"))
    env_cfg = os.environ.get("RAG_KB_CONFIG")
    if env_cfg:
        candidates.append((Path(env_cfg), "环境变量 RAG_KB_CONFIG"))
    # 从 CWD 与输入文件位置向上找 config.yml（最多 6 级）
    for base in [Path.cwd(), *list(Path.cwd().parents)[:6]]:
        candidates.append((base / "config.yml", "CWD 向上探测"))
        if (base / "config.yml").exists():
            break
    defaults = {"auto_split": True, "max_chars": DEFAULT_MAX_CHARS,
                "overlap_chars": DEFAULT_OVERLAP_CHARS}
    for path, source in candidates:
        try:
            if not path or not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        cfg = _parse_large_doc_section(text)
        if cfg is not None:
            merged = dict(defaults)
            merged.update(cfg)
            return merged, f"{path} ({source})"
    return defaults, "未找到 config.yml，使用默认值"


def _parse_large_doc_section(text: str) -> dict | None:
    """最小化解析 config.yml 的 ingestion.large_doc 段（忽略内联注释）。"""
    lines = text.splitlines()
    in_ingestion = False
    in_large_doc = False
    cfg: dict = {}
    for raw in lines:
        stripped = raw.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip())
        key, _, val = stripped.strip().partition(":")
        val = val.strip()
        if indent == 0:
            in_ingestion = key == "ingestion"
            in_large_doc = False
            continue
        if in_ingestion and indent == 2:
            in_large_doc = key == "large_doc"
            continue
        if in_ingestion and in_large_doc:
            if val.lower() in ("true", "false"):
                cfg[key] = val.lower() == "true"
            else:
                try:
                    cfg[key] = int(val)
                except ValueError:
                    cfg[key] = val
    return cfg or None


# ── 拆分算法（与后端 app/services/document_splitter.py 保持一致） ────────
def clamp_max_chars(max_chars: int) -> int:
    try:
        return max(MIN_MAX_CHARS, int(max_chars))
    except (TypeError, ValueError):
        return DEFAULT_MAX_CHARS


def content_description(text: str, max_desc_chars: int = DEFAULT_DESC_CHARS) -> str:
    """从真实正文提取纯文本摘录（去 Markdown 标记、压空白）。"""
    plain = re.sub(r"```[\s\S]*?```", " ", text or "")
    plain = re.sub(r"`([^`]+)`", r"\1", plain)
    plain = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1", plain)
    plain = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", plain)
    plain = re.sub(r"^#{1,6}\s+", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"[*_~>|-]+", " ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= max_desc_chars:
        return plain
    return plain[:max_desc_chars].rstrip() + "…"


def _sections(content: str) -> list[tuple[str, str]]:
    matches = list(_HEADING_RE.finditer(content))
    if not matches:
        return [("", content)]
    sections: list[tuple[str, str]] = []
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
    step = max(1, max_chars - (overlap or 0))
    return [text[i: i + max_chars] for i in range(0, len(text), step)] or [text]


def _window_split(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            pieces = re.split(r"(?<=[。！？.!?])\s*", para)
            buf = ""
            for piece in pieces:
                if len(piece) > max_chars:
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


def split_document(content: str, title: str, *, max_chars: int,
                   overlap_chars: int) -> list[dict]:
    """返回 [{title, content, part_index, part_count, chars, description}]。"""
    content = content or ""
    title = (title or "").strip() or "untitled"
    max_chars = clamp_max_chars(max_chars)
    if len(content) <= max_chars:
        return [{"title": title, "content": content, "part_index": 1,
                 "part_count": 1, "chars": len(content),
                 "description": content_description(content)}]

    raw_parts: list[tuple[str, str]] = []  # (章节路径, 正文)
    acc_path: str | None = None
    acc_body = ""

    def _flush() -> None:
        nonlocal acc_path, acc_body
        if acc_body.strip():
            raw_parts.append((acc_path or "", acc_body))
        acc_path, acc_body = None, ""

    for path, body in _sections(content):
        if len(body) > max_chars:
            _flush()
            for piece in _window_split(body, max_chars, overlap_chars):
                raw_parts.append((path, piece))
            continue
        if acc_body and len(acc_body) + len(body) + 2 > max_chars:
            _flush()
        if not acc_body:
            acc_path, acc_body = path, body
        else:
            acc_body = f"{acc_body}\n\n{body}"
    _flush()

    total = len(raw_parts)
    parts = []
    for idx, (path, body) in enumerate(raw_parts, 1):
        header = [f"# {title}（第 {idx}/{total} 部分）"]
        if path:
            header.append(f"章节: {path}")
        header.append("")
        part_title = f"{title} (part {idx})" + (
            f" — {path.split(' > ')[-1][:40]}" if path else "")
        parts.append({"title": part_title,
                      "content": "\n".join(header) + body,
                      "part_index": idx, "part_count": total,
                      "chars": len("\n".join(header) + body),
                      "description": content_description(body)})
    return parts


# ── CLI ────────────────────────────────────────────────────────────────
def _selftest() -> int:
    doc = "# T\n\n" + "\n".join(
        f"## S{i}\n\n{'内容测试。' * 60}" for i in range(5))
    parts = split_document(doc, "T", max_chars=1000, overlap_chars=200)
    assert len(parts) >= 2, "应拆出多个 part"
    assert all(p["chars"] <= 1000 + 200 for p in parts), "part 超限"
    assert all(p["description"] for p in parts), "描述不得为空"
    joined = "".join(p["content"] for p in parts)
    assert "S1" in joined and "S4" in joined, "章节不得丢失"
    print(json.dumps({"selftest": "pass", "parts": len(parts)},
                     ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="按设置上限拆分解析后的 markdown 文档")
    parser.add_argument("input", nargs="?", help="解析产物 markdown 路径")
    parser.add_argument("--max-chars", type=int, default=None,
                        help="临时覆盖 config.yml 的 ingestion.large_doc.max_chars")
    parser.add_argument("--config", default=None, help="config.yml 路径")
    parser.add_argument("--keep-source", action="store_true",
                        help="保留原临时 md（默认拆分成功后删除）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只输出拆分计划，不写文件不删原文")
    parser.add_argument("--out-dir", default=None,
                        help="part 文件输出目录（默认与原文件同目录）")
    parser.add_argument("--selftest", action="store_true", help="算法自检")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if args.selftest:
        return _selftest()
    if not args.input:
        parser.error("缺少 input 路径（或使用 --selftest）")
        return 1

    src = Path(args.input)
    if not src.exists():
        print(json.dumps({"success": False,
                          "error": f"文件不存在: {src}"}, ensure_ascii=False))
        return 1

    cfg, cfg_source = _read_large_doc_config(
        Path(args.config) if args.config else None)
    max_chars = clamp_max_chars(args.max_chars or cfg["max_chars"])
    overlap = int(cfg.get("overlap_chars") or DEFAULT_OVERLAP_CHARS)

    content = src.read_text(encoding="utf-8")
    parts = split_document(content, src.stem, max_chars=max_chars,
                           overlap_chars=overlap)
    split = len(parts) > 1

    result: dict = {
        "success": True,
        "source_file": str(src),
        "source_chars": len(content),
        "max_chars": max_chars,
        "max_chars_source": cfg_source,
        "auto_split_config": bool(cfg.get("auto_split", True)),
        "split": split,
        "part_count": len(parts),
        "dry_run": bool(args.dry_run),
        "parts": [],
    }

    if not split:
        # 未超限：不拆分、不删原文，原文直接进入后续步骤
        result["parts"].append({
            "file": str(src), "title": src.stem,
            "chars": len(content),
            "description": content_description(content)})
        result["source_deleted"] = False
        result["note"] = "未超过 max_chars，无需拆分，原文继续走后续入库流程"
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.dry_run:
        for p in parts:
            result["parts"].append({
                "file": None, "title": p["title"], "chars": p["chars"],
                "description": p["description"]})
        result["source_deleted"] = False
        print(json.dumps(result, ensure_ascii=False))
        return 0

    out_dir = Path(args.out_dir) if args.out_dir else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem
    for p in parts:
        part_name = f"{stem} (part {p['part_index']} of {p['part_count']}).md"
        part_path = out_dir / part_name
        part_path.write_text(p["content"], encoding="utf-8")
        result["parts"].append({
            "file": str(part_path), "title": p["title"],
            "chars": p["chars"], "description": p["description"]})

    if args.keep_source:
        result["source_deleted"] = False
    else:
        try:
            src.unlink()
            result["source_deleted"] = True
        except OSError as exc:
            result["source_deleted"] = False
            result["warning"] = f"删除原文失败（请手动处理）: {exc}"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
