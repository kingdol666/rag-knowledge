"""清理孤儿向量 collection —— 已删除 KB 残留在 ChromaDB 中的 collection。

背景：KB 删除时只清了文件系统 + .knowledge-base.yml，未清后端 ChromaDB collection，
导致 kb_search_stats 报告的 collection 数远大于活跃 KB 数（Fix 4.2 的存量清理）。

用法（从仓库根目录）：
    uv run python scripts/cleanup_orphan_collections.py            # dry-run，只列出
    uv run python scripts/cleanup_orphan_collections.py --confirm  # 实际删除

或在 backend 目录：cd backend && uv run python ../scripts/cleanup_orphan_collections.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# 让脚本能 import backend.app.*（无论从仓库根还是 backend/ 运行）
if Path("backend").is_dir():
    sys.path.insert(0, "backend")
elif Path("..", "backend").is_dir():
    sys.path.insert(0, str(Path("..", "backend").resolve()))

from app.config import config  # noqa: E402
from app.services.storage_reader_service import storage_reader  # noqa: E402
from app.services.vector_service import vector_service  # noqa: E402


def expected_collection_names() -> set[str]:
    """活跃 KB 可能产生的全部 collection 名。

    历史索引可能用 kb_id(UUID)、path、或 name 三种之一作为 collection 名后缀，
    故三种都计入"预期"集合，避免误删活跃 KB 的向量数据。
    """
    names: set[str] = set()
    for kb in storage_reader.list_knowledge_bases():
        for key in ("kb_id", "path", "name"):
            val = kb.get(key, "")
            if val:
                names.add(vector_service._collection_name(val))
    return names


def list_all_collections() -> list[str]:
    return [c.name for c in vector_service._all_kb_collections()]


def main(dry_run: bool = True) -> None:
    all_cols = list_all_collections()
    expected = expected_collection_names()
    orphans = [c for c in all_cols if c not in expected]

    print("=" * 60)
    print("孤儿向量 collection 清理")
    print("=" * 60)
    print(f"活跃 KB 数: {len(storage_reader.list_knowledge_bases())}")
    print(f"预期 collection（活跃 KB 的 uuid/path/name 命名）: {len(expected)} 个")
    for c in sorted(expected):
        print(f"  [OK] {c}")
    print(f"\nChromaDB 实际 collection: {len(all_cols)} 个")
    print(f"孤儿 collection（无活跃 KB 对应）: {len(orphans)} 个")
    for c in sorted(orphans):
        print(f"  [DEL] {c}")

    if not orphans:
        print("\n[OK] 无需清理，collection 与活跃 KB 完全一致。")
        return

    if dry_run:
        print(f"\n[DRY RUN] 上述 {len(orphans)} 个孤儿 collection 未删除。加 --confirm 实际执行。")
        return

    print(f"\n开始删除 {len(orphans)} 个孤儿 collection...")
    deleted, failed = [], []
    client = vector_service.client
    for col_name in sorted(orphans):
        try:
            client.delete_collection(col_name)
            deleted.append(col_name)
            print(f"  [OK] deleted {col_name}")
        except Exception as e:
            failed.append((col_name, str(e)))
            print(f"  [FAIL] {col_name}: {e}")
    print(f"\n完成：删除 {len(deleted)} 个，失败 {len(failed)} 个。")
    remaining = [c.name for c in vector_service._all_kb_collections()]
    print(f"剩余 collection: {len(remaining)} 个")


if __name__ == "__main__":
    main(dry_run="--confirm" not in sys.argv)
