"""BGE-M3 embedding 模型封装。惰性加载，单例模式。

只在首次调用 embed() 时加载模型（约 2.2GB）。
- 将 HF_HOME 指向项目级 models_cache/，避免 HTTPS_PROXY/HF_ENDPOINT 劫持
- 模型在缓存中则秒加载，不在则自动下载到缓存
- 模块导入时即净化环境，确保下游 huggingface_hub 不受系统 HTTPS_PROXY 污染
"""
from __future__ import annotations

import logging
import os
from typing import Any, List

from app.config import config
from app.utils.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

# ── 模块级：在 huggingface_hub/requests/urllib3 初始化前净化环境 ──────
# 系统环境的 HTTPS_PROXY（如 Clash/V2Ray 客户端）会劫持 huggingface.co 的
# HTTPS 请求，导致 SSL 错误。必须在任何网络库初始化前清除。
_HF_CACHE = (PROJECT_ROOT.parent / config.embedding_cache_dir).resolve()
_HF_CACHE.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(_HF_CACHE)
os.environ.setdefault("HF_ENDPOINT", "https://huggingface.co")
for _k in ("HTTPS_PROXY", "HTTP_PROXY", "http_proxy", "https_proxy",
           "CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE"):
    os.environ.pop(_k, None)
logger.info("HF_HOME=%s HF_ENDPOINT=%s (env sanitized at import)",
            os.environ["HF_HOME"], os.environ["HF_ENDPOINT"])


class EmbeddingService:
    _model: Any | None = None
    _available: bool = True

    @classmethod
    def is_available(cls) -> bool:
        return cls._available

    @classmethod
    def get_model(cls):
        if cls._model is None and cls._available:
            try:
                from sentence_transformers import SentenceTransformer

                # 模型已由 download_model.py 预下载到项目级缓存，
                # 因此直接 local_files_only 加载，零网络调用
                cls._model = SentenceTransformer(
                    config.embedding_model_name,
                    device=config.embedding_device,
                    local_files_only=True,
                    trust_remote_code=False,
                )
                logger.info("Embedding model loaded: %s on %s (cache=%s)",
                            config.embedding_model_name, config.embedding_device,
                            _HF_CACHE)
            except OSError as e:
                # local_files_only 失败：可能从未执行 download_model.py
                # （如首次部署或缓存被清除），尝试在线下载
                logger.warning("Local cache miss, trying online download: %s", e)
                try:
                    from sentence_transformers import SentenceTransformer
                    cls._model = SentenceTransformer(
                        config.embedding_model_name,
                        device=config.embedding_device,
                    )
                    logger.info("Embedding model loaded FROM NETWORK: %s",
                                config.embedding_model_name)
                except Exception as e2:
                    cls._available = False
                    logger.warning("Embedding model unavailable: %s. "
                                   "Vector search will be degraded.", e2)
            except Exception as e:
                cls._available = False
                logger.warning("Embedding model unavailable: %s. "
                               "Vector search will be degraded.", e)
        return cls._model

    @classmethod
    def embed(cls, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            model = cls.get_model()
        except Exception:
            cls._available = False
            return []
        if model is None:
            return []
        embeddings = model.encode(
            texts,
            normalize_embeddings=config.embedding.get("normalize", True),
            batch_size=config.embedding.get("batch_size", 32),
            show_progress_bar=False,
        )
        return embeddings.tolist()

    @classmethod
    def embed_one(cls, text: str) -> List[float]:
        result = cls.embed([text])
        return result[0] if result else []


embedding_service = EmbeddingService()
