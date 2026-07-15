# 知识库系统 全局优化计划

> **基准测试报告**: [docs/skill-test-report-20260715.md](skill-test-report-20260715.md)
> **测试评分**: 9.4/10（5 场景 × Skill 体系全部通过，MCP 优先原则 100%）
> **编制日期**: 2026-07-15
> **基准 commit**: MCP 工具精简（75→73）已完成并验证

---

## 〇、测试报告关键发现

### 已确认问题

| # | 严重度 | 类别 | 问题 | 状态 |
|---|:---:|------|------|:--:|
| P1 | 🟡 中 | 经验孤儿 | `exp-31fef256582e` 关联文档 `GraphRAG.md`/`Self-RAG.md` 已删除 | ✅ 已修复 |
| P2 | 🟢 低 | Collection 重复 | `kb_Creative-Thinking-Innovation`（name-based, 0 chunks） | ✅ 已修复 |
| P3 | 🟢 低 | 测试污染 | 高分子库 4 条测试经验（rating=0, applied=0） | ✅ 已修复 |
| P4 | 🟢 低 | 孤 tag | 435 标签中大量 0 引用历史标签 | 🔧 Phase 1 |
| P5 | 🟢 低 | 层次 KB 文档数不准确 | 父 KB catalog 只显示容器文档数（1），实际含 12 子 KB | ⚠️ 已知 |

### 系统优势（保持不变）

| 领域 | 评级 | 说明 |
|------|:---:|------|
| MCP 工具层 | 🟢 优秀 | 73 工具完整，Server↔Agent 100% 对称 |
| QDCVR 检索 | 🟢 优秀 | 六步流程完整闭环，内容裁决机制独立于向量分 |
| 经验分级 | 🟢 优秀 | P0/P1/P2/DISCARD + E11 衰减规则正确 |
| 图谱引擎 | 🟢 优秀 | Neo4j 497 节点 / 3959 边，跨库桥接有效 |
| Skill 体系 | 🟢 优秀 | 12 个 Skill 全部流程完整，MCP 优先 100% 遵守 |

---

## 一、分阶段优化路线图

```
Phase 0: 立即修复    (1-2h)  → 清理已知问题
Phase 1: 数据卫生    (3-5d)  → 自动清理机制
Phase 2: 鲁棒性      (1-2w)  → 容错与恢复
Phase 3: 检索增强    (1-2w)  → 精准度提升
Phase 4: 运维自动化  (1-2w)  → 定时维护 + 监控
Phase 5: 体验优化    (2-4w)  → UX + 文档 + 测试
```

---

## Phase 0 — 立即修复（🔥 P0）

### 0.1 清理孤儿经验

**问题**: `exp-31fef256582e` 关联的 `AI-ML-Research/GraphRAG.md` 和 `Self-RAG.md` 已删除

**修复**:
```
experience_delete(kb_id="4c1b9eb6", exp_id="exp-31fef256582e")
```
**验证**: `experience_check_stale_global()` → orphan=0

### 0.2 清理重复 Collection

**问题**: `kb_Creative-Thinking-Innovation`（name-based, 0 chunks）与 UUID collection `kb_f1046402`(413 chunks) 重复

**修复**:
```
kb_cleanup_orphan_collections(dry_run=false)
```
**验证**: `kb_search_stats("f1046402")` → 仅 1 个 collection

### 0.3 清理测试污染

**问题**: 高分子双向拉伸文献库 4 条测试经验（rating=0, applied=0, credibility=0.3）

**修复**:
```
# 对每条测试经验执行
experience_delete(kb_id="cd57e37c", exp_id="<exp-id>")
```
**验证**: `experience_summary("cd57e37c")` → total=0

### 0.4 更新层次 KB 文档计数

**问题**: 父 KB（高分子双向拉伸文献库）`doc_count=1` 不反映 12 子 KB 真实文档量

**修复**: 后端 `kb_list` 聚合子 KB 文档数（或标注为层次型 KB）

---

## Phase 1 — 数据卫生自动化（🟡 P1）

### 1.1 自动孤儿 Tag 清理

**现状**: `kb_tags_list()` 返回 435 标签，大量为 0 引用历史标签（章节标题、测试标签等）

**方案**:
- 新增 MCP 工具 `kb_tags_cleanup(dry_run=true)`：
  - 遍历所有 KB 文档 → 统计每个 tag 的实际引用计数
  - 标记 0 引用 tag（排除已知领域词表）
  - `dry_run=false` 时从 `tags` 词表中移除
