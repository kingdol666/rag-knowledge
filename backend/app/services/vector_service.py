"""ChromaDB 向量索引服务。

设计：
- 一个知识库 → 一个 collection（kb_{kb_id}）
- 一个文档 → 一组 chunk（{doc_path}__chunk_{index}）
- 通过 where={"doc_path": ...} 精准定位文档向量

当 embedding 模型不可用时，所有方法优雅降级为返回空结果。
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from app.config import config
from app.services.embedding_service import embedding_service
from app.utils.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now().isoformat()


class VectorService:
    def __init__(self) -> None:
        self._client: chromadb.ClientAPI | None = None
        self._ready = False
        # Test ChromaDB at import time — if it fails, all methods return empty
        try:
            _ = self.client  # trigger lazy init
            self._ready = True
        except Exception as e:
            logger.warning("ChromaDB unavailable: %s. Vector search disabled.", e)


    def is_ready(self) -> bool:
        return self._ready and embedding_service.is_available()

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            persist_dir = PROJECT_ROOT.parent / config.vector_persist_dir
            persist_dir = persist_dir.resolve()
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            logger.info("ChromaDB initialized at %s", persist_dir)
        return self._client

    # ── Collection 管理 ──────────────────────────────────────────

    def _collection_name(self, kb_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in kb_id)
        return f"{config.vector_collection_prefix}{safe}"

    def _get_or_create_collection(self, kb_id: str):
        return self.client.get_or_create_collection(
            name=self._collection_name(kb_id),
            metadata={"hnsw:space": "cosine"},
        )

    def _safe_get_collection(self, kb_id: str):
        """Get collection, auto-resolving UUID↔path naming inconsistency.

        历史索引入库可能用 UUID 或 path 作为 collection 后缀，
        但 kb_list 返回的 kbId 是 UUID，导致用户传 UUID 搜索时找到空 collection。
        先试原形式；未命中则通过 storage_reader 解析另一形式再试（Bug 7 修复）。
        """
        try:
            return self.client.get_collection(self._collection_name(kb_id))
        except Exception:
            pass
        # Resolve alternate form (UUID→path or path→UUID) via storage_reader
        try:
            from app.services.storage_reader_service import storage_reader
            for kb in storage_reader.list_knowledge_bases():
                if kb["kb_id"] == kb_id and kb.get("path"):
                    try:
                        return self.client.get_collection(self._collection_name(kb["path"]))
                    except Exception:
                        pass
                elif kb.get("path") == kb_id and kb.get("kb_id"):
                    try:
                        return self.client.get_collection(self._collection_name(kb["kb_id"]))
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    def _all_kb_collections(self) -> list:
        prefix = config.vector_collection_prefix
        try:
            cols = self.client.list_collections()
            return [c for c in cols if c.name.startswith(prefix)]
        except Exception:
            return []
    def _resolve_hierarchical_collections(self, kb_id: str) -> list:
        """Resolve kb_id to parent + all descendant KB collections (K1 fix).

        Hierarchical parent KBs store documents in child KB collections.
        This resolves the parent UUID to all descendant UUIDs and gathers
        their ChromaDB collections so search covers the full subtree.
        """
        try:
            from app.services.storage_reader_service import storage_reader
            all_kb_ids = storage_reader.resolve_kb_ids_with_children(kb_id)
        except Exception:
            all_kb_ids = [kb_id]
        cols = []
        for kid in all_kb_ids:
            col = self._safe_get_collection(kid)
            if col is not None:
                cols.append(col)
        if not cols:
            col = self._safe_get_collection(kb_id)
            if col is not None:
                cols.append(col)
        return cols

    # ── 索引构建 ──────────────────────────────────────────────────

    def index_document(
        self,
        kb_id: str,
        doc_path: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chunks = self._chunk_text(content)
        if not chunks:
            logger.warning("No chunks for %s", doc_path)
            return {}

        embeddings = embedding_service.embed(chunks)
        collection = self._get_or_create_collection(kb_id)

        self._delete_doc_chunks(collection, doc_path)

        chunk_ids = [f"{doc_path}__chunk_{i}" for i in range(len(chunks))]
        chunk_metadatas = [
            {
                "doc_path": doc_path,
                "kb_id": kb_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                **(metadata or {}),
            }
            for i in range(len(chunks))
        ]
        collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=chunk_metadatas,
        )

        vector_index = {
            "collection": self._collection_name(kb_id),
            "chunk_id_prefix": f"{doc_path}__chunk_",
            "total_chunks": len(chunks),
            "embedding_model": config.embedding_model_name.split("/")[-1],
            "indexed_at": _now_iso(),
            "graph_doc_id": f"doc::{doc_path.replace(chr(92), '/')}",
        }
        logger.info("Indexed %d chunks for %s in KB %s",
                    len(chunks), doc_path, kb_id)
        return vector_index

    # ── 检索 ──────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        kb_id: str | None = None,
        top_k: int | None = None,
        doc_paths: list[str] | None = None,
        score_threshold: float | None = None,
        balance_kbs: bool = False,
    ) -> list[dict[str, Any]]:
        if top_k is None or top_k <= 0:
            top_k = config.vector_top_k
        query_embedding = embedding_service.embed_one(query)

        if kb_id:
            collections = self._resolve_hierarchical_collections(kb_id)
        else:
            collections = self._all_kb_collections()

        where_filter = None
        if doc_paths:
            if len(doc_paths) == 1:
                where_filter = {"doc_path": doc_paths[0]}
            else:
                where_filter = {"doc_path": {"$in": doc_paths}}

        threshold = score_threshold if score_threshold is not None else config.vector_score_threshold

        # ── 跨库均衡搜索：每个KB独立搜索，轮询选取，防大KB主导 ──
        if balance_kbs and not kb_id and len(collections) > 1:
            return self._balanced_cross_kb_search(
                query_embedding=query_embedding,
                collections=collections,
                top_k=top_k,
                threshold=threshold,
                where_filter=where_filter,
            )

        results: list[dict[str, Any]] = []
        for col in collections:
            if col is None:
                continue
            try:
                query_kwargs = {
                    "query_embeddings": [query_embedding],
                    "n_results": top_k,
                    "include": ["documents", "distances", "metadatas"],
                }
                if where_filter:
                    query_kwargs["where"] = where_filter
                res = col.query(**query_kwargs)
            except Exception as e:
                logger.warning("Vector query failed in %s: %s", col.name, e)
                continue

            for doc, dist, meta in zip(
                res["documents"][0],
                res["distances"][0],
                res["metadatas"][0],
            ):
                if meta is None or doc is None:
                    continue
                results.append({
                    "content": doc,
                    "score": 1.0 - dist,
                    "doc_path": meta.get("doc_path", ""),
                    "kb_id": meta.get("kb_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "collection": col.name,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        results = [r for r in results[:top_k] if r["score"] >= threshold]

        # V2 增强: 短文本后处理过滤
        # 向量搜索可能返回仅标题的短 chunk(<50字符)，score 虚高但内容无实质意义
        # 将短 chunk score 降权到 0.3x，并在 metadata 标记 short_content_warning
        SHORT_CONTENT_CHARS = 50
        for r in results:
            content = r.get("content")
            content_len = len(content.strip()) if content else 0
            if content_len < SHORT_CONTENT_CHARS:
                logger.debug("Short content downgrade: %s (len=%d, score=%.3f -> %.3f)",
                             r.get("doc_path", ""), content_len, r["score"], r["score"] * 0.3)
                r["score"] = round(r["score"] * 0.3, 4)
                r["short_content_warning"] = True

        # 重新排序（降权后短文本会被自然排到底部）
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def _balanced_cross_kb_search(
        self,
        query_embedding: list[float],
        collections: list,
        top_k: int,
        threshold: float,
        where_filter: dict | None = None,
    ) -> list[dict[str, Any]]:
        """跨库均衡搜索：每个KB独立检索，轮询选取确保公平代表性。

        算法：
        1. 每个KB collection独立搜索 per_kb_cap = max(top_k // n_kbs, 2) 条结果
        2. 按KB分组，各组内按分数降序排列
        3. 轮询选取：第1轮取每个KB最高分，第2轮取次高分...
        4. 无结果的KB自动退出轮询，配额自动重新分配
        5. 最终结果按分数降序排列
        """
        n_kbs = len([c for c in collections if c is not None])
        if n_kbs == 0:
            return []
        per_kb_cap = max(top_k // n_kbs + 1, 2)

        # 每个KB独立搜索
        results_by_kb: dict[str, list[dict[str, Any]]] = {}
        for col in collections:
            if col is None:
                continue
            try:
                query_kwargs = {
                    "query_embeddings": [query_embedding],
                    "n_results": per_kb_cap,
                    "include": ["documents", "distances", "metadatas"],
                }
                if where_filter:
                    query_kwargs["where"] = where_filter
                res = col.query(**query_kwargs)
            except Exception as e:
                logger.warning("Balanced query failed in %s: %s", col.name, e)
                continue

            kb_results: list[dict[str, Any]] = []
            for doc, dist, meta in zip(
                res["documents"][0],
                res["distances"][0],
                res["metadatas"][0],
            ):
                if meta is None or doc is None:
                    continue
                score = 1.0 - dist
                if score < threshold:
                    continue
                kb_results.append({
                    "content": doc,
                    "score": score,
                    "doc_path": meta.get("doc_path", ""),
                    "kb_id": meta.get("kb_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "collection": col.name,
                })

            if kb_results:
                kb_results.sort(key=lambda x: x["score"], reverse=True)
                results_by_kb[col.name] = kb_results

        if not results_by_kb:
            return []

        # 轮询选取
        final: list[dict[str, Any]] = []
        kb_keys = list(results_by_kb.keys())
        indices: dict[str, int] = {k: 0 for k in kb_keys}

        while len(final) < top_k:
            added = False
            for kb_key in kb_keys:
                idx = indices[kb_key]
                if idx < len(results_by_kb[kb_key]):
                    final.append(results_by_kb[kb_key][idx])
                    indices[kb_key] += 1
                    added = True
                    if len(final) >= top_k:
                        break
            if not added:
                break

        # 短文本降权（与普通搜索一致）
        SHORT_CONTENT_CHARS = 50
        for r in final:
            content = r.get("content")
            content_len = len(content.strip()) if content else 0
            if content_len < SHORT_CONTENT_CHARS:
                logger.debug("Balanced short content downgrade: %s (len=%d)",
                             r.get("doc_path", ""), content_len)
                r["score"] = round(r["score"] * 0.3, 4)
                r["short_content_warning"] = True

        final.sort(key=lambda x: x["score"], reverse=True)
        logger.info("Balanced cross-KB search: %d KBs queried, %d results (per_kb_cap=%d)",
                     len(kb_keys), len(final), per_kb_cap)
        return final

    def find_similar_docs(
        self,
        doc_paths: list[str],
        kb_id: str | None = None,
        top_k: int = 5,
        score_threshold: float = 0.3,
    ) -> dict[str, list[dict[str, Any]]]:
        """根据多个源文档，批量查询与每个文档相似的文档片段。

        对每个源文档，用其内容生成 query embedding，在 ChromaDB 中搜索
        相似 chunk。返回按源文档分组的相似结果。

        Args:
            doc_paths: 源文档路径列表
            kb_id: 限定知识库；空则跨库
            top_k: 每个源文档返回的最相似结果数
            score_threshold: 最低相似度阈值

        Returns:
            {doc_path: [{content, score, matched_doc_path, chunk_index}, ...], ...}
        """
        if kb_id:
            collections = self._resolve_hierarchical_collections(kb_id)
        else:
            collections = self._all_kb_collections()

        # 读取每个源文档的内容用于生成查询向量
        doc_contents: dict[str, str] = {}
        for dp in doc_paths:
            content = ""
            try:
                from app.services.storage_reader_service import storage_reader
                content = storage_reader.read_document_content(dp, max_chars=2000)
            except Exception:
                pass
            if not content:
                # Fallback: 用 doc_path 作为查询
                content = dp
            doc_contents[dp] = content

        results: dict[str, list[dict[str, Any]]] = {dp: [] for dp in doc_paths}

        for dp, content in doc_contents.items():
            query_embedding = embedding_service.embed_one(content)
            if not query_embedding:
                continue

            for col in collections:
                if col is None:
                    continue
                try:
                    res = col.query(
                        query_embeddings=[query_embedding],
                        n_results=top_k * 2,  # 多取一些，去重后截断
                        include=["documents", "distances", "metadatas"],
                    )
                except Exception as e:
                    logger.warning("find_similar failed for %s in %s: %s",
                                   dp, col.name, e)
                    continue

                seen = set()
                for doc, dist, meta in zip(
                    res["documents"][0],
                    res["distances"][0],
                    res["metadatas"][0],
                ):
                    matched_path = meta.get("doc_path", "")
                    score = 1.0 - dist
                    if score < score_threshold:
                        continue
                    # 排除和源文档完全相同的 chunk
                    if matched_path == dp:
                        continue
                    # 去重：同一个 matched doc 只保留最高分的 chunk
                    if matched_path in seen:
                        continue
                    seen.add(matched_path)

                    results[dp].append({
                        "content": doc[:500],
                        "score": round(score, 4),
                        "matched_doc_path": matched_path,
                        "source_doc_path": dp,
                        "chunk_index": meta.get("chunk_index", 0),
                        "kb_id": meta.get("kb_id", ""),
                    })

            # 排序 + 截断
            results[dp].sort(key=lambda x: x["score"], reverse=True)
            results[dp] = results[dp][:top_k]

        return results

    def search_in_documents(
        self,
        query: str,
        doc_paths: list[str],
        top_k_per_doc: int = 3,
        kb_id: str | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Stage 2 核心：在指定文档集合内做向量检索。"""
        query_embedding = embedding_service.embed_one(query)
        result_map: dict[str, list[dict[str, Any]]] = {p: [] for p in doc_paths}

        if kb_id:
            cols = self._resolve_hierarchical_collections(kb_id)
        else:
            cols = self._all_kb_collections()

        for col in cols:
            if col is None:
                continue
            try:
                where_filter = {"doc_path": {"$in": doc_paths}}
                res = col.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k_per_doc * len(doc_paths),
                    where=where_filter,
                    include=["documents", "distances", "metadatas"],
                )
            except Exception as e:
                logger.warning("search_in_documents failed in %s: %s", col.name, e)
                continue

            for doc, dist, meta in zip(
                res["documents"][0],
                res["distances"][0],
                res["metadatas"][0],
            ):
                dp = meta.get("doc_path", "")
                if dp in result_map:
                    result_map[dp].append({
                        "content": doc,
                        "score": 1.0 - dist,
                        "chunk_index": meta.get("chunk_index", 0),
                        "kb_id": meta.get("kb_id", ""),
                    })

        for dp in result_map:
            result_map[dp].sort(key=lambda x: x["score"], reverse=True)
            result_map[dp] = result_map[dp][:top_k_per_doc]

        return result_map

    # ── 删除 ──────────────────────────────────────────────────────

    def delete_document(self, kb_id: str, doc_path: str) -> None:
        col = self._safe_get_collection(kb_id)
        if col:
            self._delete_doc_chunks(col, doc_path)
            logger.info("Deleted vector chunks for %s in KB %s", doc_path, kb_id)

    def delete_kb(self, kb_id: str) -> None:
        try:
            self.client.delete_collection(self._collection_name(kb_id))
        except Exception:
            pass

    # ── 内部工具 ──────────────────────────────────────────────────

    def _delete_doc_chunks(self, collection, doc_path: str) -> None:
        try:
            existing = collection.get(where={"doc_path": doc_path})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

    def _chunk_text(self, text: str) -> list[str]:
        size = config.vector_chunk_size
        overlap = config.vector_chunk_overlap

        sections: list[str] = []
        current: list[str] = []
        for line in text.split("\n"):
            if line.startswith("#"):
                if current:
                    sections.append("\n".join(current))
                    current = []
            current.append(line)
        if current:
            sections.append("\n".join(current))

        chunks: list[str] = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            if len(section) <= size:
                chunks.append(section)
                continue
            start = 0
            while start < len(section):
                end = start + size
                chunks.append(section[start:end].strip())
                start = end - overlap
        return [c for c in chunks if c]

    def get_stats(self, kb_id: str | None = None) -> dict[str, Any]:
        if kb_id:
            col = self._safe_get_collection(kb_id)
            if col is None:
                return {"kb_id": kb_id, "chunk_count": 0}
            return {"kb_id": kb_id, "collection": col.name, "chunk_count": col.count()}
        stats = []
        for col in self._all_kb_collections():
            stats.append({"collection": col.name, "chunk_count": col.count()})
        return {"collections": stats}


vector_service = VectorService()
