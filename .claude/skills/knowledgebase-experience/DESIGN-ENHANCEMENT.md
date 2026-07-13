# Experience Enhancement — KB文档→经验全自动流水线

> **问题**：当前经验是手工创建的（`experience-summarize` skill 靠会话中用户讲述），没有与知识库文档联动。文档入库后内容蕴含的经验因子未被提取，文档更新旧经验不会同步。

---

## 一、核心概念：经验 = 文档的"可操作精华"

### 文档 vs 经验

| 维度 | 文档 (KB Document) | 经验 (Experience) |
|---|---|---|
| 粒度 | 全文/整篇论文 | **单点知识**（一个问题→一个方案→一个教训）|
| 结构 | 自由 markdown | 结构化 JSON（scenario/problem/solution/lessons）|
| 场景 | 阅读、学习、参考 | **检索、应用、快速查阅** |
| 可信度 | 静态 | **动态**（review/apply 评分 → P0/P1/P2 衰减）|
| 变更 | 手动索引刷新 | 文档变更时**自动联动更新** |

**核心理念**：每篇文档 = 1 个或多个结构化经验的"矿源"。入库时自动提炼，入库后联动更新。

---

## 二、全链路架构

```
                    +---------------+
                    |  文档入库     |
                    |  (Ingest A5)  |
                    +-------+-------+
                            |
                  经验自动提取 (E1)
                            |
                    +-------v--------+
                    |   经验草稿池   |
                    |  .experience/  |
                    +-------+--------+
                            |
                     Agent 审核确认 (E2)
                            |
                    +-------v--------+
                    |  experience_store|
                    |  (SQLite/JSON)  |
                    +-------+--------+
                           / \
                          /   \
                 +-------v-+ +-v--------+
                 |检索时优先 | |文档更新时 |
                 |(E4/E5)   | |自动联动(E6)|
                 +----------+ +----------+
```

---

## 三、12 步经验生命周期（E0→E11）

### E0 — 经验扫描（新增，文档入库触发）
文档入库完成（A7 终检通过）后自动触发。读取文档全文（`kb_doc_read` 20000 chars），发现经验候选点：

```
输入：文档全文 markdown
输出：[{scenario, problem, solution, key_lessons, tags, severity}]
```

**检测启发式**：
- **方法类文档**（含"method/approach/proposed"）→ 输出 `method/documentation` 类型经验
- **故障类文档**（含"failure/error/issue/problem"）→ 输出 `troubleshooting` 类型经验  
- **对比类文档**（含"comparison vs better than improvement"）→ 输出 `lessons_learned` 类型经验
- **综述/教程** → 输出多个 `best_practice` 类型经验（每节一个）

### E1 — 批量经验提炼（新增，全库/选库扫描）
```
experience_extract_all(dry_run=True)   → 发现全库候选经验（预览、不写入）
experience_extract_kb(kb_id, doc_paths=[], dry_run=True)  → 指定KB的文档扫描
```

| 参数 | 说明 |
|---|---|
| `kb_id` | 目标 KB（空=全库）|
| `doc_paths` | 可选，只扫指定文档 |
| `dry_run` | True=只报告候选（默认）；False=创建草稿 |
| `min_confidence` | 0-1，控制提取严格度（默认 0.7）|

**返回**：
```json
{
  "total_candidates": 5,
  "experiences": [{
    "source_doc": "AI-ML-Research/RAG-Survey.md",
    "confidence": 0.92,
    "title": "RAG 减少幻觉的三重机制",
    "scenario": "llm-hallucination-mitigation",
    "category": "best_practice",
    "problem": "LLM 生成内容存在幻觉、知识过时、推理不可追溯",
    "solution": "通过外部知识库检索增强生成，减少模型仅依赖参数知识的幻觉",
    "key_lessons": ["引入外部知识库可减少幻觉", "检索与生成协同优于纯生成"],
    "tags": ["RAG", "LLM", "幻觉"],
    "severity": "important",
    "supporting_evidence": "原文 §2.1: 'RAG addresses these by incorporating knowledge from external databases...'"
  }, ...]
}
```

### E2 — 经验质量门控（新增）
候选写入前强制检查：

| 门控 | 规则 | 不通过则 |
|---|---|---|
| **G1 场景明确** | scenario 必须有领域前缀（如 `llm-hallucination`），禁止 `test` | 退回 |
| **G2 方案可操作** | solution ≥ 50 chars，含具体步骤/方法名 | 退回 |
| **G3 证据可追溯** | supporting_evidence 字段必须指向文档具体段落（原文行/节号）| 退回 |
| **G4 去重** | 同 KB 已有 scenario+problem 相似的经验 → 标记为"更新候选"而非新建 | 建议更新 |

