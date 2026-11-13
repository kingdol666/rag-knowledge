"""两阶段精准检索编排。

Stage 1：广搜索（关键词 BM25 + 图谱邻居扩展）→ 候选文档路径
Stage 2：精细检索（仅在候选文档的向量集合内搜索）
"""
from __future__ import annotations

import asyncio
import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, Callable

from app.config import config
from app.services.keyword_index_service import (
    keyword_index_service,
    bm25_max_content_chars,
)
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)

DEFAULT_GRAPH_BUDGET_MS = 1000.0
DEFAULT_VECTOR_BUDGET_MS = 5000.0
# Includes BM25 build/lock, fallback reads, and optional stages. This is a
# response wait limit, not a guarantee that synchronous work has stopped.
PRIMARY_SEARCH_WAIT_SECONDS = 15.0


class PrimarySearchUnavailable(RuntimeError):
    """The primary search could not be admitted or did not finish in time."""

    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(f"Primary search {status}; synchronous work may still be running")


class _PrimarySearchRunner:
    """Bound running and queued work across all event loops in this process.

    A deadline covers both queueing and execution. Abandoned queued work is
    skipped when dequeued, but keeps its slot until then. Running work retains
    its slot until it really finishes; synchronous calls cannot be interrupted.
    """

    def __init__(self, workers: int = 2, queue_size: int = 16) -> None:
        if workers < 1 or queue_size < 0:
            raise ValueError("workers must be positive and queue_size non-negative")
        self._slot = threading.BoundedSemaphore(workers + queue_size)
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="primary-search")

    async def run(self, fn: Callable[[], Any], wait_seconds: float) -> tuple[str, Any]:
        if not self._slot.acquire(blocking=False):
            return "capacity_exhausted", None
        abandoned = threading.Event()

        def invoke() -> Any:
            if not abandoned.is_set():
                return fn()
            return None

        try:
            future = self._executor.submit(invoke)
        except BaseException:
            self._slot.release()
            raise
        future.add_done_callback(lambda _: self._slot.release())
        wrapped = asyncio.wrap_future(future)
        # The worker may outlive its caller and fail after its wait ended.
        wrapped.add_done_callback(lambda f: None if f.cancelled() else f.exception())
        try:
            done, _ = await asyncio.wait({wrapped}, timeout=wait_seconds)
            if not done:
                abandoned.set()
                return "timeout", None
            return "completed", wrapped.result()
        except asyncio.CancelledError:
            abandoned.set()
            raise


_primary_search_runner = _PrimarySearchRunner()


class _BoundedStageRunner:
    """Limit outstanding optional synchronous work, including timed-out work.

    Timeouts stop waiting, not the underlying call. A slot is released only
    when that call actually finishes, so retries cannot build an unbounded
    executor queue or spawn an unbounded number of abandoned threads.
    """

    def __init__(self, workers: int) -> None:
        self._slots = threading.BoundedSemaphore(workers)
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="retrieval-stage")

    def run(self, fn: Callable[[], Any], budget_ms: float) -> tuple[str, Any]:
        if budget_ms <= 0:
            return "budget_exhausted", None
        if not self._slots.acquire(blocking=False):
            return "capacity_exhausted", None
        started = time.monotonic()
        try:
            future = self._executor.submit(fn)
        except BaseException:
            self._slots.release()
            raise
        future.add_done_callback(lambda _: self._slots.release())
        try:
            remaining = max(0.0, budget_ms / 1000 - (time.monotonic() - started))
            return "completed", future.result(timeout=remaining)
        except FutureTimeout:
            # A worker itself can raise TimeoutError; do not mislabel that
            # completed failure as a wait timeout.
            if future.done():
                return "completed", future.result()
            return "timeout", None


# Independent pools prevent a stuck graph call from consuming vector capacity.
_graph_runner = _BoundedStageRunner(4)
_vector_runner = _BoundedStageRunner(2)
# The underlying keyword index is a shared, mutable singleton. This lock must
# also cover reads and incremental updates, not only the first build.
_keyword_lock = threading.RLock()


