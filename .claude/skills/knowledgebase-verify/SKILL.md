---
name: knowledgebase-verify
description: Knowledge base integrity and quality validation. V1→V6: check KB health, validate three-way metadata consistency (disk ↔ .tree-fs.json ↔ .knowledge-base.yml), verify parse quality, detect corruption, check vector_index/graph_index coverage, generate structured integrity report. Invoked by Archival when the collection needs a health check. Trigger keywords: 校验, 核对, 完整性, 健康检查, 验证, 检查, 一致性, verify, validate, integrity, health check, quality audit, check KB, 检测问题, 审计知识库.
---

# Knowledge Verify — Integrity & Quality

**⭐ MCP 优先原则（强制）**：所有 kb-mcp 操作必须通过 MCP 工具执行（`mcp__kb-mcp__*`）。禁止用 `curl`/`python -c`/`wget` 等终端命令或直调 HTTP API。MCP 不可用时才可向用户报告。

**Read-only by default.** V4 repair requires explicit user instruction.

---

## 思维框架：先判断校验重点 ⭐

```
用户说"校验/检查"
    │
    ├── 怀疑元数据不一致 → V1 Three-Way Metadata
    ├── 文档打开报错/404 → V2 Document Integrity
    ├── 解析 PDF 后内容乱码 → V3 Parse Quality
    ├── 搜不到文档 → V4 Index Coverage
    ├── "彻底审计" → V1→V6 全流程
    └── 指定了某个 KB → 只跑该 KB 的完整流
```

### 校验策略选择

| 场景 | 广度 | 深度 | 耗时 |
|------|------|------|------|
| 快速检查 | V1 + V5 仅统计 | 抽样 10% | ~10s |
| 常规健康检查 | V1→V6 | 正常采样 | ~60s |
| 深度审计 | V1→V6 全量 | 每个文档 | ~5min+ |
| 修复后验证 | V4 索引 + V5 评分 | 对比前后 | ~30s |

---

## V1 — Three-Way Metadata Integrity
1. `kb_list()` vs `fs_get_tree()` — flag KBs with no tree node, orphan nodes, doc count mismatches.
2. For each KB: `kb_get_documents(kb_id)` — check each doc has a matching file on disk.
3. Check UUID consistency between `.tree-fs.json` and `.knowledge-base.yml`.
4. Flag: phantom entries (metadata but no disk file), orphan files (disk but no metadata), UUID mismatches.

## V2 — Document Integrity
`kb_get_documents(kb_id)` → sample `kb_doc_read` (1-10 docs: all; 11-50: 50%; >50: first 20).
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
`kb_doc_read` 2000 chars on parsed docs (infer from .pdf/.docx names).
Flag: empty content (<100 chars), OCR garbage, binary residue, heading-only (no body).

Use `backend_status()` for MinerU health (authoritative).

## V4 — Index Coverage & Repair
### Vector
`kb_get_documents(kb_id)` → check `vector_index` field per doc. `kb_search_stats(kb_id)` → check chunk counts.
**Repair**: `kb_index_document(kb_id, doc_path)` or `kb_batch_index(kb_id, [paths], force=true)`.

### Graph
`kb_graph_health()` → Neo4j available? `kb_graph_kb_overview(kb_id)` → doc_count vs actual.
**Repair**: `kb_graph_build_kb(kb_id, force=true)`.
**Clean stale**: `kb_graph_delete_document(doc_path)` for deleted docs.

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

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 无用户指令就执行V4修复 | 读-only被破坏 | 先报告结果，等用户说"修"再动 |
| 只用 `kb_list` 判断 KB 健康 | 缺失文档级检查 | 必须配合 `kb_get_documents` + 磁盘校验 |
| 大批量 doc_read 无进度汇报 | 用户以为卡死 | 大库（>50）时报告进度"x/50已检查" |
| Neo4j 挂了就不做其他检查 | V1-V4 V6 不依赖 Neo4j | 跳过 V5 Graph Health，其他照常 |
| 评分报告不写修复建议 | 用户看了不知道先修哪个 | V6 必须含"首要建议" |