**E2 有两种模式**：
- **自动模式**（默认）：confidence ≥ 0.8 直接入库，< 0.8 走草稿池等审核
- **审核模式**（全量）：全部进草稿池，Agent 逐条确认

### E3 — 草稿池管理（新增）
草稿存储在 `web/storage/tree-file-system/{kb_name}/.experience/` 目录：
```
.experience/
  draft/
    exp_001.json    # 待审核
    exp_002.json
  rejected/         # 用户拒绝的
  history/          # 已入库的历史版本
```

**工具**：
```
experience_drafts_list(kb_id)      → 列出所有草稿
experience_draft_read(draft_id)    → 查看草稿详情（含原文证据）
experience_draft_approve(draft_id) → 批准→写入正式经验
experience_draft_reject(draft_id)  → 拒绝（移至 rejected/）
experience_draft_batch(kb_id, approve_ids, reject_ids) → 批量处理
```

### E4 — 经验优先检索（强化现有 search skill）
**故障/运维型查询流程**（更新 `knowledgebase-search Step 0`）：

```
if 查询类型 in (故障型, 运维型):
    # 经验优先
    exp_results = experience_search_global(query, top_k=10)
    + experience_search_vector(query, top_k=5)
    → P0/P1 经验直接给出方案（不用读文档）
    → P2 经验 + 文档补充
    
    # 经验不够才补文档
    if exp_P0 < 2:
        kb_search_two_stage(query, balance_kbs=True, score_threshold=0.35)
```

### E5 — 经验可信度模型（强化现有）
现有模型（P0/P1/P2）保留，增加：

| 新增维度 | 规则 |
|---|---|
| **时效性加分** | 30 天内新建或更新 → 提 1 档 |
| **文档一致性加分** | 经验引用的文档与当前 KB 文档内容一致 → 提 1 档 |
| **文档不一致降级** | 文档已更新但经验未同步 → 降 1 档（触发 E6 联动）|
| **原创性加分** | `auto_extracted=true`（非手动创建）→ 标注来源 |
| **Dedup 惩罚** | 3 条以上同类经验 → 合并建议标记 |

### E6 — 文档更新→经验联动（新增，核心）
```
文档变更 → 触发 E6 检查
    │
    ├── kb_doc_update_content:
    │   └── 检查引用该文档的所有经验
    │       ├── 内容差异检测（旧版本 vs 新版本）
    │       ├── 标记 "stale" → exp.stale_since = now
    │       ├── 自动触发 E0 重新提取
    │       └── 报告变动：经验 X 的 §solution 需更新
    │
    ├── kb_doc_delete:
    │   └── 标记引用该文档的经验
    │       ├── related_docs 移除该路径
    │       └── 如果 related_docs 为空 → 标记 "orphan"
    │
    └── kb_doc_move:
        └── 自动更新经验中的 related_docs 路径
```

**E6 工具**：
```
experience_check_stale(kb_id)       → 检查 KB 内所有经验是否与关联文档一致
experience_check_stale_global()     → 全库检查
experience_sync(kb_id, exp_id)      → 单条经验从文档重新提取并更新
experience_sync_kb(kb_id)           → 整库同步
```

### E7 — 经验搜索增强（强化现有）
**搜索路径新增**：

```
故障型查询：
  experience_search_global(query, top_k=10)  ← 全库经验
  + experience_search_vector(query, top_k=5)  ← 向量精排
  + kb_search_two_stage(query, ...)           ← 文档补充

通用查询：
  kb_search_two_stage(query, ...)             ← 文档优先
  + experience_search(query, top_k=3)         ← 经验补充
```

### E8 — 经验统计与看板（新增）
```
experience_dashboard(kb_id) → 经验全貌
{
  "total": 42,
  "by_category": {"troubleshooting": 15, "best_practice": 12, ...},
  "by_severity": {"critical": 3, "important": 18, ...},
  "quality": {
    "p0_count": 8, "p1_count": 20, "p2_count": 14,
    "avg_rating": 3.8, "stale_count": 2
  }
}
```

### E9 — 经验导出/分享（新增）
```
experience_export(kb_id, format="markdown|json", 
                   include_stale=false, include_drafts=false)
→ 生成可分享的经验文档
```

### E10 — 批量经验操作（新增）
```
experience_batch_tag(kb_id, exp_ids, add_tags=[], remove_tags=[])
experience_batch_move(exp_ids, target_kb_id)    # 跨 KB 迁移经验
experience_batch_delete(kb_id, exp_ids)
experience_batch_rerate(kb_id, exp_ids)         # 重新评估 P0/P1/P2
```

