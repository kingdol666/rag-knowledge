"""补天蒸馏文件解析 — 批量上传文档 → 统一文本 → 蒸馏初始人格。

覆盖 dot-skill 支持的全部文件类型:
- 文本类: .md/.txt/.markdown/.csv — 直接读取
- 对话导出: .json(飞书/聊天记录导出, 递归提取对话字段) · .eml/.mbox(邮件)
- 表格: .xlsx/.xls — openpyxl 转文本行
- Office: .docx — python-docx 段落
- 视觉/复杂: .pdf/.png/.jpg/.jpeg/.webp/.bmp/.pptx — MinerU OCR 管线

解析结果按文件分块汇总(带文件名头), 作为 source_material 进入
soul_distill_v1.txt 蒸馏 prompt → persona/work/meta → soul-definition 架构。
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TEXT_EXTS = {".md", ".txt", ".markdown", ".csv"}
DIALOGUE_EXTS = {".json"}
EMAIL_EXTS = {".eml", ".mbox"}
SHEET_EXTS = {".xlsx", ".xls"}
DOCX_EXTS = {".docx"}
MINERU_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".pptx", ".ppt"}

MAX_FILE_CHARS = 30000  # 单文件文本上限
MAX_TOTAL_CHARS = 60000  # 汇总上限(蒸馏 prompt 预算)


async def parse_uploaded_files(files_dir: Path,
                               progress_cb=None) -> dict[str, Any]:
    """解析目录内全部文件为统一文本。

    Returns: {text, files: [{name, chars, method}], skipped: [{name, reason}]}
    """
    async def _cb(msg: str):
        if progress_cb:
            r = progress_cb({"phase": "parse_files", "msg": msg})
            if hasattr(r, "__await__"):
                await r

    blocks: list[str] = []
    parsed: list[dict] = []
    skipped: list[dict] = []
    total_chars = 0

    files = sorted(files_dir.iterdir()) if files_dir.exists() else []
    for i, f in enumerate(files):
        if not f.is_file():
            continue
        name = f.name
        ext = f.suffix.lower()
        await _cb(f"解析文件 {i + 1}/{len(files)}: {name}…")
        try:
            if ext in TEXT_EXTS:
                text, method = await _read_text(f), "text"
            elif ext in DIALOGUE_EXTS:
                text, method = _extract_dialogue(f), "dialogue-json"
            elif ext in EMAIL_EXTS:
                text, method = await _extract_email(f), "email"
            elif ext in SHEET_EXTS:
                text, method = _extract_sheet(f), "sheet"
            elif ext in DOCX_EXTS:
                text, method = _extract_docx(f), "docx"
            elif ext in MINERU_EXTS:
                text, method = await _extract_mineru(f), "mineru"
            else:
                skipped.append({"name": name, "reason": f"不支持的类型 {ext}"})
                continue

            text = (text or "").strip()
            if not text:
                skipped.append({"name": name, "reason": "解析结果为空"})
                continue
            text = text[:MAX_FILE_CHARS]
            blocks.append(f"【文件: {name}】\n{text}")
            parsed.append({"name": name, "chars": len(text), "method": method})
            total_chars += len(text)
            if total_chars >= MAX_TOTAL_CHARS:
                await _cb(f"已达文本上限({MAX_TOTAL_CHARS} 字符), 停止解析后续文件")
                break
        except Exception as e:
            logger.warning("parse file %s failed: %s", name, e)
            skipped.append({"name": name, "reason": str(e)[:120]})

    await _cb(f"解析完成: {len(parsed)} 个文件, 跳过 {len(skipped)}")
    return {"text": "\n\n".join(blocks), "files": parsed, "skipped": skipped}


# ── 各类型解析 ─────────────────────────────────────────────────────────

async def _read_text(p: Path) -> str:
    for enc in ("utf-8", "gbk", "utf-8-sig"):
        try:
            return p.read_text(encoding=enc, errors="replace")
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="replace")


def _extract_dialogue(p: Path) -> str:
    """JSON 对话提取: 递归收集 text/content/message/body 字段, 拼成对话流。"""
    raw = p.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except Exception:
        return raw  # 非 JSON → 原文
    lines: list[str] = []

    def walk(node: Any, depth: int = 0):
        if depth > 8 or len(lines) > 400:
            return
        if isinstance(node, dict):
            # 常见对话结构: {sender/name + text/content/message}
            sender = None
            for k in ("sender", "from", "name", "user", "author", "发言者"):
                v = node.get(k)
                if isinstance(v, (str, int)) and str(v).strip():
                    sender = str(v).strip()
                    break
            text = None
            for k in ("text", "content", "message", "body", "msg", "内容", "消息"):
                v = node.get(k)
                if isinstance(v, str) and v.strip():
                    text = v.strip()
                    break
            if text and (sender or len(text) > 1):
                lines.append(f"{sender}: {text}" if sender else text)
            for v in node.values():
                walk(v, depth + 1)
        elif isinstance(node, list):
            for item in node:
                walk(item, depth + 1)

    walk(data)
    return "\n".join(lines) if lines else raw[:MAX_FILE_CHARS]


def _extract_email(p: Path) -> str:
    """邮件 .eml/.mbox 简化解析: From/To/Subject/Date/Body。"""
    text = p.read_text(encoding="utf-8", errors="replace")
    out: list[str] = []
    for line in text.splitlines():
        low = line.lower()
        if low.startswith(("from:", "to:", "subject:", "date:", "cc:", "bcc:")):
            out.append(line.strip())
    # body: 跳过 header 后的空行开始
    body_start = text.find("\n\n")
    if body_start > 0:
        body = text[body_start:].strip()
        out.append(body[:MAX_FILE_CHARS])
    return "\n".join(out) if out else text


def _extract_sheet(p: Path) -> str:
    """Excel → 逐行文本(单元格以 | 分隔)。"""
    import openpyxl
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    rows_out: list[str] = []
    for ws in wb.worksheets[:3]:
        rows_out.append(f"# Sheet: {ws.title}")
        for row in ws.iter_rows(values_only=True):
            vals = [str(c) for c in row if c is not None]
            if vals:
                rows_out.append(" | ".join(vals))
            if len(rows_out) > 300:
                break
    return "\n".join(rows_out)


def _extract_docx(p: Path) -> str:
    import docx
    d = docx.Document(str(p))
    return "\n".join(par.text for par in d.paragraphs if par.text.strip())


async def _extract_mineru(p: Path) -> str:
    """PDF/图片/PPT → MinerU 异步解析(与 parse 路由同服务实例)。"""
    from app.utils.mineru_manager import get_mineru_manager
    from app.services.mineru_service import MineruParseService
    from pathlib import Path as _P
    import tempfile

    manager = get_mineru_manager()
    service = MineruParseService(manager)
    output_dir = _P(tempfile.gettempdir()) / f"soul-distill-mineru-{uuid.uuid4().hex[:8]}"
    result = await service.parse_async(
        p.read_bytes(), p.name, output_dir, use_ocr=True, poll_timeout=600)
    return (result.markdown or "") if result else ""
