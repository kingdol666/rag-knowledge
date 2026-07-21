---
name: knowledgebase-organize
description: >
  Full collection restructuring engine. O0→O13 workflow: hierarchical discovery
  (sub-KB split detection + cross-KB merge analysis), deep content audit (1000+
  chars per doc), tiered fix execution, sub-KB auto-creation, cross-KB merge,
  parent restructuring, vector index + graph rebuild, three-way consistency,
  hygiene cleanup. No document splitting. Triggered by: 整理, 清洗, 重组, 审计,
  重构, 盘点, 全面梳理, organize, restructure, audit, cleanup, reorganize,
  清洗知识库, 整理知识库, 大扫除, 归并, 合并, 拆分, 细分, 分层, 归档, 归类.
---

# Knowledge Organize — 全库智能化重组引擎

**执行者：Archival agent — 必须委托 `Agent(subagent_type="archival", ...)` 执行**

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
3. **拆分决策不可跳过** — 每个 ≥6 篇的 KB 必须检查是否需要拆分子 KB
4. **合并决策不可跳过** — 每对领域重叠的 KB 必须评估是否能合并
5. **禁止文件拆分** — 文档作为完整单元，不截断/摘要/拆分
6. **⭐ MCP 优先** — 所有操作通过 MCP 工具，禁止终端/HTTP 绕行
7. **先确认再执行** — 任何不可逆操作（删除/合并 KB）必须用户确认后才执行

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
```

> ⏱ 估算：每篇 ~1s，100 篇约 2 分钟。

**注意**：KB 数 > 10 时内容审计委托子 Agent `Agent(subagent_type="archival", prompt="audit KB docs...")`，并行处理 4 个 KB 为一组。

---

## O3 — 层级拓扑分析 ⭐（新增核心能力）

### 3a. 子KB 拆分检测

对每个文档数 **≥6** 的 KB，分析其内容子领域分布。
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

## O4 — 修复执行（按层级顺序执行，每层完成后立即 O5 验证）

### L1 描述修复（元数据层·零风险）

修复 C1（描述质量）和 C6（KB 描述）：

```
for each doc with desc_quality ≠ OK:
    kb_doc_update_meta(kb_id, doc_path, description=<新描述>)

for each KB with generic/empty description:
    kb_update(kb_id, description=<新描述>)
```

**描述质量标准**（四要素）：
1. 文档核心主题（基于 1000 chars 内容）
2. 数据类型（论文/报告/规程/规范/手册）
3. 技术领域/子领域
4. 关键实体/设备/工艺

### L2 标签卫生（元数据层·零风险）

```
# T1 黑名单清除
黑名单: "doc", "文档", "file", "test", "测试", "misc",
        "general", "其他", "temp", "暂存"
for each doc with blocked tag:
    kb_doc_update_tags(kb_id, doc_path, tags=[filtered])

# T2 同义合并 + 归一化
    "PET" / "pet" / "pet" → "PET"
    "聚乙烯" / "PE"  → "PE"
    "机器学习" / "Machine Learning" → "machine-learning"

# T3 计数修复（每篇 2-5 标签）
for each doc with tags < 2:
    kb_doc_update_tags(kb_id, doc_path, tags=[补全标签])
```

### L3 文档重分类（移动层·需验证）

```
for each doc with kb_alignment = MISMATCH:
    kb_doc_move(doc_path, correct_kb_id)
    kb_index_document(kb_id=correct_kb_id, doc_path=<新路径>)
```

### L4 子KB 拆分（结构层·需用户确认）

对 O3a 检测出的每个可拆分 KB：

```
# 1. 为用户展示拆分方案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📦 KB 拆分建议: <KB名称>

  当前: <N> 篇文档
  建议拆分为以下子知识库:
  ┌─────────────────────────────────────────┐
  │ 子KB        │ 文档数 │ 内容子领域         │
  │─────────────┼────────┼──────────────────┤
  │ <Sub-KB-1>  │ <N>    │ <子领域描述>       │
  │ <Sub-KB-2>  │ <N>    │ <子领域描述>       │
  │ …           │ …      │ …                 │
  │ [根KB保留]  │ <N>    │ 跨领域/通用         │
  └─────────────────────────────────────────┘

  是否执行？[Y/n/修改]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 2. 用户确认后执行