def _budget(value: Any) -> float | None:
    """None disables a budget; zero deliberately skips the optional stage."""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("stage budget must be a finite non-negative number") from None
    if not math.isfinite(value) or value < 0:
        raise ValueError("stage budget must be a finite non-negative number")
    return value


def _configured_budget(value: Any, default: float, name: str) -> float:
    """Keep older broken/null config usable, but never silently remove a budget."""
    try:
        parsed = _budget(value)
        if parsed is None:
            raise ValueError("missing budget")
        return parsed
    except ValueError:
        logger.warning("Invalid %s %r; using %.0f ms", name, value, default)
        return default


def _elapsed_ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 3)


class TwoStageSearchService:
    _keyword_built: bool = False
    _keyword_building: bool = False
    _keyword_failure_generation: int = 0

    def keyword_index_status(self) -> dict[str, bool]:
        """Real BM25 readiness for the health surface (never a constant).

        Instance method on purpose: ``_build_keyword_index`` publishes via
        ``self._keyword_built = True`` (instance attribute), so a classmethod
        would read the stale class default forever (observed live).

        Deliberately lock-free: ``_keyword_lock`` is held for the whole
        multi-second BM25 build, and the async health handler must never
        block on it (a lock here both froze the event loop during builds and
        made ``building: true`` unobservable — reviewer-demonstrated). Bool
        reads are atomic in CPython; these fields are advisory health hints.
        """
        return {"ready": bool(self._keyword_built), "building": bool(self._keyword_building)}

    async def search_async(self, wait_seconds: float = PRIMARY_SEARCH_WAIT_SECONDS,
                           **kwargs: Any) -> dict[str, Any]:
        """Run synchronous retrieval through shared bounded async admission."""
        status, result = await _primary_search_runner.run(
            lambda: self.search(**kwargs), wait_seconds)
        if status != "completed":
            raise PrimarySearchUnavailable(status)
        return result

    def _ensure_keyword_index(self, kb_id: str | None = None) -> None:
        """Single-flight build; waiting invalidations cannot be lost."""
        failure_generation = self._keyword_failure_generation
        with _keyword_lock:
            # Waiters that observed a build in progress share its outcome rather
            # than serially retrying the same expensive failing snapshot.
            if not self._keyword_built and failure_generation != self._keyword_failure_generation:
                raise RuntimeError("keyword index build failed in concurrent request")
            try:
                self._build_keyword_index(kb_id)
            except Exception:
                self._keyword_failure_generation += 1
                raise

    def _build_keyword_index(self, kb_id: str | None = None) -> None:
        """Lazy-build the BM25 keyword index on first search or when KB changes."""
        if self._keyword_built:
            logger.debug("Keyword index already built, skipping")
            return
        self._keyword_building = True
        try:
            from app.services.storage_reader_service import storage_reader
            logger.info("_ensure_keyword_index: reading KBs from %s", storage_reader.root)
            kbs = storage_reader.list_knowledge_bases()
            logger.info("_ensure_keyword_index: found %d KBs", len(kbs))
            # K1 fix: always build the FULL index across all KBs (no kb_id filter).
            # Hierarchical parent KBs' documents live in child KB collections;
            # filtering at build time + the _keyword_built cache would miss child
            # docs and cause stale indices across different kb_id queries.
            # KB scoping is applied at search time via resolved kb_id sets.

            all_docs: list[dict] = []
            for kb in kbs:
                kb_path = kb["path"]
                # A missing, unreadable or invalid YAML is not an empty KB.
                # Abort before publishing an incomplete global index.
                docs = storage_reader.list_documents(kb_path, strict=True)
                logger.info("_ensure_keyword_index: KB '%s' has %d docs", kb_path, len(docs))
                for doc in docs:
                    doc_path = doc.get("path", "")
                    if not doc_path:
                        continue
                    # K1: skip child-KB container entries (directories listed as docs)
                    full = storage_reader.root / doc_path
                    if full.is_dir():
                        continue
                    content = storage_reader.read_document_content(
                        doc_path, max_chars=bm25_max_content_chars())
                    all_docs.append({
                        # 统一正斜杠: tree-fs YAML 在 Windows 下可能存反斜杠,
                        # 而 ChromaDB 元数据是正斜杠 — 不归一会让 stage2 的
                        # doc_path $in 过滤全部失配, stage2 静默为空(已实测)
                        "path": doc_path.replace("\\", "/"),
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
            self._keyword_built = False
            logger.warning("Failed to build keyword index: %s", e, exc_info=True)
            raise RuntimeError("keyword index build failed") from e
        finally:
            self._keyword_building = False

    def invalidate_keyword_index(self) -> None:
        """Force rebuild on next search (call after indexing a document)."""
        with _keyword_lock:
            self._keyword_built = False

    def add_document(self, doc: dict[str, Any]) -> None:
        """Incrementally add one doc to the BM25 index. No-op if the index
        was never built (lazy build on first search picks it up). Prefer this
        over invalidate_keyword_index() after indexing a single doc — it
        avoids forcing a full BM25 rebuild on the next search."""
        # Wait for an in-flight build too: otherwise its storage snapshot can
        # miss this update before it publishes _keyword_built.
        with _keyword_lock:
            if self._keyword_built:
                keyword_index_service.add_document(doc)

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
        graph_budget_ms: float | None = None,
        vector_budget_ms: float | None = None,
    ) -> dict[str, Any]:
        """Search with optional stage wait budgets, never a whole-request deadline.

        Budgeted synchronous calls may continue after timeout; bounded per-stage
        pools prevent accumulating abandoned work. A budget of zero skips a stage.
        """
        total_start = time.monotonic()
        cfg = config.two_stage_config
        graph_budget_ms = _budget(graph_budget_ms) if graph_budget_ms is not None else _configured_budget(
            cfg.get("graph_budget_ms", DEFAULT_GRAPH_BUDGET_MS), DEFAULT_GRAPH_BUDGET_MS, "graph_budget_ms")
        vector_budget_ms = _budget(vector_budget_ms) if vector_budget_ms is not None else _configured_budget(
            cfg.get("vector_budget_ms", DEFAULT_VECTOR_BUDGET_MS), DEFAULT_VECTOR_BUDGET_MS, "vector_budget_ms")
        details: dict[str, Any] = {
            "degraded_reasons": [], "timings_ms": {},
            "graph_status": "not_requested", "vector_status": "not_run",
        }
        stage1_top_k = stage1_top_k or cfg.get("stage1_top_k", 20)
        stage2_top_k = stage2_top_k or cfg.get("stage2_top_k", 5)
        kw_weight = cfg.get("stage1_keyword_weight", 0.5)
        graph_weight = cfg.get("stage1_graph_weight", 0.5)
        min_candidates = cfg.get("min_candidates", 3)

        # Stage 1: 广搜索
        stage1_start = time.monotonic()
        candidates = self._stage1_broad_search(
            query=query, kb_id=kb_id, top_k=stage1_top_k,
            kw_weight=kw_weight, graph_weight=graph_weight,
            enable_graph_expansion=enable_graph_expansion,
            balance_kbs=balance_kbs, graph_budget_ms=graph_budget_ms,
            details=details,
        )
        details["timings_ms"]["stage1"] = _elapsed_ms(stage1_start)
        candidate_paths = [c["doc_path"] for c in candidates]
        use_filter = len(candidate_paths) >= min_candidates
        vector_stage_start = time.monotonic()

        # Stage 2: 精细检索. Optional budgets bound how long this request waits,
        # but do not cancel synchronous Chroma/embedding work after timeout.
        if candidate_paths:
            if use_filter:
                vector_call = lambda: vector_service.search_in_documents(
                    query=query, doc_paths=candidate_paths,
                    top_k_per_doc=stage2_top_k, kb_id=kb_id,
                )
            else:
                # Preserve the baseline broadening policy for 1–2 candidates.
                vector_call = lambda: vector_service.search(
                    query=query, kb_id=kb_id, top_k=stage2_top_k * 3,
                    score_threshold=score_threshold, balance_kbs=balance_kbs,
                )
            try:
                if vector_budget_ms is None:
                    vector_status = "completed"
                    vector_value = vector_call()
                else:
                    vector_status, vector_value = _vector_runner.run(
                        vector_call, vector_budget_ms)
                details["vector_status"] = vector_status
                if vector_status == "completed":
                    if use_filter:
                        chunks_map = vector_value
                    else:
                        chunks_map = {}
                        for c in vector_value:
                            chunks_map.setdefault(c["doc_path"], []).append(c)
                else:
                    chunks_map = {}
                    details["degraded_reasons"].append(f"vector_{vector_status}")
                    logger.warning("two_stage vector stage %s (budget_ms=%s)",
                                   vector_status, vector_budget_ms)
            except Exception as exc:
                chunks_map = {}
                details["vector_status"] = "failed"
                details["degraded_reasons"].append("vector_failed")
                logger.warning("two_stage vector stage failed: %s", exc, exc_info=True)
        else:
            # Deliberately preserve baseline: zero Stage 1 candidates do not
            # trigger global vector search, which previously introduced noise.
            chunks_map = {}
            details["vector_status"] = "skipped_no_candidates"
        details["timings_ms"]["vector"] = _elapsed_ms(vector_stage_start)
        if details["vector_status"] == "completed":
            # VectorService currently swallows some per-collection failures.
            # A non-empty result therefore cannot establish exhaustive coverage.
            details["vector_coverage"] = "unknown"

        # An empty vector result is not proof the service is unavailable: it
        # may mean no indexed chunks, no matches, or a swallowed backend error.
        # Retain the existing candidate fallback, with honest score provenance.
        fallback_used = bool(candidates) and not any(chunks_map.values())
        if fallback_used:
            if details["vector_status"] == "completed":
                details["vector_status"] = "empty"
                details["degraded_reasons"].append("vector_empty_fallback")
            logger.info("No vector chunks returned — using stage1 candidate fallback")
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
                    # Preserve the historic BM25 fallback scale. The response
                    # marks this distinctly from vector similarity below.
                    "score": can["score"] / max(kw_weight, 0.01),
                    "chunk_index": 0, "kb_id": can.get("kb_id", kb_id or ""),
                })

        # 路径标准化帮助函数（BM25 用 \\，ChromaDB 用 /）
        def _norm_path(p):
            return p.replace("\\", "/") if p else p

        results = []
        for doc_path, chunks in chunks_map.items():
            norm_doc_path = _norm_path(doc_path)
            stage1_sources = list(dict.fromkeys(
                source for c in candidates
                if _norm_path(c.get("doc_path", "")) == norm_doc_path
                for source in c.get("stage1_sources", [c.get("source", "keyword")])
            ))
            primary_source = stage1_sources[0] if stage1_sources else "vector"

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
                    "score_source": "stage1" if fallback_used else "vector",
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:stage2_top_k * max(1, len(candidate_paths))]

        details["timings_ms"]["total"] = _elapsed_ms(total_start)
        details["degraded"] = bool(details["degraded_reasons"])
        return {
            "query": query,
            "stage1": {"candidates": candidates, "candidate_count": len(candidate_paths)},
            "stage2": {"results": results},
            "total_results": len(results),
            "retrieval": details,
        }

    def _stage1_broad_search(
        self, query: str, kb_id: str | None, top_k: int,
        kw_weight: float, graph_weight: float, enable_graph_expansion: bool,
        balance_kbs: bool = False,
        graph_budget_ms: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}

        # Ensure keyword index is built before searching
        bm25_start = time.monotonic()
        bm25_search_start = bm25_start
        failure_generation = self._keyword_failure_generation
        try:
            with _keyword_lock:
                if not self._keyword_built and failure_generation != self._keyword_failure_generation:
                    raise RuntimeError("keyword index build failed in concurrent request")
                self._ensure_keyword_index(kb_id)
                if details is not None:
                    details["timings_ms"]["bm25_build"] = _elapsed_ms(bm25_start)

                # Resolve the requested scope while holding the lock so an
                # invalidation cannot replace the index before this search.
                resolved_kb_ids: set[str] | None = None
                if kb_id:
                    try:
                        from app.services.storage_reader_service import storage_reader
                        resolved_kb_ids = set(storage_reader.resolve_kb_ids_with_children(kb_id))
                    except Exception:
                        resolved_kb_ids = {kb_id}
                        if details is not None:
                            details["degraded_reasons"].append("kb_scope_resolution_failed")

                # Keep the existing enlarged global pool and KB quota policy.
                pool_k = top_k
                if not kb_id:
                    pool_k = max(top_k, top_k * max(1, config.stage1_pool_multiplier))
                bm25_search_start = time.monotonic()
                kw_results = keyword_index_service.search(
                    query, top_k=pool_k, kb_ids=resolved_kb_ids)
                if details is not None:
                    details["timings_ms"]["bm25_search"] = _elapsed_ms(bm25_search_start)
        except Exception as exc:
            kw_results = []
            if details is not None:
                if "bm25_build" not in details["timings_ms"]:
                    details["timings_ms"]["bm25_build"] = _elapsed_ms(bm25_start)
                    details["timings_ms"]["bm25_search"] = 0.0
                    details["degraded_reasons"].append("bm25_build_failed")
                elif "bm25_build_failed" not in details["degraded_reasons"]:
                    details["timings_ms"]["bm25_search"] = _elapsed_ms(bm25_search_start)
                    details["degraded_reasons"].append("bm25_search_failed")
                details["bm25_status"] = "failed"
            logger.warning("two_stage BM25 failed: %s", exc, exc_info=True)
        else:
            if details is not None:
                details["bm25_status"] = "ready"
        for r in kw_results:
            candidates[r["doc_path"].replace("\\", "/")] = {
                "doc_path": r["doc_path"].replace("\\", "/"),
                "score": r["score"] * kw_weight,
                "name": r.get("name", ""), "source": "keyword",
                "kb_id": r.get("kb_id", ""),
            }

        # 图谱关联扩展（仅基于有意义的关系：shared_tag / vector_similar / agent_judged）
        graph_start = time.monotonic()
        if enable_graph_expansion and config.graph_enabled and candidates:
            neighbor_paths: dict[str, float] = {}
            if details is not None:
                details["graph_status"] = "completed"
            for c in list(candidates.values())[:5]:
                try:
                    # Lazy import keeps neo4j optional. The function executed
                    # by the pool does not mutate request-owned candidate data.
                    def lookup(path: str = c["doc_path"]) -> list[dict[str, Any]]:
                        from app.services.graph_service import graph_service
                        return graph_service.get_related_documents(path)

                    if graph_budget_ms is None:
                        status, neighbor_results = "completed", lookup()
                    else:
                        remaining_ms = graph_budget_ms - (time.monotonic() - graph_start) * 1000
                        status, neighbor_results = _graph_runner.run(lookup, remaining_ms)
                    if status != "completed":
                        if details is not None:
                            details["graph_status"] = status
                            details["degraded_reasons"].append(f"graph_{status}")
                        logger.warning("two_stage graph stage %s (budget_ms=%s)", status, graph_budget_ms)
                        break
                    for nr in neighbor_results:
                        p = nr.get("path", "").replace("\\", "/")
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
                    if details is not None:
                        details["graph_status"] = "failed"
                        if "graph_failed" not in details["degraded_reasons"]:
                            details["degraded_reasons"].append("graph_failed")
                    logger.warning("Graph expansion failed for %s: %s", c["doc_path"], e)
            for path, score in neighbor_paths.items():
                if path not in candidates:
                    candidates[path] = {
                        "doc_path": path,
                        "score": score * graph_weight,
                        "source": "graph",
                    }
                else:
                    candidates[path]["stage1_sources"] = ["keyword", "graph"]
        elif details is not None:
            details["graph_status"] = ("disabled" if not enable_graph_expansion or not config.graph_enabled
                                       else "skipped_no_candidates")
        if details is not None:
            details["timings_ms"]["graph"] = _elapsed_ms(graph_start)

        ranked = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)

        # 跨库均衡：对 BM25 候选按 KB 分组轮询，防大KB主导 stage1
        # 跨库均衡：默认开启（kb_aware_candidates）—— 对未限定 KB 的查询按
        # KB 配额轮询选取，防止单一超大库主导候选集；balance_kbs 为显式开关，
        # 语义相同（保留供消融对比）。
        kb_aware = True
        try:
            from app.config import config as _cfg
            kb_aware = _cfg.kb_aware_candidates
        except Exception:
            pass
        if (balance_kbs or kb_aware) and not kb_id and len(ranked) > top_k:
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
