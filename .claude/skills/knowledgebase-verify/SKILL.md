---
name: knowledgebase-verify
description: Knowledge base integrity and quality validation. V1→V9: three-way metadata consistency (disk↔.tree-fs.json↔.knowledge-base.yml), document integrity, parse quality, index coverage+repair, scorecard (max 115), report, tag health (orphan+trash detection), experience health (stale+orphan+test pollution), auto-fix (repeat collections, orphan tags, missing indexes). Read-only by default; repair requires explicit instruction. Triggered by: 校验, 核对, 完整性, 健康检查, 验证, 检查, 一致性, verify, validate, integrity, health check, quality audit, check KB, 检测问题, 审计知识库.
---

# Knowledge Verify — Integrity & Quality

**⭐ MCP 优先原则**：[references/skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md#第五条mcp-优先原则) — MCP 优先，禁止 terminal/HTTP 绕过

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

**Read-only by default.** V4/V7/V9 repair requires explicit user instruction.

---

## 思维框架：先判断校验重点 ⭐

```
用户说"校验/检查"
    │
    ├── 怀疑元数据不一致 → V1 Three-Way Metadata
    ├── 文档打开报错/404 → V2 Document Integrity
    ├── 解析 PDF 后内容乱码 → V3 Parse Quality
    ├── 搜不到文档 → V4 Index Coverage
    ├── "彻底审计" → V1→V9 全流程
    └── 指定了某个 KB → 只跑该 KB 的完整流
```

### 校验策略选择

| 场景 | 广度 | 深度 | 耗时 |
|------|------|------|------|
| 快速检查 | V1 + V5 仅统计 | 抽样 10% | ~10s |
| 常规健康检查 | V1→V9 | 正常采样 | ~60s |
| 深度审计 | V1→V9 全量 | 每个文档 | ~5min+ |
| 修复后验证 | V4 索引 + V5 评分 | 对比前后 | ~30s |

---

## V1 — Three-Way Metadata Integrity

验证 `kb_list()` 与 `kb_get_documents()` 的文档计数一致性，以及 `fs_get_tree()` 的路径交叉引用（注意：MCP工具无法直接访问原始 `.tree-fs.json`/`.knowledge-base.yml` 文件，UUID 一致性检查已通过工具内部的原子操作保证）。

1. `mcp__kb-mcp__kb_list()` vs `mcp__kb-mcp__fs_get_tree()` — flag KBs with no tree node, orphan nodes, doc count mismatches.
2. For each KB: `mcp__kb-mcp__kb_get_documents(kb_id)` — check each doc has a matching file on disk via path cross-reference.
3. ⚠️ UUID级一致性由MCP工具原子操作保证（每次 CRUD 同步更新三层），V1 验证基于路径交叉引用而非UUID直接对比。
4. Flag: phantom entries (metadata but no disk file), orphan files (disk but no metadata).

## V2 — Document Integrity

`mcp__kb-mcp__kb_get_documents(kb_id)` → sample `mcp__kb-mcp__kb_doc_read` using the sampling strategy below.
Flag: broken 404s, empty descriptions, untagged docs.

### 采样策略

| 库大小 | 采样比例 | 最低样本 |
|--------|---------|---------|
| 1-10 | 100% | 全部 |
| 11-50 | 50% | 至少10 |
| 51-100 | 25% | 至少25 |
| >100 | 15% | 至少50 |

---

## V3 — Parse Quality

`mcp__kb-mcp__kb_doc_read` 2000 chars on parsed docs (infer from .pdf/.docx names).
Flag: empty content (<100 chars), OCR garbage, binary residue, heading-only (no body).

Use `mcp__kb-mcp__backend_status()` for MinerU health (authoritative).

## V4 — Index Coverage & Repair

### Vector
`mcp__kb-mcp__kb_get_documents(kb_id)` → check `vector_index` field per doc. `mcp__kb-mcp__kb_search_stats(kb_id)` → check chunk counts.
**Repair**: `mcp__kb-mcp__kb_index_document(kb_id, doc_path)` or `mcp__kb-mcp__kb_batch_index(kb_id, [paths], force=true)`.

### Graph
`mcp__kb-mcp__kb_graph_health()` → Neo4j available? `mcp__kb-mcp__kb_graph_kb_overview(kb_id)` → doc_count vs actual.
**Repair**: `mcp__kb-mcp__kb_graph_build_kb(kb_id, force=true)`.
**Clean stale**: `mcp__kb-mcp__kb_graph_delete_document(doc_path)` for deleted docs.

## V5 — Scorecard (max 115)

Metadata Consistency (25) | Document Quality (30) | Tag Coverage (25) | Description Quality (10) | Graph Health (15) | Vector Coverage (10)

| 维度 | 满分 | 评分方法 |
|------|------|---------|
| 元数据一致性 | 25 | 匹配的条目数 / 总条目数 × 25 |
| 文档质量 | 30 | 抽检合格率 × 30 |
| 标签覆盖 | 25 | 有标签文档 / 总文档 × 25 |
| 描述质量 | 10 | 内容型描述比例 × 10 |
| 图谱健康 | 15 | 图谱覆盖率 × 15 |
| 向量覆盖 | 10 | 向量索引覆盖率 × 10 |

## V6 — Report

Score + key findings + single most impactful recommendation.

### 报告模板
```
## 校验报告：<KB名称>
总分: XX/115

| 维度 | 得分 | 状态 |
|------|------|------|
| 元数据一致性 | XX/25 | ✅/⚠️/❌ |
| 文档质量 | XX/30 | ✅/⚠️/❌ |
| 标签覆盖 | XX/25 | ✅/⚠️/❌ |
| 描述质量 | XX/10 | ✅/⚠️/❌ |
| 图谱健康 | XX/15 | ✅/⚠️/❌ |
| 向量覆盖 | XX/10 | ✅/⚠️/❌ |

### 关键发现
- <发现1>
- <发现2>

### 首要建议
<一条最具性价比的修复建议>
```

## V7 — Tag Health

`mcp__kb-mcp__kb_tags_cleanup(dry_run=true)`

检测 0 引用孤 tag 和章节标题/测试标签等垃圾模式。
- `dry_run=false` 时从词表中清理（不可逆，建议先 preview）
- 黑名单保护：领域核心词（PET/DL/RAG/polymer 等）永不清理
- 垃圾模式自动检测：章节标题、测试标签、特殊字符、过短标签

## V8 — Experience Health

`mcp__kb-mcp__experience_check_stale_global()`
`mcp__kb-mcp__experience_dashboard(kb_id)` — 对每个有经验的 KB

- orphan 经验：关联文档已删除 → 建议 `mcp__kb-mcp__experience_delete` 或更新 `related_docs`
- stale 经验：文档已更新但经验未同步 → 建议 `mcp__kb-mcp__experience_sync_kb`
- 测试污染：rating=0, applied=0, age>7d → 建议清理
- 低质经验：rating<2, review≥3 (disputed) → 建议审查

## V9 — Auto-Fix

当 V1-V8 检测到问题后，可执行的自动修复路径：

| 检测到的问题 | 自动修复路径 |
|------------|------------|
| 重复 Collection | `mcp__kb-mcp__kb_cleanup_orphan_collections(dry_run=false)` |
| 孤 tag | `mcp__kb-mcp__kb_tags_cleanup(dry_run=false)` |
| 文档缺向量索引 | `mcp__kb-mcp__kb_index_document(kb_id, doc_path)` |
| 文档缺图谱索引 | `mcp__kb-mcp__kb_graph_build_kb(kb_id, force=false)` |
| 元数据不一致 | `mcp__kb-mcp__kb_reindex(kb_id, force=true)` 重建 |
| orphan 经验 | `mcp__kb-mcp__experience_delete(kb_id, exp_id)` 或 `mcp__kb-mcp__experience_update(related_docs=[])` |
| test 经验污染 | `mcp__kb-mcp__experience_delete(kb_id, exp_id)`（确认后） |

**Auto-fix 原则**：只修复可自动检测+可自动修复的问题；破坏性操作（删文档/删KB/合并KB）需用户确认。

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 无用户指令就执行 V4/V7/V9 修复 | 读-only 被破坏 | 先报告结果，等用户说"修"再动 |
| 只用 `kb_list` 判断 KB 健康 | 缺失文档级检查 | 必须配合 `kb_get_documents` + 磁盘校验 |
| 大批量 doc_read 无进度汇报 | 用户以为卡死 | 大库（>50）时报告进度"x/50 已检查" |
| Neo4j 挂了就不做其他检查 | V1-V4 V6 不依赖 Neo4j | 跳过 V5 Graph Health，其他照常 |
| 评分报告不写修复建议 | 用户看了不知道先修哪个 | V6 必须含"首要建议" |
