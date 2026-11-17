# -*- coding: utf-8 -*-
"""S0b — 修复根树注册表 .tree-fs.json：补回丢失的 MD语料-* folder 条目。

事故（2026-11-02）：web 树服务（nuxt dev，11:56:24 启动）的内存快照跨在
S2 入库窗口（11:55-11:58）中间，其后续全量回写把 10 个 MD语料-* 的 folder
条目从根注册表抹掉（file 条目因 read-modify-write 追加路径幸存）。
症状：kb_list 只剩 34 库；磁盘目录与 .knowledge-base.yml 完好。

修复：从每个 KB 目录的 .knowledge-base.yml（单一事实源）重建 folder 条目，
documentCount 取 .tree-fs.json 中 parentId==kb_id 的现存 file 条目数（回退 yml）。
幂等：已存在的 name 跳过。先写备份 .tree-fs.json.bak-<ts>。
"""
import json
import sys
import time
from pathlib import Path

TREE = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge/storage/tree-file-system")
PREFIX = "MD语料-"


def main():
    reg_path = TREE / ".tree-fs.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    folders = reg.get("folders", [])
    files = reg.get("files", [])
    existing = {f.get("name") for f in folders}
    added, skipped = [], []
    for kbdir in sorted(TREE.iterdir()):
        if not kbdir.is_dir() or not kbdir.name.startswith(PREFIX):
            continue
        if kbdir.name in existing:
            skipped.append(kbdir.name)
            continue
        yml = kbdir / ".knowledge-base.yml"
        if not yml.exists():
            print(f"[skip] {kbdir.name}: no .knowledge-base.yml")
            continue
        # 极简 yml 解析（无 yaml 依赖保证；只取 knowledge_base: 块的两层缩进键）
        meta, section = {}, ""
        for line in yml.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("-"):
                continue
            if not line.startswith((" ", "\t")):
                section = line.split(":", 1)[0].strip()
                continue
            if section != "knowledge_base":
                continue
            stripped = line.strip()
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                meta[k.strip()] = v.strip().strip("'\"")
        kb_id = meta.get("id", "")
        if not kb_id:
            print(f"[skip] {kbdir.name}: yml has no id")
            continue
        doc_count = sum(1 for f in files if f.get("parentId") == kb_id)
        try:
            doc_count = int(meta.get("total_documents", doc_count)) or doc_count
        except ValueError:
            pass
        entry = {
            "id": kb_id,
            "name": kbdir.name,
            "description": " ".join(meta.get("description", "").split()),
            "parentId": None,
            "path": meta.get("path", kbdir.name),
            "type": "folder",
            "childCount": 0,
            "documentCount": doc_count,
            "isKnowledgeBase": True,
            "kb_id": kb_id,
            "createdAt": meta.get("created_at", ""),
            "updatedAt": meta.get("updated_at", meta.get("created_at", "")),
        }
        folders.append(entry)
        added.append(kbdir.name)
    if added:
        bak = reg_path.with_name(f".tree-fs.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        bak.write_text(reg_path.read_text(encoding="utf-8"), encoding="utf-8")
        reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"added={len(added)} skipped={len(skipped)} total_folders={len(folders)}")
    for n in added:
        print("  +", n)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
