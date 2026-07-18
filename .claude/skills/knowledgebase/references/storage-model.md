# 存储模型 (Storage Model)

> 摘自项目 CLAUDE.md — 全局安装插件后技能可独立引用

## 三层存储

```
web/storage/tree-file-system/
├── .tree-fs.json                    # Global index: all folders + files with metadata
├── {knowledge-base-name}/
│   ├── .knowledge-base.yml          # Per-KB document index (name, description, path, tags, metadata)
│   ├── doc1.md                      # Parsed/uploaded markdown documents
│   └── images/                      # Images extracted from parsed PDFs
```

- **`.tree-fs.json`** — 权威的树结构索引；所有文件夹/文件的 CRUD 操作始终优先更新此文件。
- **`.knowledge-base.yml`** — 每个 KB 的搜索索引；`kb_search` 直接读取此文件。

## Architecture principle

- **Writes** go through HTTP API (backend/web proxy)
- **Reads** go through direct file access (`.tree-fs.json` + `.knowledge-base.yml`)

## 三写原子一致性

文件系统写入 `fs_upload_file` → 同时更新：
1. 磁盘文件 (`doc1.md`)
2. `.tree-fs.json`
3. `.knowledge-base.yml`

三层缺一不可，任何一层失败则整体回滚。
