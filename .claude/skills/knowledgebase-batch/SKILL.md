---
name: knowledgebase-batch
description: High-volume batch operations. B1→B7: bulk tag migration, bulk description updates, directory mass ingestion (file-type routing), mass document move, cross-KB dedup, export summary, graph rebuild. All batch ops follow survey→plan→confirm→execute→verify. Triggered by: 批量, 所有文档, 全部, 大规模, 批量操作, batch, bulk, mass, all documents, every KB, repetitive, 全量, 一次性处理, 统一修改.
---

# Knowledge Batch — High-Volume Operations

**⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型）+ [MCP 优先原则](../knowledgebase/references/skill-trigger-contract.md#第五条mcp-优先原则)（禁止 terminal/HTTP 绕过）

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

**所有批量操作执行 `survey → plan → confirm → execute → verify` 五步流程**。

---

## ⭐ Pre-Flight — MCP 连通性 + 项目服务预检（强制，所有作业的第一步）

> 完整规则与边界情况见 [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md)。本预检早于本 skill 的所有编号步骤（B1-B7）。

**未通过预检，禁止开始后续步骤。**

1. **一探双检** — 调用 `mcp__kb-mcp__kb_project_status`：调用成功即证明 MCP 已连接，按 `ready` 分支（`ready==true` ⇔ backend+web 双健康）；报 "No such tool" → 走 Case C。
2. **分支处置**：
   - **Case A `ready==true`** → 就绪。
   - **Case B `ready==false`** → 先 `kb_project_preflight`（未安装则报 `problems`+`ragctl setup` 让用户处理并停止）；已安装则静默 `kb_project_start(backend=true, web=true[, neo4j=true], wait=true)`（B7 图谱重建加 `neo4j=true`），回查 `ready==true` 才继续，否则读 `ragctl logs backend` 报错停止。
   - **Case C MCP 未连接** → 会话内无法自愈（MCP 由 Claude Code 启动加载）；`node command/ragctl.js status` 诊断并通知用户重启 Claude Code；**禁止**未连通硬跑操作（HTTP 兜底须用户明确同意）。
3. **冒烟测试** — `ready==true` 后正式操作前先做一次轻量只读往返（`kb_catalog()` / `kb_tags_list()`），确认 MCP↔backend 返回真实数据再作业。

---

## 思维框架：选哪个批量操作？ ⭐

```
用户要求"批量/全部/所有"
    │
    ├── 统一修改标签？ → B1 Bulk Tag Migration
    ├── 统一补充描述？ → B2 Bulk Description Update
    ├── 从目录批量入库？ → B3 Directory Mass Ingestion
    ├── 批量移动文档到另一KB？ → B4 Mass Document Move
    ├── 全库去重？ → B5 Cross-KB Dedup
    ├── 导出全库概览？ → B6 Export Summary
    └── 全库重建图谱？ → B7 Graph Rebuild
```

### 批量操作前自检

| 问题 | 如果不查后果 |
|------|------------|
| 目标范围多大？（10个文档还是1000个？） | 超时/资源耗尽 |
| 是否可以 `dry_run` 预检？ | 不可逆变更无回退 |
| 速率限制？工具能承受多少并发？ | 中途失败难恢复 |
| 是否需要分批 + 断点续跑？ | 全部重来浪费时间 |

---

## B1 — Bulk Tag Migration

1. `kb_tags_list()` — 当前词表
2. 构建标签映射：旧→新，合并重复，拆分泛化标签
3. 对每个 KB：`kb_get_documents(kb_id)` → 筛选含目标标签的文档
4. 对每个文档：`kb_doc_update_tags(kb_id, doc_path, new_tags)`
5. 验证：`kb_doc_get_by_tag(new_tag)` — 确认文档数

### 批量标签注意事项
- 分批次执行（一次30个文档），防超时
- 每批次后验证成功率，打日志
- 发现报错文档单独标记，不等全部失败

---

## B2 — Bulk Description Update

1. `kb_get_documents(kb_id)` — 识别弱描述文档（空/文件名/泛泛）
2. 对每个文档读 2000 chars：`kb_doc_read(kb_id, doc_path, max_chars=2000)`
3. 按 [description-guide.md](../knowledgebase-ingest/references/description-guide.md) 生成内容型描述
4. 对每个文档：`kb_doc_update_meta(kb_id, doc_path, description=new_desc)`
5. 验证：随机采样 20% 文档，`kb_doc_read` 500 chars 确认描述与内容匹配

### 批量描述注意事项
- 大库（>50文档）分批处理，每批10-15个
- 委托子 Agent 并行生成描述（分KB执行）
- 每次生成后用四要素（主体/方法/场景/数据）自检

---

## B3 — Directory → KB Mass Ingestion

> **⭐ 质量门控强制要求**：B3 批量入库**不得绕过** Ingest 的质量门控。每个文档必须经过 Ingest A0-A7 的等效检查。
> 批量是"量"的优化（并行/分批），不是"质"的降级。详见 [knowledgebase-ingest](../knowledgebase-ingest/SKILL.md) A0-A7。

1. 调查目录：列出所有文件，按类型分类
2. **A0 去重（每文件必做）**：`kb_search_vector(query=<文件名+前200chars特征>, score_threshold=0.85)` → ≥0.85 命中则跳过（已存在）
3. 文件类型路由：
   - PDF/DOCX/PPTX/images → `parse_doc_batch(file_paths=[...], use_ocr=true)`（非阻塞）
   - MD/TXT/JSON/YAML/code → 直接读
   - Binary → `fs_upload_file(file_path, parent_id)`
4. 等待所有解析任务完成 → **A2-Q 解析质量检查**（乱码/空正文/二进制残留 → 拒绝入库）
5. 存储：`kb_doc_save_parsed(parent_id, task_id, description)`（解析文档必须用 save_parsed，禁止 kb_doc_create）
6. **A3b 标签质量门控**：每个文档标签过 [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md) T1黑名单+T2归一化+T3正文回查
7. **A3c 描述质量门控**：每个文档描述过四要素（主体/方法/场景/数据）+ 内容回查
8. 每个新文档：`kb_index_document` + `kb_doc_update_tags`
9. **A6-V 索引验证**：`kb_search_stats(kb_id)` 确认 collection 正确 + chunks ≥ 1
10. 验证：`kb_search_stats(kb_id)` — 确认 chunk count；**A7 抽样终检**（随机 20% 文档 kb_doc_read 确认内容/标签/描述一致）

### 目录入库注意事项
- 解析文件 >10个时务必用 `parse_doc_batch`（单 task_id 管理）
- 分批提交解析（20个一批），避免 MCP 工具超时
- 任务队列状态的轮询间隔 ≥5秒
- **质量门控不可跳过**：B3 是 Ingest A0-A7 的批量包装，不是简化版。跳过 A0 去重 → 重复文档堆积；跳过 A3b → 标签污染；跳过 A6-V → 向量漏索引

---

## B4 — Mass Document Move (KB→KB)

1. `kb_get_documents(source_kb_id)` — 全文档列表
2. 向用户确认
3. 对每个文档：`kb_doc_move(doc_path, target_kb_id)` → `kb_index_document(target_kb_id, new_path)`
4. `kb_search_stats(target_kb_id)` + `kb_get_documents(source_kb_id)` — 验证

### 批量移动注意事项
- 源KB非空不删（迁移完毕后用户决定）
- 移动后 `force=true` 重索引，确保 collection UUID 更新

---

## B5 — Cross-KB Dedup

> ⚠️ 注意：当 KB 数量大时复杂度为 O(n²)（每对 KB 比较）。优化策略：先按文档名哈希到桶中（同名的才比较），跨 KB 对超过 100 对时用 `kb_search_vector` 指纹判重替代逐对比较。

1. `kb_list()` → 所有 KB
2. 优化路径（推荐）：`kb_search_vector(query=doc_name + 前 200 chars 特征, score_threshold=0.85)` → 高分候选即为疑似重复
3. 完整路径（小规模）：按文件名初筛同名文档 → 读 500 chars 内容对比 → >80% 重叠标记重复
4. 标记重复 → 用户确认 → `kb_doc_delete(kb_id, doc_path)`
5. 验证：搜索确认无重复标题残留

---

## B6 — Export Summary

1. `kb_list()` + 每个 KB 的 `kb_get_documents`
2. 输出表格：KB name | doc count | total size | tag coverage | vector/graph index coverage | top docs

---

## B7 — Graph Rebuild

1. `kb_list()` → 所有 KB ID
2. `kb_graph_build(force=true)` — 批量重建（空 kb_id = 全库）
3. 验证：`kb_graph_stats()` → 检查 node/edge 数合理

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 不 survey 直接跑 batch | 误伤范围超预期 | 先 `kb_list`/`kb_get_documents` 确认范围 |
| 跳过用户确认 | 批量操作不可逆 | 所有破坏性操作先问用户 |
| 一次性尝试解析 100 个 PDF | MCP 超时 | 分批（20个/批）提交 `parse_doc_batch` |
| 批量操作后跳过验证 | 部分失败不知 | 采样验证 + 统计对比 |
| 标签映射测试目标不验证存在性 | `kb_doc_get_by_tag` 返回空 | 事前确认标签真实存在于文档 |
| 目录批量入库忽略去重 | 大量重复文档 | 入库前先做 `kb_search_vector` 指纹去重 |
