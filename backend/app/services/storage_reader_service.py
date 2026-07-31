"""存储读取服务：让后端能读取 web 端的 .tree-fs.json 和 .knowledge-base.yml。

这是关键模块：后端需要读文档内容才能构建向量索引。
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import yaml

from app.utils.paths import get_storage_root
from app.utils.atomic_io import atomic_write_text
from app.utils.file_lock import file_lock, yaml_lock_path

logger = logging.getLogger(__name__)

# Per-YAML-path write lock registry — prevents concurrent read-modify-write
# races when multiple threads index documents in the same KB.
# 跨进程互斥改用 file_lock（web 与 backend 两进程共享同一 YAML 文件，
# 线程锁无法阻止跨进程读改写竞争 —— 并发 create + 自动索引写回曾丢失文档条目）。
_yaml_locks_guard = threading.Lock()
_yaml_locks: dict[str, threading.Lock] = {}


def _yaml_lock(kb_path: str) -> threading.Lock:
    """Get (or create) a threading.Lock for a given KB path's YAML file."""
    with _yaml_locks_guard:
        lk = _yaml_locks.get(kb_path)
        if lk is None:
            lk = threading.Lock()
            _yaml_locks[kb_path] = lk
        return lk


def _yaml_file_lock(kb_path: str):
    """跨进程文件锁：与 web 端 withFileLock 同协议，锁住整个 read-modify-write。"""
    yml_path = Path(get_storage_root()) / kb_path / ".knowledge-base.yml"
    return file_lock(yaml_lock_path(yml_path))


