#!/usr/bin/env python3
"""Step 0 — 清空当前系统全部知识库(级联删除向量/图谱), 为基准重建干净状态."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import WEB, http_delete, http_get  # noqa: E402


def main() -> int:
    # 多轮清扫: 批量删除会引发 verify 401 风暴, 每轮删光当前 catalog 直到为空
    for sweep in range(5):
        catalog = http_get(f"{WEB}/api/kb/catalog", timeout=180)
        kbs = catalog.get("knowledgeBases") or []
        if not kbs:
            break
        print(f"sweep {sweep + 1}: {len(kbs)} KBs to delete")
        for k in kbs:
            try:
                http_delete(f"{WEB}/api/kb/delete",
                            {"kbId": k.get("kbId") or k.get("id")}, timeout=300)
                print(f"  deleted {k.get('name')}")
            except Exception as e:  # noqa: BLE001
                print(f"  delete failed {k.get('name')}: {str(e)[:100]}")
        time.sleep(10)
    after = http_get(f"{WEB}/api/kb/catalog", timeout=180)
    remaining = [k.get("name") for k in (after.get("knowledgeBases") or [])]
    print(f"remaining KBs: {len(remaining)} {remaining[:5]}")
    return 0 if not remaining else 1


if __name__ == "__main__":
    sys.exit(main())
