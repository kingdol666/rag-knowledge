---
name: knowledgebase-manage
description: Document and KB administration. M1→M6 workflow: survey, confirm destructive ops, execute (move/rename/delete/merge/update), post-change reindex+experience linkage, verify, content update flow. All operations are atomic (disk + .tree-fs.json + .knowledge-base.yml). Triggered by: 移动, 改名, 重命名, 删除文档, 删除KB, 合并KB, move, rename, delete, merge, update content, 移动文档, 更新内容, 修改描述.
---

# Knowledge Manage — Document & KB Administration

**⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型）+ [MCP 优先原则](../knowledgebase/references/skill-trigger-contract.md#第五条mcp-优先原则)（禁止 terminal/HTTP 绕过）

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

All operations are **atomic**: each call syncs disk file + `.tree-fs.json` + `.knowledge-base.yml`.

---

## 思维框架

本 skill 管理知识库和文档的生命周期变更。核心原则：

1. **调查先行** — 任何操作前先 survey 当前结构
2. **破坏性操作必确认** — 删除/合并不可逆，必须先问用户
3. **变更必重索引** — move/update/delete 后自动重建向量索引+清理图谱
4. **经验联动** — 文档变更后检查关联经验是否 stale
5. **验证闭环** — 每步操作后必须验证结果一致性

操作流程覆盖 6 个阶段（M1→M6），按场景选择路径：

```
M1 调查 → M2 确认 → M3 执行 → M4 重索引+经验联动 → M5 验证 → M6 内容更新
```

---

## 操作决策树：Move vs Merge vs Delete vs Update?

```
用户要求"处理"一个文档/KB
    │
    ├── 移动文档到另一KB？
    │   → M3 Move + M4 Reindex（必须！）
    │
    ├── 合并两个KB？
    │   → Move ALL docs from A→B → kb_delete(A) → kb_graph_build(B)
    │   → 先确认用户 A 的文档可以全部迁走
    │
    ├── 删除文档/KB？
    │   → M2 确认不可逆 → M3 Delete → M4 图谱清理
    │   → KB 非空时不能直接删：先迁移或清空
    │
    ├── 改名/改描述？
    │   → M3 Rename → M5 验证
    │
    └── 更新内容？
        → M6: 读旧内容 → 改 → 更新 → 验证 → 重建索引
```

---

## M1 — 调查

`kb_list()` + `kb_get_documents(source_kb_id)`

## M2 — 确认破坏性操作

`kb_delete` / `kb_doc_delete` / 合并 → **必须询问用户**（skip in Module Mode）。

## M3 — 执行

### KB 操作
| 操作 | 工具 | 注意 |
|------|------|------|
| 改名/改描述 | `kb_update(kb_id, name, description)` | 仅 KB 级元数据 |
| 删除 KB | `kb_delete(kb_id)` | **不可逆**，必须先清空文档 |

### 文档操作
| 操作 | 工具 | 注意 |
|------|------|------|
| 移动 | `kb_doc_move(doc_path, target_kb_id)` | UUID 保留。⭐ `kb_doc_move` **自动触发重索引**（fire-and-forget），为保险起见 M4 显式执行一次 `kb_index_document` 确保完成 |
| 改名/改描述 | `kb_doc_update_meta(kb_id, doc_path, name, description)` | UUID 保留 |
| 更新内容 | `kb_doc_update_content(kb_id, doc_path, content)` | **不自动重索引** → 必须 M4 |
| 删除 | `kb_doc_delete(kb_id, doc_path)` | 接受短名或全路径 |
| 批量删除 | `kb_doc_batch_delete(kb_id, ["KB/doc1.md", ...])` | **必须用完整相对路径** |
| 合并 A→B | Move ALL from A → `kb_delete(A)` | 先确认、先验证 A 已清空 |

## M4 — 变更后重索引 + 经验联动

| 操作 | 必须执行的重索引 |
|------|-----------------|
| 移动文档 | `kb_index_document(kb_id=target, doc_path=new_path)` |
| 更新内容 | `kb_index_document(kb_id, doc_path)`（旧索引自动失效） |
| 删除文档 | `kb_graph_delete_document(doc_path=old_path)` 清理图谱 |
| 合并 KB | `kb_graph_build(target_kb_id, force=false)` |

### 经验联动（文档变更后必查）
文档移动/删除/更新内容后，关联的经验可能 stale 或 orphan：
```
experience_check_stale(kb_id=source_kb)   # 源 KB 经验检查
experience_check_stale(kb_id=target_kb)   # 目标 KB 经验检查
```
发现 stale 经验 → 后续 `experience_sync_kb` 修复。
> 详见 [knowledgebase-experience](../knowledgebase-experience/SKILL.md) 经验联动流程。

## M5 — 验证 + 报告

`kb_get_documents(source)` + `kb_get_documents(target)` + `kb_list()` + `fs_get_tree()`

## M6 — 更新内容流程

```
kb_doc_read(kb_id, doc_path, max_chars=20000) → 展示当前内容
用户提供新内容 → kb_doc_update_content → kb_doc_read 验证 → kb_index_document 重建索引
```

> **三写原子一致性**：磁盘文件 + .tree-fs.json + .knowledge-base.yml 同步更新。任何一层失败整体回滚。

---

## NEVER 清单 （禁止模式）

| 不要这样做 | 原因 | 应该这样做 |
|-----------|------|-----------|
| 移动后不重索引 | 移了但搜不到 | 立刻 `kb_index_document(target, new_path)` |
| 合并前不确认 | 不可逆 | M2 必须问用户 |
| 删除非空 KB | 会丢文档 | 先 `kb_get_documents` → 迁移或 `kb_doc_batch_delete` |
| 更新内容后不验证 | 可能写入失败 | `kb_doc_read` 确认内容一致 |
| 批量删用短路径 | 工具报错 | 用完整 `KB/doc.md` 相对路径 |
| 假设 move/delete 是同步的 | 实际是异步，需轮询验证 | M5 验证步骤不可跳过 |