- 入库 Ingest A3b 黑名单增强：自动拦截章节标题模式（罗马数字+关键词、数字编号模式）

**验收**: `kb_tags_list()` count 从 435 降至合理范围（预期 ~250-300）

### 1.2 经验自动体检

**现状**: `experience_check_stale_global()` 可检测但不能自动修复

**方案**:
- 新建 Skill 步骤：`knowledgebase-experience` 新增 E12 定期体检
  - 自动检测 stale/orphan/测试污染
  - orphan → 自动标记 `needs_sync`，无法恢复则 30 天后自动归档
  - 测试经验（rating=0, applied=0, age>7d）→ 自动进回收站
- 新增经验回收站机制：软删除 → 30 天保留 → 到期永久删除

**验收**: `experience_check_stale_global()` → stale=0, orphan=0

### 1.3 Collection 一致性守护

**现状**: `kb_cleanup_orphan_collections` 为手动触发

**方案**:
- Ingest A6-V 索引后验证增强：若 collection UUID 与目标 KB UUID 不匹配 → 自动 alert
- Manage M4 移动文档后：自动验证新旧 collection 一致性
- 新增定时任务（Phase 4）：每周自动 `dry_run` + 报告

### 1.4 元数据一致性自动修复

**现状**: V1 三向元数据校验依赖手动 verify

**方案**:
- 新增 `kb_verify_auto_fix(kb_id)` 工具：
  - 磁盘有但 `.tree-fs.json` 无 → 自动注册
  - `.knowledge-base.yml` 有但磁盘无 → 自动清理元数据
  - UUID 不一致 → 自动对齐
- 所有写操作（create/update/delete/move）后自动运行 light 版本（仅当前文档）

---

## Phase 2 — 系统鲁棒性（🟡 P1）

### 2.1 Skill 执行容错

**现状**: Skill 步骤严格但缺少异常处理

**方案**:
| 故障场景 | 当前行为 | 改进 |
|---------|---------|------|
| MCP 工具超时 | 整个流程中断 | 自动重试 1 次 → 降级到替代工具 → 报告部分成功 |
| 解析任务失败（MinerU crash） | 未知 | `parse_task_status` 增加 `error` 状态 + 重试建议 |
| Neo4j 不可用 | 图谱步骤全部失败 | 跳过图谱步骤，完成其他校验，报告"图谱暂不可用" |
| ChromaDB 不可用 | 向量操作失败 | 自动重试，持久失败后降级到纯 BM25 |
| 磁盘空间不足 | 写入失败 | 写入前预检空间（`fs_get_count` + 文件大小估算） |

### 2.2 并发写入保护

**现状**: 无并发锁（CLAUDE.md 提到"并发锁（默认关）"）

**方案**:
- 启用并发锁：`.knowledge-base.yml` 写入时加文件锁（`fcntl.flock` / `msvcrt.locking`）
- 同一文档的并发写 → 排队
- 不同文档的并发写 → 允许

### 2.3 索引健康自动修复

**方案**:
- `kb_reindex(kb_id, force=true)` 增加 `--verify-only` 模式：仅检测不一致，不重建
- 入库完成 24h 后自动验证索引→检测遗漏 chunk
- 新增 `kb_index_verify(kb_id)` 工具：对比文档数 × 预估 chunks vs 实际 chunks

### 2.4 部分失败恢复

**方案**:
- 所有批量操作（Batch B1-B7）增加断点续跑：
  - 每处理 10 个文档记录一次 checkpoint
  - 失败后从 checkpoint 继续（不重做已成功的）
- Skill 步骤间状态持久化到 `.omc/state/kb-task-<id>.json`

---

## Phase 3 — 检索体验增强（🟢 P2）

### 3.1 QDCVR 精准度提升

**现状**: QDCVR 工作良好，但依赖 Agent 手动执行（非自动化）

**改进**:
| 环节 | 当前 | 改进 |
|------|------|------|
| Step 0 查询改写 | Agent 手动改写 | 预置改写模板（中英双语、多粒度）|
| Step 1 选库 | Agent 读 description 判断 | `kb_catalog` 增加领域词向量预匹配（快速初筛 top 3）|
| Step 2.5 去重 | Agent 手动逻辑去重 | `kb_search_two_stage` 内置文档级去重 + 短内容过滤 |
| Step 3 内容裁决 | Agent 手工 0-8 打分 | 增加 `kb_doc_relevance(query, doc_path)` 自动评分工具 |

