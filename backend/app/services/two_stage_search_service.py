"""两阶段精准检索编排。

Stage 1：广搜索（关键词 BM25 + 图谱邻居扩展）→ 候选文档路径
Stage 2：精细检索（仅在候选文档的向量集合内搜索）
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import config
from app.services.graph_service import graph_service
from app.services.keyword_index_service import (
    keyword_index_service,
    _BM25_MAX_CONTENT_CHARS,
)
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


class TwoStageSearchService:
    _keyword_built: bool = False

    def _ensure_keyword_index(self, kb_id: str | None = None) -> None:
        """Lazy-build the BM25 keyword index on first search or when KB changes."""
        if self._keyword_built:
            logger.debug("Keyword index already built, skipping")
            return
        try:
            from app.services.storage_reader_service import storage_reader
            logger.info("_ensure_keyword_index: reading KBs from %s", storage_reader.root)
            kbs = storage_reader.list_knowledge_bases()
            logger.info("_ensure_keyword_index: found %d KBs", len(kbs))
            if kb_id:
                kbs = [kb for kb in kbs if kb["kb_id"] == kb_id or kb["path"] == kb_id]
                logger.info("_ensure_keyword_index: filtered to %d KBs", len(kbs))

            all_docs: list[dict] = []
            for kb in kbs:
                kb_path = kb["path"]
                docs = storage_reader.list_documents(kb_path)
                logger.info("_ensure_keyword_index: KB '%s' has %d docs", kb_path, len(docs))
                for doc in docs:
                    doc_path = doc.get("path", "")
                    if not doc_path:
                        continue
                    content = storage_reader.read_document_content(doc_path, max_chars=_BM25_MAX_CONTENT_CHARS)
                    all_docs.append({
                        "path": doc_path,
                        "name": doc.get("name", ""),
                        "description": doc.get("description", ""),
                        "content": content,
                        "kb_id": kb.get("kb_id", ""),
                    })
            logger.info("_ensure_keyword_index: building BM25 index with %d docs", len(all_docs))
            keyword_index_service.build(all_docs)
            self._keyword_built = True
            logger.info("BM25 keyword index built with %d docs (unique tokens: %d)", len(all_docs), len(keyword_index_service._inverted) if hasattr(keyword_index_service, '_inverted') else 0)
        except Exception as e:
            logger.warning("Failed to build keyword index: %s", e, exc_info=True)

    def invalidate_keyword_index(self) -> None:
        """Force rebuild on next search (call after indexing a document)."""
        self._keyword_built = False

    @staticmethod
    def _infer_kb_id(doc_path: str) -> str:
        """从 doc_path 前缀推断 kb_id（e.g. 'Thermal-Power-Monitoring/...' -> 'a2cfead0-...'）。

        如果 doc_path 以 KB 目录名开头，通过 storage_reader 查询对应的 kb_id。
        """
        parts = doc_path.replace("\\", "/").split("/")
        if len(parts) < 1:
            return ""
        kb_dir = parts[0]
        try:
            from app.services.storage_reader_service import storage_reader
            for kb in storage_reader.list_knowledge_bases():
                if kb["path"] == kb_dir:
                    return kb["kb_id"]
        except Exception:
            pass
        return ""

    def search(
        self,
        query: str,
        kb_id: str | None = None,
        stage1_top_k: int | None = None,
        stage2_top_k: int | None = None,
        enable_graph_expansion: bool = True,
        score_threshold: float | None = None,
        balance_kbs: bool = False,
    ) -> dict[str, Any]:
        cfg = config.two_stage_config
        stage1_top_k = stage1_top_k or cfg.get("stage1_top_k", 20)
        stage2_top_k = stage2_top_k or cfg.get("stage2_top_k", 5)
        kw_weight = cfg.get("stage1_keyword_weight", 0.5)
        graph_weight = cfg.get("stage1_graph_weight", 0.5)
        min_candidates = cfg.get("min_candidates", 3)

        # Stage 1: 广搜索
        candidates = self._stage1_broad_search(
            query=query, kb_id=kb_id, top_k=stage1_top_k,
            kw_weight=kw_weight, graph_weight=graph_weight,
            enable_graph_expansion=enable_graph_expansion,
            balance_kbs=balance_kbs,
        )
        candidate_paths = [c["doc_path"] for c in candidates]
        use_filter = len(candidate_paths) >= min_candidates

        # Stage 2: 精细检索
        if use_filter:
            chunks_map = vector_service.search_in_documents(
                query=query, doc_paths=candidate_paths,
                top_k_per_doc=stage2_top_k, kb_id=kb_id,
            )
        else:
            chunks = vector_service.search(query=query, kb_id=kb_id,
                                           top_k=stage2_top_k * 3,
                                           score_threshold=score_threshold,
                                           balance_kbs=balance_kbs)
            chunks_map = {}
            for c in chunks:
                chunks_map.setdefault(c["doc_path"], []).append(c)

        # Fallback: 向量服务不可用时，直接用 BM25（Stage 1）结果，并从磁盘补正文（不再返回空 content）
        if not any(chunks_map.values()):
            logger.info("Vector service unavailable — falling back to BM25-only results")
            from app.services.storage_reader_service import storage_reader
            for can in candidates:
                dp = can["doc_path"]
                chunks_map[dp] = chunks_map.get(dp, [])
                try:
                    fallback_content = storage_reader.read_document_content(dp, max_chars=500)
                except Exception:
                    fallback_content = ""
                chunks_map[dp].append({
                    "content": fallback_content, "doc_path": dp,
                    "score": can["score"] / max(kw_weight, 0.01),
                    "chunk_index": 0, "kb_id": kb_id or "",
                })

        # 路径标准化帮助函数（BM25 用 \\，ChromaDB 用 /）
        def _norm_path(p):
            return p.replace("\\", "/") if p else p

        results = []
        for doc_path, chunks in chunks_map.items():
            norm_doc_path = _norm_path(doc_path)
            stage1_sources = list(dict.fromkeys(
                c.get("source", "keyword") for c in candidates
                if _norm_path(c.get("doc_path", "")) == norm_doc_path
            ))
            primary_source = stage1_sources[0] if stage1_sources else "keyword"

            for chunk in chunks:
                results.append({
                    "content": chunk.get("content", ""),
                    "doc_path": doc_path,
                    "score": chunk.get("score", 0),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "kb_id": chunk.get("kb_id", ""),
                    "stage1_score": next(
                        (c["score"] for c in candidates
                         if _norm_path(c.get("doc_path", "")) == norm_doc_path), 0
                    ),
                    "source": primary_source,  # V2: 来源追踪
                    "stage1_sources": stage1_sources,  # V2: 多来源回溯
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:stage2_top_k * max(1, len(candidate_paths))]

        return {
            "query": query,
            "stage1": {"candidates": candidates, "candidate_count": len(candidate_paths)},
            "stage2": {"results": results},
            "total_results": len(results),
        }

    def _stage1_broad_search(
        self, query: str, kb_id: str | None, top_k: int,
        kw_weight: float, graph_weight: float, enable_graph_expansion: bool,
        balance_kbs: bool = False,
    ) -> list[dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}

        # Ensure keyword index is built before searching
        self._ensure_keyword_index(kb_id)

        # BM25 关键词检索
        kw_results = keyword_index_service.search(query, top_k=top_k)
        for r in kw_results:
            # 按 kb_id 过滤：如果指定了 kb_id，只保留属于该 KB 的文档
            if kb_id:
                doc_kb_id = r.get("kb_id", "") or self._infer_kb_id(r["doc_path"])
                if doc_kb_id != kb_id and not r["doc_path"].startswith(kb_id):
                    continue
            candidates[r["doc_path"]] = {
                "doc_path": r["doc_path"], "score": r["score"] * kw_weight,
                "name": r.get("name", ""), "source": "keyword",
            }

        # 图谱关联扩展（仅基于有意义的关系：shared_tag / vector_similar / agent_judged）
        if enable_graph_expansion and config.graph_enabled:
            neighbor_paths: dict[str, float] = {}
            for c in list(candidates.values())[:5]:
                try:
                    neighbor_results = graph_service.get_related_documents(c["doc_path"])
                    for nr in neighbor_results:
                        p = nr.get("path", "")
                        weight = nr.get("weight", 0.5)
                        reason = nr.get("reason", "")
                        if not p:
                            continue
                        # 不同关系权重不同：
                        # agent_judged（1.0~1.5）> vector_similar（0.7~0.9）> shared_tag（1~N）
                        rel_boost = 1.0
                        if reason == "agent_judged":
                            rel_boost = 1.5
                        elif reason == "vector_similar":
                            rel_boost = 0.8
                        elif reason == "shared_tag":
                            rel_boost = min(0.5 + weight * 0.3, 1.5)
                        neighbor_paths[p] = max(neighbor_paths.get(p, 0), weight * rel_boost)
                except Exception as e:
                    logger.warning("Graph expansion failed for %s: %s", c["doc_path"], e)
            for path, score in neighbor_paths.items():
                if path not in candidates:
                    candidates[path] = {
                        "doc_path": path,
                        "score": score * graph_weight,
                        "source": "graph",
                    }

        ranked = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)

        # 跨库均衡：对 BM25 候选按 KB 分组轮询，防大KB主导 stage1
        if balance_kbs and not kb_id and len(ranked) > top_k:
            ranked = self._balance_candidates_by_kb(ranked, top_k)

        return ranked[:top_k]

    @staticmethod
    def _balance_candidates_by_kb(
        candidates: list[dict[str, Any]], top_k: int,
    ) -> list[dict[str, Any]]:
        """对 stage1 候选按 KB 分组轮询选取，确保跨库多样性。"""
        from collections import defaultdict

        # 按 doc_path 前缀（KB目录名）分组
        by_kb: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for c in candidates:
            dp = c.get("doc_path", "")
            kb_prefix = dp.replace("\\", "/").split("/")[0] if dp else "_unknown"
            by_kb[kb_prefix].append(c)

        n_kbs = len(by_kb)
        if n_kbs <= 1:
            return candidates[:top_k]

        per_kb_cap = max(top_k // n_kbs + 1, 2)
        # 每组只保留 per_kb_cap 条
        for kb_key in by_kb:
            by_kb[kb_key] = by_kb[kb_key][:per_kb_cap]

        # 轮询合并
        final: list[dict[str, Any]] = []
        kb_keys = list(by_kb.keys())
        idx = {k: 0 for k in kb_keys}
        while len(final) < top_k:
            added = False
            for kb_key in kb_keys:
                if idx[kb_key] < len(by_kb[kb_key]):
                    final.append(by_kb[kb_key][idx[kb_key]])
                    idx[kb_key] += 1
                    added = True
                    if len(final) >= top_k:
                        break
            if not added:
                break

        logger.info("Stage1 balanced: %d KBs, %d candidates -> %d (per_kb_cap=%d)",
                     n_kbs, len(candidates), len(final), per_kb_cap)
        return final


two_stage_search_service = TwoStageSearchService()
