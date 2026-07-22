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

logger = logging.getLogger(__name__)

# Per-YAML-path write lock registry — prevents concurrent read-modify-write
# races when multiple threads index documents in the same KB.
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


class StorageReaderService:
    """读取 web 端 tree-file-system 存储。"""

    @property
    def root(self) -> Path:
        return get_storage_root()

    @property
    def tree_fs_path(self) -> Path:
        return self.root / ".tree-fs.json"

    def read_tree_fs(self) -> dict[str, Any]:
        if not self.tree_fs_path.exists():
            return {"folders": [], "files": []}
        try:
            return json.loads(self.tree_fs_path.read_text(encoding="utf-8"))
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
        with _yaml_lock(kb_path):
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
        with _yaml_lock(kb_path):
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
