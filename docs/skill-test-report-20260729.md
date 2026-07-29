# RAG Knowledge Platform — 全流程 QA 测试报告

> 测试日期: 2026-07-29 | 测试方式: 8 个 archival 子 Agent 并行端到端测试
> 测试范围: 14 子 skill + 71 MCP 工具全链路 | 测试数据: 8 个隔离 `QA-` 测试 KB（测后全删）
> 测试原则: 发现大逻辑 bug，小问题（文案/性能/样式）忽略

## 一、测试概览

| 模块 | Agent | 工具数 | 结果 | 大 bug | 耗时 |
|------|-------|--------|------|--------|------|
| Ingest 入库 (A0-A9) | IngestTest | 19 | 15 PASS / 4 PASS+bug | 2 | 9m |
| Search 搜索 (QDCVR) | SearchTest | 9 (24 calls) | 22 PASS / 2 FAIL | 1 | 7m |
| Search-Enterprise 跨库 | SearchEnterpriseTest | 10 | 11 PASS / 2 FAIL | 1(+2) | 12m |
| Graph 知识图谱 | GraphTest | 18 | 18 PASS (机械) | 2(+2) | 12m |
| Experience 经验 (E0-E12) | ExperienceTest | 26 | 23 PASS / 2+bug | 1(+1) | 10m |
| List + FS 文件系统 | ListFSTest | 16 | 16 PASS / 0 FAIL | 0 | 6m |
| Manage CRUD (M1-M6) | ManageTest | 22 | 14 PASS / 5 partial / 1 FAIL | 3(+2) | 17m |
| Verify + Batch (V/B) | VerifyBatchTest | 19 | 19 PASS / 0 FAIL | 0 | 14m |

**总计**: 8 模块, ~139 工具调用点, 138 PASS, 确认 **9 个大逻辑 bug + 多个文档不符项**。

---

## 二、大 Bug 汇总（按严重度排序）

### 🔴 CRITICAL — KB 改名系统性破坏三层一致性
**来源**: ManageTest BUG#1-4 | **复现率**: 100%
- **根因**: `kb_update(name=)` 只级联更新 ①磁盘 + ②tree-fs.json，**不更新 ③.knowledge-base.yml** —— 所有文档条目保留旧 KB 文件夹路径，①② 与 ③ 永久分裂。
- **级联破坏**:
  1. `update_meta` 在改名 KB 上产生 **ghost YML 条目**（新路径条目 + 旧路径残留，删不干净）
  2. **整个 KB 向量搜索失效** —— `kb_search_vector` 返回 0（向量 chunk 保留旧 doc_path 前缀被过滤），跨库搜索也不浮现
  3. `kb_doc_update_tags` 彻底 **404**（新路径 YML 无 / 旧路径磁盘无）
- **临时缓解**: 对 KB 内任一文档执行一次 `kb_index_document` 可恢复整个 collection 搜索能力；彻底修复需 `kb_reindex(force=true)`。
- **建议修复**: `kb_update` 重命名逻辑须遍历 YML 文档条目做路径替换，并触发向量层 doc_path 重写。

### 🔴 CRITICAL — 向量 collection 命名分裂（NAME 键 vs UUID 键）
**来源**: ManageTest BUG#5 / ExperienceTest MAJOR / VerifyBatch #3 | **复现率**: 100%（系统性）
- **现象**: `kb_doc_move`、`experience_update`（及部分路径）把向量写入 `kb_<KB_NAME>` collection，而 create/approve 用 `kb_<KB_UUID>`。
- **后果**: 
  - 被移动文档 / 更新经验在目标位置**向量隐形**（`kb_search_vector` 返回 0）
  - 经验更新后向量检索返回**陈旧值**（severity / applied_count / rating_avg 全是旧的）
  - 产生孤儿 collection（路径键版本 + UUID 键版本并存）
- **证据**: 与平台自身经验 `exp-87993d41a050` 记录的"双 collection 根因"完全吻合，本测试直接复现。
- **建议修复**: 统一 collection 命名键为 UUID；写入路径全量校验。

### 🟠 MAJOR — 图谱标签关系层从未创建 + 单 KB 构建不产生关系
**来源**: GraphTest BUG#1-2
- **BUG#1**: `kb_graph_build` 的 `_write_doc_metadata` 只建 Document/KB/BELONGS_TO 节点，**从不建 Tag 节点或 HAS_TAG 边** → `_relate_by_shared_tags` 查询恒为 0，标签关系推理整体失效（全局 `tag_count=0` 印证，尽管 tag 词汇表有 150 个）。
- **BUG#2**: 单 KB `kb_graph_build` 不调用 `_build_vector_similarity_edges`（该函数只被全局 `build_all_graphs` 调用）→ **新建 KB 关系图为空**，4 篇强相关文档全部 degree:0。
- **影响**: 新建 KB 的图谱关系推理功能失效。既有 13 KB 的关系（vector_similar 2382 边）靠历史全局 build 产生，增量/单 KB build 无法获得。
- **建议修复**: `build_kb_graph` 须调用向量相似度边构建；`_write_doc_metadata` 须建 Tag 节点 + HAS_TAG 边。

