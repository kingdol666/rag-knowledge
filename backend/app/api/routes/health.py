"""
Health-check router.
"""

import logging
from fastapi import APIRouter
from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    # 向量子系统探测:chroma 就绪 + 嵌入模型可用。任一不满足时 overall 仍为
    # healthy(HTTP 语义:进程活着),但 vector 字段会如实降级 —— 运维/上游
    # (AgentWorkShop rag-bridge)据此区分"服务活着"与"检索质量完好"。
    vector: dict = {"ready": None, "embedding_available": None}
    try:
        from app.services.embedding_service import EmbeddingService
        from app.services.vector_service import vector_service

        vector["ready"] = bool(vector_service.is_ready())
        vector["embedding_available"] = EmbeddingService.is_available()
        if not vector["ready"]:
            vector["hint"] = "vector search degraded; POST /api/v1/search/reindex 可重建索引"
    except Exception as exc:  # 探测自身失败不推翻 overall status
        logger.warning("vector subsystem probe failed: %s", exc)
        vector = None
    return HealthResponse(vector=vector)