### E11 — 经验自动衰减周期任务（新增）
```
experience_decay(kb_id) → 应用衰减规则
{
  "stale_unverified": ">30d no read → max P1",
  "disputed": "rating<2.0 with ≥3 reviews → max P2",
  "unvetted": "0 reviews ∧ 0 applied → max P1",
  "document_changed": "stale_since ≥ 7d → marked stale"
}
```

---

## 四、与现有 skill 体系集成

### 在 `knowledgebase-search` 的集成（Step 0 修改）

```diff
 故障/运维型查询 → 先查经验
+   experience_search_global(query, top_k=5)
+   experience_search_vector(query, top_k=3)
+   命中 P0/P1 经验 → 直接回答（跳过 kb_search_two_stage）
+   命中 P2 或无命中 → 补充文档检索
```

### 在 `knowledgebase-ingest` 的集成（A7→A8 之间加）

```diff
 A7 终检通过 → ✅
+  E0 自动经验扫描（可选，默认 enabled）
+    分析文档内容 → 提取候选经验
+    confidence≥0.8 自动入库 | <0.8 进草稿池
 A8 子KB评估 + 孤儿清理
```

### 在 `knowledgebase-organize` 的集成（O5 后加）

```diff
 O5 验证每个变更
+  O5-E 经验同步
+    experience_check_stale(kb_id)   # 整理后检查经验一致性
```

---

## 五、所需新增 MCP 工具

| 工具 | 用途 | 优先级 |
|---|---|---|
| `experience_extract_kb(kb_id, doc_paths, dry_run)` | KB/文档→经验提取 | **P0** |
| `experience_extract_all(dry_run)` | 全库扫描 | **P0** |
| `experience_drafts_list(kb_id)` | 草稿池查看 | **P0** |
| `experience_draft_approve(draft_id)` | 批准草稿 | P1 |
| `experience_draft_reject(draft_id)` | 拒绝草稿 | P1 |
| `experience_check_stale(kb_id)` | 检查经验与文档一致性 | **P0** |
| `experience_sync(kb_id, exp_id)` | 单条经验同步 | **P0** |
| `experience_sync_kb(kb_id)` | 整库经验同步 | P1 |
| `experience_dashboard(kb_id)` | 经验看板 | P2 |
| `experience_batch_tag(kb_id, exp_ids, ...)` | 批量打标 | P2 |
| `experience_decay(kb_id)` | 衰减周期 | P1 |

**不新增，只改 search skill Step 0 逻辑**（现有 `experience_search_global` + `experience_search_vector` 已够用）。

---

## 六、后端新增路由

```python
# /api/v1/experience/{kb_id}/extract  POST  → 提取经验
# /api/v1/experience/{kb_id}/drafts   GET   → 草稿列表
# /api/v1/experience/{kb_id}/drafts/{draft_id}/approve  POST → 批准  
# /api/v1/experience/{kb_id}/drafts/{draft_id}/reject   POST → 拒绝
# /api/v1/experience/{kb_id}/sync    POST  → 整库同步
# /api/v1/experience/{kb_id}/sync/{exp_id}  POST → 单条同步
# /api/v1/experience/{kb_id}/dashboard GET  → 经验看板
# /api/v1/experience/{kb_id}/decay   POST  → 衰减
# /api/v1/experience/export          GET   → 全库导出
```

---

## 七、实施路线

| 阶段 | 内容 | 依赖 |
|---|---|---|
| **Phase 1** | `experience_extract_kb` + `experience_check_stale` + `experience_sync` MCP 工具 | 后端路由 /api/v1/experience/{kb_id}/extract |
| **Phase 2** | 草稿池管理（drafts_list/approve/reject）| 后端 .experience/ 目录 |
| **Phase 3** | E6 联动（文档更新自动触发经验同步）| kb-mcp 增加文档变更 hook |
| **Phase 4** | Dashboard + Decay + 批量操作 | 后端统计聚合 |

---

## 八、预期效果

| 维度 | 现状 | 增强后 |
|---|---|---|
| 经验来源 | 仅用户手工创建 | **文档自动提取** + 手工 |
| 经验数量 | ~0（手动创建少） | 每 KB 的文档数 × 1.5~3（自动提取）|
| 检索体验 | 故障型需读文档全文 | **直接回答 P0 经验**，秒级 |
| 文档联动 | 无 | **文档更新→经验自动同步** |
| 草稿审核 | 无需 | 置信度门控保证入库质量 |
| 知识衰减 | 无 | 30 天衰减周期保持新鲜度 |