class StorageReaderService:
    """读取 web 端 tree-file-system 存储。"""
    def __init__(self) -> None:
        # Instance-level mtime cache for read_tree_fs(): avoids re-reading +
        # re-parsing .tree-fs.json on every hot-path call (N+1 disk reads).
        self._tree_fs_cache: dict[str, Any] | None = None
        self._tree_fs_mtime: int | None = None
        self._cache_lock = threading.Lock()

    @property
    def root(self) -> Path:
        return get_storage_root()

    @property
    def tree_fs_path(self) -> Path:
        return self.root / ".tree-fs.json"

    def read_tree_fs(self) -> dict[str, Any]:
        path = self.tree_fs_path
        if not path.exists():
            # Invalidate cache when the source file disappears.
            with self._cache_lock:
                self._tree_fs_cache = None
                self._tree_fs_mtime = None
            return {"folders": [], "files": []}
        try:
            mtime = path.stat().st_mtime_ns
            with self._cache_lock:
                if (self._tree_fs_cache is not None
                        and self._tree_fs_mtime == mtime):
                    return self._tree_fs_cache
            data = json.loads(path.read_text(encoding="utf-8"))
            with self._cache_lock:
                self._tree_fs_cache = data
                self._tree_fs_mtime = mtime
            return data
        except Exception as e:
            logger.warning("Failed to read .tree-fs.json: %s", e)
            return {"folders": [], "files": []}

    def list_knowledge_bases(self) -> list[dict[str, Any]]:
        tree = self.read_tree_fs()
        return [{"kb_id": f.get("id", ""), "path": f.get("path", ""),
                  "name": f.get("name", ""), "description": f.get("description", ""),
                  "parent_id": f.get("parentId")}
                for f in tree.get("folders", []) if f.get("isKnowledgeBase")]

    def get_kb_parent(self, kb_id: str) -> str | None:
        """返回父 KB 的 kb_id（若无父则 None）。kb_id 可为 UUID 或 path。"""
        tree = self.read_tree_fs()
        for f in tree.get("folders", []):
            if f.get("isKnowledgeBase") and (f.get("id") == kb_id or f.get("path") == kb_id):
                parent_id = f.get("parentId")
                if not parent_id:
                    return None
                # 找父节点（必须是 KB）
                for p in tree.get("folders", []):
                    if p.get("id") == parent_id and p.get("isKnowledgeBase"):
                        return p.get("id")
                return None
        return None

    def list_sub_kbs(self, kb_id: str) -> list[dict[str, Any]]:
        """递归返回某 KB 的所有子孙 KB（含嵌套子 KB）。

        kb_id 可为 UUID 或 path。返回 [{kb_id, path, name, description, parent_id}]。
        用于分层图谱构建：父 KB 图谱包含所有子 KB 的文档实体。
        """
        tree = self.read_tree_fs()
        # 先找到这个 KB 的 folder id
        target_folder_id = None
        for f in tree.get("folders", []):
            if f.get("isKnowledgeBase") and (f.get("id") == kb_id or f.get("path") == kb_id):
                target_folder_id = f.get("id")
                break
        if not target_folder_id:
            return []
        # BFS 递归找所有子孙 KB
        result: list[dict[str, Any]] = []
        queue = [target_folder_id]
        visited: set[str] = set()
        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            for f in tree.get("folders", []):
                if (f.get("isKnowledgeBase") and f.get("parentId") == current_id
                        and f.get("id") not in visited):
                    result.append({
                        "kb_id": f.get("id", ""),
                        "path": f.get("path", ""),
                        "name": f.get("name", ""),
                        "description": f.get("description", ""),
                        "parent_id": f.get("parentId"),
                    })
                    queue.append(f.get("id"))
        return result

    def resolve_kb_ids_with_children(self, kb_id: str) -> list[str]:
        """Resolve a kb_id (UUID or path) to itself + all descendant kb_ids.

        For hierarchical/parent KBs this returns the parent UUID plus every
        child KB UUID, so search services can query all descendant collections
        instead of only the parent's (K1 fix: parent KBs with docs in child KBs).
        Non-hierarchical KBs return ``[kb_id]`` unchanged.
        """
        # Normalise kb_id to UUID form
        resolved_uuid = kb_id
        tree = self.read_tree_fs()
        for f in tree.get("folders", []):
            if f.get("isKnowledgeBase") and (f.get("id") == kb_id or f.get("path") == kb_id):
                resolved_uuid = f.get("id", kb_id)
                break
        result = [resolved_uuid]
        for skb in self.list_sub_kbs(kb_id):
            if skb.get("kb_id") and skb["kb_id"] not in result:
                result.append(skb["kb_id"])
        return result

    def resolve_kb_path_for_doc(self, doc_path: str, kb_id: str = "") -> str:
        """从文档路径解析其所属 KB 的 path（最长前缀匹配），兜底用 kb_id 匹配。

        子库文档的 YAML 写回必须落在子库自身的 .knowledge-base.yml；
        若调用方传入的是父库/根库的 kb_id，写回会因"文档不在该 YAML 中"
        而静默失败（auto-index 空操作缺陷的根因之一）。
        """
        norm_doc = (doc_path or "").replace("\\", "/").strip("/")
        if norm_doc:
            tree = self.read_tree_fs()
            best = ""
            for f in tree.get("folders", []):
                if not f.get("isKnowledgeBase"):
                    continue
                fp = (f.get("path") or "").replace("\\", "/").strip("/")
                if not fp:
                    continue
                if norm_doc == fp or norm_doc.startswith(fp + "/"):
                    if len(fp) > len(best):
                        best = fp
            if best:
                return best
        if kb_id:
            for kb in self.list_knowledge_bases():
                if kb["kb_id"] == kb_id or kb["path"] == kb_id:
                    return kb["path"]
        return ""

    def resolve_kb_uuid_for_path(self, kb_path: str) -> str:
        """KB path（含子库路径）→ KB UUID。解析失败返回空串。"""
        if not kb_path:
            return ""
        norm_target = kb_path.replace("\\", "/").strip("/").lower()
        tree = self.read_tree_fs()
        for f in tree.get("folders", []):
            if not f.get("isKnowledgeBase"):
                continue
            fp = (f.get("path") or "").replace("\\", "/").strip("/").lower()
            if fp == norm_target and f.get("id"):
                return f["id"]
        return ""

    def list_documents(self, kb_path: str) -> list[dict[str, Any]]:
        yml_path = self.root / kb_path / ".knowledge-base.yml"
        if not yml_path.exists():
            return []
        try:
            data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
            return data.get("documents", []) if data else []
        except Exception as e:
            logger.warning("Failed to read %s: %s", yml_path, e)
            return []

    def read_document_content(self, doc_path: str, max_chars: int = 50000) -> str:
        full_path = self.root / doc_path
        if not full_path.exists():
            return ""
        try:
            content = full_path.read_text(encoding="utf-8")
            return content[:max_chars] if max_chars > 0 else content
        except Exception as e:
            logger.warning("Failed to read %s: %s", full_path, e)
            return ""

    def get_document_metadata(self, kb_path: str, doc_path: str) -> dict[str, Any] | None:
        docs = self.list_documents(kb_path)
        norm = doc_path.replace("\\", "/")
        for d in docs:
            if d.get("path", "").replace("\\", "/") == norm:
                return d
        return None

    def find_document_by_id(self, doc_id: str) -> dict[str, Any] | None:
        """在所有 KB 的 .knowledge-base.yml 中按文档 ID (UUID) 查找文档。

        返回 {kb_path, doc} 或 None。
        """
        kbs = self.list_knowledge_bases()
        for kb in kbs:
            kb_path = kb["path"]
            docs = self.list_documents(kb_path)
            for d in docs:
                if d.get("id") == doc_id:
                    return {"kb_path": kb_path, "kb_id": kb["kb_id"], "doc": d}
        return None

    def update_document_vector_index(
        self,
        kb_path: str,
        doc_path: str,
        vector_index: dict[str, Any],
    ) -> bool:
        """更新 .knowledge-base.yml 中某文档的 vector_index 字段。"""
        yml_path = self.root / kb_path / ".knowledge-base.yml"
        if not yml_path.exists():
            logger.warning("YAML not found: %s", yml_path)
            return False
        with _yaml_file_lock(kb_path):
            try:
                data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
                if not data or "documents" not in data:
                    return False
                norm = doc_path.replace("\\", "/")
                for doc in data["documents"]:
                    if doc.get("path", "").replace("\\", "/") == norm:
                        doc["vector_index"] = vector_index
                        break
                else:
                    logger.warning("Document not found in YAML: %s", doc_path)
                    return False
                atomic_write_text(
                    yml_path,
                    yaml.dump(data, allow_unicode=True, sort_keys=False, indent=2),
                )
                return True
            except Exception as e:
                logger.error("Failed to update vector_index: %s", e)
                return False

    def update_document_graph_index(
        self,
        kb_path: str,
        doc_path: str,
        graph_index: dict[str, Any],
    ) -> bool:
        """更新 .knowledge-base.yml 中某文档的 graph_index 字段。

        与 ``update_document_vector_index`` 对称，用于闭环记录图谱索引元信息。
        传入空 dict 或 ``{"deleted": True}`` 可清除字段。
        """
        yml_path = self.root / kb_path / ".knowledge-base.yml"
        if not yml_path.exists():
            logger.warning("YAML not found: %s", yml_path)
            return False
        with _yaml_file_lock(kb_path):
            try:
                data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
                if not data or "documents" not in data:
                    return False
                norm = doc_path.replace("\\", "/")
                for doc in data["documents"]:
                    if doc.get("path", "").replace("\\", "/") == norm:
                        if graph_index and not graph_index.get("deleted"):
                            doc["graph_index"] = graph_index
                        elif "graph_index" in doc:
                            del doc["graph_index"]
                        break
                else:
                    logger.warning("Document not found in YAML: %s", doc_path)
                    return False
                atomic_write_text(
                    yml_path,
                    yaml.dump(data, allow_unicode=True, sort_keys=False, indent=2),
                )
                return True
            except Exception as e:
                logger.error("Failed to update graph_index: %s", e)
                return False


storage_reader = StorageReaderService()