### 3.2 混合检索增强

**方案**:
- 新增 `kb_search_hybrid(query, kb_id, top_k)`：自动融合 BM25+向量+图谱扩展
- 查询分类器：自动识别查询类型（事实/方法/对比/故障）→ 自动选择最优检索策略
- 结果摘要：对 P0 文档自动生成 2-3 句摘要（避免 Agent 读 3000 chars）

### 3.3 经验-文档双向链接

**现状**: 经验有 `related_docs` 但文档无 `related_experiences`

**方案**:
- `kb_doc_read` 返回增加 `related_experiences` 字段
- `kb_graph_document` 图谱视图增加经验节点和 `HAS_EXPERIENCE` 边
- 检索时同时返回文档 + 关联经验（无需二次查询）

---

## Phase 4 — 运维自动化（🟢 P2）

### 4.1 定时维护任务

**方案**: 新增 `kb_maintenance` 工具 + Skill

```
# 每日（轻量）
kb_maintenance(mode="daily"):
  - kb_cleanup_orphan_collections(dry_run=true) → 报告中异常
  - 检查 MinerU 健康

# 每周（标准）
kb_maintenance(mode="weekly"):
  - experience_apply_decay(all KBs)
  - experience_check_stale_global()
  - kb_tags_cleanup(dry_run=true)

# 每月（深度）
kb_maintenance(mode="monthly"):
  - 全库 reindex 验证
  - 图谱重建验证
  - 全面一致性审计（V1→V6）
  - 生成月度健康报告
```

### 4.2 系统健康看板

**方案**: 新增 `kb_health_dashboard` 工具

```json
{
  "services": {"backend": "healthy", "mineru": "running", "neo4j": "available", "chromadb": "ok"},
  "collection": {"total_kbs": 11, "total_docs": 140, "total_chunks": 1033},
  "quality": {"orphan_tags": "many", "orphan_collections": 0, "duplicate_collections": 1},
  "experience": {"total": 19, "orphan": 1, "stale": 0, "test_pollution": 4},
  "graph": {"nodes": 497, "edges": 3959, "health": "ok"},
  "last_maintenance": "2026-07-15",
  "alerts": [
    {"severity": "warning", "message": "1 orphan experience needs cleanup"},
    {"severity": "info", "message": "4 test experiences with rating=0"}
  ]
}
```

### 4.3 告警规则

| 条件 | 级别 | 动作 |
|------|:---:|------|
| orphan 经验 > 0 | ⚠️ Warning | 自动标记 + 通知 |
| stale 经验 > 5 | ⚠️ Warning | 触发 sync |
| orphan collection chunks > 100 | 🔴 Error | 立即通知（索引丢失） |
| Neo4j 不可用 | 🔴 Error | 立即通知 |
| MinerU 不可用 | 🟡 Info | 通知（影响解析） |
| experience rating=0 超过 30 天 | 🟢 Info | 自动归档建议 |

---

## Phase 5 — 体验与测试（🟢 P2-P3）

### 5.1 Skill 端到端测试套件

**方案**: 新增自动化测试脚本

```
tests/skills/
├── test_list.py        # S1: L1→L3
├── test_search.py      # S2: QDCVR 六步
├── test_verify.py      # S3: V1→V6
├── test_experience.py  # S4: E4+E6+E8+E11
├── test_graph.py       # S5: 图谱查询
├── test_ingest.py      # A0→A9 入库全流程
├── test_manage.py      # M1→M6 管理操作
├── test_organize.py    # O0→O13 整理审计
├── test_batch.py       # B1→B7 批量操作
└── conftest.py         # 共享 fixtures
```

每个测试：MCP 工具连通性 → 核心流程执行 → 结果断言 → 评分 >= 阈值

### 5.2 错误信息友好化

**现状**: MCP 工具错误信息为原始 JSON

**方案**:
- 错误码标准化：`KB-404`（KB 不存在）/ `DOC-404`（文档不存在）/ `PARSE-TIMEOUT` / `INDEX-FAIL`
- 每个错误码配备：中文说明 + 建议操作
- Agent 自动解释错误给用户

### 5.3 文档与注释完善

| 项目 | 当前 | 目标 |
|------|------|------|
| CLAUDE.md | ✅ 完整 | 持续同步更新 |
| ARCHITECTURE.md | ⚠️ 过时（提到 40 tools） | 更新到 73 tools + 最新架构 |
| Skill 注释 | ✅ 完整 | 保持 |
| MCP 工具 docstring | ✅ 完整 | 补充示例 |
| API 参考 | ❌ 缺失 | 自动生成 API 文档 |

