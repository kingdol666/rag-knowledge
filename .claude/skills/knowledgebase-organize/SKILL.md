---
name: knowledgebase-organize
description: Full collection restructuring engine. O0→O13 workflow: define compliance criteria, deep survey (2000+ chars per doc), audit every document, content-driven reclassification, execute fixes (descriptions→tags→moves→KB ops), verify each change, auto-create sub-KBs, batch-fix descriptions, audit vector index coverage, clean 3-way consistency (disk↔.tree-fs.json↔.knowledge-base.yml), knowledge graph rebuild. No document splitting. Triggered by: 整理, 清洗, 重组, 审计, 重构, 盘点, 全面梳理, organize, restructure, audit, cleanup, reorganize, 清洗知识库, 整理知识库, 大扫除.
---

# Knowledge Organize — Collection Restructuring

**⭐ MCP 优先原则（强制）**：所有 kb-mcp 操作必须通过 MCP 工具执行（`mcp__kb-mcp__*`）。禁止用 `curl`/`python`/`wget` 等终端命令或直调 HTTP API 替代 MCP 工具。MCP 不可用时才可向用户报告让用户决策。

**执行者：此技能由 Archival agent 执行**
- 当 knowledgebase 调度器检测到对应场景后 → 路由到本 skill
- 本 skill **必须**委托 Archival agent（`Agent(subagent_type="archival", ...)`）执行

---

## 思维框架：整理前想清楚三件事 ⭐

1. **范围是什么？** — 全库整理还是单 KB？用户说了"整理"但没说范围？全库默认。
2. **修复优先级？** — 描述质量 > 标签规范 > KB归属 > 索引覆盖 > 图谱。不会全修？至少修前三项。
3. **哪些必须读？** — 2000 chars 不可省。不读内容直接改描述 = 猜，禁止。

---

Ensure every document meets all 6 compliance criteria. Documents failing any criterion are auto-fixed.

## Compliance Criteria (O0)
| # | Criterion | Check |
|---|---|---|
| C1 | Content-based description (not empty/filename/generic) | `kb_doc_read` 500 chars → compare |
| C2 | 2-5 content-relevant tags | `kb_get_documents` → check tags |
| C3 | Document domain matches its KB | Read 2000 chars → classify |
| C4 | Vector index present | Check `vector_index` in metadata |
| C5 | Graph index present | `kb_graph_kb_overview(kb_id)` |
| C6 | Disk ↔ .tree-fs.json ↔ .knowledge-base.yml consistent | Cross-reference |

## O1 — Full Survey
```
kb_list()
kb_tags_list()
fs_get_tree(include_files=True, max_depth=0)
```

## O2 — Deep Content Audit (Every KB, Every Document)

> ⏱️ 估算：每文档 ~2s（读+分类），100 篇文档约 3-4 分钟。大库（>50 文档）委派子 Agent 并行处理。

For each document:
```
content = kb_doc_read(kb_id, doc.doc_path, max_chars=2000)
```
Check C1-C6. Flag failures: `desc=MISSING/WEAK/MISMATCH`, `tags=INSUFFICIENT/GENERIC`, `kb=MISCLASSIFIED`, `index=MISSING`.

For KBs with >10 docs: delegate to sub-agent with content samples. Request JSON array with `doc_path, true_domain, description_quality, suggested_description, suggested_tags, kb_match`.

## O3 — Categorize KBs
Classify each KB: Compliant / Needs cleanup / Test-scratch / Empty / Domain overlap / Misclassified.

Reclassify misclassified docs: find correct KB by content domain → `kb_doc_move(doc_path, correct_kb_id)`.

## O4 — Execute Fixes (in order)
1. **Fix descriptions** (C1): `kb_doc_update_meta(kb_id, doc_path, description=suggested)` — 按 [description-guide.md](../knowledgebase-ingest/references/description-guide.md) 四要素+内容回查，拒绝泛泛描述
2. **Fix tags** (C2): `kb_doc_update_tags(kb_id, doc_path, suggested_tags)` — 严格按 [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md) T1黑名单+T2归一化+T3数量执行
3. **Move misclassified** (C3): `kb_doc_move(doc_path, correct_kb_id)` → `kb_index_document(kb_id=correct, doc_path=new_path)`
4. **KB ops**: merge (`move all → kb_delete`), rename (`kb_update`), delete (`kb_delete`)