### 🟠 HIGH — 并发双重索引竞态（静默失败）
**来源**: SearchEnterpriseTest
- **现象**: `kb_doc_create` 的 fire-and-forget 自动索引 + 立即并发 `kb_index_document` → ChromaDB 进入"chunks 已计数但不可查询"状态。
- **后果**: `kb_index_document` 报 success、`kb_search_stats` 显示 chunks，**但 `kb_search_vector` 持续返回空**，直到 `kb_reindex(force=true)`。
- **关键**: 这正是文档推荐的 happy-path 流程，时延假设已排除（累计等 35s+ 仍空）。
- **建议修复**: `kb_index_document` 对进行中的自动索引去重/加锁/等待。

### 🟠 HIGH — kb_search_two_stage 忽略 top_k 参数
**来源**: SearchTest
- **现象**: `top_k=2` 返回 `total_results=15`；`top_k=5` 返回 10。stage2 直接返回 stage1 候选全部 chunk，未施加 top_k 截断。
- **对比**: `kb_search_vector` 严格遵守 top_k（3→3, 5→5）。两工具行为不一致，大库返回量不受控。
- **建议修复**: two_stage 的 stage2 须对最终结果施加 top_k 截断。

### 🟡 MEDIUM 级 bug
| # | Bug | 来源 |
|---|-----|------|
| 6 | `experience_search_smart(kb_id)` scope 未生效 —— 传入自己的 KB 却返回其他 KB 经验 | ExperienceTest |
| 7 | `kb_search_two_stage` 的 `source` 标签恒报 `keyword`（stage1=0 候选仍返回向量结果标 keyword，失真） | SearchEnterpriseTest |
| 8 | `kb_doc_update_tags` 无垃圾标签门控（纯数字 `123`/单字母 `x` 被接受） | IngestTest |
| 9 | `balance_kbs` 参数无可见效果（大库仍按体量主导） | SearchEnterpriseTest |

---

## 三、文档与实现不符（需更新文档/经验库）

| 文档声明 | 实际行为 | 评级 |
|---------|---------|------|
| `kb_doc_update_content` **不会**自动重索引④，需手动 `kb_index_document` | 实际返回 `_auto_index.triggered=true`，<1s 内向量更新（**对用户是改善**） | 文档过时 |
| `kb_doc_delete` 留向量残留，需 `kb_reindex(force)` | 实际 delete 会清理向量（chunk_count 下降） | 文档过时 |
| `kb_doc_save_parsed` 会 auto-index | 实际**不**自动索引，须显式 `kb_index_document`（与 `kb_doc_create` 不一致） | **真不一致** |

---

## 四、健康模块（无大 bug，按规范作业）

- **List + FS**（16 工具全 PASS）: `documentCount` 跨工具准确、三层同步完整、`fs_upload_file` 原子同步①②③、8 个只读工具无副作用。
- **Search 向量链路**: `kb_search_vector` 相关性优秀（top1 正确）、返回结构正确、鲁棒性强（空查询/非法 kb_id/600 字 query 全优雅处理）。
- **Ingest 主链路**: 解析非阻塞正常（~15s）、三层原子同步①②③生效、自动后台索引快速可靠（<250ms）。
- **Experience E0-E12**: 22 工具全生命周期打通无断裂，评分/应用/衰变状态一致，meditation scope 隔离不污染全局调度器。
- **Verify + Batch**: `dry_run` 安全模式真实有效，CRUD 原子同步①②③④ 正确，`kb_batch_index` 具 per-doc 索引状态检测，`reindex` 内置可查询性自检。

### 已证伪的"大 bug 候选"
- **孤儿图数据 26 vs 13**: 经删除前后图计数对比 + 口径分析**证伪**。图 kb_count 计入子 KB（13 顶层 + ~13 子 KB ≈ 26），且 `kb_delete` 会正确清理图节点。非数据损坏。

---

## 五、根因聚类（3 个根因解释 9 个大 bug）

1. **写操作的路径/命名键级联不完整**（占 5 个 bug）: KB 改名不更新 YML③层；向量 collection 用 NAME 键而非 UUID 键（move/update/experience）。→ 修复 kb_update 级联 + 统一 collection 命名键。
2. **图谱构建逻辑缺失**（占 2 个 bug）: 标签层未实现 + 单 KB 构建漏调相似度边函数。→ 补全 build_kb_graph 逻辑。
3. **并发/参数处理**（占 2 个 bug）: 自动索引与显式索引竞态；two_stage top_k 未截断。→ 加锁去重 + 参数生效。

---

## 六、清理确认

- ✅ 8 个 QA- 测试 KB 全部 `kb_delete`（kb_list 13 个真实 KB 无残留）
- ✅ 向量 collection 0 孤儿 0 重复（随 KB 删除同步清理）
- ✅ 清理 23 个 0 引用孤儿 tag（含本次测试产生的 `123`/`x`/`qa-*`/`cleantag-*` 等），127 个有效 tag 保留
- ✅ 全局调度器/图谱/经验库未受污染，未触碰任何真实 KB

---

## 七、总体结论

**系统核心检索与入库能力健全**：向量搜索、文档入库、三层原子同步、经验全生命周期、跨库检索主干均按规范作业，鲁棒性强。

**存在一组围绕"重命名 / 移动 / 更新"写操作的一致性缺陷**，集中在上述 3 个根因，导致 9 个大逻辑 bug。其中 **KB 改名破坏三层一致性** 和 **向量 collection 命名分裂** 为最高优先级（CRITICAL），建议优先修复。图谱模块的标签关系层与单 KB 构建逻辑为功能缺失（MAJOR），影响新建 KB 的关系推理。

其余小问题（路径分隔符跨工具不一致、字段命名 full vs lightweight 不统一、错误分类文案、source 标签失真等）按约定忽略。