### 5.4 性能基准与监控

**方案**:
- 建立性能基准（当前值作为基线）：

| 操作 | 基线 | P50 目标 | P99 目标 |
|------|------|:---:|:---:|
| `kb_catalog()` | <0.5s | <0.3s | <1s |
| `kb_search_two_stage()` (1033 chunks) | <2s | <1.5s | <3s |
| `kb_doc_read(3000)` | <0.5s | <0.3s | <1s |
| `kb_graph_stats()` | <1s | <0.5s | <2s |
| `parse_doc(10MB PDF)` | 取决于 MinerU | <30s | <120s |

---

## 二、优先级矩阵

```
影响力 ↑
        │ Phase 2: 鲁棒性        │ Phase 3: 检索增强
        │ (容错/恢复/并发)       │ (QDCVR 增强/混合检索)
        │                        │
        │ Phase 0: 立即修复      │ Phase 1: 数据卫生
        │ (清理孤儿/重复/污染)   │ (自动清理/一致性)
        │                        │
        └────────────────────────┼──────────────────→ 紧迫度
                                │
        Phase 5: 体验测试       │ Phase 4: 运维自动化
        (测试套件/文档/性能)    │ (定时任务/看板/告警)
```

---

## 三、里程碑时间线

```
Week 1          Week 2-3        Week 4-5        Week 6-8        Week 9-12
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Phase 0  │───▶│ Phase 1  │───▶│ Phase 2  │───▶│ Phase 3  │───▶│ Phase 5  │
│ 立即修复 │    │ 数据卫生 │    │ 鲁棒性   │    │ 检索增强 │    │ 体验测试 │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                      │                               │
                                      └─────── Phase 4 ──────────────┘
                                         运维自动化（贯穿 Phase 1→5）
```

---

## 四、验收标准

### 系统最终状态目标

| 指标 | 当前值 | 目标值 |
|------|:---:|:---:|
| Skill 场景通过率 | 5/5 (100%) | 12/12 (100%) |
| MCP 工具可用率 | 73/73 (100%) | 73/73 (100%) |
| 孤儿经验数 | 1 | 0（自动清理） |
| 孤儿 tag 数 | ~150+ | <20 |
| 重复 collection | 1 | 0 |
| 测试污染 | 4 条 | 0 |
| 向量索引覆盖率 | 100% | 100% |
| 图谱覆盖率 | 100% | 100% |
| 元数据一致性 | 108/115 | 112/115 |
| Skill 质量评分均值 | 9.4/10 | 9.7/10 |
| 自动维护覆盖率 | 0% | 100%（日/周/月） |
| 失败自动恢复率 | 0% | 80%+ |

### 关卡评审

- **Phase 0 exit**: P1-P4 全部清零 → 系统"干净"
- **Phase 1 exit**: 日/周任务自动运行且 0 告警
- **Phase 2 exit**: 模拟 5 种故障 → Skill 继续执行（降级但不中断）
- **Phase 3 exit**: QDCVR 精准度基准测试 → P0 命中率 >90%
- **Phase 4 exit**: 健康看板可用，告警实时推送
- **Phase 5 exit**: 自动化测试套件 12/12 通过，文档完整

---

## 五、改动影响矩阵

| 改动 | 影响文件 | 风险 | 回滚方案 |
|------|---------|:--:|------|
| Phase 0 清理操作 | 数据层（不可逆删除） | 低 | 无（确认后执行） |
| 新增 `kb_tags_cleanup` | `server.py` + `client.py` + 后端路由 | 中 | 新工具，不影响存量 |
| 并发锁启用 | `tree-file-system-service.ts` + `knowledge-base-yaml-service.ts` | 中 | feature flag 控制 |
| `kb_health_dashboard` | `server.py` + 后端路由 | 低 | 新工具，只读 |
| 定时维护任务 | Skill 新增 + 后端调度 | 低 | 新功能 |
| QDCVR 增强 | `kb_search_two_stage` 参数扩展 | 中 | 向后兼容（新参数默认 old behavior） |
| 测试套件 | `tests/skills/` 新目录 | 零 | 独立于生产代码 |

---

*计划基于 [skill-test-report-20260715.md](skill-test-report-20260715.md) 测试数据编制，所有目标值可量化验证。*