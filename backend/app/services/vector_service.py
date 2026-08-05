"""ChromaDB 向量索引服务。

设计：
- 一个知识库 → 一个 collection（kb_{kb_id}）
- 一个文档 → 一组 chunk（{doc_path}__chunk_{index}）
- 通过 where={"doc_path": ...} 精准定位文档向量

当 embedding 模型不可用时，所有方法优雅降级为返回空结果。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
import threading
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from app.config import config
from app.services.embedding_service import embedding_service
from app.utils.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    # UTC-aware, matching graph_service._now_iso() and experience_service.
    # The previous naive-local datetime produced indexed_at timestamps in a
    # different timezone than every other service, corrupting time-based
    # comparisons (stale detection, decay) across the metadata YAML.
    return datetime.now(timezone.utc).isoformat()


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

    def _canonical_kb_id(self, kb_id: str) -> str:
        """Return the UUID form of a kb_id.

        UUID-like values pass through; path/name values resolve to their UUID
        so collection naming is always kb_<UUID>. This prevents the
        kb_<NAME> vs kb_<UUID> fragmentation where moved/updated documents
        become invisible to vector search (root cause of BUG#2/BUG#5 in QA).
        """
        if not kb_id:
            return kb_id
        # UUID v4 heuristic: 36 chars with 4 dashes
        if len(kb_id) == 36 and kb_id.count("-") == 4:
            return kb_id
        cache = getattr(self, "_kb_id_cache", None)
        if cache is None:
            cache = {}
            self._kb_id_cache = cache
        if kb_id in cache:
            return cache[kb_id]
        try:
            from app.services.storage_reader_service import storage_reader
            for kb in storage_reader.list_knowledge_bases():
                if kb.get("path") == kb_id and kb.get("kb_id"):
                    cache[kb_id] = kb["kb_id"]
                    return kb["kb_id"]
        except Exception:
            pass
        return kb_id

    def _collection_name(self, kb_id: str) -> str:
        canonical = self._canonical_kb_id(kb_id)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in canonical)
        return f"{config.vector_collection_prefix}{safe}"

    # Per-collection write locks — serialize concurrent index_document calls
    # on the same KB to prevent the ChromaDB concurrent-write race that left
    # collections "counted but unqueryable" (auto-index vs explicit-index).
    _collection_locks: dict = {}
    _locks_guard = threading.Lock()

    # 全局 chroma 访问锁(RL 可重入): PersistentClient 非线程安全, asyncio
    # to_thread 并发查询/写入会损坏内部 segment 状态(症状: 查询报
    # "Error creating hnsw segment reader: Nothing found on disk", 重启后
    # 恢复)。所有公开入口用 RLock 串行化, 彻底消除并发竞态。
    _chroma_lock = threading.RLock()

    def _chroma_locked(self, fn, *args, **kwargs):
        with self._chroma_lock:
            return fn(*args, **kwargs)

    def _collection_lock(self, kb_id: str):
        canonical = self._canonical_kb_id(kb_id)
        with self._locks_guard:
            if canonical not in self._collection_locks:
                self._collection_locks[canonical] = threading.Lock()
            return self._collection_locks[canonical]

    def _get_or_create_collection(self, kb_id: str):
        with self._chroma_lock:
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
            with self._chroma_lock:
                return self.client.get_collection(self._collection_name(kb_id))
        except Exception:
            pass
        # Resolve alternate form (UUID→path or path→UUID) via storage_reader
        try:
            from app.services.storage_reader_service import storage_reader
            for kb in storage_reader.list_knowledge_bases():
                if kb["kb_id"] == kb_id and kb.get("path"):
                    try:
                        with self._chroma_lock:
                            return self.client.get_collection(self._collection_name(kb["path"]))
                    except Exception:
                        pass
                elif kb.get("path") == kb_id and kb.get("kb_id"):
                    try:
                        with self._chroma_lock:
                            return self.client.get_collection(self._collection_name(kb["kb_id"]))
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    def _all_kb_collections(self) -> list:
        prefix = config.vector_collection_prefix
        try:
            with self._chroma_lock:
                cols = self.client.list_collections()
            return [c for c in cols if c.name.startswith(prefix)]
        except Exception:
            return []
    def _resolve_hierarchical_collections(self, kb_id: str) -> list:
        """Resolve kb_id to all descendant KB collections.

        Hierarchical parent KBs store documents in child KB collections.
        This resolves the parent UUID to all descendant UUIDs and gathers
        their ChromaDB collections so search covers the full subtree.

        After UUID-based resolution, an *ancestor-collection fallback*
        walks up the folder tree for any child KB that lacks a dedicated
        ChromaDB collection, falling back to the nearest ancestor KB's
        collection.  This protects against collection UUID drift — for
        example when a sub-KB was re-imported with a different UUID, or
        when a KB was moved to a new parent without reindexing.
        """
        try:
            from app.services.storage_reader_service import storage_reader
            all_kb_ids = storage_reader.resolve_kb_ids_with_children(kb_id)
        except Exception:
            all_kb_ids = [kb_id]
        cols = []
        seen = set()
        for kid in all_kb_ids:
            col = self._safe_get_collection(kid)
            if col is not None:
                cname = col.name
                if cname not in seen:
                    cols.append(col)
                    seen.add(cname)

        # --- Ancestor-collection fallback (KB-operation resilience) ---
        # If a child KB has no dedicated collection, walk UP the tree to
        # find the nearest ancestor KB that DOES have one.  In the common
        # flat-index architecture (all sub-KB docs indexed under the root
        # KB's collection), this correctly scopes retrieval to the ancestor's
        # collection whose doc_paths naturally cover the entire subtree.
        # This guarantees retrieval correctness after KB moves, merges, and
        # splits without requiring reindexing.
        try:
            tree = storage_reader.read_tree_fs()
            for kid in all_kb_ids:
                if any(kid == self._canonical_kb_id(c.name[3:]).split('-')[0]
                       for c in cols if c.name.startswith('kb_')):
                    continue  # already resolved
                current = kid
                for _ in range(10):  # max depth — walk up to ancestor
                    # Match folder by id OR path (handles partial/truncated UUIDs)
                    folder = next((f for f in tree.get("folders", [])
                                   if f.get("id") == current or f.get("path") == current), None)
                    if not folder:
                        break
                    # Try to get collection for this folder
                    anc_col = self._safe_get_collection(current)
                    if anc_col is not None and anc_col.name not in seen:
                        cols.append(anc_col)
                        seen.add(anc_col.name)
                        break  # found an ancestor collection — stop walking
                    # Go up to parent
                    pid = folder.get("parentId")
                    if not pid or pid == current:
                        break
                    current = pid
        except Exception:
            pass

        # Last-ditch: single-kb fallback (original logic)
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
        # 全局 chroma 锁(可重入): 串行化写入, 防并发损坏(替代 per-collection 锁)
        with self._chroma_lock:
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
                # 全局 chroma 锁: 客户端非线程安全, 并发查询会损坏 segment 状态
                with self._chroma_lock:
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
                with self._chroma_lock:
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
                    with self._chroma_lock:
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
                    # BUGFIX: 损坏 collection 的 segment 可能返回 None metadata,
                    # 直接 .get 会抛 'NoneType' object has no attribute 'get'
                    # 导致整个 find_similar_docs 失败(全库图谱 phase2 崩溃)
                    if meta is None:
                        continue
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
        """Stage 2 核心：在指定文档集合内做向量检索。

        Path separators are normalized to '/' because ChromaDB stores
        forward-slash doc_paths while the BM25 keyword index (Stage 1)
        yields Windows backslash paths on this platform. Querying with
        un-normalized paths silently matched nothing and triggered the
        cross-KB fallback — mirrors the normalization already used by
        ``_delete_doc_chunks``.
        """
        query_embedding = embedding_service.embed_one(query)
        # Normalize every requested path to '/' and build a lookup so we
        # can map a hit back to whichever original variant was requested.
        norm_paths: list[str] = []
        _to_original: dict[str, str] = {}
        for p in doc_paths:
            np = p.replace("\\", "/") if p else p
            if np not in _to_original:
                norm_paths.append(np)
            _to_original.setdefault(np, p)
        result_map: dict[str, list[dict[str, Any]]] = {p: [] for p in doc_paths}

        if kb_id:
            cols = self._resolve_hierarchical_collections(kb_id)
        else:
            cols = self._all_kb_collections()

        for col in cols:
            if col is None:
                continue
            try:
                # Match both normalized ('/') and raw Windows ('\\') forms so
                # a chunk stored with either separator is returned. 存量数据
                # 以 Windows 反斜杠存储, 调用方可能传任一种形态 → 两种都生成。
                path_variants: list[str] = []
                for p in doc_paths:
                    np = p.replace("\\", "/") if p else p
                    for v in (np, np.replace("/", "\\")):
                        if v and v not in path_variants:
                            path_variants.append(v)
                where_filter = {"doc_path": {"$in": path_variants}}
                # 全局 chroma 锁: 客户端非线程安全(RL 并发检索/索引会损坏 segment)
                with self._chroma_lock:
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
                np = dp.replace("\\", "/") if dp else dp
                original = _to_original.get(np, dp)
                if original in result_map:
                    result_map[original].append({
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
        # Split-brain sweep: legacy sub-KB docs may be indexed into the PARENT
        # collection (高分子 01-11 sub-KBs etc.), so the kb-resolved collection
        # can miss them entirely. Sweep ONLY ancestor collections of this KB —
        # 全库 sweep 会对无匹配 collection 执行 get(where) 查询, chromadb 1.5.9
        # 的 get(where) 无匹配会确定性损坏客户端状态(后续所有向量查询
        # 挂起/报 Nothing found on disk, 压测实证; 祖先集合覆盖 split-brain
        # 场景且不会命中无匹配路径)。
        for other in self._ancestor_collections(kb_id):
            if col is not None and other.name == col.name:
                continue
            self._delete_doc_chunks(other, doc_path)

    def _ancestor_collections(self, kb_id: str) -> list:
        """解析 kb_id 的所有祖先 KB 的 collection(split-brain 的唯一落点)。

        split-brain 成因: 子库文档在旧版索引入库时落入了父库 collection。
        因此只按路径逐级截断找祖先(如 Materials-ML-InverseDesign 之于
        Materials-ML-InverseDesign/ML-DefectDetection-Prediction), 避免对
        无关 collection 执行 chroma get(where) 无匹配查询(触发客户端损坏)。
        """
        try:
            from app.services.storage_reader_service import storage_reader
            kbs = storage_reader.list_knowledge_bases()
            my_path = next(
                (kb.get("path") or "" for kb in kbs
                 if kb.get("kb_id") == kb_id or kb.get("path") == kb_id), "")
            if not my_path:
                return []
            ancestors: list = []
            parts = my_path.split("/")
            for i in range(1, len(parts)):
                p = "/".join(parts[:i])
                for kb in kbs:
                    if kb.get("path") == p and kb.get("kb_id"):
                        col = self._safe_get_collection(kb["kb_id"])
                        if col is not None:
                            ancestors.append(col)
                        break
            return ancestors
        except Exception:
            return []

    def delete_kb(self, kb_id: str, kb_path: str = "") -> None:
        """Delete a KB's vector collection(s), silently handling misses.

        Deletes BOTH the canonical (UUID) and raw path/name forms:
        ``_canonical_kb_id`` may hold a stale path→UUID cache entry from
        before the KB was deleted, so a cached UUID delete alone would leave
        the path-named ghost collection behind (observed: kb_E2E-Integration-Test
        survived 2 cleanup runs).

        kb_path (optional): when given, also sweeps ALL collections for chunks
        whose doc_path lives under this KB — legacy sub-KB docs are indexed
        into the parent collection, so deleting only the sub-KB's own (missing)
        collection would leave their vectors behind.
        """
        names = {self._collection_name(kb_id)}
        # Raw form (path/name) — the one a stale cache entry would skip
        raw = f"{config.vector_collection_prefix}{kb_id}"
        names.add(raw)
        # Cache-inverse: if kb_id itself is a UUID with a cached path form,
        # also drop the path-named collection so both conventions die together.
        cache = getattr(self, "_kb_id_cache", None) or {}
        for cached_kb, cached_uuid in cache.items():
            if cached_uuid == kb_id and cached_kb != kb_id:
                names.add(f"{config.vector_collection_prefix}{cached_kb}")
        for name in names:
            try:
                self.client.delete_collection(name)
            except Exception:
                pass
        # Split-brain sweep: purge this KB's chunks from other collections
        # (e.g. sub-KB chunks living in the parent collection).
        if kb_path:
            prefix = kb_path.replace("\\", "/").strip("/")
            for col in self._all_kb_collections():
                if col.name in names:
                    continue
                self._delete_chunks_by_path_prefix(col, prefix)

    def delete_kb_path_only(self, kb_id: str) -> None:
        """Delete ONLY the raw path/name-named collection (kb_<kb_id> as-is),
        never the canonical UUID collection.

        Used by orphan/duplicate cleanup: when a KB still exists and owns a
        real UUID collection, the path-named duplicate must be removed WITHOUT
        touching the UUID one. Routing the path through _collection_name()
        would resolve to the UUID form and delete production vectors
        (2026-07-31 incident: kb_Materials-Science cleanup deleted 714 chunks).
        """
        try:
            self.client.delete_collection(f"{config.vector_collection_prefix}{kb_id}")
        except Exception:
            pass

    # ── 内部工具 ──────────────────────────────────────────────────

    def _delete_doc_chunks(self, collection, doc_path: str) -> None:
        """Delete all chunks for a document. Normalizes path separators
        to handle Windows backslash vs forward slash mismatch."""
        # Normalize to forward slashes for consistent matching
        norm_path = doc_path.replace("\\", "/")
        deleted_any = False
        where_failed = False  # where 查询是否抛异常(仅异常时启用全量 fallback)
        for path_variant in [doc_path, norm_path, doc_path.replace("/", "\\")]:
            try:
                with self._chroma_lock:
                    existing = collection.get(where={"doc_path": path_variant})
                    if existing and existing.get("ids"):
                        collection.delete(ids=existing["ids"])
                        deleted_any = True
                        logger.info("Deleted %d chunks for %s (variant=%s)", len(existing["ids"]), doc_path, path_variant[:50])
            except Exception as e:
                where_failed = True
                logger.debug("delete chunks variant %s failed: %s", path_variant[:50], e)
        # 全量 fallback 仅限 where 查询异常时(where 双形态已覆盖正常存储;
        # 对 sweep 的每个 collection 都全量 get 会触发 chroma 大集合扫描的
        # 段读取器状态损坏(压测实证: 54 collection 全量 get 后 "Nothing
        # found on disk", 重启进程恢复)
        if not deleted_any and where_failed:
            # Last resort: scan all chunks and match by substring
            try:
                with self._chroma_lock:
                    all_data = collection.get()
                if all_data and all_data.get("ids"):
                    to_delete = []
                    for i, meta in enumerate(all_data.get("metadatas", [])):
                        stored = (meta.get("doc_path", "")).replace("\\", "/")
                        if stored == norm_path:
                            to_delete.append(all_data["ids"][i])
                    if to_delete:
                        with self._chroma_lock:
                            collection.delete(ids=to_delete)
                        logger.info("Fallback delete: removed %d chunks for %s", len(to_delete), doc_path)
            except Exception as e:
                logger.warning("Fallback chunk scan failed for %s: %s", doc_path, e)

    def _delete_chunks_by_path_prefix(self, collection, path_prefix: str) -> None:
        """Delete all chunks whose doc_path starts with the given prefix.

        Used by the split-brain sweep in delete_kb: legacy sub-KB docs are
        indexed into the parent collection with their full path as doc_path,
        so a prefix match reliably identifies a deleted KB's orphaned chunks
        regardless of which collection they landed in.
        """
        prefix = path_prefix.replace("\\", "/").lower().rstrip("/") + "/"
        try:
            with self._chroma_lock:
                all_data = collection.get()
        except Exception as e:
            logger.warning("prefix sweep get failed for %s: %s", collection.name, e)
            return
        if not all_data or not all_data.get("ids"):
            return
        to_delete = []
        for i, meta in enumerate(all_data.get("metadatas", [])):
            stored = (meta.get("doc_path", "") or "").replace("\\", "/").lower()
            if stored.startswith(prefix):
                to_delete.append(all_data["ids"][i])
        if to_delete:
            try:
                with self._chroma_lock:
                    collection.delete(ids=to_delete)
                logger.info("Prefix sweep: removed %d chunks under %s from %s",
                            len(to_delete), path_prefix, collection.name)
            except Exception as e:
                logger.warning("prefix sweep delete failed for %s: %s", collection.name, e)

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
