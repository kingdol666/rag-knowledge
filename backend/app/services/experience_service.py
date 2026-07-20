"""Experience Service — 经验管理系统核心服务.

管理经验文件夹初始化、经验 CRUD、应用记录、评审、统计。
经验不干扰已有文档体系，独立存储在 KB/experience/ 下。
"""
from __future__ import annotations

import json
import logging
import uuid
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from app.config import config
from app.utils.paths import get_storage_root
from app.models.experience_models import (
    ExperienceCategory,
    ExperienceCreate,
    ExperienceUpdate,
    ExperienceApplyRequest,
    ExperienceReviewRequest,
    ExperienceResult,
    ExperienceSeverity,
    ExperienceStatus,
)

logger = logging.getLogger(__name__)

_EXP_INDEX_FILENAME = ".experience-index.yml"
_EXP_DIRNAME = "experience"
_EXP_IMAGES_DIRNAME = "images"


def _normalize_path(p: str) -> str:
    """统一路径分隔符为 /"""
    return p.replace("\\", "/")


class ExperienceService:
    """经验管理系统服务。单例模式。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── 路径 ────────────────────────────────────────────────────

    @property
    def storage_root(self) -> Path:
        return get_storage_root()

    def _exp_dir(self, kb_path: str) -> Path:
        return self.storage_root / _normalize_path(kb_path) / _EXP_DIRNAME

    def _index_path(self, kb_path: str) -> Path:
        return self._exp_dir(kb_path) / _EXP_INDEX_FILENAME

    def _resolve_kb_path(self, kb_id: str) -> Optional[str]:
        """从 kb_id（UUID 或 path）解析 KB 的相对路径。"""
        tree = self._read_tree_fs()
        for folder in tree.get("folders", []):
            if folder.get("id") == kb_id or folder.get("path") == kb_id:
                return folder.get("path")
        # 如果 kb_id 本身就是 path
        if (self.storage_root / kb_id).exists():
            return kb_id
        return None

    def _read_tree_fs(self) -> dict:
        tree_path = self.storage_root / ".tree-fs.json"
        if not tree_path.exists():
            return {"folders": [], "files": []}
        try:
            return json.loads(tree_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to read .tree-fs.json: %s", e)
            return {"folders": [], "files": []}

    def _read_index(self, kb_path: str) -> dict:
        idx = self._index_path(kb_path)
        if not idx.exists():
            return {"knowledge_base": {"path": kb_path}, "experience_count": 0, "experience_tags": [], "experiences": []}
        try:
            data = yaml.safe_load(idx.read_text(encoding="utf-8"))
            return data if data else {}
        except Exception as e:
            logger.warning("Failed to read experience index %s: %s", idx, e)
            return {}

    def _write_index(self, kb_path: str, data: dict) -> bool:
        idx = self._index_path(kb_path)
        try:
            idx.write_text(
                yaml.dump(data, allow_unicode=True, sort_keys=False, indent=2, default_flow_style=False),
                encoding="utf-8",
            )
            return True
        except Exception as e:
            logger.error("Failed to write experience index %s: %s", idx, e)
            return False

    def _generate_markdown(self, exp: dict) -> str:
        """从经验元数据生成 Markdown 正文。"""
        lines = []
        lines.append(f"# {exp.get('title', '')}")
        lines.append("")
        lines.append("## 经验概览")
        lines.append(f"- **知识库**: {exp.get('kb_path', '')}")
        lines.append(f"- **类别**: {exp.get('category', 'tip')}")
        lines.append(f"- **严重程度**: {exp.get('severity', 'normal')}")
        lines.append(f"- **场景**: {exp.get('scenario', '')}")
        lines.append(f"- **创建时间**: {exp.get('created_at', '')}")
        lines.append("")
        if exp.get("problem"):
            lines.append("## 问题")
            lines.append(exp["problem"])
            lines.append("")
        if exp.get("solution"):
            lines.append("## 方案")
            lines.append(exp["solution"])
            lines.append("")
        if exp.get("key_lessons"):
            lines.append("## 关键教训")
            for i, lesson in enumerate(exp["key_lessons"], 1):
                lines.append(f"{i}. {lesson}")
            lines.append("")
        if exp.get("related_docs"):
            lines.append("## 关联知识")
            for doc in exp["related_docs"]:
                lines.append(f"- 📄 {doc}")
            lines.append("")
        if exp.get("metrics"):
            lines.append("## 量化指标")
            for k, v in exp["metrics"].items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")
        lines.append("---")
        lines.append(f"*经验 ID: {exp.get('id', '')}*")
        return "\n".join(lines)

    # ── 初始化 ────────────────────────────────────────────────────

    async def init_experience_folder(self, kb_path: str) -> dict:
        """在 KB 目录下创建 experience/ 文件夹和索引文件。

        先通过 _resolve_kb_path 将 kb_id(UUID 或 path) 转为实际路径。
        只在真正的 KB 目录下创建，不在 UUID 名称下创建空目录。
        """
        # 先解析：UUID -> path
        if not self.storage_root.exists():
            return {"success": False, "error": f"Storage root not found: {self.storage_root}"}
        resolved = self._resolve_kb_path(kb_path)
        if not resolved:
            return {"success": False, "error": f"KB not found: {kb_path}"}
        kb_path = resolved
        exp_dir = self._exp_dir(kb_path)
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / _EXP_IMAGES_DIRNAME).mkdir(exist_ok=True)

        if not self._index_path(kb_path).exists():
            yaml_content = {
                "knowledge_base": {"path": kb_path},
                "experience_count": 0,
                "experience_tags": [],
                "experiences": [],
            }
            self._write_index(kb_path, yaml_content)

        logger.info("Experience folder initialized for KB: %s", kb_path)
        return {"success": True, "kb_path": kb_path, "experience_path": str(exp_dir)}

    # ── CRUD ────────────────────────────────────────────────────

    async def create_experience(self, kb_id: str, data: ExperienceCreate) -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}

        # 确保经验文件夹存在
        await self.init_experience_folder(kb_path)

        exp_id = f"exp-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        exp_entry = {
            "id": exp_id,
            "title": data.title,
            "path": f"{_normalize_path(kb_path)}/{_EXP_DIRNAME}/{exp_id}.md",
            "scenario": data.scenario,
            "category": data.category.value if isinstance(data.category, ExperienceCategory) else data.category,
            "problem": data.problem,
            "solution": data.solution,
            "result": data.result.value if isinstance(data.result, ExperienceResult) else data.result,
            "key_lessons": data.key_lessons,
            "tags": data.tags,
            "severity": data.severity.value if isinstance(data.severity, ExperienceSeverity) else data.severity,
            "status": ExperienceStatus.PUBLISHED.value,
            "related_docs": data.related_docs,
            "prerequisites": data.prerequisites,
            "metrics": data.metrics,
            "author": "",
            "created_at": now,
            "updated_at": now,
            "applied_count": 0,
            "rating_avg": 0.0,
            "review_count": 0,
        }

        # 写入 .md 正文
        md_content = self._generate_markdown(exp_entry)
        md_path = self.storage_root / _normalize_path(exp_entry["path"])
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_content, encoding="utf-8")

        # 更新索引
        index = self._read_index(kb_path)
        experiences = index.get("experiences", [])
        experiences.append(exp_entry)
        index["experiences"] = experiences
        index["experience_count"] = len(experiences)

        # 更新 tags 聚合
        for tag in data.tags:
            if tag not in index.get("experience_tags", []):
                index.setdefault("experience_tags", []).append(tag)

        self._write_index(kb_path, index)

        # ── 经验向量索引（共享 KB collection）──
        # 注意：vector_service 用 kb_id(UUID) 做 collection 命名，而此处 kb_path 是中文路径
        # 必须解析为 UUID 后再索引，否则会创建新的空 collection 导致检索不到
        try:
            from app.services.vector_service import vector_service as _vs
            # Resolve path → UUID (vector_service 用 UUID 命名 collection "kb_{uuid}")
            tree = self._read_tree_fs()
            kb_id_for_vec = None
            for folder in tree.get("folders", []):
                if folder.get("path") == kb_path:
                    kb_id_for_vec = folder.get("id", kb_path)
                    break
            if not kb_id_for_vec:
                kb_id_for_vec = kb_path  # fallback

            md_content_for_index = self._generate_markdown(exp_entry)
            vi = _vs.index_document(
                kb_id_for_vec,
                exp_entry["path"],
                md_content_for_index,
                metadata={
                    "doc_type": "experience",
                    "exp_id": exp_id,
                    "scenario": data.scenario,
                    "category": exp_entry["category"],
                    "severity": exp_entry["severity"],
                }
            )
            if vi and vi.get("total_chunks", 0) > 0:
                exp_entry["vector_index"] = vi
                # Re-update index with vector_index info
                index["experiences"][-1] = exp_entry
                self._write_index(kb_path, index)
                logger.info("Experience %s indexed: %d chunks (collection=%s)",
                            exp_id, vi["total_chunks"], vi.get("collection"))
            else:
                logger.warning("Experience %s vector indexing returned empty result, retrying once", exp_id)
                # Retry once
                vi2 = _vs.index_document(
                    kb_id_for_vec,
                    exp_entry["path"],
                    md_content_for_index,
                    metadata={
                        "doc_type": "experience",
                        "exp_id": exp_id,
                        "scenario": data.scenario,
                        "category": exp_entry["category"],
                        "severity": exp_entry["severity"],
                    }
                )
                if vi2 and vi2.get("total_chunks", 0) > 0:
                    exp_entry["vector_index"] = vi2
                    index["experiences"][-1] = exp_entry
                    self._write_index(kb_path, index)
        except Exception as e:
            logger.error("Vector indexing failed for experience %s: %s", exp_id, e)

        return {"success": True, "experience": exp_entry}

    async def reindex_experiences(self, kb_id: str, exp_id: str = None) -> dict:
        """重索引经验到向量库。

        Args:
            kb_id: KB ID 或 path
            exp_id: 可选，只重索引指定经验；空则重索引整个 KB

        Returns:
            {success, reindexed: n, skipped: n, errors: [...]}
        """
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        # Resolve path → UUID for vector_service
        tree = self._read_tree_fs()
        kb_id_for_vec = None
        for folder in tree.get("folders", []):
            if folder.get("path") == kb_path:
                kb_id_for_vec = folder.get("id", kb_path)
                break
        if not kb_id_for_vec:
            kb_id_for_vec = kb_path

        from app.services.vector_service import vector_service as _vs

        index = self._read_index(kb_path)
        exps = list(index.get("experiences", []))
        if exp_id:
            exps = [e for e in exps if e.get("id") == exp_id]

        reindexed = 0
        skipped = 0
        errors = []
        for exp in exps:
            try:
                md_content = self._generate_markdown(exp)
                vi = _vs.index_document(
                    kb_id_for_vec,
                    exp["path"],
                    md_content,
                    metadata={
                        "doc_type": "experience",
                        "exp_id": exp.get("id"),
                        "scenario": exp.get("scenario", ""),
                        "category": exp.get("category", "tip"),
                        "severity": exp.get("severity", "normal"),
                    }
                )
                if vi and vi.get("total_chunks", 0) > 0:
                    exp["vector_index"] = vi
                    reindexed += 1
                else:
                    skipped += 1
            except Exception as e:
                errors.append(f"{exp.get('id','?')}: {e}")
                skipped += 1

        if reindexed > 0 or errors:
            # Write back updated index
            index["experiences"] = list(index.get("experiences", []))
            for exp in exps:
                for i, e in enumerate(index["experiences"]):
                    if e.get("id") == exp.get("id"):
                        index["experiences"][i] = exp
                        break
            self._write_index(kb_path, index)

        return {
            "success": True,
            "reindexed": reindexed,
            "skipped": skipped,
            "errors": errors,
        }

    async def read_experience(self, kb_id: str, exp_id: str) -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        for exp in index.get("experiences", []):
            if exp["id"] == exp_id:
                # 也读取 .md 正文
                md_path = self.storage_root / _normalize_path(exp["path"])
                content = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
                return {"success": True, "experience": exp, "content": content}
        return {"success": False, "error": f"Experience not found: {exp_id}"}

    async def list_experiences(self, kb_id: str, scenario: str = "",
                                category: str = "", tag: str = "") -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        exps = list(index.get("experiences", []))

        # 过滤
        if scenario:
            exps = [e for e in exps if scenario.lower() in e.get("scenario", "").lower()]
        if category:
            exps = [e for e in exps if e.get("category") == category]
        if tag:
            exps = [e for e in exps if tag in e.get("tags", [])]

        # 按评分排序
        exps.sort(key=lambda x: (x.get("rating_avg", 0), x.get("applied_count", 0)), reverse=True)

        return {"success": True, "count": len(exps), "experiences": exps}

    async def update_experience(self, kb_id: str, exp_id: str, data: ExperienceUpdate) -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        for exp in index.get("experiences", []):
            if exp["id"] == exp_id:
                update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
                for k, v in update_fields.items():
                    if hasattr(v, 'value'):
                        v = v.value
                    exp[k] = v
                exp["updated_at"] = datetime.now(timezone.utc).isoformat()

                # 如果标题或结构改了，重新生成 .md
                md_path = self.storage_root / _normalize_path(exp["path"])
                if md_path.exists():
                    md_content = self._generate_markdown(exp)
                    md_path.write_text(md_content, encoding="utf-8")

                self._write_index(kb_path, index)

                # Re-index if title/problem/solution/key_lessons changed
                try:
                    from app.services.vector_service import vector_service as _vs
                    md_content_for_index = self._generate_markdown(exp)
                    vi = _vs.index_document(
                        kb_path, exp["path"], md_content_for_index,
                        metadata={"doc_type": "experience", "exp_id": exp_id, "scenario": exp.get("scenario", ""), "category": exp.get("category", "")}
                    )
                    if vi:
                        exp["vector_index"] = vi
                        self._write_index(kb_path, index)
                    reindexed = True
                    reindex_error = None
                except Exception as e:
                    logger.warning("Re-indexing failed: %s", e)
                    reindexed = False
                    reindex_error = str(e)

                return {"success": True, "experience": exp,
                        "reindexed": reindexed, "reindex_error": reindex_error}

        return {"success": False, "error": f"Experience not found: {exp_id}"}

    async def delete_experience(self, kb_id: str, exp_id: str) -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        exps = index.get("experiences", [])

        # Find the experience BEFORE filtering
        target = None
        for e in exps:
            if e["id"] == exp_id:
                target = e
                break

        if not target:
            return {"success": False, "error": f"Experience not found: {exp_id}"}

        # Delete .md file
        md_path = self.storage_root / _normalize_path(target["path"])
        if md_path.exists():
            md_path.unlink()

        # Delete from vector DB
        try:
            from app.services.vector_service import vector_service as _vs
            _vs.delete_document(kb_path, target["path"])
        except Exception as e:
            logger.warning("Vector deletion failed: %s", e)

        # Remove from index
        index["experiences"] = [e for e in exps if e["id"] != exp_id]
        index["experience_count"] = len(index["experiences"])
        self._write_index(kb_path, index)
        return {"success": True, "deleted_id": exp_id}

    # ── 操作 ────────────────────────────────────────────────────

    async def apply_experience(self, kb_id: str, exp_id: str, req: ExperienceApplyRequest) -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        for exp in index.get("experiences", []):
            if exp["id"] == exp_id:
                exp["applied_count"] = exp.get("applied_count", 0) + 1
                exp["updated_at"] = datetime.now(timezone.utc).isoformat()
                # V2: 持久化应用记录（用于追溯）
                apply_records = exp.setdefault("apply_records", [])
                apply_records.append({
                    "user": req.user,
                    "context": req.context,
                    "result": req.result,
                    "notes": req.notes,
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                })
                # 只保留最近 100 条
                if len(apply_records) > 100:
                    exp["apply_records"] = apply_records[-100:]
                self._write_index(kb_path, index)
                return {"success": True, "experience": exp, "apply_record": req.model_dump()}
        return {"success": False, "error": f"Experience not found: {exp_id}"}

    async def review_experience(self, kb_id: str, exp_id: str, req: ExperienceReviewRequest) -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        for exp in index.get("experiences", []):
            if exp["id"] == exp_id:
                old_count = exp.get("review_count", 0)
                old_avg = exp.get("rating_avg", 0.0)
                new_count = old_count + 1
                exp["rating_avg"] = round(((old_avg * old_count) + req.rating) / new_count, 2)
                exp["review_count"] = new_count
                exp["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write_index(kb_path, index)
                return {"success": True, "experience": exp, "review_record": req.model_dump()}
        return {"success": False, "error": f"Experience not found: {exp_id}"}

    async def experience_summary(self, kb_id: str) -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        exps = index.get("experiences", [])
        total = len(exps)
        if total == 0:
            return {"success": True, "summary": {"total": 0}}

        # 统计
        by_category = {}
        by_severity = {}
        total_applied = 0
        avg_rating = 0.0
        # V2: 对每条经验计算综合可信度评分
        def _credibility_score(e: dict) -> float:
            """0-1: 综合可信度。考虑时效性、应用次数、评分。"""
            try:
                created = datetime.fromisoformat(e.get("created_at", ""))
                age_days = (datetime.now(timezone.utc) - created).days
            except Exception:
                age_days = 0
            recency = max(0.0, 1.0 - age_days / 365.0)
            rating_factor = e.get("rating_avg", 0) / 5.0 if e.get("review_count", 0) > 0 else 0.0
            applied_factor = min(e.get("applied_count", 0) / 5.0, 1.0)
            return round(0.4 * rating_factor + 0.3 * applied_factor + 0.3 * recency, 2)

        # V2: 按可信度排序 top experiences
        ranked = sorted(exps, key=_credibility_score, reverse=True)
        top_exps = ranked[:5]

        for e in exps:
            cat = e.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            sev = e.get("severity", "normal")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            total_applied += e.get("applied_count", 0)
            avg_rating += e.get("rating_avg", 0)

        avg_rating = round(avg_rating / total, 2) if total > 0 else 0.0

        return {
            "success": True,
            "summary": {
                "total": total,
                "by_category": by_category,
                "by_severity": by_severity,
                "total_applied": total_applied,
                "avg_rating": avg_rating,
                "total_tags": len(index.get("experience_tags", [])),
                "top_experiences": [
                    {"id": e["id"], "title": e.get("title", ""), "rating": e.get("rating_avg", 0),
                     "credibility": _credibility_score(e)}
                    for e in top_exps
                ],
            },
        }


    async def search_experiences(self, kb_id: str, query: str, top_k: int = 10) -> dict:
        """元信息搜索经验: 在 title/problem/solution/tags/key_lessons 中匹配关键词（CJK 感知）。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        exps = index.get("experiences", [])
        # CJK 感知分词：中文做 N-gram 滑窗，避免整句当 1 个 token 导致全部落空
        tokens = self._tokenize_query(query)
        scored = []
        for exp in exps:
            score = 0
            title = exp.get("title", "").lower()
            problem = exp.get("problem", "").lower()
            solution = exp.get("solution", "").lower()
            scenario = exp.get("scenario", "").lower()
            tags_str = " ".join(exp.get("tags", [])).lower()
            lessons_str = " ".join(exp.get("key_lessons", [])).lower()
            for tok in tokens:
                # Title match = highest weight
                if tok in title:
                    score += 10
                # Scenario match
                if tok in scenario:
                    score += 8
                # Tag match
                if tok in tags_str:
                    score += 5
                # Problem/solution match
                if tok in problem:
                    score += 3
                if tok in solution:
                    score += 3
                # Key lessons match
                if tok in lessons_str:
                    score += 4
            if score > 0:
                # Boost by rating and applied_count
                score += exp.get("rating_avg", 0) * 0.5
                score += min(exp.get("applied_count", 0), 5)
                scored.append((score, exp))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [exp for _, exp in scored[:top_k]]
        return {"success": True, "count": len(results), "query": query, "experiences": results}

    async def vector_search_experiences(self, kb_id: str, query: str, top_k: int = 5) -> dict:
        """向量语义搜索经验: 在 KB 的向量集合中搜索，只返回 doc_type=experience 的结果。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        try:
            from app.services.vector_service import vector_service as _vs
            if not _vs.is_ready():
                return {"success": False, "error": "Vector service not ready (embedding model may be loading)"}
            # Search in the KB collection, then filter by doc_type
            # 用经验专属阈值(0.55,高于文档0.35),避免无关 query 错配聚焦短内容
            results = _vs.search(query, kb_path, top_k=top_k * 3,
                                 score_threshold=config.experience_score_threshold)
            exp_results = []
            for r in results:
                # Check if this chunk belongs to an experience (path contains /experience/)
                doc_path = r.get("doc_path", "")
                if "/experience/" in doc_path.replace("\\", "/") or "\\experience\\" in doc_path:
                    exp_results.append(r)
                    if len(exp_results) >= top_k:
                        break
            return {"success": True, "query": query, "count": len(exp_results), "results": exp_results}
        except Exception as e:
            logger.warning("Vector search experiences failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── 经验检索：QDCVR 向量+内容验证（与文档检索同流程）──────────────

    @staticmethod
    def _tokenize_query(query: str) -> list[str]:
        """查询分词：兼顾空格分隔（英文）和 CJK 连续文本（中文）。

        中文无空格，直接 split() 会把整句当成 1 个 token，子串匹配全部落空。
        对 CJK 部分做 **bigram (2-gram) 滑窗** —— 2字是中文最小有义单元，
        既覆盖"红烧/炒糖/糖色/炒焦"等真实词，又避免 3-4gram 噪声膨胀分母。
        英文按空格切分。
        """
        query = query.lower().strip()
        tokens: set[str] = set()
        for part in query.split():
            if not part:
                continue
            # 判断是否含 CJK 字符
            has_cjk = any('一' <= ch <= '鿿' for ch in part)
            if has_cjk:
                # CJK bigram 滑窗
                cjk_chars = [ch for ch in part if '一' <= ch <= '鿿' or ch.isalnum()]
                for i in range(len(cjk_chars) - 1):
                    gram = cjk_chars[i:i + 2]
                    if len(gram) == 2:
                        tokens.add("".join(gram))
                # 保留较长的英文/数字片段（如 "RAG", "DQN"）
                ascii_parts = [w for w in part.replace('/', ' ').split() if w and any(c.isascii() and c.isalnum() for c in w)]
                tokens.update(ascii_parts)
            else:
                tokens.add(part)
        return list(tokens)

    @staticmethod
    def _detect_query_type(query: str) -> str:
        """Detect query intent type from keywords. Returns troubleshooting/decision/best_practice/learning."""
        ql = query.lower()
        troubleshoot_kw = ["怎么", "如何", "故障", "报错", "失败", "修复", "排查", "解决",
                           "how to", "fix", "error", "fail", "troubleshoot", "debug", "bug",
                           "不工作", "出问题", "异常", "crash", "timeout"]
        decision_kw = ["选", "对比", "选择", "推荐", "哪个好", "评估", "which", "compare",
                       "recommend", "best option", "方案对比", "优缺点"]
        best_practice_kw = ["最佳实践", "经验", "practice", "pattern", "规范", "标准流程",
                            "best way", "推荐做法", "标准做法"]

        if any(kw in ql for kw in troubleshoot_kw):
            return "troubleshooting"
        if any(kw in ql for kw in decision_kw):
            return "decision"
        if any(kw in ql for kw in best_practice_kw):
            return "best_practice"
        return "learning"

    def _content_verify(self, query: str, exp: dict, vector_score: float) -> tuple[bool, int, str]:
        """内容验证：读经验正文(problem/solution/key_lessons/tags)，独立打分(0-8)。

        向量分只能定候选；内容分定去留。内容分 > 向量分。
        返回 (relevant, content_score, reason)。
        """
        tokens = self._tokenize_query(query)
        if not tokens:
            return False, 0, "empty_query"

        # 聚合可检索文本
        title = exp.get("title", "")
        problem = exp.get("problem", "")
        solution = exp.get("solution", "")
        scenario = exp.get("scenario", "")
        tags_str = " ".join(exp.get("tags", []))
        lessons_str = " ".join(exp.get("key_lessons", []))
        full_text = f"{title} {scenario} {problem} {solution} {tags_str} {lessons_str}".lower()

        # ── 防误报护栏: query 主体词覆盖率 ──
        # CJK(中文bigram)阈值25%, ASCII(英文单词)阈值50%
        # 防"quantum computing error"因"error"偶然命中而误关联
        meaningful_tokens = [t for t in tokens if len(t) >= 2]
        if meaningful_tokens:
            meaningful_matched = sum(1 for t in meaningful_tokens if t in full_text)
            meaningful_cov = meaningful_matched / len(meaningful_tokens)
            # 判断查询类型
            has_cjk = any('一' <= ch <= '鿿' for ch in query)
            threshold_mc = 0.25 if has_cjk else 0.50
            if meaningful_cov < threshold_mc:
                return False, 0, f"meaningful_coverage={meaningful_cov:.0%} < {threshold_mc:.0%}"

        # 维度1: 主题相关 (0-3) — query 关键词在全文的覆盖率
        matched = sum(1 for tok in tokens if tok in full_text)
        coverage = matched / len(tokens) if tokens else 0
        if coverage >= 0.6:
            topic_score = 3
        elif coverage >= 0.35:
            topic_score = 2
        elif coverage >= 0.15:
            topic_score = 1
        else:
            topic_score = 0

        # 维度2: 场景/问题匹配 (0-3) — 是否命中 problem/scenario（经验的核心）
        problem_text = f"{scenario} {problem}".lower()
        prob_matched = sum(1 for tok in tokens if tok in problem_text)
        prob_coverage = prob_matched / len(tokens) if tokens else 0
        if prob_coverage >= 0.4:
            scenario_score = 3
        elif prob_coverage >= 0.2:
            scenario_score = 2
        elif prob_coverage >= 0.1:
            scenario_score = 1
        else:
            scenario_score = 0

        # 维度3: 方案证据 (0-2) — solution 是否含可操作的实质内容且命中
        solution_text = f"{solution} {lessons_str}".lower()
        sol_matched = sum(1 for tok in tokens if tok in solution_text)
        sol_coverage = sol_matched / len(tokens) if tokens else 0
        if sol_coverage >= 0.3 and len(solution) >= 50:
            evidence_score = 2
        elif sol_coverage >= 0.15:
            evidence_score = 1
        else:
            evidence_score = 0

        content_score = topic_score + scenario_score + evidence_score

        # ── 反例检测: domain mismatch penalty ──
        has_mismatch, delta_penalty, delta_reason = self._semantic_verify_delta(query, exp)
        reason_parts = []
        if has_mismatch:
            content_score = max(1, int(content_score * delta_penalty))
            reason_parts.append(f"delta:{delta_reason}")

        if delta_penalty < 0.5:
            # Severe domain mismatch — force discard regardless of content_score
            relevant = False
            reason = f"content_score={content_score} [domain_mismatch_penalty={delta_penalty}]"
        else:
            # 内容分低但向量分高 → 可能是向量"看起来像"但实际无关 → 判负
            relevant = content_score >= 3
            if relevant:
                reason = f"content_score={content_score} (coverage={coverage:.0%}, prob={prob_coverage:.0%})"
            else:
                reason = f"content_score={content_score} < 3 (coverage={coverage:.0%})"

        if reason_parts:
            reason += " [" + " ".join(reason_parts) + "]"

        return relevant, content_score, reason

    @staticmethod
    def _semantic_verify_delta(query: str, exp: dict) -> tuple:
        """Semantic delta detection: identify domain mismatch between query and experience.

        Computes domain-term overlap and applies penalty for significant mismatch.
        Returns (has_mismatch: bool, penalty: float, reason: str).
        penalty is a float 0.0-1.0 (multiplier on content_score).
        """
        # Extract domain terms from query
        query_terms = ExperienceService._extract_domain_terms(query)
        # Extract domain terms from experience
        exp_title = exp.get("title", "")
        exp_scenario = exp.get("scenario", "")
        exp_tags = " ".join(exp.get("tags", []))
        exp_text = f"{exp_title} {exp_scenario} {exp_tags}"
        exp_terms = ExperienceService._extract_domain_terms(exp_text)

        if not query_terms:
            return False, 1.0, "empty_query_terms"

        # Compute intersection and difference
        query_set = set(query_terms)
        exp_set = set(exp_terms)
        intersection = query_set & exp_set
        diff = exp_set - query_set

        # Ratio of unmatched experience domain terms
        diff_ratio = len(diff) / max(len(exp_set), 1)
        overlap_ratio = len(intersection) / max(len(query_set), 1)

        # Decision logic
        if overlap_ratio >= 0.5:
            # Strong domain overlap - no penalty
            return False, 1.0, f"strong_domain_overlap={overlap_ratio:.0%}"
        elif diff_ratio > 0.5 and overlap_ratio < 0.3:
            # Significant domain mismatch - heavy penalty
            return True, 0.5, f"domain_mismatch(diff={diff_ratio:.0%},overlap={overlap_ratio:.0%})"
        elif diff_ratio > 0.3 and overlap_ratio < 0.4:
            # Moderate mismatch
            return True, 0.75, f"partial_mismatch(diff={diff_ratio:.0%},overlap={overlap_ratio:.0%})"
        else:
            return False, 0.9, f"acceptable(overlap={overlap_ratio:.0%})"

    @staticmethod
    def _extract_domain_terms(text: str) -> list[str]:
        """Extract domain-specific noun terms from text. Filters out stop words."""
        text = text.lower().strip()
        if not text:
            return []

        STOP_WORDS = {
            "the", "and", "for", "this", "that", "with", "from", "have", "has",
            "was", "are", "were", "been", "its", "his", "her", "their",
            "about", "into", "each", "some", "any", "not", "but", "can",
            "all", "will", "just", "also", "very", "than", "then", "more",
            "only", "over", "such", "when", "what", "which", "where", "who",
            "how", "use", "using", "used", "make", "made", "get", "got",
            "的", "了", "是", "在", "和", "有", "也", "都", "就", "这",
            "那", "要", "会", "可以", "一个", "这个", "那个", "什么",
            "怎么", "如何", "为什么", "因为", "所以", "如果", "虽然",
            "但是", "然后", "之后", "之前", "上面", "下面", "里面",
            "问题", "方法", "方案", "结果", "结论", "经验", "教训",
        }

        tokens = []
        # English words >= 3 chars
        english_words = re.findall(r'[a-z][a-z0-9]{2,}', text)
        for w in english_words:
            if w not in STOP_WORDS:
                tokens.append(w)

        # CJK bigrams
        cjk_chars = [ch for ch in text if '一' <= ch <= '鿿']
        for i in range(len(cjk_chars) - 1):
            gram = "".join(cjk_chars[i:i+2])
            if gram not in STOP_WORDS:
                tokens.append(gram)

        return list(set(tokens))

    @staticmethod
    def _tier_experience(vector_score: float, content_score: int,
                          rating: float, applied: int, review_count: int) -> tuple[str, str]:
        """可信度定级（与 experience skill E5 模型对齐）。

        P0 Strong:   vector≥0.65 ∧ content≥6 ∧ rating≥4
        P1 Reference: vector≥0.45 ∧ content≥4
        P2 Weak:     vector≥0.35 ∧ content≥3 （默认抑制）
        Discard:     其他
        返回 (tier, reason)。
        """
        # 衰减修正：低评分/未评审压低层级
        credibility_mod = ""
        if review_count >= 3 and rating < 2.0:
            credibility_mod = " [disputed→max P2]"
        elif review_count == 0 and applied == 0:
            credibility_mod = " [unvetted→max P1]"

        if vector_score >= 0.65 and content_score >= 6 and rating >= 4 and review_count >= 1:
            return "P0", f"vector={vector_score:.2f} content={content_score} rating={rating}" + credibility_mod
        if vector_score >= 0.45 and content_score >= 4:
            # unvetted 经验最高 P1
            if credibility_mod and "disputed" in credibility_mod:
                return "P2", f"disputed downgraded (vector={vector_score:.2f} content={content_score})"
            return "P1", f"vector={vector_score:.2f} content={content_score} rating={rating}" + credibility_mod
        if vector_score >= 0.35 and content_score >= 3:
            return "P2", f"weak (vector={vector_score:.2f} content={content_score})" + credibility_mod
        return "DISCARD", f"vector={vector_score:.2f} content={content_score} below threshold"

    async def search_experiences_global(self, query: str, top_k: int = 10,
                                         score_threshold: float | None = None,
                                         verify_content: bool = True) -> dict:
        """跨 KB 全局经验检索 — QDCVR 流程（与文档检索同构）。

        流程: 向量召回 → 硬阈值 → 经验级去重 → 内容验证 → 可信度定级 → 诚实空返回。
        向量负责"快"，内容负责"准"；无确认经验则诚实声明，不"不懂装懂"。

        Args:
            query: 自然语言查询（中英文均可）
            top_k: 返回上限（默认10）
            score_threshold: 向量硬阈值；None 用经验默认(0.45)
            verify_content: True=读正文内容验证（推荐）；False=仅向量分
        """
        query_clean = query.strip()
        if not query_clean:
            return {"success": True, "query": query, "count": 0, "experiences": [],
                    "message": "空查询"}

        tree = self._read_tree_fs()
        kb_paths = [f.get("path", "") for f in tree.get("folders", [])
                     if f.get("isKnowledgeBase") and f.get("path")]

        # ── Query type detection + adaptive threshold ──
        query_type = self._detect_query_type(query_clean)
        type_thresholds = {
            "troubleshooting": 0.55,
            "decision": 0.50,
            "best_practice": 0.45,
            "learning": 0.35,
        }
        effective_threshold = score_threshold if score_threshold is not None else type_thresholds.get(query_type, 0.45)

        # ── Step 1+2: 向量召回 + 硬阈值（跨所有 KB 的经验 collection）──
        vector_hits: dict[str, dict] = {}  # exp_path → best hit
        try:
            from app.services.vector_service import vector_service as _vs
            vector_available = _vs.is_ready()
        except Exception:
            vector_available = False

        # Multi-round vector search with adaptive threshold degradation
        rounds = 0
        degraded = False
        if vector_available:
            while True:
                rounds += 1
                for kb_path in kb_paths:
                    try:
                        vr = await self.vector_search_experiences(kb_path, query_clean, top_k=15)
                        if not vr.get("success"):
                            continue
                        for r in vr.get("results", []):
                            score = r.get("score", 0)
                            if score < effective_threshold:
                                continue  # 硬阈值过滤
                            doc_path = _normalize_path(r.get("doc_path", ""))
                            # 经验级去重：同一经验取最高分 chunk
                            if doc_path not in vector_hits or score > vector_hits[doc_path]["score"]:
                                vector_hits[doc_path] = {
                                    "score": score,
                                    "content": r.get("content", ""),
                                    "kb_path": kb_path,
                                    "chunk_index": r.get("chunk_index", 0),
                                    "_from_keyword": False,
                                }
                    except Exception as e:
                        logger.warning("Vector experience search failed in %s: %s", kb_path, e)

                if vector_hits:
                    break

                # Round 2 fallback: lower threshold by 30%
                if rounds == 1 and effective_threshold > 0.25:
                    degraded = True
                    effective_threshold = max(effective_threshold * 0.7, 0.25)
                    continue

                # Round 3 fallback: lower threshold further, skip content verification
                if rounds == 2 and effective_threshold > 0.20:
                    effective_threshold = max(effective_threshold * 0.6, 0.15)
                    verify_content = False
                    continue

                break  # No more rounds to try

        # ── Step 1b (互补召回): 关键词元信息搜索 ──
        # 向量可能未覆盖未索引的经验；关键词路径作为互补，补充向量召回的盲点。
        # 不替换向量命中，只补充。仍走后续内容验证 + 硬阈值，不"不懂装懂"。
        keyword_recall_count = 0
        for kb_path in kb_paths:
            index = self._read_index(kb_path)
            for exp in index.get("experiences", []):
                exp_path = _normalize_path(
                    f"{kb_path}/{_EXP_DIRNAME}/{exp.get('id', '')}.md")
                if exp_path in vector_hits:
                    continue  # 向量已命中，不覆盖
                tokens = self._tokenize_query(query_clean)
                if not tokens:
                    continue
                full_text = f"{exp.get('title','')} {exp.get('problem','')} {exp.get('solution','')} {exp.get('scenario','')} {' '.join(exp.get('tags',[]))} {' '.join(exp.get('key_lessons',[]))}".lower()
                matched = sum(1 for t in tokens if t in full_text)
                if matched == 0:
                    continue  # 关键词完全无命中 → 不是候选
                # 关键词匹配分作为 score 的近似（0-1 归一）
                # 基础分 0.42 + 每个命中 token +0.06，封顶 0.72（略低于强向量命中）
                coverage = matched / len(tokens) if tokens else 0
                approx_score = min(0.42 + matched * 0.06 + coverage * 0.15, 0.72)
                if approx_score >= effective_threshold:
                    vector_hits[exp_path] = {
                        "score": approx_score,
                        "content": exp.get("solution", "")[:500],
                        "kb_path": kb_path,
                        "chunk_index": 0,
                        "_from_keyword": True,
                    }
                    keyword_recall_count += 1

        if not vector_hits:
            return {"success": True, "query": query, "count": 0, "experiences": [],
                    "vector_recall": 0, "keyword_recall": 0,
                    "message": f"向量+关键词召回均为空（阈值={effective_threshold}）— 无语义相关经验，不编造",
                    "query_type": query_type, "rounds": rounds, "degraded": degraded,
                    "threshold": effective_threshold}

        # ── Step 3: 加载经验元数据 + Step 4 内容验证 ──
        # 构建 exp_path → exp_meta 索引（一次读取）
        exp_meta_by_path: dict[str, dict] = {}
        for kb_path in kb_paths:
            index = self._read_index(kb_path)
            for exp in index.get("experiences", []):
                ep = _normalize_path(f"{kb_path}/{_EXP_DIRNAME}/{exp.get('id', '')}.md")
                exp["kb_path"] = kb_path
                exp_meta_by_path[ep] = exp

        scored_results = []
        for exp_path, hit in vector_hits.items():
            exp = exp_meta_by_path.get(exp_path, {})
            if not exp:
                # 向量命中但元数据丢失 → 跳过（可能是孤儿索引）
                continue

            vector_score = hit["score"]
            from_keyword = hit.get("_from_keyword", False)
            if verify_content:
                relevant, content_score, reason = self._content_verify(
                    query_clean, exp, vector_score)
                if not relevant:
                    # 内容分 < 3 → 向量"看起来像"但实际无关 → 丢弃
                    continue
            else:
                # verify_content=False：用 vector_score 推断 content_score 伪值
                # 关键词命中 + 高匹配 → 内容分至少 4（可 P1）；向量高分 → 4
                if from_keyword:
                    content_score = 4 if vector_score >= 0.55 else 3
                else:
                    content_score = 4 if vector_score >= 0.55 else 3
                relevant = True

            # ── Step 5: 可信度定级 ──
            rating = exp.get("rating_avg", 0)
            applied = exp.get("applied_count", 0)
            review_count = exp.get("review_count", 0)
            tier, tier_reason = self._tier_experience(
                vector_score, content_score, rating, applied, review_count)

            if tier == "DISCARD":
                continue

            scored_results.append({
                "id": exp.get("id", ""),
                "title": exp.get("title", ""),
                "scenario": exp.get("scenario", ""),
                "category": exp.get("category", ""),
                "problem": exp.get("problem", ""),
                "solution": exp.get("solution", ""),
                "key_lessons": exp.get("key_lessons", []),
                "tags": exp.get("tags", []),
                "severity": exp.get("severity", "normal"),
                "kb_path": hit["kb_path"],
                "related_docs": exp.get("related_docs", []),
                "rating_avg": rating,
                "applied_count": applied,
                "review_count": review_count,
                # 检索质量元信息（透明化为什么这条经验入选）
                "vector_score": round(vector_score, 3),
                "content_score": content_score,
                "tier": tier,
                "tier_reason": tier_reason,
                "content_preview": hit["content"][:200],
            })

        # ── 排序：tier 优先 → content_score → vector_score → rating ──
        tier_order = {"P0": 0, "P1": 1, "P2": 2}
        scored_results.sort(key=lambda x: (
            tier_order.get(x["tier"], 9),
            -(x["content_score"]),
            -(x["vector_score"]),
            -(x["rating_avg"]),
        ))

        # ── P2 默认抑制：只在 P0/P1 不足时展示 ──
        p0_p1 = [r for r in scored_results if r["tier"] in ("P0", "P1")]
        p2 = [r for r in scored_results if r["tier"] == "P2"]
        if len(p0_p1) >= top_k:
            final = p0_p1[:top_k]
        else:
            # P0/P1 不足，补 P2 但标注"弱参考"
            remaining = top_k - len(p0_p1)
            final = p0_p1 + p2[:remaining]

        # ── Step 6: 诚实空返回 ──
        if not final:
            return {
                "success": True, "query": query, "count": 0, "experiences": [],
                "vector_recall": len([h for h in vector_hits.values() if not h.get("_from_keyword")]),
                "keyword_recall": len([h for h in vector_hits.values() if h.get("_from_keyword")]),
                "message": f"召回{len(vector_hits)}条但内容验证全部不过——无确认经验，不编造",
                "tier_counts": {"P0": 0, "P1": 0, "P2": 0, "discarded": len(vector_hits)},
                "query_type": query_type, "rounds": rounds, "degraded": degraded,
            }

        tier_counts = {"P0": 0, "P1": 0, "P2": 0, "discarded": 0}
        for r in scored_results:
            if r["tier"] in tier_counts:
                tier_counts[r["tier"]] += 1
        tier_counts["discarded"] = len(vector_hits) - len(scored_results)

        vec_count = len([h for h in vector_hits.values() if not h.get("_from_keyword")])
        kw_count = len([h for h in vector_hits.values() if h.get("_from_keyword")])

        return {
            "success": True, "query": query, "count": len(final),
            "experiences": final,
            "vector_recall": vec_count,
            "keyword_recall": kw_count,
            "tier_counts": tier_counts,
            "threshold": effective_threshold,
            "query_type": query_type,
            "rounds": rounds,
            "degraded": degraded,
            "message": f"向量{vec_count}+关键词{kw_count}召回 → 内容验证通过{len(scored_results)} → 返回{len(final)} (P0:{tier_counts['P0']} P1:{tier_counts['P1']} P2:{tier_counts['P2']})",
        }


    # ── E0/E1: 经验提取（启发式 + 任务包，不调 LLM）──────────────

    def _heuristic_extract_from_doc(self, doc_path: str, content: str) -> list:
        """从单篇文档启发式提取候选经验（规则，非 LLM）。"""
        lines = content.split("\n")
        doc_title = ""
        for line in lines[:10]:
            if line.startswith("# "):
                doc_title = line[2:].strip()
                break
        if not doc_title:
            doc_title = doc_path.split("/")[-1].replace(".md", "")

        sections = []
        current = {"title": "", "lines": []}
        for line in lines:
            if line.startswith("## "):
                if current["title"]:
                    sections.append(current)
                current = {"title": line[3:].strip(), "lines": []}
            else:
                current["lines"].append(line)
        if current["title"]:
            sections.append(current)

        problem_kw = ["问题", "problem", "issue", "challenge", "故障", "挑战", "动机", "motivation", "局限", "limitation", "痛点"]
        solution_kw = ["方案", "solution", "method", "approach", "方法", "提出", "propose", "采用", "设计"]
        lesson_kw = ["教训", "lesson", "结论", "conclusion", "贡献", "contribution", "发现", "finding", "关键", "result", "结果", "实验"]

        def _match(section, keywords):
            text = (section["title"] + " " + " ".join(section["lines"])).lower()
            return any(kw.lower() in text for kw in keywords)

        candidates = []
        first_500 = content[:500].replace("\n", " ").strip()
        candidates.append({
            "title": f"{doc_title} - 核心要点",
            "scenario": (doc_title.lower().replace(" ", "-"))[:50],
            "category": "best_practice",
            "problem": f"文档《{doc_title}》研究的核心问题" + (": " + first_500[:200] if first_500 else ""),
            "solution": (first_500[:300] if first_500 else "见原文"),
            "result": "success",
            "key_lessons": [s["title"] for s in sections[:5] if s["title"]],
            "tags": [],
            "severity": "normal",
            "related_docs": [doc_path],
            "source_doc": doc_path,
            "confidence": 0.6,
            "extraction_method": "document_overview",
        })

        problem_sections = [s for s in sections if _match(s, problem_kw)]
        solution_sections = [s for s in sections if _match(s, solution_kw)]
        lesson_sections = [s for s in sections if _match(s, lesson_kw)]
        if problem_sections and solution_sections:
            prob = problem_sections[0]
            sol = solution_sections[0]
            prob_text = " ".join(prob["lines"]).strip()[:400]
            sol_text = " ".join(sol["lines"]).strip()[:400]
            lessons = [s["title"] for s in lesson_sections[:3]]
            candidates.append({
                "title": f"{doc_title} - {prob['title']}",
                "scenario": f"{doc_title.lower().replace(' ', '-')[:30]}-{prob['title'].lower().replace(' ', '-')[:20]}",
                "category": "lesson_learned",
                "problem": prob_text or prob["title"],
                "solution": sol_text or sol["title"],
                "result": "success",
                "key_lessons": lessons or [f"参见 {sol['title']}"],
                "tags": [],
                "severity": "important",
                "related_docs": [doc_path],
                "source_doc": doc_path,
                "confidence": 0.75,
                "extraction_method": "section_match",
            })
        return candidates

    async def prepare_extraction(self, kb_id: str, doc_paths: list = None) -> dict:
        """E0: 准备经验提取任务包。读文档全文 + 去重上下文 + 提取模板。
        不调 LLM。返回供 Agent LLM 提炼的任务包。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        tree = self._read_tree_fs()
        if not doc_paths:
            doc_paths = []
            kb_norm = _normalize_path(kb_path)
            for f in tree.get("files", []):
                fp = _normalize_path(f.get("path", ""))
                if fp.startswith(kb_norm + "/") and fp.endswith(".md") and "/experience/" not in fp:
                    doc_paths.append(fp)
        docs_content = []
        for dp in doc_paths[:20]:
            full = self.storage_root / _normalize_path(dp)
            if full.exists():
                try:
                    content = full.read_text(encoding="utf-8")
                    docs_content.append({"path": dp, "content": content[:8000], "full_length": len(content)})
                except Exception:
                    pass
        index = self._read_index(kb_path)
        existing_scenarios = [e.get("scenario", "") for e in index.get("experiences", [])]
        return {
            "success": True, "kb_id": kb_id, "kb_path": kb_path,
            "docs_to_extract": len(docs_content), "documents": docs_content,
            "existing_scenarios": existing_scenarios,
            "extraction_template": {
                "title": "简洁经验标题（非文档标题）",
                "scenario": "场景标识 kebab-case，如 llm-hallucination-mitigation",
                "category": "best_practice|troubleshooting|lesson_learned|optimization|tip|workflow|decision",
                "problem": "具体问题（≥50字）",
                "solution": "具体方案/方法（≥50字）",
                "key_lessons": ["可操作的教训1", "教训2"],
                "tags": ["领域词", "方法词"],
                "severity": "critical|important|normal|tip",
                "related_docs": ["本文档路径"],
                "supporting_evidence": "原文具体段落引用",
            },
            "hint": "Agent 用 LLM 根据 documents 按 extraction_template 提炼，去重 existing_scenarios。",
        }

    async def heuristic_extract(self, kb_id: str, doc_paths: list = None, dry_run: bool = True) -> dict:
        """E1: 启发式提取候选经验（规则，不调 LLM）。
        dry_run=True 只返回候选；False 写入草稿池。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        task = await self.prepare_extraction(kb_id, doc_paths)
        if not task.get("success"):
            return task
        all_candidates = []
        for doc in task["documents"]:
            all_candidates.extend(self._heuristic_extract_from_doc(doc["path"], doc["content"]))
        existing = set(task["existing_scenarios"])
        new_candidates = [c for c in all_candidates if c.get("scenario", "") not in existing]
        if dry_run:
            return {"success": True, "kb_id": kb_id, "dry_run": True,
                    "total_candidates": len(new_candidates), "candidates": new_candidates,
                    "hint": "确认后 dry_run=False 写草稿池，或交 Agent LLM 精炼。"}
        drafts_created = []
        for cand in new_candidates:
            r = await self.save_draft(kb_id, cand)
            if r.get("success"):
                drafts_created.append(r["draft_id"])
        return {"success": True, "kb_id": kb_id, "dry_run": False,
                "drafts_created": len(drafts_created), "draft_ids": drafts_created}

    # ── E3: 草稿池 ────────────────────────────────────────────

    def _draft_dir(self, kb_path: str) -> Path:
        return self._exp_dir(kb_path) / "draft"

    def _draft_path(self, kb_path: str, draft_id: str) -> Path:
        return self._draft_dir(kb_path) / f"{draft_id}.json"

    async def save_draft(self, kb_id: str, draft_data: dict) -> dict:
        """保存候选经验到草稿池。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        await self.init_experience_folder(kb_path)
        draft_id = f"draft-{uuid.uuid4().hex[:12]}"
        draft = {"id": draft_id, **draft_data, "status": "draft",
                 "created_at": datetime.now(timezone.utc).isoformat()}
        dpath = self._draft_path(kb_path, draft_id)
        dpath.parent.mkdir(parents=True, exist_ok=True)
        dpath.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "draft_id": draft_id, "draft": draft}

    async def list_drafts(self, kb_id: str) -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        ddir = self._draft_dir(kb_path)
        drafts = []
        if ddir.exists():
            for f in sorted(ddir.glob("draft-*.json")):
                try:
                    drafts.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        return {"success": True, "kb_id": kb_id, "count": len(drafts), "drafts": drafts}

    async def read_draft(self, kb_id: str, draft_id: str) -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        dpath = self._draft_path(kb_path, draft_id)
        if not dpath.exists():
            return {"success": False, "error": f"Draft not found: {draft_id}"}
        return {"success": True, "draft": json.loads(dpath.read_text(encoding="utf-8"))}

    async def approve_draft(self, kb_id: str, draft_id: str, edits: dict = None) -> dict:
        """批准草稿→正式经验。edits 可覆盖字段。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        dpath = self._draft_path(kb_path, draft_id)
        if not dpath.exists():
            return {"success": False, "error": f"Draft not found: {draft_id}"}
        draft = json.loads(dpath.read_text(encoding="utf-8"))
        if edits:
            draft.update(edits)
        create_data = ExperienceCreate(
            title=draft.get("title", ""), scenario=draft.get("scenario", ""),
            category=draft.get("category", "tip"), problem=draft.get("problem", ""),
            solution=draft.get("solution", ""), result=draft.get("result", "success"),
            key_lessons=draft.get("key_lessons", []), tags=draft.get("tags", []),
            severity=draft.get("severity", "normal"), related_docs=draft.get("related_docs", []),
            prerequisites=draft.get("prerequisites", []), metrics=draft.get("metrics", {}),
        )
        r = await self.create_experience(kb_id, create_data)
        if r.get("success"):
            exp = r.get("experience", {})
            exp["auto_extracted"] = True
            exp["extraction_method"] = draft.get("extraction_method", "heuristic")
            dpath.unlink()
            return {"success": True, "approved": True, "experience": exp, "exp_id": exp.get("id")}
        return r

    async def reject_draft(self, kb_id: str, draft_id: str, reason: str = "") -> dict:
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        dpath = self._draft_path(kb_path, draft_id)
        if not dpath.exists():
            return {"success": False, "error": f"Draft not found: {draft_id}"}
        rejected_dir = self._exp_dir(kb_path) / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)
        draft = json.loads(dpath.read_text(encoding="utf-8"))
        draft["rejected_reason"] = reason
        draft["rejected_at"] = datetime.now(timezone.utc).isoformat()
        (rejected_dir / f"{draft_id}.json").write_text(
            json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
        dpath.unlink()
        return {"success": True, "rejected": draft_id}

    # ── E6: 联动 / stale 检测 ─────────────────────────────────

    async def check_stale(self, kb_id: str) -> dict:
        """检查 KB 内经验的 related_docs 一致性。文档更新晚于经验→stale；不存在→orphan。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        stale_list, orphan_list, ok_count = [], [], 0
        for exp in index.get("experiences", []):
            exp_updated = exp.get("updated_at", exp.get("created_at", ""))
            exp_time = 0
            try:
                exp_time = datetime.fromisoformat(exp_updated).timestamp() if exp_updated else 0
            except Exception:
                pass
            related = exp.get("related_docs", [])
            if not related:
                ok_count += 1
                continue
            is_stale = False
            is_orphan = False
            for doc in related:
                doc_full = self.storage_root / _normalize_path(doc)
                if not doc_full.exists():
                    is_orphan = True
                    break
                try:
                    if doc_full.stat().st_mtime > exp_time and exp_time > 0:
                        is_stale = True
                except Exception:
                    pass
            if is_orphan:
                exp["stale_status"] = "orphan"
                orphan_list.append({"exp_id": exp["id"], "title": exp.get("title", ""), "missing_docs": related})
            elif is_stale:
                exp["stale_status"] = "stale"
                stale_list.append({"exp_id": exp["id"], "title": exp.get("title", ""),
                                   "updated_at": exp_updated, "related_docs": related})
            else:
                exp.pop("stale_status", None)
                ok_count += 1
        self._write_index(kb_path, index)
        return {"success": True, "kb_id": kb_id,
                "total": len(index.get("experiences", [])),
                "fresh": ok_count, "stale": len(stale_list), "orphan": len(orphan_list),
                "stale_experiences": stale_list, "orphan_experiences": orphan_list}

    async def check_stale_global(self) -> dict:
        tree = self._read_tree_fs()
        all_stale, all_orphan, total = [], [], 0
        for folder in tree.get("folders", []):
            if not folder.get("isKnowledgeBase"):
                continue
            kb_path = folder.get("path", "")
            if not kb_path:
                continue
            r = await self.check_stale(kb_path)
            if r.get("success"):
                total += r["total"]
                all_stale.extend(r.get("stale_experiences", []))
                all_orphan.extend(r.get("orphan_experiences", []))
        return {"success": True, "total_experiences": total,
                "stale": len(all_stale), "orphan": len(all_orphan),
                "stale_experiences": all_stale, "orphan_experiences": all_orphan}

    async def sync_experience(self, kb_id: str, exp_id: str) -> dict:
        """标记单条经验需重新提取。实际重新提取由 Agent E0 完成。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        for exp in index.get("experiences", []):
            if exp["id"] == exp_id:
                exp["needs_sync"] = True
                exp["sync_requested_at"] = datetime.now(timezone.utc).isoformat()
                self._write_index(kb_path, index)
                return {"success": True, "exp_id": exp_id,
                        "hint": "已标记 needs_sync。Agent 读 related_docs 重新提取后 update_experience。"}
        return {"success": False, "error": f"Experience not found: {exp_id}"}

    async def sync_kb(self, kb_id: str) -> dict:
        """整库标记同步。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        stale = await self.check_stale(kb_id)
        marked = 0
        if stale.get("success"):
            index = self._read_index(kb_path)
            now = datetime.now(timezone.utc).isoformat()
            for exp in index.get("experiences", []):
                if exp.get("stale_status") in ("stale", "orphan"):
                    exp["needs_sync"] = True
                    exp["sync_requested_at"] = now
                    marked += 1
            self._write_index(kb_path, index)
        return {"success": True, "kb_id": kb_id, "marked_for_sync": marked,
                "hint": f"{marked} 条经验已标记需同步。"}

    # ── E8/E11: 看板 / 衰减 ───────────────────────────────────

    async def dashboard(self, kb_id: str) -> dict:
        """经验看板：聚合统计。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        summary = await self.experience_summary(kb_id)
        stale = await self.check_stale(kb_id)
        drafts = await self.list_drafts(kb_id)
        index = self._read_index(kb_path)
        exps = index.get("experiences", [])

        def _cred(e):
            r = e.get("rating_avg", 0); rc = e.get("review_count", 0); ac = e.get("applied_count", 0)
            if rc >= 3 and r >= 4:
                return "P0"
            elif r >= 3 or ac >= 1:
                return "P1"
            return "P2"
        tier_counts = {"P0": 0, "P1": 0, "P2": 0}
        for e in exps:
            tier_counts[_cred(e)] += 1
        return {"success": True, "kb_id": kb_id, "total_experiences": len(exps),
                "by_tier": tier_counts, "summary": summary.get("summary", {}),
                "drafts_pending": drafts.get("count", 0),
                "stale": stale.get("stale", 0), "orphan": stale.get("orphan", 0),
                "needs_sync": sum(1 for e in exps if e.get("needs_sync"))}

    async def apply_decay(self, kb_id: str) -> dict:
        """应用衰减规则：stale_unverified/disputed/unvetted 标记。"""
        kb_path = self._resolve_kb_path(kb_id)
        if not kb_path:
            return {"success": False, "error": f"KB not found: {kb_id}"}
        index = self._read_index(kb_path)
        now = datetime.now(timezone.utc)
        decayed = {"stale_unverified": 0, "disputed": 0, "unvetted": 0}
        for exp in index.get("experiences", []):
            try:
                created = datetime.fromisoformat(exp.get("created_at", now.isoformat()))
            except Exception:
                created = now
            age_days = (now - created).days
            rating = exp.get("rating_avg", 0)
            review_count = exp.get("review_count", 0)
            applied = exp.get("applied_count", 0)
            if age_days > 30 and applied == 0:
                exp["decay_flag"] = "stale_unverified"; decayed["stale_unverified"] += 1
            elif review_count >= 3 and rating < 2.0:
                exp["decay_flag"] = "disputed"; decayed["disputed"] += 1
            elif review_count == 0 and applied == 0:
                exp["decay_flag"] = "unvetted"; decayed["unvetted"] += 1
            else:
                exp.pop("decay_flag", None)
        self._write_index(kb_path, index)
        return {"success": True, "kb_id": kb_id, "decayed": decayed,
                "total_flagged": sum(decayed.values())}


experience_service = ExperienceService()