for each sub_domain:
    kb_create(name="<KB>-<Sub>", description="...", parent_id=parent_kb_id)
    for doc_path in sub_domain.docs:
        kb_doc_move(doc_path, sub_kb_id)

# 3. 更新父 KB 描述
kb_update(kb_id=parent_kb_id, description="<更新>。子KB：[Sub1], [Sub2]...")

# 4. 索引重建
for each new sub_kb:
    kb_batch_index(kb_id=sub_kb_id, force=true)
```

### L5 跨KB 合并（结构层·需用户确认）

对 O3b 检测出的每对可合并 KB：

```
# 1. 展示合并方案
# 2. 用户确认后执行
target_kb = kbA (保留)
source_kb = kbB (被合并)

# 2a. 若 kB 的文档形成独立子领域 → 创建子KB
target_sub = kb_create(name="<target>-<sub>", ..., parent_id=target_kb_id)
for doc in source_kb.docs:
    kb_doc_move(doc.doc_path, target_sub_kb_id)
else:
    # 2b. 直接合并到目标
    for doc in source_kb.docs:
        kb_doc_move(doc.doc_path, target_kb_id)

kb_delete(source_kb_id)
kb_batch_index(target_kb_id, force=true)
kb_graph_build(target_kb_id, force=true)
```

### L6 KB 层级重组（结构层·需用户确认）

对需要重组的 KB 层级进行：

```
# 场景 1: flat → 创建父 KB
kb_create(name="<父-KB>", description="...")
for each sub_kb in [sub_kbs]:
    kb_update(parent_id=new_parent_kb_id)

# 场景 2: 重命名/归位
kb_update(kb_id=<id>, name="<新名称>", description="<新描述>")

# 场景 3: 删除空/测试 KB
kb_delete(test_kb_id)
```

### L7 索引 + 图谱重建（基础设施层）

```
# 7a. 向量索引覆盖
for each kb:
    docs = kb_get_documents(kb_id)
    missing = [d for d in docs if not d.vector_index]
    if missing:
        kb_batch_index(kb_id, [d.path for d in missing], force=true)

# 7b. 知识图谱重建
for each kb:
    kb_graph_build(kb_id, force=true)

# 7c. 全库图谱 —— 按需（KB 数 > 5 且都有文档）
kb_graph_build(kb_id="", force=true)    # 空 = 全库
```

---

## O5 — 逐层验证

每层修复完成后立即验证：

| 修复 | 验证方法 |
|------|----------|
| L1 描述 | `kb_doc_read` 500 chars 确认新描述 |
| L2 标签 | `kb_get_documents` 检查 tags 数组 |
| L3 重分类 | `kb_get_documents(source)` 确认离开, `kb_get_documents(target)` 确认到达 |
| L4 子KB | `kb_list()` 子 KB 可见, `kb_get_documents(sub_kb)` 文档正确 |
| L5 合并 | 源 KB 已删除, 目标 KB + 子KB 文档正确 |
| L6 层级 | `fs_get_tree(max_depth=3)` 层级正确 |
| L7 索引 | `kb_search_stats(kb_id)` 确认 collection + chunks ≥ 1 |

---

## O5b — 元数据三级一致性校验 ⭐（强制，结构变更后必须执行）

每个 L3/L4/L5/L6 操作完成后，**必须**校验三层元数据：

```
# 1. 三层存在一致性
for each affected KB:
    kb_get_documents(kb_id)            # 返回 metadata 列表
    for each doc in metadata:
        disk_exists = fs_get_children(parent_id=<dir>) 检查所有 .md
        treefs_exists = doc in .tree-fs.json
        yml_exists = doc in .knowledge-base.yml

