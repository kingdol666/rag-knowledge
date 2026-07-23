"""Neo4j knowledge graph (v4 -- document/KB/tag centric, no NER).

Core philosophy: every edge represents a REAL, meaningful connection.

Node types:
  - KnowledgeBase (kb_id)
  - Document (graph_doc_id)
  - Tag (name)

Relationship types:
  - (Document)-[:BELONGS_TO]->(KnowledgeBase)
  - (KnowledgeBase)-[:HAS_SUBKB]->(KnowledgeBase)
  - (Document)-[:HAS_TAG]->(Tag)
  - (Document)-[:RELATED_TO {reason, weight}]->(Document)
  - (KnowledgeBase)-[:RELATED_TO {reason, weight}]->(KnowledgeBase)

Relationship reason meaning:
  - "shared_tag" (weight=shared count) -- tag overlap
  - "vector_similar" (weight=cosine) -- vector similarity top-3 on ingest
  - "agent_judged" (weight=1.0~1.5, reasoning) -- agent reading judgment
"""
from __future__ import annotations

import functools
import logging
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError

from app.config import config

logger = logging.getLogger(__name__)

_TRANSIENT_EXC = (ServiceUnavailable, TransientError)
_GRAPH_SCHEMA_VERSION = 4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _graph_doc_id(doc_path: str) -> str:
    return "doc::" + doc_path.replace("\\", "/")


def _norm_path(p: str) -> str:
    return (p or "").replace("\\", "/")


