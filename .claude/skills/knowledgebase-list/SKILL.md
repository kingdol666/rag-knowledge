---
name: knowledgebase-list
description: Knowledge base listing and discovery. L1→L3 workflow: full inventory of all KBs with document counts, KB drill-down with document metadata, folder tree browsing. Read-only. Invoked by Archival when information needs to be found or displayed. Trigger keywords: 查看, 列出, 展示, 浏览, 有什么, 列出来, 清单, list, show, overview, tree, browse, display, 知识库内容, 知识库有什么, 查看知识库, 有哪些知识库.
---

# Knowledge List — Collection Overview

**⭐ MCP 优先原则（强制）**：所有 kb-mcp 操作必须通过 MCP 工具执行（`mcp__kb-mcp__*`）。禁止用 `curl`/`python -c`/`wget` 等终端命令或直调 HTTP API。MCP 不可用时才可向用户报告。

**Read-only. Never modify anything.**

---

## 思维框架：用户要看多深？ ⭐

```
"看看知识库有什么"
    │
    ├── "有什么 KB？" → L1 Full Inventory（KB 级别概览）
    ├── "KB 里有什么文档？" → L2 KB Drill-Down（文档清单）
    ├── "目录树长什么样？" → L3 Browse Tree（文件树）
    └── "不知道，随便看看" → L1 → 根据用户反应决定是否进 L2
```

### 汇报深度策略
| 用户问题 | 展示级别 | 信息量 |
|---------|---------|--------|
| "有什么知识库" | L1 | KB 名 + 描述 + 文档数 |
| "XX库里有什么" | L2 | 文档名 + 标签 + 向量索引状态 |
| "目录结构" | L3 | 完整文件树 |
| "帮我看看XX库的文档详情" | L2 + `kb_doc_read` preview | 文档内容预览 |

---

## L1 — Full Inventory
```
kb_list()                    # all KBs: id, name, description, docCount
kb_tags_list()               # full tag vocabulary
fs_get_tree(max_depth=2)     # KB hierarchy
```
Lightweight: `kb_catalog()` returns `[{kb_id, name, description, doc_count}]`.

Present as table: KB Name | Description | Docs.

### 汇报格式
```
📚 知识库总览（共 N 个）
| KB | 描述 | 文档数 |
|----|------|--------|
| Embodied-AI | 具身智能 | 12 |
| ... | ... | ... |

📌 标签词表: [tag1, tag2, ...]（共 N 个）
📁 目录深度: 2 层
```

## L2 — KB Drill-Down
```
kb_get_documents(kb_id)      # docs with name, path, tags, size, vector_index, dates
```
Lightweight: `kb_doc_catalog(kb_id)` returns `[{doc_path, name, description}]`.

Check `vector_index` field per doc. Offer `kb_doc_read` for content preview.

## L3 — Browse Tree
```
fs_get_tree(include_files=True, max_depth=0)   # 0 = unlimited
fs_get_count()                                  # folder/file/total counts
```
Lightweight: `kb_catalog()` for KB-level, `kb_doc_catalog(kb_id)` for doc-level.

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 非读-only 操作（改/删/移） | List 是纯查看 | 读-only，其他操作路由到 Manage/Ingest |
| 全库用 `fs_get_tree(max_depth=0)` | 大库拖慢 | 先 L1 用 `max_depth=2`，再按需 L3 |
| 不展示标签词表 | 用户想看分类 | L1 必须展示 `kb_tags_list()` |
| 不用 lightweight 方法 | 信息过载 | `kb_catalog`→`kb_doc_catalog` 递进 |
| 省略 KB 的 description | 用户靠名字猜内容 | L1 必须展示 description |