# 2. UUID 同步校验
# 移动/创建后 UUID 是否一致，若有分叉重新注册

# 3. 文件内容校验
# 随机抽查 20% 的文档：kb_doc_read → 确认返回正确内容
```

**校验规则**：
- 三层中任一缺失 → 标记 `INCONSISTENCY`，重新注册缺失层
- UUID 不一致 → `kb_doc_move` 后原路径 UUID 可能残留，清理
- 内容读取失败 → 文件可能损坏或路径指向错误

```
# 实例修复：三层不一致
if tree_entry.missing_on_disk:
    kb_doc_delete(kb_id, doc.doc_path)    # 清理幽灵 entry
elif disk_file.missing_in_treefs:
    kb_doc_create(kb_id, name, content, description)  # 重新注册
elif yml_entry.missing:
    kb_doc_update_meta(kb_id, doc.doc_path, description=<补全>)  # 补全 YAML
```

---

## O6 — 经验联动

```
for each KB that had structural changes (L4/L5/L6):
    experience_check_stale(kb_id)
for each stale experience:
    report to user — "N 条经验的关联文档已迁移，建议 review"
```

---

## O7 — 自定义合规策略（高级）

用户可指定额外合规要求。默认全部执行，用户说"只修描述和标签"则仅执行 L1+L2+L7。

| 策略 | 含义 | 层级 |
|------|------|------|
| `strict_descriptions` | 每篇必须四要素描述 | L1 |
| `clean_tags` | 无黑名单 + 归一化 + ≥2 标签 | L2 |
| `align_docs` | 所有文档归属正确 KB | L3 |
| `split_kbs` | ≥6 篇 + ≥2 子领域 → 拆分 | L4 |
| `merge_kbs` | 重叠 → 合并 | L5 |
| `hierarchy` | 补全层级树 | L6 |
| `full_index` | 向量 + 图谱覆盖 | L7 |

---

## O8 — 终验报告

```
═══════════════════════════════════════════════════════════
  📋 整理完成报告

  前状态:        <N> KBs, <N> 篇文档, <N> 个子KB
  后状态:        <N> KBs, <N> 篇文档, <N> 个子KB

  L1 描述修复:   <N> 篇文档, <N> 个 KB
  L2 标签修复:   <N> 篇文档, <N> 个标签
  L3 文档移动:   <N> 篇
  L4 子KB拆分:   <N> 个 KB → <N> 个子 KB
  L5 KB合并:     <N> 对合并
  L6 层级重组:   <N> 个 KB
  L7 索引重建:   <N> 个 KB, <N> 个 KB 图谱

  合规评分:
    C1 描述质量:  <M>/<N> (≥?%)
    C2 标签质量:  <M>/<N> (≥?%)
    C3 KB对齐:    <M>/<N> (≥?%)
    C4 向量索引:  <M>/<N> (≥?%)
    C5 图谱覆盖:  <M>/<N> (≥?%)
    C6 三级一致:  <M>/<N> (≥?%)

  待处理:
    - <N> 条经验需 review（文档已迁移）
═══════════════════════════════════════════════════════════
```

---

## 执行流程速查

```
O1 全局调研 → O2 深层审计 → O3 层级拓扑分析 → 展示方案
  │
  ├──→ (用户确认不可逆操作)
  │
  ├── L1 描述修复 ─── O5 验证
  ├── L2 标签卫生 ─── O5 验证
  ├── L3 文档重分类 ─ O5 验证
  ├── L4 子KB拆分 ──  O5 验证
  ├── L5 跨KB合并 ──  O5 验证
  ├── L6 层级重组 ──  O5 验证
  ├── L7 索引+图谱 ─  O5 验证
  │
  ├── O6 经验联动 ─── O8 报告
  └── 
```

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
