"""向量与两阶段检索 API 路由。"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.config import config
from app.models.search_models import (
    BatchIndexDocumentRequest,
    BatchVectorSearchRequest,
    IndexDocumentRequest,
    ReindexRequest,
    TwoStageSearchRequest,
    VectorSearchRequest,
)
from app.services.storage_reader_service import storage_reader, StorageReaderService
from app.services.two_stage_search_service import two_stage_search_service
from app.services.vector_service import vector_service as _vs
from app.api.deps.auth import verify_token

# vector_service with graceful fallback
def _get_vs():
    if hasattr(_vs, 'is_ready') and _vs.is_ready():
        return _vs
    return None

logger = logging.getLogger(__name__)

# Lazily import graph_service to avoid dependency on neo4j when graph is disabled
def _get_graph_service():
    try:
        from app.services.graph_service import graph_service as _gs
        return _gs
    except ImportError:
        logger.warning("graph_service not available (neo4j not installed)")
        return None


def _find_vector_similar_docs(doc_path: str, content: str, kb_id: str) -> list[dict]:
    """计算新文档与已有文档的向量相似度，返回 top-3 相似文档。

    用于给 graph_service.index_document 的 similar_docs 参数。
    用新文档的内容作为 query，在向量库搜索最相似的文档。
    """
    try:
        vs = _get_vs()
        if not vs:
            return []
        # 用文档内容前 2000 字作为查询
        query = content[:2000] if content else ""
        if not query:
            return []
        results = vs.search(query=query, kb_id=kb_id, top_k=3,
                            score_threshold=config.vector_score_threshold)
        # 排除自身
        return [
            {"doc_path": r["doc_path"], "score": r["score"]}
            for r in results
            if r.get("doc_path", "") != doc_path
        ]
    except Exception as e:
        logger.warning("Vector similar docs calc failed: %s", e)
        return []


router = APIRouter(prefix="/api/v1/search", tags=["Search"])


@router.get("/debug-paths")
async def debug_paths(kb_id: str = "", doc_path: str = "") -> dict[str, Any]:
    """Debug: test path resolution logic. Dev-mode only — exposes internal
    storage paths, KB enumeration, and config internals that have no place in
    a production deployment."""
    if config.app_mode != "dev":
        raise HTTPException(404, "Not found")
    kbs = storage_reader.list_knowledge_bases()
    kb_path = next(
        (kb["path"] for kb in kbs
         if kb["kb_id"] == kb_id or kb["path"] == kb_id),
        ""
    ) if kb_id else ""
    resolved = f"{kb_path}/{doc_path}" if kb_path and doc_path else doc_path
    content = storage_reader.read_document_content(resolved) if resolved else ""
    return {
        "kb_id": kb_id,
        "kb_path": kb_path,
        "doc_path": doc_path,
        "resolved": resolved,
        "content_len": len(content) if content else 0,
        "kbs_count": len(kbs),
        "kbs": [{"id": k["kb_id"], "path": k["path"]} for k in kbs[:5]],
        "storage_root": str(storage_reader.root),
        "tree_fs_exists": storage_reader.tree_fs_path.exists(),
        "config_tree_fs_root": config.storage_tree_fs_root,
    }


@router.post("/vector")
async def vector_search(req: VectorSearchRequest) -> dict[str, Any]:
    """纯向量检索。"""
    if not config.vector_enabled:
        raise HTTPException(503, "Vector search is disabled")
    vs = _get_vs()
    if not vs:
        return {"success": True, "results": [], "count": 0, "note": "vector service not ready"}
    results = vs.search(query=req.query, kb_id=req.kb_id,
                                    top_k=req.top_k, doc_paths=req.doc_paths,
                                    score_threshold=req.score_threshold,
                                    balance_kbs=req.balance_kbs)
    return {"success": True, "results": results, "count": len(results)}


@router.post("/batch-vector")
async def batch_vector_search(req: BatchVectorSearchRequest) -> dict[str, Any]:
    """批量向量相似度查询：对多个源文档，找出与每个源文档最相似的文档片段。

    典型使用场景：
    - 跨文档相似度分析
    - 批量文档去�?   - 相关文档发现

    Args:
        query_doc_paths: 源文档路径列表（相对于 tree-fs root）
        kb_id: 可选，限定在某个知识库内搜�?        top_k: 每个源文档返回的相似文档�?        score_threshold: 最低余弦相似度阈值 (0~1)

    Returns:
        {success, results: {doc_path: [{content, score, matched_doc_path, ...}], ...}}
    """
    if not config.vector_enabled:
        raise HTTPException(503, "Vector search is disabled")
    vs = _get_vs()
    if not vs:
        return {"success": True, "results": {}, "count": 0, "note": "vector service not ready"}
    results = vs.find_similar_docs(
        doc_paths=req.query_doc_paths,
        kb_id=req.kb_id,
        top_k=req.top_k,
        score_threshold=req.score_threshold,
    )
    total = sum(len(v) for v in results.values())
    return {"success": True, "results": results, "count": total}


@router.post("/two-stage")
async def two_stage_search(req: TwoStageSearchRequest) -> dict[str, Any]:
    """两阶段精准检索：广搜索 → 文档向量精筛。"""
    if not config.vector_enabled:
        raise HTTPException(503, "Vector search is disabled")
    result = two_stage_search_service.search(
        query=req.query, kb_id=req.kb_id,
        stage1_top_k=req.stage1_top_k, stage2_top_k=req.stage2_top_k,
        enable_graph_expansion=req.enable_graph_expansion,
        score_threshold=req.score_threshold,
        balance_kbs=req.balance_kbs,
    )
    return {"success": True, **result}


@router.post("/index-document", dependencies=[Depends(verify_token)])
async def index_document(req: IndexDocumentRequest) -> dict[str, Any]:
    """单文档索引：向量 + 图谱。

    支持两种调用方式：
    1. 提供 doc_id（文档 UUID）→ 自动解析 kb_id 和 doc_path
    2. 提供 kb_id + doc_path → 直接使用
    """
    # ── doc_id 优先：从 .knowledge-base.yml 解析 kb_id 和 doc_path ──
    if req.doc_id and not req.doc_path:
        found = storage_reader.find_document_by_id(req.doc_id)
        if not found:
            raise HTTPException(404, f"Document not found by id: {req.doc_id}")
        req.kb_id = found["kb_id"] or found["kb_path"]
        req.doc_path = found["doc"]["path"]
        if not req.doc_name:
            req.doc_name = found["doc"].get("name", "")
        if not req.description:
            req.description = found["doc"].get("description", "")
        logger.info("index_document: resolved doc_id=%s -> kb_id=%s, doc_path=%s",
                     req.doc_id, req.kb_id, req.doc_path)

    content = req.content

    # Resolve bare doc_path (e.g. "doc.md") to full path (e.g. "kb_name/doc.md")
    # by using the kb_id to find the KB's path prefix.
    resolved_doc_path = req.doc_path
    # 裸文件名一律解析为全路径（kb_path/doc.md）—— 不论 content 是否由调用方提供。
    # 这样 ChromaDB 元数据与 BM25 返回的全路径一致（修复 two_stage stage2 content 为空），
    # 也保证 read_document_content 能命中磁盘文件。
    if "/" not in req.doc_path.replace("\\", "/"):
        kbs = storage_reader.list_knowledge_bases()
        kb_path = next(
            (kb["path"] for kb in kbs
             if kb["kb_id"] == req.kb_id or kb["path"] == req.kb_id),
            ""
        )
        if kb_path:
            resolved_doc_path = f"{kb_path}/{req.doc_path.lstrip('/').lstrip('\\')}"
            logger.info("index_document: resolved %r -> %r", req.doc_path, resolved_doc_path)

    if not content:
        content = storage_reader.read_document_content(resolved_doc_path)
        if not content:
            raise HTTPException(404, f"Document content not found: {resolved_doc_path}")

    vector_index = {}
    vs = _get_vs()
    if vs:
        try:
            vector_index = await asyncio.to_thread(
                vs.index_document,
                kb_id=req.kb_id, doc_path=resolved_doc_path, content=content,
                metadata={"description": req.description, "name": req.doc_name},
            )
        except Exception as e:
            logger.error("Vector indexing failed: %s", e)

    graph_stats = {}
    # skip_graph=True（默认, 解析上传时）→ 不构建图谱, 图谱在整理阶段由 graph_build_kb 统一构建
    if not req.skip_graph and config.graph_enabled:
        gs = _get_graph_service()
        if gs:
            try:
                similar_docs = _find_vector_similar_docs(resolved_doc_path, content, req.kb_id)
                graph_stats = await asyncio.to_thread(
                    gs.index_document,
                    doc_path=resolved_doc_path, content=content,
                    kb_id=req.kb_id, doc_name=req.doc_name,
                    description=req.description,
                    tags=req.tags,
                    similar_docs=similar_docs,
                )
            except Exception as e:
                logger.warning("Graph indexing failed: %s", e)

    # 解析 kb_path 用于 YAML 写回
    kbs = storage_reader.list_knowledge_bases()
    kb_path = next(
        (kb["path"] for kb in kbs
         if kb["kb_id"] == req.kb_id or kb["path"] == req.kb_id),
        ""
    )

    if vector_index and kb_path:
        storage_reader.update_document_vector_index(
            kb_path=kb_path, doc_path=resolved_doc_path, vector_index=vector_index,
        )

    # Phase 1: graph_index 写回 .knowledge-base.yml（与 vector_index 对称）
    # 仅当 skip_graph=False（整理阶段）才写回 graph_index
    if graph_stats and kb_path and not req.skip_graph:
        try:
            storage_reader.update_document_graph_index(
                kb_path=kb_path, doc_path=resolved_doc_path, graph_index=graph_stats,
            )
        except Exception as e:
            logger.warning("Failed to write back graph_index: %s", e)

    # Invalidate keyword index so BM25 picks up new content on next search
    if vector_index or graph_stats:
        two_stage_search_service.invalidate_keyword_index()

    return {"success": True, "vector_index": vector_index,
            "graph_index": graph_stats, "graph_stats": graph_stats}


@router.post("/batch-index", dependencies=[Depends(verify_token)])
async def batch_index_documents(req: BatchIndexDocumentRequest) -> dict[str, Any]:
    """批量文档向量索引。

    Args:
        kb_id: 知识库 ID
        doc_paths: 文档路径列表
        force: 是否覆盖已有索�?

    Returns:
        {success, indexed: [...], skipped: [...], errors: [...]}
    """
    vs = _get_vs()
    gs = _get_graph_service() if config.graph_enabled else None
    kbs = storage_reader.list_knowledge_bases()
    kb_path = next(
        (kb["path"] for kb in kbs
         if kb["kb_id"] == req.kb_id or kb["path"] == req.kb_id),
        ""
    )

    indexed = []
    skipped = []
    errors = []

    for doc_path in req.doc_paths:
        # 将裸 doc_path 解析为全路径（kb_path/doc.md）—— read_document_content /
        # get_document_metadata / update_document_vector_index 都按 root+doc_path 拼接，
        # 裸名会读不到内容；同时让 ChromaDB 元数据存全路径，与 BM25 返回值一致。
        resolved = doc_path
        if kb_path and "/" not in doc_path.replace("\\", "/"):
            resolved = f"{kb_path}/{doc_path.lstrip('/').lstrip('\\')}"

        if not req.force:
            # 检查是否已有向量索引
            if kb_path:
                doc_meta = storage_reader.get_document_metadata(kb_path, resolved)
                if doc_meta and doc_meta.get("vector_index"):
                    skipped.append({"doc_path": doc_path, "reason": "already indexed"})
                    continue

        content = storage_reader.read_document_content(resolved)
        if not content:
            errors.append({"doc_path": doc_path, "reason": "no content"})
            continue

        try:
            vi = {}
            if vs:
                vi = await asyncio.to_thread(
                    vs.index_document,
                    kb_id=req.kb_id, doc_path=resolved, content=content,
                )
            # 批量索引仅建向量（skip_graph=True 逻辑）
            # 图谱在整理阶段由 graph_build_kb 按 KB 统一构建，
            # 比逐文档构建更高效且能建立 KB 内文档间关联
            gi = {}
            if vi and kb_path:
                storage_reader.update_document_vector_index(
                    kb_path=kb_path, doc_path=resolved, vector_index=vi,
                )
            # Phase 1: graph_index 写回 YAML
            if gi and kb_path:
                try:
                    storage_reader.update_document_graph_index(
                        kb_path=kb_path, doc_path=resolved, graph_index=gi,
                    )
                except Exception as e:
                    logger.warning("graph_index writeback failed for %s: %s", doc_path, e)
            indexed.append({
                "doc_path": doc_path,
                "vector_index": vi,
                "graph_index": gi,
            })
        except Exception as e:
            logger.error("Batch index failed for %s: %s", doc_path, e)
            errors.append({"doc_path": doc_path, "reason": str(e)[:200]})

    if indexed:
        two_stage_search_service.invalidate_keyword_index()

    return {
        "success": True,
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
        "total_indexed": len(indexed),
    }


@router.post("/reindex", dependencies=[Depends(verify_token)])
async def reindex(req: ReindexRequest) -> dict[str, Any]:
    """重建向量索引和知识图谱。kb_id 为空则重建全部。"""
    kbs = storage_reader.list_knowledge_bases()
    if req.kb_id:
        kbs = [kb for kb in kbs if kb["kb_id"] == req.kb_id or kb["path"] == req.kb_id]

    total_docs = total_chunks = total_relations = 0
    errors = []

    for kb in kbs:
        kb_id, kb_path = kb["kb_id"], kb["path"]

        # force=True: delete and recreate the collection to clear stale chunks
        # (documents moved out of this KB would leave orphaned vectors otherwise)
        if req.force:
            try:
                vs = _get_vs()
                if vs:
                    vs.delete_kb(kb_id)
            except Exception as e:
                logger.debug("Collection delete for reindex: %s", e)
            # Phase 6.6: 同步清理该 KB 的图谱数据（与 vector 对称）
            if config.graph_enabled:
                gs = _get_graph_service()
                if gs:
                    try:
                        gs.delete_kb_graph(kb_id)
                    except Exception as e:
                        logger.debug("Graph delete for reindex: %s", e)

        docs = storage_reader.list_documents(kb_path)
        for doc in docs:
            doc_path = doc.get("path", "")
            if not doc_path:
                continue
            if not req.force and doc.get("vector_index"):
                continue
            content = storage_reader.read_document_content(doc_path)
            if not content:
                continue
            try:
                vs = _get_vs()
                vi = {}
                if vs:
                    vi = vs.index_document(
                        kb_id=kb_id, doc_path=doc_path, content=content,
                        metadata={"description": doc.get("description", "")},
                    )
                gi = {}
                if config.graph_enabled:
                    gs = _get_graph_service()
                    if gs:
                        # 提取标签
                        raw_tags = doc.get("tags", [])
                        doc_tags = []
                        if isinstance(raw_tags, list):
                            doc_tags = [t.get("name", str(t)) if isinstance(t, dict) else str(t) for t in raw_tags]
                        elif isinstance(raw_tags, str):
                            doc_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
                        # 计算向量 top-3 相似文档
                        similar_docs = _find_vector_similar_docs(doc_path, content, kb_id)
                        gi = gs.index_document(
                            doc_path=doc_path, content=content, kb_id=kb_id,
                            doc_name=doc.get("name", ""),
                            description=doc.get("description", ""),
                            tags=doc_tags,
                            similar_docs=similar_docs,
                        )
                if vi:
                    storage_reader.update_document_vector_index(
                        kb_path=kb_path, doc_path=doc_path, vector_index=vi,
                    )
                    total_chunks += vi.get("total_chunks", 0)
                if gi:
                    try:
                        storage_reader.update_document_graph_index(
                            kb_path=kb_path, doc_path=doc_path, graph_index=gi,
                        )
                    except Exception as e:
                        logger.warning("graph_index writeback failed for %s: %s", doc_path, e)
                    total_relations += gi.get("vector_relations", 0) + gi.get("agent_relations", 0)
                total_docs += 1
            except Exception as e:
                logger.error("Reindex failed for %s: %s", doc_path, e)
                errors.append({"doc_path": doc_path, "error": str(e)})

    return {"success": True, "total_docs": total_docs, "total_chunks": total_chunks,
            "total_relations": total_relations,
            "errors": errors}


@router.get("/stats")
async def search_stats(kb_id: str | None = None) -> dict[str, Any]:
    """向量索引统计。"""
    vs = _get_vs()
    if not vs:
        return {"success": True, "stats": {}}
    return {"success": True, "stats": vs.get_stats(kb_id)}


@router.delete("/kb/{kb_id}", dependencies=[Depends(verify_token)])
async def delete_kb_vectors(kb_id: str, kb_path: str = "") -> dict[str, Any]:
    """删除某知识库的整个向量 collection。

    自动清理两种命名约定（kb_{uuid} 与 kb_{path}），因为历史索引可能用 UUID 也可能用 path。
    KB 删除时由 web 端联动调用，避免孤儿 collection 累积（Fix 4.2）。
    delete_kb 内部对不存在的 collection 静默处理，故可安全地对两个候选都调用。
    """
    candidates = list(dict.fromkeys([c for c in [kb_id, kb_path] if c]))  # 去重保序
    # Use _get_vs() readiness guard (not the bare _vs singleton) so we don't
    # trigger a lazy ChromaDB init when the service isn't ready — matching the
    # sibling delete_document_vectors handler and all other search routes.
    vs = _get_vs()
    if not vs:
        return {"success": True, "kb_id": kb_id, "kb_path": kb_path,
                "cleaned": [], "note": "vector service not ready — nothing to delete"}
    for cand in candidates:
        try:
            vs.delete_kb(cand)
            logger.info("Deleted vector collection for %s", cand)
        except Exception as e:
            logger.warning("delete_kb failed for %s: %s", cand, e)
    return {"success": True, "kb_id": kb_id, "kb_path": kb_path, "cleaned": candidates}


@router.delete("/document", dependencies=[Depends(verify_token)])
async def delete_document_vectors(
    kb_id: str, doc_path: str,
) -> dict[str, Any]:
    """删除单文档的向量 chunks（文档移动/删除时联动清理）。

    与 ``DELETE /api/v1/graph/document`` 配合使用：
    移动文档时先清旧向量+旧图谱节点，再对新路径重新索引。
    """
    vs = _get_vs()
    deleted_chunks = 0
    if vs:
        try:
            # delete_document 内部按 doc_path 匹配 chunks
            vs.delete_document(kb_id, doc_path)
            deleted_chunks = 1
            logger.info("Deleted vector chunks for %s in %s", doc_path, kb_id)
        except Exception as e:
            logger.warning("delete_document vectors failed for %s: %s", doc_path, e)
    return {"success": True, "kb_id": kb_id, "doc_path": doc_path,
            "cleaned": deleted_chunks}
