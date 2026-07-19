---
name: knowledgebase-list
description: Knowledge base listing and discovery. L1→L3 read-only workflow: full inventory (KB names + descriptions + doc counts + tag vocabulary), KB drill-down (document metadata), folder tree browsing. Lightweight methods (kb_catalog→kb_doc_catalog) for progressive disclosure. Never modifies anything. Triggered by: 查看, 列出, 展示, 浏览, 有什么, 列出来, 清单, list, show, overview, tree, browse, display, 知识库内容, 知识库有什么, 查看知识库, 有哪些知识库.
---

# Knowledge List — Collection Overview

**⭐ MCP 优先原则**：[references/skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md#第五条mcp-优先原则) — MCP 优先，禁止 terminal/HTTP 绕过

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

---

## 思维框架：用户要看多深？ ⭐

用户意图决定展示层级。通过第一轮回应探测用户想要的粒度。

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

**目标**：返回所有 KB 的顶级概览（名称、描述、文档数、标签词表）。

**执行步骤**：

1. `mcp__kb-mcp__kb_list()` — 获取所有 KB：id, name, description, docCount
2. `mcp__kb-mcp__kb_tags_list()` — 获取完整标签词表
3. `mcp__kb-mcp__fs_get_tree(max_depth=2)` — KB 层级结构

轻量方法：`mcp__kb-mcp__kb_catalog()` 返回 `[{kb_id, name, description, doc_count}]`。

展示为表格：KB Name | Description | Docs.

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

**目标**：进入特定 KB 查看文档清单及元数据。

**执行步骤**：

1. `mcp__kb-mcp__kb_get_documents(kb_id)` — 文档元数据：name, path, tags, size, vector_index, dates
2. 检查每个文档的 `vector_index` 字段
3. 按需提供 `mcp__kb-mcp__kb_doc_read()` 内容预览

轻量方法：`mcp__kb-mcp__kb_doc_catalog(kb_id)` 返回 `[{doc_path, name, description}]`。

**注意**：`vector_index` 字段可能缺失（见下方已知问题）。如需确认向量索引状态，可用 `mcp__kb-mcp__kb_search_vector()` 验证。

## L3 — Browse Tree

**目标**：展示文件系统的完整树形结构。

**执行步骤**：

1. `mcp__kb-mcp__fs_get_tree(include_files=True, max_depth=0)` — 0 = unlimited
2. `mcp__kb-mcp__fs_get_count()` — 文件夹/文件/总量统计

轻量方法：KB 级用 `mcp__kb-mcp__kb_catalog()`，文档级用 `mcp__kb-mcp__kb_doc_catalog(kb_id)`。

---

## 已知问题

- **层次化KB搜索返回空内容** — 父 KB 的 `kb_search_two_stage` 返回子 KB 容器条目，content 为空。子KB本身无向量chunk。应使用 `kb_graph_kb_overview(kb_id)` 获取子 KB UUID 列表，然后在子 KB 内分别检索。
- **向量索引元数据可能缺失** — 部分文档的 `vector_index` 字段在索引后未写入 YAML（向量实际存在于 ChromaDB）。用 `kb_reindex(kb_id, force=true)` 修复（写操作，List 流程不自动执行）。
- **图谱子KB节点仅显示UUID** — `kb_graph_kb_overview` 的子 KB name 字段为 UUID 而非可读名称。回查 `kb_catalog()` 获取可读名。
- **`kb_graph_build` 返回的 `total_relations` 可能为 0** — 这是 stats 统计 bug，实际图谱数据已写入 Neo4j。**不要**因为返回 0 就认为构建失败。用 `kb_graph_document(doc_path)` 抽检验证。
- **标签注册表积累孤儿标签** — `kb_tags_list()` 返回的标签列表包含 0 文档引用的历史标签。用 `kb_tags_cleanup(dry_run=true)` 检测。不影响搜索功能——文档级标签自动过滤。
- **⭐ kb-mcp MCP 启动检查** — 执行任何 KB 操作前，先调用 `mcp__kb-mcp__backend_status` 验证 MCP 连通性。MCP 不可用时：① Bash 检查服务 ② 检查 `.mcp.json` ③ 手动启动 kb-mcp ④ 后端健康但 MCP 不可用 → 通知用户重启 Claude Code ⑤ 仅在用户确认后才用 HTTP API 兜底。

## 存储模型

```
$TREE_STORAGE_PATH/
├── .tree-fs.json                    # 全局树结构索引
├── {knowledge-base-name}/
│   ├── .knowledge-base.yml          # KB 文档索引 (name, description, path, tags)
│   └── doc1.md                      # Markdown 文档
```
- **存储路径**：从 config.yml 读取 `TREE_STORAGE_PATH`（默认 `./storage/tree-file-system`）
- **Writes** → HTTP API (backend/web proxy)
- **Reads** → 直接文件访问 (`.tree-fs.json` + `.knowledge-base.yml`)
- **三写原子一致性**：`fs_upload_file` → 同时更新 ①磁盘文件 ②`.tree-fs.json` ③`.knowledge-base.yml`。任何一层失败则整体回滚。

---

## 参考

- [知识库技能触发契约](../knowledgebase/references/skill-trigger-contract.md) — 全文详见 knowledgebase 通用参考：skill 触发链、Archival 委托、MCP 优先原则

> 以上参考文件位于 `knowledgebase/references/` 目录，全局安装插件后可独立访问。

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 非读-only 操作（改/删/移） | List 是纯查看 | 读-only，其他操作路由到 Manage/Ingest |
| 全库用 `fs_get_tree(max_depth=0)` | 大库拖慢 | 先 L1 用 `max_depth=2`，再按需 L3 |
| 不展示标签词表 | 用户想看分类 | L1 必须展示 `kb_tags_list()` |
| 不用 lightweight 方法 | 信息过载 | `kb_catalog`→`kb_doc_catalog` 递进 |
| 省略 KB 的 description | 用户靠名字猜内容 | L1 必须展示 description |