### 高效批量修复技巧
- 大库（>10文档）委托子 Agent 并行生成建议，分 KB 执行
- 每次修复后立即 O5 验证，不要"先全修完再验证"——错了能及时停
- 描述修复用 `kb_doc_update_meta`（不改正文，只改元数据）

## O5 — Verify Each Change
After each fix: `kb_doc_read` / `kb_doc_get_by_tag` / `kb_get_documents` to confirm.

## O5-E — 经验联动（文档变更后必查）⭐
文档移动/重分类/改标签后，关联的经验可能失联。立即检查：
```
experience_check_stale(kb_id)      # 检查该 KB 经验与文档一致性
```
发现 stale 经验 → 标记 `needs_sync`，后续整理时更新。

## O6 — Orphan Cleanup
Check for orphaned `experience/` dirs, phantom `.tree-fs.json` entries. Report only — don't auto-delete.

## O7 — Compliance Scorecard
Re-audit all docs. Score: C1-C6 each as N/total (target 100%).

## O8 — Tag Hygiene
`kb_tags_list()` → `kb_doc_get_by_tag(tag)`. Clean strictly per [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md):

### 标签卫生执行顺序
1. T1 黑名单清除 → 丢弃章节标题 / 测试标签 / 描述性标签
2. T2 同义合并 → 大小写统一（PET/pet）→ 中英合并（聚乙烯/PE）
3. 孤儿清除 → 0 文档引用的标签自动消失（不操作，只验证）
4. 单文档独有且非新概念 → 归并主词

### 需要 `kb_doc_update_tags` 才能生效的操作
T1 和 T2 中被文档引用的标签，必须逐个文档更新：
```
kb_get_documents(kb_id) → 过滤含旧标签的文档 → kb_doc_update_tags(tags=新列表)
```
仅删除词表的标签不会自动从文档移除。

## O9 — Sub-KB Auto-Creation
If parent KB ≥8 docs across ≥2 sub-domains: create sub-KBs. See [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md).

## O10 — Vector Index Coverage
```
for each kb: docs = kb_get_documents(kb_id)
  missing = [d for d in docs if not d.vector_index]
  if missing: kb_batch_index(kb_id, [d.path for d in missing], force=true)
```
> 如果整个 KB 索引都有问题（如 collection UUID 不对齐），可改用 `kb_reindex(kb_id, force=true)` 全量重建。

## O11 — Three-Way Consistency
Cross-check disk ↔ `.tree-fs.json` ↔ `.knowledge-base.yml`. Fix: re-register via `kb_doc_create`, delete stale via `kb_doc_delete`, reindex via `kb_index_document`.

## O12 — Graph Rebuild
```
for each kb:
    if kb_graph_kb_overview(kb_id).doc_count < actual_doc_count:
        kb_graph_build_kb(kb_id, force=true)
```

## O13 — Final Report
KBs before/after, documents, moves, merges, deletions, fixes, reindexes, compliance scores.

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 不读 2000 chars 直接分类 | 文件名分类99%错 | 读正文 → 按 domain/sub_domain 分类 |
| 修复不验证就走下一步 | 描述改了但不对 | 即时 `kb_doc_read` 500 chars 对比 |
| 全修完再统一验证 | 中间错了无法回退 | 每步修完即 O5 |
| 不报告用户直接删 KB | 不可逆 | 报告 + 确认后再删 |
| 跳过 orphan cleanup | 幽灵 entry 积累 | O6 必须检查 |
| 认为 tags_list 清除了标签 = 文档标签已清 | 词表和文档标签是两回事 | 必须逐文档 `kb_doc_update_tags` 更新 |

## Critical Rules
- Read 2000+ chars per doc for classification — never classify by filename
- Every document is audited — no skips
- Fixes in order: descriptions → tags → moves → KB ops
- Verify each change immediately
- No document splitting — documents stay as single units
