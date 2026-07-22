---
name: knowledgebase-organize
description: >
  Full collection restructuring engine. O1→O8 workflow (plus O5b three-way
  consistency): hierarchical discovery (sub-KB split detection + cross-KB merge
  analysis), deep content audit (1000+ chars per doc), tiered fix execution,
  sub-KB auto-creation, cross-KB merge, parent restructuring, vector index +
  graph rebuild, three-way consistency, hygiene cleanup. No document splitting.
  Triggered by: 整理, 清洗, 重组, 盘点, 全面梳理, organize, restructure, cleanup,
  reorganize, 清洗知识库, 整理知识库, 大扫除, 归并, 合并, 拆分, 细分, 分层, 归档, 归类.
---

# Knowledge Organize — 全库智能化重组引擎
> **⭐ 操作前必读**：[kb-architecture.md](../knowledgebase/references/kb-architecture.md)（5层数据模型+一致性不变量+76工具地图）


**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

> **阈值权威源**：子KB 拆分/合并阈值统一定义在 [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md)。本 skill 与 Ingest A8 共享同一阈值（≥6 篇检查、≥8 篇自动拆分），避免不一致。

---

## 核心能力

此 skill 完成以下七类整理操作，按复杂度依次执行：

| 层级 | 操作 | 说明 |
|------|------|------|
| **L1** | 描述修复 | 内容驱动的文档/KB 描述重写 |
| **L2** | 标签卫生 | 黑名单清除 → 同义合并 → 孤儿清除 |
| **L3** | 文档重分类 | 错位文档移到正确 KB |
| **L4** | KB → 子KB 拆分 | 大 KB 按子领域拆分为子知识库 |
| **L5** | 跨KB 合并 | 重叠域名的 KB 合并为一个父 KB + 子 KB |
| **L6** | KB 层级重组 | 创建/重命名/重组父-KB-子KB 层级树 |
| **L7** | 索引 + 图谱重建 | 全库向量索引、知识图谱重建 |

---

## 思维框架：整理前想清楚五件事 ⭐

1. **用户说了什么范围？** — "整理全部"=全库；"整理热工"=单 KB；没说？先问。
2. **这个 KB 有几个子领域？** — ≥2 个子领域且 ≥6 篇文档 → 考虑拆分。
3. **有重复/重叠的 KB 吗？** — 内容重叠 ≥60% → 考虑合并。
4. **修复优先级？** — 描述质量 > 标签规范 > KB归属(L3) > 子KB拆分(L4) > 合并(L5) > 层级(L6) > 索引(L7)。
5. **那些必须读内容？** — 1000 chars 不可省。不读内容直接改归类 = 猜，禁止。

---

## 规则

1. **每条内容必须读 1000 chars** — `kb_doc_read(max_chars=1000)`，不得以文件名/路径替代
2. **修复逐批验证** — L1→L7 依次执行，每层完成即验证，不批量堆到最后
3. **拆分决策不可跳过** — 每个 ≥ `SUB_KB_CHECK_THRESHOLD`（≥6 篇，见 [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md) 权威源）的 KB 必须检查是否需要拆分子 KB
4. **合并决策不可跳过** — 每对领域重叠的 KB 必须评估是否能合并
5. **禁止文件拆分** — 文档作为完整单元，不截断/摘要/拆分
6. **⭐ MCP 优先** — 所有操作通过 MCP 工具，禁止终端/HTTP 绕行
7. **先确认再执行** — 任何不可逆操作（删除/合并 KB）必须用户确认后才执行
8. **单文档 KB 必须归并** — 仅 1 篇文档的 KB 不可独立存在，O3 中标记为"待归并"
9. **三轴权重自适应** — 标签词表为空时：entity_sim 升为 0.55，domain_sim 升为 0.45（tag 无数据不可信）
10. **O3 自动生成 combo** — O3a+O3b 跑完后必须生成合并+拆分的组合方案，不让用户手动组合

---

## O1 — 全局调研

```
kb_list()                              # 所有 KB（UUID + 描述 + 文档数）
kb_tags_list()                         # 全局标签词表
fs_get_tree(include_files=False, max_depth=0)  # KB 层级结构
```

**输出**：全库拓扑图 — 父KB、子KB、孤立KB、空KB、测试KB。

---

## O2 — 深层内容审计

> **并行加速**：KB 数 > 8 或总文档数 > 50 时，委托子 Agent 并行审计各 KB。

对每个非空 KB，逐文档读取内容并标记状态：

```
for each doc in KB:
    content = kb_doc_read(max_chars=1000)
    
    # 标记
    mark:
      desc_quality:    [OK | MISSING | FILENAME | GENERIC | MISMATCH]
      tag_quality:     [OK | EMPTY | GENERIC | BLOCKLIST | COUNT_LOW]
      domain:          <根据内容推断的子领域>
      kb_alignment:    [MATCH | MISMATCH]
      suggested_tags:  <[2-5 content-derived tags]>    ← ⭐ 审计时自动生成
```

> **标签在 O2 审计阶段自动生成**，不等到 L2。L2 只做清洗、归一化和批量写回。

> ⏱ 估算：每篇 ~1s，100 篇约 2 分钟。

**注意**：KB 数 > 10 时内容审计委托子 Agent `Agent(subagent_type="archival", prompt="audit KB docs...")`，并行处理 4 个 KB 为一组。

---

## O3 — 层级拓扑分析 ⭐（新增核心能力）

### 3a. 子KB 拆分检测

