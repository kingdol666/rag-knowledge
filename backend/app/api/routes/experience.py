"""Experience API Routes — 经验管理 HTTP 接口。"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from app.models.experience_models import (
    ExperienceCategory,
    ExperienceCreate,
    ExperienceUpdate,
    ExperienceApplyRequest,
    ExperienceReviewRequest,
)
from app.services.experience_service import experience_service
from app.api.deps.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/experience", tags=["Experience"])


@router.post("/global-search")
async def global_search_experiences(body: dict = None):
    """跨 KB 全局经验检索 — QDCVR 流程（向量召回→硬阈值→内容验证→可信度定级→诚实空返回）。

    body 字段:
        query: 自然语言查询（中英文均可）
        top_k: 返回上限（默认10）
        score_threshold: 向量硬阈值（默认0.45；追求精度0.55，追求召回0.35）
        verify_content: True=读正文内容验证（默认，推荐）；False=仅向量分
    """
    body = body or {}
    query = body.get("query", "")
    top_k = body.get("top_k", 10)
    score_threshold = body.get("score_threshold")  # None → 用服务层默认 0.45
    verify_content = body.get("verify_content", True)
    return await experience_service.search_experiences_global(
        query, top_k, score_threshold=score_threshold, verify_content=verify_content)


@router.post("/stale-global")
async def check_stale_global():
    """E6: 全库 stale 检查。注意：无 {kb_id} 前缀，必须在 /{kb_id} 之前注册。"""
    return await experience_service.check_stale_global()


@router.get("/{kb_id}/init")
async def init_experience(kb_id: str):
    """初始化经验文件夹。KB创建后调用一次即可。确保在真正的KB路径下创建。"""
    # 先通过 resolve 把 UUID 转成实际路径，避免在 UUID 名称下创建空目录
    resolved = experience_service._resolve_kb_path(kb_id)
    if not resolved:
        return {"success": False, "error": f"KB not found: {kb_id}"}
    return await experience_service.init_experience_folder(resolved)


@router.post("/{kb_id}", dependencies=[Depends(verify_token)])
async def create_experience(kb_id: str, body: ExperienceCreate):
    """创建一条新经验。"""
    return await experience_service.create_experience(kb_id, body)


@router.post("/{kb_id}/reindex")
async def reindex_experiences(kb_id: str, body: dict = None):
    """重索引经验到向量库。exp_id 为空则重索引整个 KB。

    用于修复：已有经验创建时向量索引缺失/失败的问题。
    """
    body = body or {}
    exp_id = body.get("exp_id")
    return await experience_service.reindex_experiences(kb_id, exp_id)


@router.get("/{kb_id}")
async def list_experiences(kb_id: str, scenario: str = "", category: str = "", tag: str = ""):
    """列出知识库中的经验，支持按场景/类别/标签过滤。按评分排序。"""
    return await experience_service.list_experiences(kb_id, scenario, category, tag)


# ── 静态路由（必须在 {kb_id}/{exp_id} 之前注册，防止被动态参数捕获） ──

@router.get("/{kb_id}/summary")
async def experience_summary(kb_id: str):
    """获取经验统计摘要。"""
    return await experience_service.experience_summary(kb_id)


@router.post("/{kb_id}/search")
async def search_experiences(kb_id: str, body: dict = None):
    """元信息搜索经验（title/problem/solution/tags/key_lessons）。"""
    body = body or {}
    query = body.get("query", "")
    top_k = body.get("top_k", 10)
    return await experience_service.search_experiences(kb_id, query, top_k)


@router.post("/{kb_id}/vector-search")
async def vector_search_experiences(kb_id: str, body: dict = None):
    """向量语义搜索经验。"""
    body = body or {}
    query = body.get("query", "")
    top_k = body.get("top_k", 5)
    return await experience_service.vector_search_experiences(kb_id, query, top_k)


# ── E0/E1: 经验提取（启发式 + 任务包）── 静态路由 ──

@router.post("/{kb_id}/extract")
async def extract_experiences(kb_id: str, body: dict = None, dependencies=None):
    """E0/E1: 经验提取。dry_run=True 返回候选任务包；False 写草稿池。"""
    body = body or {}
    doc_paths = body.get("doc_paths")
    dry_run = body.get("dry_run", True)
    mode = body.get("mode", "heuristic")  # heuristic | prepare
    if mode == "prepare":
        return await experience_service.prepare_extraction(kb_id, doc_paths)
    return await experience_service.heuristic_extract(kb_id, doc_paths, dry_run)


@router.get("/{kb_id}/drafts")
async def list_drafts(kb_id: str):
    """E3: 列出草稿池。"""
    return await experience_service.list_drafts(kb_id)


@router.get("/{kb_id}/drafts/{draft_id}")
async def read_draft(kb_id: str, draft_id: str):
    """E3: 读取草稿详情。"""
    return await experience_service.read_draft(kb_id, draft_id)


@router.post("/{kb_id}/drafts/{draft_id}/approve", dependencies=[Depends(verify_token)])
async def approve_draft(kb_id: str, draft_id: str, body: dict = None):
    """E3: 批准草稿→正式经验。body.edits 可覆盖字段。"""
    body = body or {}
    edits = body.get("edits")
    return await experience_service.approve_draft(kb_id, draft_id, edits)


@router.post("/{kb_id}/drafts/{draft_id}/reject", dependencies=[Depends(verify_token)])
async def reject_draft(kb_id: str, draft_id: str, body: dict = None):
    """E3: 拒绝草稿→rejected/。"""
    body = body or {}
    return await experience_service.reject_draft(kb_id, draft_id, body.get("reason", ""))


# ── E6/E8/E11: 联动/看板/衰减 ── 静态路由 ──

@router.get("/{kb_id}/stale")
async def check_stale(kb_id: str):
    """E6: 检查经验与文档一致性。"""
    return await experience_service.check_stale(kb_id)


@router.post("/{kb_id}/sync", dependencies=[Depends(verify_token)])
async def sync_kb(kb_id: str):
    """E6: 整库标记需同步。"""
    return await experience_service.sync_kb(kb_id)


@router.get("/{kb_id}/dashboard")
async def dashboard(kb_id: str):
    """E8: 经验看板。"""
    return await experience_service.dashboard(kb_id)


@router.post("/{kb_id}/decay", dependencies=[Depends(verify_token)])
async def apply_decay(kb_id: str):
    """E11: 应用衰减规则。"""
    return await experience_service.apply_decay(kb_id)


# ── 动态路由（包含 {exp_id} 参数的必须放在最后，避免捕获静态路由） ──

@router.get("/{kb_id}/{exp_id}")
async def read_experience(kb_id: str, exp_id: str):
    """读取一条经验的元数据和正文。"""
    return await experience_service.read_experience(kb_id, exp_id)


@router.put("/{kb_id}/{exp_id}", dependencies=[Depends(verify_token)])
async def update_experience(kb_id: str, exp_id: str, body: ExperienceUpdate):
    """更新一条经验。只传需要更新的字段。"""
    return await experience_service.update_experience(kb_id, exp_id, body)


@router.delete("/{kb_id}/{exp_id}", dependencies=[Depends(verify_token)])
async def delete_experience(kb_id: str, exp_id: str):
    """永久删除一条经验。"""
    return await experience_service.delete_experience(kb_id, exp_id)


@router.post("/{kb_id}/{exp_id}/apply", dependencies=[Depends(verify_token)])
async def apply_experience(kb_id: str, exp_id: str, body: ExperienceApplyRequest):
    """标记经验被应用。"""
    return await experience_service.apply_experience(kb_id, exp_id, body)


@router.post("/{kb_id}/{exp_id}/review", dependencies=[Depends(verify_token)])
async def review_experience(kb_id: str, exp_id: str, body: ExperienceReviewRequest):
    """评审经验（评分+评论）。"""
    return await experience_service.review_experience(kb_id, exp_id, body)
