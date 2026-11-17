"""KB Automation API Routes — 自动经验总结机制 HTTP 接口。

每 KB 独立开关；开启后每篇文档入库计数 +1（元数据持久化于
storage/tree-file-system/.kb-automation.json），计数每达到 interval
（默认 5）的倍数自动执行一次经验总结更新。

入口约定：
- 前端 → web(Nitro) /api/kb/automation/* → 本路由（web 代理注入 Bearer）
- web documents/create 入库钩子 → POST /{kb_id}/ingest（fire-and-forget，
  fail-open：本机制任何异常不得阻断入库）
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.models.automation_models import AutomationIngestRequest, AutomationToggleRequest
from app.services.kb_automation_service import kb_automation_service
from app.api.deps.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/automation", tags=["KBAutomation"])


@router.get("/states")
async def list_states():
    """列出所有 KB 的自动化状态（前端设置面板用）。"""
    return kb_automation_service.list_all()


@router.get("/{kb_id}")
async def get_status(kb_id: str):
    """查询单个 KB 的自动化状态：开关、计数器、下次触发点、历史。"""
    status = kb_automation_service.get_status(kb_id)
    if not status.get("success"):
        raise HTTPException(500, status.get("error", "status failed"))
    return status


@router.post("/{kb_id}/toggle", dependencies=[Depends(verify_token)])
async def toggle_automation(kb_id: str, body: AutomationToggleRequest):
    """开启/关闭自动经验总结。关闭后入库不再计数、不再触发总结。"""
    result = kb_automation_service.set_enabled(kb_id, body.enabled)
    if not result.get("success"):
        raise HTTPException(404, result.get("error", "KB not found"))
    return result


@router.post("/{kb_id}/ingest", dependencies=[Depends(verify_token)])
async def record_ingest(kb_id: str, body: AutomationIngestRequest):
    """入库钩子：开启状态下计数 +doc_count；达到 interval 倍数触发经验总结。

    未开启的 KB 调用本接口是合法的 no-op（counted=0），便于调用方无需
    预查开关状态。
    """
    try:
        return await kb_automation_service.record_ingest(
            kb_id, doc_path=body.doc_path, title=body.title,
            doc_count=body.doc_count)
    except Exception as e:
        # fail-open：自动化机制故障绝不阻断入库主流程
        logger.exception("automation ingest hook failed for %s", kb_id)
        return {"success": False, "kb_id": kb_id, "counted": 0,
                "triggered": False, "error": str(e), "fail_open": True}


@router.post("/{kb_id}/summarize", dependencies=[Depends(verify_token)])
async def trigger_summary(kb_id: str):
    """手动触发一次经验总结更新（首次创建 / 后续更新同一条经验）。"""
    result = await kb_automation_service.trigger_summary(kb_id)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "summary failed"))
    return result
