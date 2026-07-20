"""Pydantic models for search API."""
from typing import Any, Optional
from pydantic import BaseModel


class VectorSearchRequest(BaseModel):
    query: str
    kb_id: Optional[str] = None
    top_k: int = 5
    doc_paths: Optional[list[str]] = None
    score_threshold: Optional[float] = None  # None=用 config 默认；显式传值则覆盖
    balance_kbs: bool = False  # 跨库搜索时均衡结果，防大KB主导


class TwoStageSearchRequest(BaseModel):
    query: str
    kb_id: Optional[str] = None
    stage1_top_k: int = 20
    stage2_top_k: int = 5
    enable_graph_expansion: bool = True
    score_threshold: Optional[float] = None  # None=用 config 默认；影响 stage2 fallback 的向量过滤
    balance_kbs: bool = False  # 跨库搜索时均衡结果，防大KB主导


class IndexDocumentRequest(BaseModel):
    kb_id: str = ""
    doc_path: str = ""
    doc_id: str = ""  # 文档 UUID（来自 .knowledge-base.yml）；提供时自动解析 kb_id 和 doc_path
    doc_name: str = ""
    description: str = ""
    content: str = ""
    tags: list[str] = []
    skip_graph: bool = True  # 默认仅建向量，图谱在整理阶段使用 graph_build_kb 构建


class BatchVectorSearchRequest(BaseModel):
    """批量向量相似度查�?"""
    query_doc_paths: list[str]  # 源文档路径列表
    kb_id: Optional[str] = None  # 可选限定知识库
    top_k: int = 5              # 每个源文档返回的相似文档数
    score_threshold: float = 0.3  # 最低相似度阈值


class BatchIndexDocumentRequest(BaseModel):
    """批量文档向量索引请求。"""
    kb_id: str                   # 目标知识库
    doc_paths: list[str]         # 文档路径列表
    force: bool = False          # 是否覆盖已有索�?


class ReindexRequest(BaseModel):
    kb_id: Optional[str] = None
    force: bool = False
