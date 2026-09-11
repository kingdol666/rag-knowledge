"""Documents API — 入库规范化（大文档拆分）对外端点。

POST /api/v1/documents/split
  body: {title, content, max_chars?, overlap_chars?, auto_split?}
  → {success, split, part_count, parts:[{title, content, part_index, part_count, chars}]}

用途：写盘层（web /api/kb/documents/create、MinerU 解析落盘、批量入库脚本）在
内容超过阈值时先调用本端点取得片段计划，再将每个 part 作为独立文档写盘入库 ——
向量分块、BM25 关键词窗口、图谱节点、检索粒度全部自然受益于更小的文档单元。
纯计算端点，无 I/O，不落盘。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.api.deps.auth import verify_token
from app.config import config
from app.services import document_splitter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post("/split", dependencies=[Depends(verify_token)])
async def split_document(body: dict = None):
    """大文档拆分规划（见模块 docstring）。配置默认来自 config.yml ingestion.large_doc。"""
    body = body or {}
    content = str(body.get("content") or "")
    title = str(body.get("title") or "").strip() or "untitled"
    # 请求级覆盖 > config.yml > 服务默认
    cfg = dict(config.large_doc_split)
    for key in ("max_chars", "overlap_chars"):
        if body.get(key) is not None:
            try:
                cfg[key] = int(body[key])
            except (TypeError, ValueError):
                pass
    if body.get("auto_split") is not None:
        cfg["auto_split"] = bool(body["auto_split"])

    plan = document_splitter.plan_split(content, title, cfg)
    plan["success"] = True
    plan["config"] = cfg
    plan["source_chars"] = len(content)
    logger.info("documents/split: title=%r chars=%d -> parts=%d (split=%s)",
                title[:60], len(content), plan["part_count"], plan["split"])
    return plan
