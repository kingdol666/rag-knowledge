"""知识图谱 API 路由（v3 — 文档/KB/标签为中心，无 NER）。"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j.exceptions import ServiceUnavailable
from pydantic import BaseModel

from app.config import config
from app.services.graph_service import graph_service
from app.api.deps.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/graph", tags=["Graph"])


# ── 请求模型 ───────────────────────────────────────────────────

class BuildKbGraphRequest(BaseModel):
    kb_id: str
    force: bool = False


class BuildAllGraphsRequest(BaseModel):
    force: bool = False
    enable_vector_similarity: bool = True


class AgentRelationRequest(BaseModel):
    """添加 Agent 判断的文档关联。"""
    doc_path: str
    target_doc_path: str
    relation_type: str = "agent_judged"
    weight: float = 1.0
    reasoning: str = ""


class BatchAgentRelationRequest(BaseModel):
    relations: list[AgentRelationRequest]


# ── 辅助装饰器 ─────────────────────────────────────────────────

def _guard_graph_enabled() -> None:
    """如图谱功能未启用则抛 503。"""
    if not config.graph_enabled:
        raise HTTPException(503, "Graph is disabled (set graph.enabled=true in config.yml)")


def _handle_graph_unavailable(func):
    """将 Neo4j ServiceUnavailable 转为 503（而非 500）。"""
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except ServiceUnavailable as exc:
            logger.warning("Graph endpoint %s unavailable: %s", func.__name__, exc)
            raise HTTPException(
                503,
                "Graph database (Neo4j) is unavailable. "
                "Start it with: docker compose up -d neo4j",
            ) from exc

    return wrapper


# ── 健康与统计 ─────────────────────────────────────────────────

@router.get("/health")
async def graph_health() -> dict[str, Any]:
    """图谱依赖健康探测（永不抛错）。"""
    return {"success": True, "health": graph_service.health()}


@router.get("/stats")
@_handle_graph_unavailable
async def graph_stats() -> dict[str, Any]:
    _guard_graph_enabled()
    return {"success": True, "stats": graph_service.get_stats()}


# ── 搜索查询 ───────────────────────────────────────────────────

@router.get("/search/documents")
@_handle_graph_unavailable
async def graph_search_documents(keyword: str = Query(..., min_length=1),
                                  limit: int = 20) -> dict[str, Any]:
    """按名称/路径搜索文档节点。"""
    _guard_graph_enabled()
    docs = graph_service.search_documents(keyword, limit)
    return {"success": True, "documents": docs, "count": len(docs)}


@router.get("/search/kbs")
@_handle_graph_unavailable
async def graph_search_kbs(keyword: str = Query(..., min_length=1),
                            limit: int = 20) -> dict[str, Any]:
    """搜索知识库节点。"""
    _guard_graph_enabled()
    kbs = graph_service.search_kbs(keyword, limit)
    return {"success": True, "kbs": kbs, "count": len(kbs)}


@router.get("/search/tags")
@_handle_graph_unavailable
async def graph_search_tags(keyword: str = Query(..., min_length=1),
                             limit: int = 20) -> dict[str, Any]:
    """搜索标签节点。"""
    _guard_graph_enabled()
    tags = graph_service.search_tags(keyword, limit)
    return {"success": True, "tags": tags, "count": len(tags)}


# ── 文档中心查询 ──────────────────────────────────────────────

@router.get("/document")
@_handle_graph_unavailable
async def graph_for_document(doc_path: str, limit: int = 50) -> dict[str, Any]:
    """文档中心图谱视图：文档信息 + 关联文档 + 跨 KB 连接。"""
    _guard_graph_enabled()
    return {"success": True, "graph": graph_service.get_document_graph(doc_path, limit)}


@router.get("/document/related")
@_handle_graph_unavailable
async def graph_related_documents(doc_path: str, limit: int = 20) -> dict[str, Any]:
    """返回与某文档真正关联的其他文档（质量过滤后的 RELATED_TO 边）。"""
    _guard_graph_enabled()
    related = graph_service.get_related_documents(doc_path, limit)
    return {"success": True, "related": related, "count": len(related)}


@router.get("/document/enhanced")
@_handle_graph_unavailable
async def graph_document_enhanced(doc_path: str, limit: int = 20) -> dict[str, Any]:
    """增强版文档关联查询：按连接类型分组（vector_similar / shared_tag / agent_judged）。

    与 /document/related 的区别：
    - 结果按连接类型分组，清楚展示每条关联的来源
    - shared_tag 结果包含 shared_tags 字段（具体哪些标签重叠）
    - vector_similar 结果包含 similarity score
    - 包含跨 KB 连接统计
    """
    _guard_graph_enabled()
    result = graph_service.get_related_documents_enhanced(doc_path, limit)
    return {"success": True, **result}


@router.get("/documents-by-tag")
@_handle_graph_unavailable
async def docs_by_tag(tag_name: str, limit: int = 50) -> dict[str, Any]:
    """按标签查找文档。"""
    _guard_graph_enabled()
    docs = graph_service.get_documents_by_tag(tag_name, limit)
    return {"success": True, "documents": docs, "count": len(docs)}


# ── KB 概览 ────────────────────────────────────────────────────

@router.get("/kb-overview")
@_handle_graph_unavailable
async def graph_kb_overview(kb_id: str) -> dict[str, Any]:
    """KB 级图谱概览：文档统计 + 标签分布 + 关联 KB + Top 文档。"""
    _guard_graph_enabled()
    return {"success": True, "overview": graph_service.get_kb_overview(kb_id)}


# ── 节点邻居 ──────────────────────────────────────────────────

@router.get("/neighbors")
@_handle_graph_unavailable
async def graph_neighbors(
    node_id: str,
    node_type: str = Query("document", pattern="^(document|kb|tag)$"),
    depth: int = 1,
) -> dict[str, Any]:
    """按节点 ID 查询邻居子图。node_type: document|kb|tag"""
    _guard_graph_enabled()
    g = graph_service.get_neighbors(node_id, node_type, depth)
    return {"success": True, "graph": g}


# ── Agent 关联 ────────────────────────────────────────────────

@router.post("/agent-relation", dependencies=[Depends(verify_token)])
@_handle_graph_unavailable
async def add_agent_relation(req: AgentRelationRequest) -> dict[str, Any]:
    """添加 Agent 判断的文档间关联（可追溯 reasoning）。"""
    _guard_graph_enabled()
    result = graph_service.index_document(
        doc_path=req.doc_path,
        agent_relations=[{
            "doc_path": req.target_doc_path,
            "relation_type": req.relation_type,
            "weight": req.weight,
            "reasoning": req.reasoning,
        }],
    )
    return {"success": True, "result": result}


@router.post("/agent-relations/batch", dependencies=[Depends(verify_token)])
@_handle_graph_unavailable
async def batch_add_agent_relations(req: BatchAgentRelationRequest) -> dict[str, Any]:
    """批量添加 Agent 判断的文档间关联。"""
    _guard_graph_enabled()
    results = []
    for rel in req.relations:
        r = graph_service.index_document(
            doc_path=rel.doc_path,
            agent_relations=[{
                "doc_path": rel.target_doc_path,
                "relation_type": rel.relation_type,
                "weight": rel.weight,
                "reasoning": rel.reasoning,
            }],
        )
        results.append({
            "doc_path": rel.doc_path,
            "target": rel.target_doc_path,
            "result": r,
        })
    return {"success": True, "results": results}


# ── 批量构建 ──────────────────────────────────────────────────

@router.post("/build-kb", dependencies=[Depends(verify_token)])
@_handle_graph_unavailable
async def graph_build_kb(req: BuildKbGraphRequest) -> dict[str, Any]:
    """为整个 KB 自动构建文档关系图谱（基于 metadata，不读文档内容）。"""
    _guard_graph_enabled()
    result = graph_service.build_kb_graph(req.kb_id, req.force)
    return {"success": result.get("success", True), "result": result}


@router.post("/build-all", dependencies=[Depends(verify_token)])
@_handle_graph_unavailable
async def graph_build_all(req: BuildAllGraphsRequest) -> dict[str, Any]:
    """为所有 KB 构建文档关系图谱。

    三阶段构建：
    1. 元数据 + 标签关联（shared_tag）
    2. 内容向量相似度关联（vector_similar）—— 读取文档内容计算
    3. KB 间关联（基于共享标签 + 跨库文档相似度）
    """
    _guard_graph_enabled()
    result = graph_service.build_all_graphs(req.force, req.enable_vector_similarity)
    return {"success": True, "result": result}


# ── 跨 KB 分析 ────────────────────────────────────────────────

@router.get("/cross-kb-documents")
@_handle_graph_unavailable
async def cross_kb_documents(limit: int = 50) -> dict[str, Any]:
    """跨 KB 桥梁文档：通过 shared_tag/vector_similar 关联到不同 KB 的文档。"""
    _guard_graph_enabled()
    docs = graph_service.find_cross_kb_documents(limit)
    return {"success": True, "documents": docs, "count": len(docs)}


# ── 路径与中心度 ──────────────────────────────────────────────

@router.get("/document-paths")
@_handle_graph_unavailable
async def doc_paths(doc_a: str, doc_b: str, max_depth: int = 4) -> dict[str, Any]:
    """两个文档之间的最短路径（经 RELATED_TO 关系）。"""
    _guard_graph_enabled()
    result = graph_service.find_document_paths(doc_a, doc_b, max_depth)
    return {"success": True, "result": result}


@router.get("/central-documents")
@_handle_graph_unavailable
async def central_documents(kb_id: str, top_n: int = 20) -> dict[str, Any]:
    """KB 内关联度最高的文档（按 RELATED_TO 度中心性）。"""
    _guard_graph_enabled()
    docs = graph_service.find_central_documents(kb_id, top_n)
    return {"success": True, "documents": docs, "count": len(docs)}


# ── 删除清理 ──────────────────────────────────────────────────

@router.delete("/document", dependencies=[Depends(verify_token)])
@_handle_graph_unavailable
async def graph_delete_document(doc_path: str) -> dict[str, Any]:
    """删除单文档图谱数据（级联清理 RELATED_TO/HAS_TAG 边 + 孤儿节点）。"""
    _guard_graph_enabled()
    deleted = graph_service.delete_document(doc_path)
    return {"success": True, "doc_path": doc_path, "nodes_deleted": deleted}


@router.delete("/kb/{kb_id}", dependencies=[Depends(verify_token)])
@_handle_graph_unavailable
async def graph_delete_kb(kb_id: str) -> dict[str, Any]:
    """删除整个 KB 的图谱数据（级联清理文档/边 + 孤儿标签）。"""
    _guard_graph_enabled()
    result = graph_service.delete_kb_graph(kb_id)
    return {"success": True, "result": result}