def _retry_transient(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        rc = config.graph_retry_config
        max_attempts = int(rc["max_attempts"])
        base_delay = float(rc["base_delay"])
        last_exc = None
        for attempt in range(max_attempts):
            try:
                return func(self, *args, **kwargs)
            except _TRANSIENT_EXC as exc:
                last_exc = exc
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning("Neo4j transient error in %s (attempt %d/%d): %s", func.__name__, attempt + 1, max_attempts, exc)
                    self._reset_driver_silent()
                    time.sleep(delay)
        raise last_exc
    return wrapper


class GraphService:
    def __init__(self):
        self._driver = None
        self._lock = threading.Lock()
        self._schema_ready = False

    def _create_driver(self):
        return GraphDatabase.driver(config.graph_uri, auth=(config.graph_username, config.graph_password), **config.graph_pool_config)

    @property
    def driver(self):
        if self._driver is None:
            with self._lock:
                if self._driver is None:
                    drv = self._create_driver()
                    try:
                        drv.verify_connectivity()
                    except Exception as e:
                        drv.close()
                        raise
                    self._driver = drv
        return self._driver

    def _reset_driver_silent(self):
        with self._lock:
            if self._driver is not None:
                try:
                    self._driver.close()
                except Exception:
                    pass
                self._driver = None
            # Reset schema flag so next ensure_schema retries
            self._schema_ready = False

    def close(self):
        self._reset_driver_silent()

    def is_available(self):
        try:
            _ = self.driver
            return True
        except Exception:
            return False

    def health(self):
        if not config.graph_enabled:
            return {"enabled": False, "available": False}
        try:
            _ = self.driver
            return {"enabled": True, "available": True, "uri": config.graph_uri, "schema_version": _GRAPH_SCHEMA_VERSION}
        except Exception as e:
            return {"enabled": True, "available": False, "uri": config.graph_uri, "error": str(e)}

    def _ensure_schema(self, session):
        if self._schema_ready:
            return
        # Drop any pre-existing index on KnowledgeBase(kb_id) BEFORE creating
        # the constraint, because Neo4j cannot create a uniqueness constraint
        # when a non-constraint index already exists on the same property.
        # This can happen after a manual schema reset or migration.
        # Try both possible index names (legacy 'kb_id_idx' and the one
        # this code originally created as 'idx_kb_id').
        for idx_name in ("idx_kb_id", "kb_id_idx"):
            try:
                session.run(f"DROP INDEX {idx_name} IF EXISTS").consume()
            except Exception:
                pass
        session.run("CREATE CONSTRAINT doc_gid_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.graph_doc_id IS UNIQUE").consume()
        session.run("CREATE CONSTRAINT kb_id_unique IF NOT EXISTS FOR (kb:KnowledgeBase) REQUIRE kb.kb_id IS UNIQUE").consume()
        session.run("CREATE CONSTRAINT tag_name_unique IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE").consume()
        session.run("CREATE INDEX doc_kb_idx IF NOT EXISTS FOR (d:Document) ON (d.kb_id)").consume()
        session.run("CREATE INDEX doc_path_idx IF NOT EXISTS FOR (d:Document) ON (d.path)").consume()
        self._schema_ready = True
        logger.info("Neo4j v4 schema ensured")

    def _resolve_kb_path(self, kb_id):
        from app.services.storage_reader_service import storage_reader
        for kb in storage_reader.list_knowledge_bases():
            if kb["kb_id"] == kb_id or kb["path"] == kb_id:
                return kb["path"]
        return ""

    def _resolve_kb_id(self, raw):
        if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", raw.lower()):
            return raw
        from app.services.storage_reader_service import storage_reader
        for kb in storage_reader.list_knowledge_bases():
            if kb["path"] == raw and kb.get("kb_id"):
                return kb["kb_id"]
        return raw

    def _resolve_kb_name(self, kb_id):
        """Resolve the human-readable KB name for a kb_id (or path).
        list_knowledge_bases() returns ALL KB folders (top-level + sub-KBs),
        so a single pass suffices. Falls back to '' (keeps any existing name)."""
        from app.services.storage_reader_service import storage_reader
        for kb in storage_reader.list_knowledge_bases():
            if kb.get("kb_id") == kb_id or kb.get("path") == kb_id:
                return kb.get("name") or kb.get("path") or ""
        return ""

    def index_document(self, doc_path="", content="", kb_id="", doc_name="", description="", tags=None, similar_docs=None, agent_relations=None):
        from app.services.storage_reader_service import storage_reader
        gid = _graph_doc_id(doc_path)
        norm = _norm_path(doc_path)
        tags = tags or []
        parent_kb_id = storage_reader.get_kb_parent(kb_id) or ""
        kb_name = self._resolve_kb_name(kb_id) if kb_id else ""
        try:
            with self.driver.session(database=config.graph_database) as session:
                self._ensure_schema(session)
                only_agent = (not kb_id and not tags and agent_relations and not similar_docs)
                shared_tag_edge_count = 0
                if not only_agent:
                    self._write_doc_metadata(session, gid, norm, kb_id, doc_name, description, tags, parent_kb_id, kb_name)
                    if tags:
                        shared_tag_edge_count = self._relate_by_shared_tags(session, gid, kb_id, tags)
                    if similar_docs:
                        self._relate_vector_similar(session, gid, similar_docs)
                agent_count = 0
                if agent_relations:
                    agent_count = self._relate_agent_judged(session, gid, agent_relations)
        except Exception as e:
            return {"graph_doc_id": gid, "kb_id": kb_id, "parent_kb_id": parent_kb_id or None, "tag_count": len(tags) if tags else 0, "shared_tag_relations": 0, "vector_relations": 0, "agent_relations": 0, "indexed_at": _now_iso(), "error": str(e)[:200]}
        logger.info("Graph indexed %s (%d tags, %d shared_tag edges)",
                         doc_path, len(tags) if tags else 0, shared_tag_edge_count)
        return {"graph_doc_id": gid, "kb_id": kb_id, "parent_kb_id": parent_kb_id or None, "tag_count": len(tags) if tags else 0, "shared_tag_relations": shared_tag_edge_count, "vector_relations": len(similar_docs) if similar_docs else 0, "agent_relations": agent_count if agent_relations else 0, "indexed_at": _now_iso()}

    def _write_doc_metadata(self, session, gid, doc_path, kb_id, doc_name, description, tags, parent_kb_id="", kb_name=""):
        # SET kb.name = coalesce($kb_name, kb.name): always-SET so re-indexing
        # back-fills the human-readable name onto nodes originally seeded with
        # their UUID (the historical ON CREATE SET kb.name=$kb_id bug).
        if parent_kb_id:
            session.run("""
                MERGE (d:Document {graph_doc_id: $gid}) SET d.path=$doc_path, d.kb_id=$kb_id, d.name=$doc_name, d.description=$description, d.indexed_at=datetime(), d.schema_version=$sv
                WITH d MERGE (kb:KnowledgeBase {kb_id: $kb_id}) SET kb.name = coalesce($kb_name, kb.name) MERGE (d)-[:BELONGS_TO]->(kb)
                WITH kb MERGE (parent:KnowledgeBase {kb_id: $parent_kb_id}) MERGE (parent)-[:HAS_SUBKB]->(kb)
            """, gid=gid, doc_path=doc_path, kb_id=kb_id, doc_name=doc_name, description=description, sv=_GRAPH_SCHEMA_VERSION, parent_kb_id=parent_kb_id, kb_name=kb_name)
        else:
            session.run("""
                MERGE (d:Document {graph_doc_id: $gid}) SET d.path=$doc_path, d.kb_id=$kb_id, d.name=$doc_name, d.description=$description, d.indexed_at=datetime(), d.schema_version=$sv
                WITH d MERGE (kb:KnowledgeBase {kb_id: $kb_id}) SET kb.name = coalesce($kb_name, kb.name) MERGE (d)-[:BELONGS_TO]->(kb)
            """, gid=gid, doc_path=doc_path, kb_id=kb_id, doc_name=doc_name, description=description, sv=_GRAPH_SCHEMA_VERSION, kb_name=kb_name)

    def _relate_by_shared_tags(self, session, gid, kb_id, tags):
        """创建基于共享标签的关联，带质量过滤：
        - 共享 ≥2 个标签：强关联，直接建立
        - 共享 1 个标签 + 同一 KB：同KB文档，建立关联（同一知识域的文档共享标签即有意义）
        - 共享 1 个标签 + 稀有标签（<5 文档）：弱但有意关联
        - 共享 1 个通用标签（≥5 文档）+ 不同 KB：不建立关系（跨KB噪声）
        - 每个文档最多 30 条 shared_tag 出边
        """
        # 先计算标签稀有度（被多少文档使用）
        tag_rarity = {}
        for tag in set(tags):
            count_rec = session.run(
                "MATCH (t:Tag {name: $tag})<-[:HAS_TAG]-(d:Document) RETURN count(d) AS cnt",
                tag=tag
            ).single()
            tag_rarity[tag] = count_rec["cnt"] if count_rec else 999

        # 查询与当前文档共享标签的其他文档
        result = session.run("""
            MATCH (me:Document {graph_doc_id: $gid})
            MATCH (other:Document) WHERE other.graph_doc_id <> $gid
            MATCH (other)-[:HAS_TAG]->(t:Tag) WHERE t.name IN $tags
            WITH me, other, count(DISTINCT t) AS shared,
                 collect(DISTINCT t.name) AS shared_tag_names,
                 me.kb_id = other.kb_id AS same_kb
            WHERE shared >= 2
               OR (shared = 1 AND same_kb = true)
               OR (shared = 1 AND size([tag IN shared_tag_names WHERE tag IN $rare_tags]) > 0)
            RETURN other.graph_doc_id AS ogid, shared, shared_tag_names, same_kb
            ORDER BY shared DESC
            LIMIT 30
        """, gid=gid, tags=list(set(tags)),
             rare_tags=[t for t, c in tag_rarity.items() if c < 5])

        edge_count = 0
        for rec in result:
            shared = rec["shared"]
            ogid = rec["ogid"]
            shared_names = rec["shared_tag_names"]
            same_kb = rec.get("same_kb", False)
            session.run("""
                MATCH (me:Document {graph_doc_id: $gid})
                MATCH (other:Document {graph_doc_id: $ogid})
                MERGE (me)-[r:RELATED_TO]->(other)
                ON CREATE SET r.reason='shared_tag', r.weight=$shared,
                              r.shared_tags=$shared_names, r.same_kb=$same_kb,
                              r.created_at=datetime()
                ON MATCH SET r.weight=$shared, r.reason='shared_tag',
                              r.shared_tags=$shared_names, r.same_kb=$same_kb
            """, gid=gid, ogid=ogid, shared=shared, shared_names=shared_names,
                 same_kb=same_kb)
            edge_count += 1
        logger.debug("_relate_by_shared_tags: %d edges created for %s", edge_count, gid)
        return edge_count

    def _relate_vector_similar(self, session, gid, similar_docs):
        for sim in similar_docs:
            op = sim.get("doc_path", "")
            sc = sim.get("score", 0.0)
            if not op or sc < config.vector_score_threshold: continue
            og = _graph_doc_id(op)
            session.run("MATCH (me:Document {graph_doc_id: $gid}) MATCH (other:Document {graph_doc_id: $og}) MERGE (me)-[r:RELATED_TO]->(other) ON CREATE SET r.reason='vector_similar', r.weight=$sc, r.created_at=datetime() ON MATCH SET r.weight=$sc, r.reason='vector_similar'", gid=gid, og=og, sc=round(sc, 4))
            session.run("MATCH (other:Document {graph_doc_id: $og}) MATCH (me:Document {graph_doc_id: $gid}) MERGE (other)-[r:RELATED_TO]->(me) ON CREATE SET r.reason='vector_similar', r.weight=$sc, r.created_at=datetime() ON MATCH SET r.weight=$sc, r.reason='vector_similar'", gid=gid, og=og, sc=round(sc, 4))

    def _relate_agent_judged(self, session, gid, agent_relations):
        for rel in agent_relations:
            op = rel.get("doc_path", "")
            reasoning = rel.get("reasoning", "")[:500]
            rtype = rel.get("relation_type", "agent_judged")
            weight = float(rel.get("weight", 1.0))
            if not op: continue
            og = _graph_doc_id(op)
            session.run("MATCH (me:Document {graph_doc_id: $gid}) MATCH (other:Document {graph_doc_id: $og}) MERGE (me)-[r:RELATED_TO]->(other) ON CREATE SET r.reason=$rtype, r.weight=$weight, r.reasoning=$reasoning, r.created_at=datetime() ON MATCH SET r.reason=$rtype, r.weight=CASE WHEN $weight>r.weight THEN $weight ELSE r.weight END, r.reasoning=$reasoning", gid=gid, og=og, rtype=rtype, weight=weight, reasoning=reasoning)

    def _extract_tags(self, doc):
        raw = doc.get("tags")
        if isinstance(raw, list):
            return [t.get("name", str(t)) if isinstance(t, dict) else str(t) for t in raw]
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(",") if t.strip()]
        return []

    def build_kb_graph(self, kb_id, force=False):
        from app.services.storage_reader_service import storage_reader
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        kb_id_resolved = self._resolve_kb_id(kb_id)
        if force:
            try: self.delete_kb_graph(kb_id_resolved)
            except Exception as e: logger.warning("Pre-build delete failed: %s", e)
        try:
            with self.driver.session(database=config.graph_database) as session: self._ensure_schema(session)
        except Exception as e: logger.warning("Schema ensure failed: %s", e)
        parent_kb_id = storage_reader.get_kb_parent(kb_id_resolved) or ""
        direct = self._build_single_kb_docs(kb_id_resolved, kb_path, force, parent_kb_id)
        sub_kbs = storage_reader.list_sub_kbs(kb_id_resolved)
        sub_results = []
        for sub in sub_kbs:
            sub_r = self._build_single_kb_docs(sub["kb_id"], sub["path"], force, parent_kb_id=kb_id_resolved)
            sub_results.append({"kb_id": sub["kb_id"], "kb_path": sub["path"], **sub_r})
        self._relate_kbs_by_tags(kb_id_resolved, sub_kbs)
        total_docs = direct["docs_processed"] + sum(s["docs_processed"] for s in sub_results)
        total_rels = direct["total_relations"] + sum(s["total_relations"] for s in sub_results)
        return {"success": True, "kb_id": kb_id_resolved, "kb_path": kb_path, "docs_processed": total_docs, "docs_skipped": direct["docs_skipped"] + sum(s["docs_skipped"] for s in sub_results), "total_relations": total_rels, "sub_kb_count": len(sub_kbs), "sub_kbs": sub_results, "errors": direct["errors"] + [e for s in sub_results for e in s["errors"]]}

    def _build_single_kb_docs(self, kb_id, kb_path, force, parent_kb_id=""):
        from app.services.storage_reader_service import storage_reader
        docs = storage_reader.list_documents(kb_path)
        processed, skipped, errors = [], [], []
        total_relations = 0
        for doc in docs:
            doc_path = doc.get("path", "")
            if not doc_path or doc.get("file_type") == "knowledge-base": continue
            if not force and doc.get("graph_index"): skipped.append(doc_path); continue
            tags = self._extract_tags(doc)
            try:
                result = self.index_document(doc_path=doc_path, kb_id=kb_id, doc_name=doc.get("name", ""), description=doc.get("description", ""), tags=tags)
                gi = {"graph_doc_id": result["graph_doc_id"], "kb_id": kb_id, "parent_kb_id": parent_kb_id or None, "tag_count": result["tag_count"], "indexed_at": _now_iso(), "schema_version": _GRAPH_SCHEMA_VERSION}
                storage_reader.update_document_graph_index(kb_path, doc_path, gi)
                total_relations += (result.get("vector_relations", 0) +
                               result.get("agent_relations", 0) +
                               result.get("shared_tag_relations", 0))
                processed.append(doc_path)
            except Exception as e:
                errors.append({"doc_path": doc_path, "reason": str(e)[:200]})
        return {"docs_processed": len(processed), "docs_skipped": len(skipped), "total_relations": total_relations, "processed": processed, "skipped": skipped, "errors": errors}

    def _build_vector_similarity_edges(self, force=False) -> dict:
        """读取所有文档内容，计算向量相似度，创建 vector_similar 关联边。

        使用 embedding 模型对每篇文档内容编码，然后在 ChromaDB 中搜索相似文档。
        对每篇文档，找到 top-K 相似文档（跨所有 KB），创建双向 RELATED_TO 边。
        """
        from app.services.storage_reader_service import storage_reader

        # 尝试使用向量服务
        try:
            from app.services.vector_service import vector_service
            vs_ready = vector_service.is_ready()
        except Exception:
            vs_ready = False

        # 尝试使用 embedding 服务（即使没有 ChromaDB，也可以用 embedding 直接计算）
        try:
            from app.services.embedding_service import embedding_service
            emb_ready = embedding_service.is_available()
        except Exception:
            emb_ready = False

        if not vs_ready and not emb_ready:
            logger.warning("Neither vector service nor embedding service available — skipping vector similarity")
            return {"enabled": False, "total_edges": 0, "cross_kb_edges": 0,
                    "errors": ["No vector/embedding service available"]}

        # 收集所有文档
        kbs = storage_reader.list_knowledge_bases()
        all_docs = []  # [{path, kb_id, content, name, description, tags}]
        for kb in kbs:
            docs = storage_reader.list_documents(kb["path"])
            for doc in docs:
                doc_path = doc.get("path", "")
                if not doc_path or doc.get("file_type") == "knowledge-base":
                    continue
                content = storage_reader.read_document_content(doc_path, max_chars=3000)
                if not content or len(content.strip()) < 50:
                    continue
                all_docs.append({
                    "path": doc_path,
                    "kb_id": kb["kb_id"],
                    "content": content,
                    "name": doc.get("name", ""),
                    "tags": self._extract_tags(doc),
                })

        logger.info("Vector similarity: processing %d documents", len(all_docs))
        total_edges = 0
        cross_kb_edges = 0
        errors = []

        if vs_ready:
            # ── 方案 A: 使用 ChromaDB 向量搜索 ──
            doc_paths = [d["path"] for d in all_docs]

            # force=True 时先清除旧 vector_similar 边
            if force:
                try:
                    with self.driver.session(database=config.graph_database) as session:
                        session.run("MATCH ()-[r:RELATED_TO {reason: 'vector_similar'}]->() DELETE r").consume()
                    logger.info("Cleared old vector_similar edges for force rebuild")
                except Exception as e:
                    logger.warning("Failed to clear old vector_similar edges: %s", e)

            # 批量查询相似文档（每篇取 top-8，阈值 0.35）
            # TOP_K 从 5 提升到 8，确保内容相关文档的覆盖面更广
            similar_map = vector_service.find_similar_docs(
                doc_paths=doc_paths,
                kb_id=None,  # 跨库搜索
                top_k=8,
                score_threshold=config.vector_score_threshold,
            )

            with self.driver.session(database=config.graph_database) as session:
                for doc_path, similar_docs in similar_map.items():
                    gid = _graph_doc_id(doc_path)
                    for sim in similar_docs:
                        matched_path = sim.get("matched_doc_path", "")
                        score = sim.get("score", 0.0)
                        if not matched_path or score < config.vector_score_threshold:
                            continue
                        # 跳过自引用
                        if _norm_path(matched_path) == _norm_path(doc_path):
                            continue
                        og = _graph_doc_id(matched_path)
                        # 判断是否跨库
                        src_kb = next((d["kb_id"] for d in all_docs if d["path"] == doc_path), "")
                        tgt_kb = sim.get("kb_id", "")
                        is_cross_kb = src_kb and tgt_kb and src_kb != tgt_kb

                        # 创建双向边，存储 shared_content 片段作为证据
                        evidence = sim.get("content", "")[:200] if sim.get("content") else ""
                        reason = "vector_similar"
                        weight = round(score, 4)
                        session.run(
                            "MATCH (me:Document {graph_doc_id: $gid}) "
                            "MATCH (other:Document {graph_doc_id: $og}) "
                            "MERGE (me)-[r:RELATED_TO]->(other) "
                            "ON CREATE SET r.reason=$reason, r.weight=$weight, "
                            "  r.shared_content=$evidence, r.created_at=datetime() "
                            "ON MATCH SET r.weight=CASE WHEN $weight > r.weight "
                            "  THEN $weight ELSE r.weight END, "
                            "  r.shared_content=$evidence",
                            gid=gid, og=og, reason=reason, weight=weight,
                            evidence=evidence,
                        )
                        session.run(
                            "MATCH (other:Document {graph_doc_id: $og}) "
                            "MATCH (me:Document {graph_doc_id: $gid}) "
                            "MERGE (other)-[r:RELATED_TO]->(me) "
                            "ON CREATE SET r.reason=$reason, r.weight=$weight, "
                            "  r.shared_content=$evidence, r.created_at=datetime() "
                            "ON MATCH SET r.weight=CASE WHEN $weight > r.weight "
                            "  THEN $weight ELSE r.weight END, "
                            "  r.shared_content=$evidence",
                            gid=gid, og=og, reason=reason, weight=weight,
                            evidence=evidence,
                        )
                        total_edges += 1
                        if is_cross_kb:
                            cross_kb_edges += 1
        elif emb_ready:
            # ── 方案 B: 直接用 embedding 计算余弦相似度 ──
            logger.info("Using direct embedding similarity (ChromaDB not ready)")
            # 批量编码所有文档
            contents = [d["content"] for d in all_docs]
            embeddings = embedding_service.embed(contents)
            if not embeddings or len(embeddings) != len(all_docs):
                return {"enabled": False, "total_edges": 0, "cross_kb_edges": 0,
                        "errors": ["Embedding failed or returned wrong count"]}

            import numpy as np
            emb_matrix = np.array(embeddings)
            # 归一化（如果 embedding_service 没有归一化）
            norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1
            emb_matrix = emb_matrix / norms

            # 计算相似度矩阵
            sim_matrix = emb_matrix @ emb_matrix.T
            TOP_K = 5
            SCORE_THRESHOLD = 0.55

            with self.driver.session(database=config.graph_database) as session:
                for i, doc in enumerate(all_docs):
                    gid = _graph_doc_id(doc["path"])
                    # 取 top-K 相似文档（排除自身）
                    scores = sim_matrix[i].copy()
                    scores[i] = -1  # 排除自身
                    top_indices = np.argsort(scores)[-TOP_K:][::-1]

                    for j in top_indices:
                        score = float(scores[j])
                        if score < SCORE_THRESHOLD:
                            continue
                        matched = all_docs[j]
                        og = _graph_doc_id(matched["path"])
                        is_cross_kb = doc["kb_id"] != matched["kb_id"]
                        reason = "vector_similar"
                        weight = round(score, 4)

                        session.run(
                            "MATCH (me:Document {graph_doc_id: $gid}) MATCH (other:Document {graph_doc_id: $og}) "
                            "MERGE (me)-[r:RELATED_TO]->(other) "
                            "ON CREATE SET r.reason=$reason, r.weight=$weight, r.created_at=datetime() "
                            "ON MATCH SET r.weight=CASE WHEN $reason='vector_similar' AND $weight>r.weight THEN $weight ELSE r.weight END",
                            gid=gid, og=og, reason=reason, weight=weight,
                        )
                        session.run(
                            "MATCH (other:Document {graph_doc_id: $og}) MATCH (me:Document {graph_doc_id: $gid}) "
                            "MERGE (other)-[r:RELATED_TO]->(me) "
                            "ON CREATE SET r.reason=$reason, r.weight=$weight, r.created_at=datetime() "
                            "ON MATCH SET r.weight=CASE WHEN $reason='vector_similar' AND $weight>r.weight THEN $weight ELSE r.weight END",
                            gid=gid, og=og, reason=reason, weight=weight,
                        )
                        total_edges += 1
                        if is_cross_kb:
                            cross_kb_edges += 1

        logger.info("Vector similarity edges created: %d total, %d cross-KB", total_edges, cross_kb_edges)
        return {"enabled": True, "total_edges": total_edges, "cross_kb_edges": cross_kb_edges, "errors": errors}

    def _relate_all_kbs_comprehensive(self) -> dict:
        """全面构建 KB 间关联：基于共享标签 + 跨库文档相似度。"""
        with self.driver.session(database=config.graph_database) as session:
            # 1. 共享标签关联
            shared_tag_pairs = 0
            result = session.run("""
                MATCH (a:KnowledgeBase), (b:KnowledgeBase)
                WHERE a.kb_id < b.kb_id
                MATCH (a)<-[:BELONGS_TO]-(da:Document)-[:HAS_TAG]->(t:Tag)
                MATCH (b)<-[:BELONGS_TO]-(db:Document)-[:HAS_TAG]->(t)
                WITH a, b, count(DISTINCT t) AS shared_tags
                WHERE shared_tags > 0
                MERGE (a)-[r:RELATED_TO]->(b)
                ON CREATE SET r.reason='shared_tag', r.weight=shared_tags, r.created_at=datetime()
                ON MATCH SET r.weight=shared_tags, r.reason='shared_tag'
                RETURN count(r) AS cnt
            """).single()
            if result:
                shared_tag_pairs = result["cnt"]

            # 2. 跨库文档向量相似度关联
            vector_sim_pairs = 0
            result = session.run("""
                MATCH (a:KnowledgeBase), (b:KnowledgeBase)
                WHERE a.kb_id < b.kb_id
                MATCH (a)<-[:BELONGS_TO]-(da:Document)-[r:RELATED_TO]->(db:Document)-[:BELONGS_TO]->(b)
                WHERE r.reason = 'vector_similar' AND da.kb_id <> db.kb_id
                WITH a, b, count(r) AS vec_links, round(avg(r.weight), 4) AS avg_sim
                WHERE vec_links > 0
                MERGE (a)-[r2:RELATED_TO]->(b)
                ON CREATE SET r2.reason='vector_similar', r2.weight=avg_sim, r2.link_count=vec_links, r2.created_at=datetime()
                ON MATCH SET r2.weight=CASE WHEN avg_sim > coalesce(r2.weight, 0) THEN avg_sim ELSE r2.weight END,
                              r2.link_count=vec_links
                RETURN count(r2) AS cnt
            """).single()
            if result:
                vector_sim_pairs = result["cnt"]

            total = shared_tag_pairs + vector_sim_pairs
            return {
                "total_kb_pairs": total,
                "by_shared_tag": shared_tag_pairs,
                "by_vector_similarity": vector_sim_pairs,
            }

    def _relate_kbs_by_tags(self, parent_kb_id, sub_kbs):
        from app.services.storage_reader_service import storage_reader
        sub_ids = [s["kb_id"] for s in sub_kbs]
        all_ids = [parent_kb_id] + sub_ids
        with self.driver.session(database=config.graph_database) as session:
            for i, a_id in enumerate(all_ids):
                for b_id in all_ids[i + 1:]:
                    self._relate_two_kbs(session, a_id, b_id)
            all_kbs = storage_reader.list_knowledge_bases()
            other_ids = [kb["kb_id"] for kb in all_kbs if not kb.get("parent_id") and kb["kb_id"] not in all_ids]
            for kid in all_ids:
                for oid in other_ids:
                    self._relate_two_kbs(session, kid, oid)

    def _relate_two_kbs(self, session, a_id, b_id):
        row = session.run("MATCH (a:KnowledgeBase {kb_id: $a_id}) MATCH (b:KnowledgeBase {kb_id: $b_id}) RETURN size([(a)<-[:BELONGS_TO]-(:Document)-[:HAS_TAG]->(t:Tag) WHERE (t)<-[:HAS_TAG]-(:Document)-[:BELONGS_TO]->(b) | t]) AS shared", a_id=a_id, b_id=b_id).single()
        shared = row["shared"] if row else 0
        if shared > 0:
            session.run("MATCH (a:KnowledgeBase {kb_id: $a_id}) MATCH (b:KnowledgeBase {kb_id: $b_id}) MERGE (a)-[r:RELATED_TO]->(b) ON CREATE SET r.reason='shared_tag', r.weight=$shared, r.created_at=datetime() ON MATCH SET r.weight=$shared", a_id=a_id, b_id=b_id, shared=shared)

    def build_all_graphs(self, force=False, enable_vector_similarity=True):
        """构建全量知识图谱。

        三阶段构建：
        1. 元数据 + 标签关联（shared_tag）
        2. 内容向量相似度关联（vector_similar）—— 读取真实文档内容计算
        3. KB 间关联（基于共享标签 + 跨库文档相似度）
        """
        from app.services.storage_reader_service import storage_reader
        results = []
        kbs = storage_reader.list_knowledge_bases()
        top_kbs = [kb for kb in kbs if not kb.get("parent_id")]
        # ── Phase 1: 按 KB 构建元数据 + 标签关联 ──
        for kb in top_kbs:
            kid = kb["kb_id"] or kb["path"]
            r = self.build_kb_graph(kid, force)
            results.append({"kb_id": kid, "kb_path": kb["path"], **r})

        total_docs_phase1 = sum(r.get("docs_processed", 0) for r in results)

        # ── Phase 2: 内容向量相似度关联 ──
        vector_stats = {"enabled": False, "total_edges": 0, "cross_kb_edges": 0, "errors": []}
        if enable_vector_similarity:
            try:
                vector_stats = self._build_vector_similarity_edges(force)
                logger.info("Vector similarity edges: %d total, %d cross-KB",
                            vector_stats["total_edges"], vector_stats["cross_kb_edges"])
            except Exception as e:
                logger.error("Vector similarity build failed: %s", e)
                vector_stats["errors"].append(str(e)[:300])

        # ── Phase 3: KB 间关联（基于标签 + 向量相似度） ──
        kb_relation_stats = {"total_kb_pairs": 0, "by_shared_tag": 0, "by_vector_similarity": 0}
        try:
            kb_relation_stats = self._relate_all_kbs_comprehensive()
        except Exception as e:
            logger.warning("KB relation build failed: %s", e)

        return {
            "success": True,
            "total_top_kbs": len(results),
            "kbs": results,
            "phase1_metadata": {"docs_processed": total_docs_phase1},
            "phase2_vector_similarity": vector_stats,
            "phase3_kb_relations": kb_relation_stats,
        }

    @_retry_transient
    def search_documents(self, keyword, limit=20):
        with self.driver.session(database=config.graph_database) as s:
            return [dict(r) for r in s.run("MATCH (d:Document) WHERE d.name CONTAINS $k OR d.path CONTAINS $k RETURN d.graph_doc_id AS graph_doc_id, d.path AS path, d.name AS name, d.kb_id AS kb_id, d.description AS description ORDER BY d.name ASC LIMIT $limit", k=keyword, limit=limit)]

    @_retry_transient
    def search_kbs(self, keyword, limit=20):
        with self.driver.session(database=config.graph_database) as s:
            return [dict(r) for r in s.run("MATCH (kb:KnowledgeBase) WHERE kb.kb_id CONTAINS $k OR kb.name CONTAINS $k OPTIONAL MATCH (kb)<-[:BELONGS_TO]-(d:Document) WITH kb, count(d) AS dc RETURN kb.kb_id AS kb_id, kb.name AS name, dc AS doc_count ORDER BY dc DESC LIMIT $limit", k=keyword, limit=limit)]

    @_retry_transient
    def search_tags(self, keyword, limit=20):
        with self.driver.session(database=config.graph_database) as s:
            return [dict(r) for r in s.run("MATCH (t:Tag) WHERE t.name CONTAINS $k OPTIONAL MATCH (t)<-[:HAS_TAG]-(d:Document) WITH t, count(d) AS dc RETURN t.name AS name, dc AS doc_count ORDER BY dc DESC LIMIT $limit", k=keyword, limit=limit)]

    @_retry_transient
    def get_related_documents(self, doc_path, limit=20):
        """获取与目标文档真正相关的文档（质量过滤）。

        过滤规则：
        - vector_similar: score ≥ 0.35 → 直接通过（内容相似）
        - shared_tag: shared≥2 强关联通过; shared=1 且为稀有标签通过
        - agent_judged: 直接通过
        按综合相关性得分排序：vector_similar(0.7) > agent_judged(0.5) > shared_tag(0.3)
        """
        gid = _graph_doc_id(doc_path)
        with self.driver.session(database=config.graph_database) as s:
            return [dict(r) for r in s.run("""
                MATCH (me:Document {graph_doc_id: $gid})-[r:RELATED_TO]->(other:Document)
                WHERE r.reason = 'vector_similar'
                   OR r.reason = 'agent_judged'
                   OR (r.reason = 'shared_tag' AND r.weight >= 2)
                   OR (r.reason = 'shared_tag' AND r.weight = 1 AND r.same_kb = true)
                   OR (r.reason = 'shared_tag' AND r.weight = 1
                       AND size([tag IN r.shared_tags WHERE tag IS NOT NULL]) > 0)
                WITH other, r,
                     CASE r.reason
                       WHEN 'vector_similar' THEN r.weight * 0.7
                       WHEN 'agent_judged' THEN r.weight * 0.5
                       WHEN 'shared_tag' THEN r.weight * 0.15
                       ELSE 0
                     END AS relevance
                RETURN other.graph_doc_id AS graph_doc_id,
                       other.path AS path,
                       other.name AS name,
                       other.kb_id AS kb_id,
                       r.reason AS reason,
                       r.weight AS weight,
                       r.reasoning AS reasoning,
                       r.shared_tags AS shared_tags,
                       round(relevance, 4) AS relevance
                ORDER BY relevance DESC, r.weight DESC
                LIMIT $limit
            """, gid=gid, limit=limit)]

    @_retry_transient
    def get_related_documents_enhanced(self, doc_path, limit=20):
        """增强版关联文档查询：按连接类型分组，展示真实关联理由。

        返回结构：
        {
          "by_vector_similar": [{path, name, score, kb_id}, ...],  # 内容相似
          "by_shared_tags": [{path, name, shared_count, shared_tags, kb_id}, ...],  # 标签相关
          "by_agent_judged": [{path, name, reasoning, kb_id}, ...],  # Agent 判定
          "summary": {total, vector_count, tag_count, agent_count, cross_kb_count}
        }
        """
        gid = _graph_doc_id(doc_path)
        with self.driver.session(database=config.graph_database) as s:
            # 获取文档自身的 kb_id
            me_rec = s.run("MATCH (d:Document {graph_doc_id: $gid}) RETURN d.kb_id AS kb_id", gid=gid).single()
            my_kb = me_rec["kb_id"] if me_rec else ""

            # 向量相似关联
            vec = [dict(r) for r in s.run("""
                MATCH (me:Document {graph_doc_id: $gid})-[r:RELATED_TO {reason: 'vector_similar'}]->(other:Document)
                WHERE r.weight >= $threshold
                RETURN other.path AS path, other.name AS name, other.kb_id AS kb_id,
                       r.weight AS score
                ORDER BY r.weight DESC LIMIT $limit
            """, gid=gid, limit=limit, threshold=config.vector_score_threshold)]

            # 标签关联（共享≥2，或同一KB共享≥1）
            tag = [dict(r) for r in s.run("""
                MATCH (me:Document {graph_doc_id: $gid})-[r:RELATED_TO {reason: 'shared_tag'}]->(other:Document)
                WHERE r.weight >= 2 OR (r.weight = 1 AND r.same_kb = true)
                RETURN other.path AS path, other.name AS name, other.kb_id AS kb_id,
                       r.weight AS shared_count, r.shared_tags AS shared_tags
                ORDER BY r.weight DESC LIMIT $limit
            """, gid=gid, limit=limit)]

            # Agent 判定关联
            agent = [dict(r) for r in s.run("""
                MATCH (me:Document {graph_doc_id: $gid})-[r:RELATED_TO]->(other:Document)
                WHERE r.reason = 'agent_judged'
                RETURN other.path AS path, other.name AS name, other.kb_id AS kb_id,
                       r.weight AS weight, r.reasoning AS reasoning
                ORDER BY r.weight DESC LIMIT $limit
            """, gid=gid, limit=limit)]

            cross_kb = sum(1 for v in vec if v.get("kb_id") != my_kb) + \
                       sum(1 for t in tag if t.get("kb_id") != my_kb) + \
                       sum(1 for a in agent if a.get("kb_id") != my_kb)

            return {
                "by_vector_similar": vec,
                "by_shared_tags": tag,
                "by_agent_judged": agent,
                "summary": {
                    "total": len(vec) + len(tag) + len(agent),
                    "vector_count": len(vec),
                    "tag_count": len(tag),
                    "agent_count": len(agent),
                    "cross_kb_count": cross_kb,
                }
            }

    @_retry_transient
    def get_related_documents_by_reason(self, doc_path, reason, limit=20):
        gid = _graph_doc_id(doc_path)
        with self.driver.session(database=config.graph_database) as s:
            return [dict(r) for r in s.run("MATCH (me:Document {graph_doc_id: $gid})-[r:RELATED_TO {reason: $reason}]->(other:Document) RETURN other.graph_doc_id AS graph_doc_id, other.path AS path, other.name AS name, other.kb_id AS kb_id, r.weight AS weight ORDER BY r.weight DESC LIMIT $limit", gid=gid, reason=reason, limit=limit)]

    @_retry_transient
    def get_documents_by_tag(self, tag_name, limit=50):
        with self.driver.session(database=config.graph_database) as s:
            return [dict(r) for r in s.run("MATCH (t:Tag {name: $tag})<-[:HAS_TAG]-(d:Document) RETURN d.graph_doc_id AS graph_doc_id, d.path AS path, d.name AS name, d.kb_id AS kb_id, d.description AS description ORDER BY d.name ASC LIMIT $limit", tag=tag_name, limit=limit)]

    @_retry_transient
    def get_document_graph(self, doc_path, limit=50):
        """增强版文档图谱：仅返回真正相关的文档，带连接详情。

        与旧版区别：
        - 过滤掉 shared_tag weight=1 的噪声连接（通用标签重叠）
        - 返回每条连接的 shared_tags（具体哪些标签重叠）
        - 返回 relevance 综合得分
        - cross_kb_links 仅包含真正跨KB且有意义的连接
        """
        gid = _graph_doc_id(doc_path)
        with self.driver.session(database=config.graph_database) as s:
            doc = s.run("""
                MATCH (d:Document {graph_doc_id: $gid})
                OPTIONAL MATCH (d)-[:BELONGS_TO]->(kb:KnowledgeBase)
                OPTIONAL MATCH (d)-[:HAS_TAG]->(t:Tag)
                RETURN d.graph_doc_id AS graph_doc_id, d.path AS path, d.name AS name,
                       d.kb_id AS kb_id, d.description AS description,
                       kb.name AS kb_name, collect(DISTINCT t.name) AS tags
            """, gid=gid).single()

            # 质量过滤后的关联文档
            related = list(s.run("""
                MATCH (me:Document {graph_doc_id: $gid})-[r:RELATED_TO]->(other:Document)
                WHERE r.reason = 'vector_similar'
                   OR r.reason = 'agent_judged'
                   OR (r.reason = 'shared_tag' AND r.weight >= 2)
                   OR (r.reason = 'shared_tag' AND r.weight = 1 AND r.same_kb = true)
                WITH other, r,
                     CASE r.reason
                       WHEN 'vector_similar' THEN r.weight * 0.7
                       WHEN 'agent_judged' THEN r.weight * 0.5
                       WHEN 'shared_tag' THEN r.weight * 0.15
                       ELSE 0
                     END AS relevance
                RETURN other.path AS path, other.name AS name, other.kb_id AS kb_id,
                       r.reason AS reason, r.weight AS weight, r.reasoning AS reasoning,
                       r.shared_tags AS shared_tags, round(relevance, 4) AS relevance
                ORDER BY relevance DESC, r.weight DESC
                LIMIT $limit
            """, gid=gid, limit=limit))

            doc_data = dict(doc) if doc else {}
            doc_kb_id = doc_data.get("kb_id", "")
            cross_kb = [dict(r) for r in related if r.get("kb_id", "") != doc_kb_id]

            # 按连接类型统计
            by_reason = {}
            for r in related:
                reason = r.get("reason", "other")
                by_reason[reason] = by_reason.get(reason, 0) + 1

            return {
                "doc_path": _norm_path(doc_path),
                "graph_doc_id": gid,
                "document": doc_data,
                "tags": doc_data.get("tags", []),
                "related_documents": [dict(r) for r in related],
                "by_connection_type": by_reason,
                "cross_kb_links": cross_kb,
                "related_count": len(related),
                "cross_kb_count": len(cross_kb),
            }

    @_retry_transient
    def get_kb_overview(self, kb_id):
        kb_id = self._resolve_kb_id(kb_id)
        with self.driver.session(database=config.graph_database) as s:
            dc = s.run("MATCH (kb:KnowledgeBase {kb_id: $k}) OPTIONAL MATCH (kb)<-[:BELONGS_TO]-(d:Document) RETURN count(DISTINCT d) AS c", k=kb_id).single()["c"]
            subs = list(s.run("MATCH (p:KnowledgeBase {kb_id: $k})-[:HAS_SUBKB]->(sub:KnowledgeBase) OPTIONAL MATCH (sub)<-[:BELONGS_TO]-(d:Document) RETURN sub.kb_id AS kb_id, sub.name AS name, count(DISTINCT d) AS doc_count ORDER BY sub.name ASC", k=kb_id))
            tags = list(s.run("MATCH (kb:KnowledgeBase {kb_id: $k})<-[:BELONGS_TO]-(d:Document)-[:HAS_TAG]->(t:Tag) RETURN t.name AS tag, count(DISTINCT d) AS doc_count ORDER BY doc_count DESC LIMIT 30", k=kb_id))
            rkbs = list(s.run("MATCH (kb:KnowledgeBase {kb_id: $k})-[r:RELATED_TO]->(other:KnowledgeBase) RETURN other.kb_id AS kb_id, other.name AS name, r.weight AS shared_tags ORDER BY r.weight DESC LIMIT 20", k=kb_id))
            tops = list(s.run("MATCH (kb:KnowledgeBase {kb_id: $k})<-[:BELONGS_TO]-(d:Document) OPTIONAL MATCH (d)-[r:RELATED_TO]->() WITH d, count(r) AS degree, round(coalesce(sum(r.weight),0),2) AS tw RETURN d.graph_doc_id AS gid, d.name AS name, d.path AS path, degree, tw ORDER BY degree DESC, tw DESC LIMIT 20", k=kb_id))
            return {"kb_id": kb_id, "doc_count": dc, "sub_kbs": [dict(r) for r in subs], "tag_distribution": [dict(r) for r in tags], "related_kbs": [dict(r) for r in rkbs], "top_docs": [dict(r) for r in tops]}

    @_retry_transient
    def get_neighbors(self, node_id, node_type="document", depth=1):
        depth = max(1, min(int(depth), 3))
        with self.driver.session(database=config.graph_database) as s:
            if node_type == "document":
                gid = _graph_doc_id(node_id) if not node_id.startswith("doc::") else node_id
                q = f"MATCH path=(d:Document {{graph_doc_id: $id}})-[*1..{depth}]-(n) RETURN nodes(path) AS ns, relationships(path) AS rs LIMIT 50"
                result = s.run(q, id=gid)
            elif node_type == "kb":
                q = f"MATCH path=(kb:KnowledgeBase {{kb_id: $id}})-[*1..{depth}]-(n) RETURN nodes(path) AS ns, relationships(path) AS rs LIMIT 50"
                result = s.run(q, id=node_id)
            else:
                q = f"MATCH path=(t:Tag {{name: $id}})-[*1..{depth}]-(n) RETURN nodes(path) AS ns, relationships(path) AS rs LIMIT 50"
                result = s.run(q, id=node_id)
            nm, edges = {}, []
            for rec in result:
                for n in rec["ns"]:
                    p = dict(n)
                    lbls = list(n.labels)
                    primary = lbls[0] if lbls else "Unknown"
                    if primary == "Document":
                        nid = p.get("graph_doc_id", n.id)
                        label = p.get("name") or p.get("path", "")
                        group = "Document"
                    elif primary == "KnowledgeBase":
                        nid = p.get("kb_id", n.id)
                        label = p.get("name") or p.get("kb_id", "")
                        group = "KnowledgeBase"
                    elif primary == "Tag":
                        nid = f"tag::{p.get('name', n.id)}"
                        label = p.get("name", "")
                        group = "Tag"
                    else:
                        nid, label, group = str(n.id), str(n.id), primary
                    if nid not in nm:
                        nm[nid] = {"id": nid, "label": label, "group": group}
                for r in rec["rs"]:
                    sp, ep = dict(r.start_node), dict(r.end_node)
                    nm.setdefault(sp.get("graph_doc_id") or sp.get("kb_id") or f"tag::{sp.get('name','')}", {"id": sp.get("graph_doc_id") or sp.get("kb_id") or f"tag::{sp.get('name','')}", "label": "?", "group": "?"})
                    nm.setdefault(ep.get("graph_doc_id") or ep.get("kb_id") or f"tag::{ep.get('name','')}", {"id": ep.get("graph_doc_id") or ep.get("kb_id") or f"tag::{ep.get('name','')}", "label": "?", "group": "?"})
                    edges.append({"from": str(sp.get("graph_doc_id") or sp.get("kb_id") or f"tag::{sp.get('name','')}"), "to": str(ep.get("graph_doc_id") or ep.get("kb_id") or f"tag::{ep.get('name','')}"), "label": r.type})
            return {"nodes": list(nm.values()), "edges": edges}

    @_retry_transient
    def get_stats(self):
        with self.driver.session(database=config.graph_database) as s:
            return {"node_count": s.run("MATCH (n) RETURN count(n) AS c").single()["c"], "edge_count": s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"], "doc_count": s.run("MATCH (d:Document) RETURN count(d) AS c").single()["c"], "kb_count": s.run("MATCH (kb:KnowledgeBase) RETURN count(kb) AS c").single()["c"], "tag_count": s.run("MATCH (t:Tag) RETURN count(t) AS c").single()["c"], "relation_by_reason": {r["reason"]: r["c"] for r in s.run("MATCH ()-[r:RELATED_TO]->() RETURN r.reason AS reason, count(r) AS c ORDER BY c DESC")}, "schema_version": _GRAPH_SCHEMA_VERSION}

    @_retry_transient
    def find_cross_kb_documents(self, limit=50):
        with self.driver.session(database=config.graph_database) as s:
            return [dict(r) for r in s.run("MATCH (d:Document)-[r:RELATED_TO]->(other:Document) WHERE other.kb_id<>d.kb_id WITH d, collect(DISTINCT other.kb_id) AS kbs, count(r) AS lc WHERE size(kbs)>=1 RETURN d.graph_doc_id AS graph_doc_id, d.path AS path, d.name AS name, d.kb_id AS kb_id, kbs AS related_kbs, lc AS link_count ORDER BY lc DESC LIMIT $limit", limit=limit)]

    @_retry_transient
    def find_document_paths(self, doc_a, doc_b, max_depth=4):
        md = max(1, min(int(max_depth), 6))
        ga, gb = _graph_doc_id(doc_a), _graph_doc_id(doc_b)
        with self.driver.session(database=config.graph_database) as s:
            paths = [dict(r) for r in s.run(f"MATCH (a:Document {{graph_doc_id: $na}}), (b:Document {{graph_doc_id: $nb}}) MATCH p=shortestPath((a)-[:RELATED_TO*1..{md}]-(b)) RETURN [n IN nodes(p) | n.path] AS doc_path, [r IN relationships(p) | r.reason] AS reasons, length(p) AS hops LIMIT 5", na=ga, nb=gb)]
            return {"doc_a": doc_a, "doc_b": doc_b, "paths": paths, "path_count": len(paths)}

    @_retry_transient
    def find_central_documents(self, kb_id, top_n=20):
        kb_id = self._resolve_kb_id(kb_id)
        with self.driver.session(database=config.graph_database) as s:
            return [dict(r) for r in s.run("MATCH (kb:KnowledgeBase {kb_id: $k})<-[:BELONGS_TO]-(d:Document) OPTIONAL MATCH (d)-[r:RELATED_TO]->() WITH d, count(r) AS degree, round(coalesce(sum(r.weight),0),2) AS tw RETURN d.graph_doc_id AS gid, d.name AS name, d.path AS path, degree, tw ORDER BY degree DESC, tw DESC LIMIT $tn", k=kb_id, tn=top_n)]

    @_retry_transient
    def delete_document(self, doc_path):
        gid = _graph_doc_id(doc_path)
        with self.driver.session(database=config.graph_database) as s:
            s.run("MATCH (d:Document {graph_doc_id: $gid})-[r:RELATED_TO]-() DELETE r", gid=gid)
            s.run("MATCH (d:Document {graph_doc_id: $gid})-[r:HAS_TAG]->() DELETE r", gid=gid)
            r = s.run("MATCH (d:Document {graph_doc_id: $gid}) DETACH DELETE d", gid=gid)
            s.run("MATCH (t:Tag) WHERE NOT (t)<-[:HAS_TAG]-() DETACH DELETE t")
            s.run("MATCH (kb:KnowledgeBase) WHERE NOT (kb)<-[:BELONGS_TO]-() AND NOT (kb)-[:HAS_SUBKB]->() DETACH DELETE kb")
            return r.consume().counters.nodes_deleted

    @_retry_transient
    def delete_kb_graph(self, kb_id):
        kb_id = self._resolve_kb_id(kb_id)
        with self.driver.session(database=config.graph_database) as s:
            s.run("MATCH (kb:KnowledgeBase {kb_id: $k})<-[:BELONGS_TO]-(d:Document) OPTIONAL MATCH (d)-[r:RELATED_TO]-() DELETE r", k=kb_id)
            s.run("MATCH (kb:KnowledgeBase {kb_id: $k})<-[:BELONGS_TO]-(d:Document) OPTIONAL MATCH (d)-[r:HAS_TAG]->() DELETE r", k=kb_id)
            s.run("MATCH (kb:KnowledgeBase {kb_id: $k})<-[:BELONGS_TO]-(d:Document) DETACH DELETE d", k=kb_id)
            s.run("MATCH (kb:KnowledgeBase {kb_id: $k}) DETACH DELETE kb", k=kb_id)
            s.run("MATCH (kb:KnowledgeBase {kb_id: $k})-[r:RELATED_TO]-() DELETE r", k=kb_id)
            s.run("MATCH (t:Tag) WHERE NOT (t)<-[:HAS_TAG]-() DETACH DELETE t")
            return {"kb_id": kb_id, "status": "deleted"}


graph_service = GraphService()