对每个文档数 ≥ `SUB_KB_CHECK_THRESHOLD`（**≥6 篇**，见 [sub-kb-creation.md](../knowledgebase-ingest/references/sub-kb-creation.md) 权威源表）的 KB，分析其内容子领域分布。
**必须使用** [sub-kb-creation.md 中的三轴相似度协议](../knowledgebase-ingest/references/sub-kb-creation.md#multi-dimensional-similarity-scoring)：

```
scan KB → 读每篇 1000 chars → 提取关键实体 → 归类子领域（同 entity_sim ≥ 0.4 归一组）
结果: {kb_id, kb_name, doc_count, sub_domains: {sub_domain: [doc_paths]}}
```

**拆分条件**：有 ≥2 个子领域（inter-group similarity ≤ 0.25），且每个子领域 ≥2 篇文档。

### 3b. 跨KB 合并检测

对所有 KB 对（尤其命名相似的），**必须**使用三轴综合相似度计算：

```
Axis 1 (0.3) = tag_similarity:    |tags(a) ∩ tags(b)| / |tags(a) ∪ tags(b)|
Axis 2 (0.4) = entity_similarity: |entities(a) ∩ entities(b)| / |entities(a) ∪ entities(b)|
Axis 3 (0.3) = domain_similarity: 三级分类对比 (l1/l2/l3)

total = 0.3*tag + 0.4*entity + 0.3*domain
```

完整决策矩阵见 [sub-kb-creation.md § 决策矩阵](../knowledgebase-ingest/references/sub-kb-creation.md#decision-matrix)。

### 3c. KB 层级分析

```
现状:
  flat：所有 KB 平铺，无父子关系
  partial：部分有父子，部分散落
  structured：已有完整层级

优化目标:
  flat → 创建父 KB，子 KB 归类
  partial → 补全缺失的父 KB
  structured → 验证分级是否合理
```

**输出**：`topology_report` — 列出每个 KB 的拆分/合并/层级建议。

> **关键**：此步结果必须向用户展示确认，不可逆操作（合并/删除）需用户批准。

---

## O4 — 修复执行（按层级顺序，每层完成即 O5 验证）

按 L1→L7 顺序执行，每层完成后立即验证。详细执行伪代码、对话模板、参数见 [execution-details.md](references/execution-details.md)。

| 层级 | 操作 | 风险 | 关键命令 |
|------|------|------|---------|
| **L1** 描述修复 | 内容型描述重写（四要素） | 零风险 | `kb_doc_update_meta` / `kb_update` |
| **L2** 标签卫生 | T1黑名单清除 + T2归一化 + T3计数 | 零风险 | `kb_doc_update_tags`（黑名单见 [tag-quality-rules.md](../knowledgebase-ingest/references/tag-quality-rules.md)） |
| **L3** 文档重分类 | 错位文档移到正确 KB | 需验证 | `kb_doc_move` + `kb_index_document` |
| **L4** 子KB 拆分 | O3a 检测的可拆分 KB | **需用户确认** | `kb_create(parent_id)` + `kb_doc_move` + `kb_batch_index(force=true)` |
| **L5** 跨KB 合并 | O3b 检测的可合并 KB 对 | **需用户确认** | `kb_doc_move` → `kb_delete(source)` + `kb_graph_build(force=true)` |
| **L6** KB 层级重组 | 创建/重命名/删除父KB | **需用户确认** | `kb_create` / `kb_update` / `kb_delete` |
| **L7** 索引+图谱 | 向量覆盖 + 图谱重建 | 基础设施 | `kb_batch_index(force=true)` + `kb_graph_build(force=true)` |

**L4 拆分/L5 合并必须展示方案等用户确认后才执行**（不可逆操作）。

---

## O5 — 逐层验证 + O5b 三级一致性

每层修复后立即验证（验证方法表见 [execution-details.md](references/execution-details.md) §O5）。

**O5b（强制）**：L3/L4/L5/L6 后必须校验三层元数据（disk ↔ .tree-fs.json ↔ .knowledge-base.yml）+ UUID 同步 + 20% 内容抽查。修复规则见 [execution-details.md](references/execution-details.md) §O5b。

---

## O6 — 经验联动

```
for each KB with structural changes (L4/L5/L6):
    experience_check_stale(kb_id)
for each stale experience:
    report — "N 条经验的关联文档已迁移，建议 review"
```

## O7 — 自定义合规策略

用户可指定额外合规要求。默认全部执行，用户说"只修描述和标签"则仅 L1+L2+L7。策略表（strict_descriptions/clean_tags/align_docs/split_kbs/merge_kbs/hierarchy/full_index）见 [execution-details.md](references/execution-details.md) §O7。

## O8 — 终验报告

前/后状态对比 + L1-L7 各层修复数量 + 合规评分（C1描述/C2标签/C3对齐/C4向量/C5图谱/C6三级一致）+ 待处理经验。

---


## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 不读 1000 chars 直接分类 | 文件名分类误差>90% | 读正文 → 按 domain/sub_domain 分类 |
| 不分析子领域就说"不需要拆分" | 全平铺 KB 是最差结构 | O3a 必须分析 |
| 跳过合并检测 | 重复 KB 是最大污染源 | O3b 必须分析 |
| 不用户确认就合并/删除 KB | 不可逆 | 展示方案 → 用户确认 → 执行 |
| 全修完再统一验证 | 中间错了无法回退 | 每层修完即 O5 |
| 认为 L4/L5 后不需要更新描述 | 父 KB 描述会过时 | O4 L4 #3 必须更新 |
| 移动文档后不索引 | 向量搜索漏召回 | `kb_batch_index` 必须在小循环后执行 |
| 大库不委派子 Agent | 响应太慢用户等不及 | >50 文档或 >8 KB → 并行 |
| 跳过 orphan cleanup | 幽灵 entry 积累 | O6 必须检查 |
| 认为 tags_list 清除了标签 = 文档标签已清 | 词表和文档标签是两回事 | 必须逐文档 `kb_doc_update_tags` |
