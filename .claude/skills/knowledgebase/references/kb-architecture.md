# Knowledge Base Architecture — 系统数据模型与操作心智模型

> ⭐ **所有 KB 操作前必读**。本文解释 THIS 系统的知识库架构（非通用 KB 概念）。
> Agent 必须理解这 5 层数据模型才能正确操作，否则会破坏一致性。

## 5 层数据模型

```
用户文档 (.md)
    │  kb_doc_create / kb_doc_save_parsed / kb_doc_update_content
    ▼
① 磁盘层 (storage/tree-file-system/<KB>/<doc>.md)
    │  原始 markdown 文件，内容的唯一真相源
    │
    │  文件树 CRUD 自动同步
    ▼
② .tree-fs.json (全局树索引：所有文件夹+文件+metadata)
    │  kb_list / kb_get_documents / fs_get_tree 读这里
    │
    │  KB 内文档 CRUD 自动同步
    ▼
③ .knowledge-base.yml (每 KB 的文档索引：name/description/path/tags/vector_index)
    │  kb_search / kb_tags_list 读这里
    │
    │  kb_index_document / kb_batch_index 写这里
    ▼
④ ChromaDB (向量存储：kb_<UUID> collection，文档 chunk 向量)
    │  kb_search_vector / kb_search_two_stage 查这里
    │
    │  kb_graph_build 写这里
    ▼
⑤ Neo4j (知识图谱：Document/Tag/KB 节点 + RELATED_TO/HAS_TAG 边)
    │  kb_graph_* 查这里
```

## 一致性不变量（atomic 保证）

**每次 MCP CRUD 调用原子更新 ①②③**（后端保证三层同步）。但 ④⑤ 需显式触发：

| 操作 | 自动同步 | 需手动触发 |
|------|---------|-----------|
| `kb_doc_create` / `kb_doc_save_parsed` | ①②③ | `kb_index_document` (→④) + `kb_graph_build` (→⑤) |
| `kb_doc_update_content` | ①③ | `kb_index_document` (→④，内容变向量必须重算) |
| `kb_doc_move` | ①②③ | `kb_index_document(target)` (→④) + 图谱清理 |
| `kb_doc_delete` | ①②③ | 向量 collection 残留需 `kb_reindex(force=true)` 清理 |

> ⚠️ **最常见的一致性破坏**：修改内容/移动文档后忘记重索引 → 向量层用旧 chunk → 搜索漏召回。`kb_doc_update_content` **不会**自动重索引。

## KB 层级结构

```
顶层 KB (高分子双向拉伸文献库)
├── 子KB (03_PET_BOPET - 聚酯双向拉伸)    ← isKnowledgeBase=true
│   └── 文档 (PET-deformation-2022.md)
├── 子KB (04_PVA_BOPVA - 聚乙烯醇双向拉伸)
│   └── 文档 (...)
└── 直接文档 (cross-domain-review.md)      ← 父KB自己的文档
```

**关键坑**（⭐ 经实测验证）：
- **父 KB 的 `kb_search_two_stage` 返回子 KB 容器条目（content 为空）** → 正确做法：用 **`kb_search_vector(kb_id=<父KB>)`** 检索真实内容（子 KB 文档的向量 chunk 存储在**父 KB collection** 下，搜子 KB UUID 返回 0 结果）。`kb_graph_kb_overview(kb_id)` 仅用于查看子 KB 结构/文档数，**不能**作为搜索入口。
- `kb_doc_catalog` 无 type 字段区分文档 vs 子KB容器 → 用 `file_type: knowledge-base` 或 `fs_get_tree(max_depth=2)` 区分
- `kb_graph_kb_overview.related_kbs[].name` 和 `sub_kbs[].name` 返回 UUID → 用 `kb_catalog()` 回查可读名

## 76 个 MCP 工具地图（按操作类型）

| 类别 | 工具数 | 代表工具 | 何时用 |
|------|--------|---------|--------|
| **KB CRUD** | 4 | `kb_create` `kb_list` `kb_update` `kb_delete` | 建库/列库/改库/删库 |
| **KB Catalog** | 2 | `kb_catalog` `kb_doc_catalog` | 轻量列库（agent 第一步扫描） |
| **文档读** | 2 | `kb_get_documents` `kb_doc_read` | 读元数据/读正文（检索后必读） |
| **文档写** | 7 | `kb_doc_create` `kb_doc_save_parsed` `kb_doc_update_meta` `kb_doc_update_content` `kb_doc_delete` `kb_doc_batch_delete` `kb_doc_move` | 文档 CRUD |
| **文件系统** | 4 | `fs_get_tree` `fs_get_children` `fs_get_count` `fs_upload_file` | 树结构/原始文件 |
| **解析** | 3 | `parse_doc` `parse_doc_batch` `parse_task_status` | PDF→MD（非阻塞）；`kb_doc_save_parsed` 归入文档写 |
| **标签** | 4 | `kb_tags_list` `kb_doc_update_tags` `kb_doc_get_by_tag` `kb_tags_cleanup` | 标签管理 |
| **搜索** | 4 | `kb_search` `kb_search_vector` `kb_search_two_stage` `kb_search_stats` | 元数据/向量/两阶段/统计 |
| **向量索引** | 4 | `kb_index_document` `kb_batch_index` `kb_reindex` `kb_cleanup_orphan_collections` | 索引管理 |
| **图谱** | 14 | `kb_graph_search` `kb_graph_build` `kb_graph_kb_overview` `kb_graph_document` ... | Neo4j 图谱 |
| **经验** | 22 | `experience_search_smart` `experience_create` `experience_rerank` ... | 经验库全生命周期 |
| **项目** | 5 | `kb_project_status` `kb_project_start` `kb_project_version` ... | 服务生命周期 |
| **健康** | 1 | `backend_status` | 预检 |

> 合计 76 工具（4+2+2+7+4+3+4+4+4+14+22+5+1）。`kb_doc_save_parsed` 横跨解析+写入（解析产物落盘入库），归入文档写避免重复计数。

> **写入路径原则**：写操作（create/update/delete/move）必须走 MCP 工具（HTTP→后端→原子更新三层）。读操作可以直接读文件，但推荐用 MCP 工具保证一致性。

## 操作前的预检契约

**任何 KB 操作前**，Agent 必须先确认：
1. `mcp__kb-mcp__backend_status()` → backend healthy + MinerU 可用
2. 如果操作跨多文档/KB → 先 `kb_catalog()` 建立全局认知
3. 如果是写操作 → 确认目标 KB 存在（`kb_list` 或 `fs_get_tree`）

## 路径格式约定

- `kb_get_documents` 在 Windows 返回**反斜杠**路径（`KB\doc.md`）
- `kb_graph_*` 用**正斜杠**路径（`KB/doc.md`）
- `kb_doc_read` 两者都接受
- **跨工具传参时统一转正斜杠**避免 miss
