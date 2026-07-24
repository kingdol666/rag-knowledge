---
name: knowledgebase-manage
description: Document and KB administration. M1→M6 workflow: survey, confirm destructive ops, execute (move/rename/delete/merge/update), post-change reindex+experience linkage, verify, content update flow. All operations are atomic (disk + .tree-fs.json + .knowledge-base.yml). Triggered by: 移动, 改名, 重命名, 删除文档, 删除KB, 合并KB, move, rename, delete, merge, update content, 移动文档, 更新内容, 修改描述.
---

# Knowledge Manage — Document & KB Administration

**⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型）+ [MCP 优先原则](../knowledgebase/references/skill-trigger-contract.md#第五条mcp-优先原则)（禁止 terminal/HTTP 绕过）

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

All operations are **atomic**: each call syncs disk file + `.tree-fs.json` + `.knowledge-base.yml`.

---

## ⭐ Pre-Flight（强制，所有作业第一步）

**未通过预检禁止作业。** 执行 [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md) 的完整流程（一探双检 `kb_project_status` → 分支处置 → 冒烟测试）。
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

**Freedom Map**（每步自由度）：
| 步骤 | 自由度 | 说明 |
|------|--------|------|
| M1 调查 / M5 验证 | 🔒 **强制**（低自由度） | 必须走完整流程，不可跳步骤 |
| M2 确认破坏性操作 / M4 重索引 | 🔒 **强制**（低自由度） | 不可逆操作必须用户确认；重索引不可省略 |
| M3 执行（move/rename/delete/merge） | 🎯 **执行**（中自由度） | 按工具表操作，参数精确 |
| M6 内容更新 | 🧠 **判断**（高自由度） | 新内容由用户决定，Agent 仅验证一致性 |

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


## 已知问题 + 错误恢复

| 病症 | 检测 | 处置 |
|------|------|------|
| **move 后旧路径仍有向量残留** | `kb_search_vector(query, kb_id=target)` 返回旧路径 chunk | `kb_reindex(kb_id=target, force=true)` 清理旧 collection |
| **batch_delete 报 "Not found"** | 短名 vs 全路径混用 | 必须用完整相对路径 `"KB/doc.md"`（非裸文件名） |
| **update_content 后搜索返回旧内容** | 向量层用旧 chunk | 必须显式 `kb_index_document` 重索引（不自动触发） |
| **合并后 KB description 过时** | 父 KB 描述未含新迁入的子域 | M5 验证时顺带检查描述是否需更新 |
| **经验 stale 未检测** | move/delete 后关联经验变 orphan | M4 `experience_check_stale` 必查（否则经验库逐步腐烂） |
| **kb_doc_move 返回成功但文件未到** | fire-and-forget 异步未完成 | M5 回查 `kb_get_documents(target)` 确认 doc 已在目标 KB |
| **图谱旧节点残留** | move 后 Neo4j 仍有旧路径 Document 节点 | `kb_graph_delete_document(doc_path=old_path)` 清理 |

### 错误恢复策略
- **工具调用失败** → 重试一次（5s 间隔）；仍失败 → 报告用户当前状态，不静默跳过
- **批量操作部分失败** → 完成成功的，单独标记失败的，不因部分失败回滚成功的
- **不可逆操作执行后发现错误** → 立即停止，评估损失范围，用 `kb_doc_read` 确认受影响文档，报告用户
---

## NEVER 清单 （禁止模式）

| 不要这样做 | 原因 | 应该这样做 |
|-----------|------|-----------|
| 移动后不重索引 | 移了但搜不到——向量层用旧路径 chunk | 立刻 `kb_index_document(target, new_path)` + `kb_graph_delete_document(old_path)` |
| 合并前不确认 | 不可逆——文档一旦迁走源 KB 为空 | M2 必须问用户，展示迁移计划 |
| 删除非空 KB | 会丢文档——`kb_delete` 不检查是否有文档 | 先 `kb_get_documents` → 迁移或 `kb_doc_batch_delete` |
| 更新内容后不验证 | 可能写入失败——HTTP 无回执确认 | `kb_doc_read` 确认内容一致 + `kb_index_document` 重建索引 |
| 批量删用短路径 | 工具报错——`batch_delete` 仅接受全路径 | 用完整 `KB/doc.md` 相对路径（非裸文件名） |
| 假设 move/delete 是同步的 | fire-and-forget 异步——返回成功≠已完成 | M5 回查 `kb_get_documents(target)` 确认 |
| `kb_doc_update_content` 后不重索引 | 向量层仍用旧 chunk——搜索返回过时内容 | 必须显式 `kb_index_document`（不自动触发） |
| move/delete 后不查经验 stale | 关联经验变 orphan——经验库逐步腐烂 | M4 `experience_check_stale(source)` + `(target)` 必查 |
| 改名后图谱旧节点残留 | Neo4j 不自动跟随文件改名 | `kb_graph_delete_document(old_path)` + `kb_graph_build(kb_id, force=false)` |
