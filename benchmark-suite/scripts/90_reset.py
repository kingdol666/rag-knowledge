#!/usr/bin/env python3
"""Step 0 — 清空当前系统全部知识库(级联删除向量/图谱), 为基准重建干净状态."""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import REPO, WEB, http_delete, http_get  # noqa: E402


def main() -> int:
    deleted = []
    # 多轮清扫: 批量删除会引发 verify 401 风暴, 每轮删光当前 catalog 直到为空
    for sweep in range(6):
        catalog = http_get(f"{WEB}/api/kb/catalog", timeout=180)
        kbs = catalog.get("knowledgeBases") or []
        if not kbs:
            break
        print(f"[kbs] sweep {sweep + 1}: {len(kbs)} to delete", flush=True)
        for k in kbs:
            try:
                http_delete(f"{WEB}/api/kb/delete",
                            {"kbId": k.get("kbId") or k.get("id")}, timeout=300)
                deleted.append(k.get("name"))
                print(f"  deleted {k.get('name')}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"  delete failed {k.get('name')}: {str(e)[:100]}", flush=True)
        time.sleep(10)
    after = http_get(f"{WEB}/api/kb/catalog", timeout=180)
    remaining = [k.get("name") for k in (after.get("knowledgeBases") or [])]

    # 幽灵兜底: catalog 已空但磁盘仍有 KB 目录(API 删除失败残留)
    storage = REPO / "storage" / "tree-file-system"
    ghosts = []
    if storage.exists() and not remaining:
        for entry in sorted(storage.iterdir()):
            if entry.is_dir():
                ghosts.append(entry.name)
        if ghosts:
            print(f"[ghosts] removing leftover dirs: {ghosts}", flush=True)
            for g in ghosts:
                shutil.rmtree(storage / g, ignore_errors=True)
    ok = not remaining
    print(json.dumps({"deleted": deleted, "remaining": remaining,
                      "ghosts_removed": ghosts, "ok": ok},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
