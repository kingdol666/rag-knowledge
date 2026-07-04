---
name: optimization-phase-2
description: "Phase 2 enterprise optimization plan for the RAG knowledge base system"
metadata:
  type: project
  priority: P0
---

# RAG Knowledge Base — 企业级极致优化计划 (Phase 2)

Based on comprehensive code audit and e2e testing, this plan targets **concrete, implementable** improvements across 5 dimensions.

---

## Dimension 1: 缺失的 MCP 工具补全（最高优先级 🚨）

### D1a — 新增 `kb_content_search`（全文向量搜索）

**问题:** 现有 `kb_search` 只搜索文档 name+description（metadata），**不搜索正文**。文档名写错了就完全找不到。T6 的 BM25 盲区也是因为 content 索引只有 2000 字固定截断。

**方案:** 新增 MCP 工具，利用已有 ChromaDB 向量库做全文语义搜索：

```python
@mcp.tool()
async def kb_content_search(query: str, kb_id: str = "", top_k: int = 5):
    """全文语义搜索：搜索所有 KB 文档的正文内容（非 metadata）。
    
    使用 ChromaDB 向量索引定位最相关的文档片段。
    kb_id 为空则跨库全部搜索。
    """
    return _j(await _client().vector_search(query, kb_id, top_k))
```

**实现:** server.py 已暴露 `kb_search_vector`，但 description 未强调 "全文搜索" 和跨库能力。需更新 description + 更新 agent 知识。

**影响文件:** `kb-mcp/server.py` (工具 description 增强)

### D1b — 新增 `kb_search_hybrid`（混合搜索：向量+关键词双路径合并）

**问题:** 纯BM25（T6 盲区）和纯向量（短文本虚高）各有缺陷，缺少融合手段。

**方案:** 合并在 MCP 层做一次 Recency 融合：

```python
@mcp.tool()
async def kb_search_hybrid(query: str, kb_id: str = "", top_k: int = 5):
    """混合搜索：向量语义 + BM25 关键词双路径合并（Reciprocal Rank Fusion）。
    
    解决跨库搜索时纯向量或纯 BM25 各自的盲区。
    返回结果含来源标记 (vector/bm25/both)。
    """
```

**实现:** 后端 `two_stage_search_service` 已有 stage1 BM25 + stage2 向量，但限定在 stage1 候选内。新增一个 `hybrid_search` 方法做真正的双路径独立搜索后 RRF 合并。

**影响文件:** `backend/app/services/two_stage_search_service.py` (新增 hybrid_search)

### D1c — 新增 `kb_collection_health`（向量 + 文件系统一致性检查）

**问题:** 目前没有快速查看 KB 是否有文档被添加但未索引的工具。

**方案:** 对比 `.knowledge-base.yml` doc 数量和 ChrromaDB chunk 数量报告缺失索引。

```python
@mcp.tool()
async def kb_collection_health(kb_id: str = ""):
    """检查 KB 的向量索引健康状况：对比文档数量 vs 向量索引分块数量。
    
    返回: {kb_id, doc_count, chunk_count, indexed_pct, missing_docs: [...]}
    帮助发现忘记索引的文档。
    """
```

**影响文件:** `kb-mcp/server.py` + `backend/app/api/routes/search.py`

---

## Dimension 2: 搜索增强（精准度与召回率）

### D2a — BM25 索引增强：content 长度动态调整

**问题:** `keyword_index_service.py` 固定 `content[:2000]`，导致长文档的 BM25 索引稀疏，跨库搜索时 Thermal-Power-Monitoring 等长文档 KB 无法被命中。

**方案:**
```python
# keyword_index_service.py
MAX_CONTENT_CHARS_FOR_BM25 = 8000  # 从 2000 提升
```

还要确保 BM25 重建触发时机正确——目前 `invalidate_keyword_index()` 在 `index_document` 和 `batch_index` 后才触发，但 `kb_doc_create/update_content` 不走这个路径。

**影响文件:** `backend/app/services/keyword_index_service.py` (L34: 2000→8000), `backend/app/services/two_stage_search_service.py` (新增 `Webhook: doc_create → invalidate`)

### D2b — 短文本过滤：后端强制（不依赖 agent）

**问题:** 短文本过滤目前只在 SKILL 层面定义（agent 知识），后端 `vector_service.py` 没有拦截。如果 agent 不遵循规则就会返回虚高短文本。

**方案:** 在 `vector_service.search()` 结果后追加短文本过滤：

```python
# vector_service.py: after sorting results
def _filter_short_results(results, min_chars=50):
    """短文本过滤：<min_chars 的 chunk 降权到 P2 级别"""
    filtered = []
    for r in results:
        if len(r.get("content", "").strip()) < min_chars:
            r["score"] *= 0.3  # 降权而非丢弃（保留可追溯性）
            r["short_content_warning"] = True
        filtered.append(r)
    return filtered
```

**影响文件:** `backend/app/services/vector_service.py` (search() 添加后处理)

### D2c — 跨库向量搜索聚合优化

**问题:** 跨库 `kb_search_vector(kb_id="")` 需要枚举所有 collection 各自查一次再合并，性能随 KB 数线性增长。

**方案:** 不修改（ChromaDB 本身限制），但增加缓存提高效率：
- `_all_kb_collections()` 结果增加缓存（30秒 TTL）
- 避免每次搜索都 `client.list_collections()`

**影响文件:** `backend/app/services/vector_service.py`

### D2d — 搜索溯源增强

**问题:** 搜索结果不返回 `source`（BM25/vector/graph），agent 无法区分搜索路径的可靠性。

**方案:** 两阶段返回增加 `source` 字段标记命中来源。

**影响文件:** `backend/app/services/two_stage_search_service.py`

---

## Dimension 3: 企业级运维能力

### D3a — KB 导出/导入（批量迁移）

**问题:** 没有整库导出/导入功能。迁移 KB 需要在环境间手动重建。

**方案:**

**MCP 工具:**
```python
@mcp.tool()
async def kb_export(kb_id: str, output_dir: str = "") -> str:
    """导出整个 KB 为可移植格式。包含：
    - Docs: 全部文档正文
    - Metadata: description, tags, associated docs
    - Experiences: 全部经验（含 rating/applied_count）
    - Vector index: 导出 Embedding 便于热加载
    输出: ZIP 包路径
    """

@mcp.tool()
async def kb_import(zip_path: str, target_kb_id: str = "", create_new: bool = False) -> str:
    """从 ZIP 包导入 KB。可选合并到已有 KB 或创建新 KB。"""
```

**影响文件:** `kb-mcp/server.py` + `backend/app/services/export_service.py` (新建)

### D3b — 文档版本管理与变更追踪

**问题:** 目前 `kb_doc_update_content` 直接覆盖，无法回滚。企业要求可审计。

**方案:** 实现一个轻量版本追踪（非完整 git），基于 `.knowledge-base.yml` 增加 `version_history` 字段：

```python
# storage_reader.update_document_content() 新增:
{
    "content": "...",
    "version_history": [
        {"version": 1, "updated_at": "...", "updated_by": "...", "char_count": 5000},
        {"version": 2, "updated_at": "...", "updated_by": "...", "char_count": 5200},
    ]
}
```

**MCP 工具:**
```python
@mcp.tool()
async def kb_doc_history(kb_id: str, doc_path: str) -> str:
    """查看文档的版本历史。"""

@mcp.tool()
async def kb_doc_rollback(kb_id: str, doc_path: str, version: int) -> str:
    """回滚到指定版本。"""
```

**影响文件:** `web/server/api/kb/documents/content.put.ts` (修改), `kb-mcp/server.py` (新增工具)

### D3c — 定期健康检查自动任务

**问题:** 目前只在用户主动调用时才检查健康。企业级需要自动巡检。

**方案:** 基于 OMC cron 机制或系统定时任务：

```yaml
# .omc/cron.yml
cron_jobs:
  - schedule: "0 6 * * 1"  # 每周一 6AM
    skill: knowledge-verify
    args: "V1→V6 full scan"
  - schedule: "0 0 1 * *"  # 每月1号
    skill: knowledge-organize
    args: "audit: orphan cleanup"
```

**影响文件:** `.omc/cron.yml` (新建)

### D3d — KB 备份与恢复

**问题:** 存储依赖 `.tree-fs.json` + `.knowledge-base.yml`，没有备份机制。

**方案:** 简单的定期备份 MCP 工具：

```python
@mcp.tool()
async def kb_backup(kb_id: str = "", output_path: str = "") -> str:
    """备份 KB 或全部。备份内容：.tree-fs.json + 所有 .knowledge-base.yml + .md 文件。"""
```

---

## Dimension 4: 经验管理增强（可信度机制完善）

### D4a — 经验可信度衰减自动计算

**问题:** 目前 `rating_avg` 和 `applied_count` 不会随时间衰减。3 年前评分 5.0 现在可能已过时。

**方案:** 后端 `experience_summary` 增加可信度评分：

```python
def _credibility_score(exp: dict) -> float:
    """0-1: 综合可信度。考虑了时效性、应用次数、评分。"""
    age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(exp.get("created_at"))).days
    recency = max(0, 1 - age_days / 365)  # 1年内满分，3年归零
    rating_factor = exp.get("rating_avg", 0) / 5.0
    applied_factor = min(exp.get("applied_count", 0) / 5, 1.0)
    return round(0.4 * rating_factor + 0.3 * applied_factor + 0.3 * recency, 2)
```

**影响文件:** `backend/app/services/experience_service.py` (新增可信度评分 + 排序)

### D4b — 经验全文再索引触发器

**问题:** 更新经验后需要主动调 `kb_batch_index` 才能更新向量索引。`experience_update` 最后调了 `_vs.index_document`，但如果有错误不会报给用户。

**方案:** 增加重试机制和明确的索引状态返回：

```python
# experience_service.py: update_experience 返回值增加:
"reindexed": True/False
"reindex_error": "" if ok
```

**影响文件:** `backend/app/services/experience_service.py` (L302-314 增强)

### D4c — 经验应用记录持久化

**问题:** `experience_apply` 只增加 `applied_count`，不保留历史记录。无法追溯"谁在什么时候用了什么经验"。

**方案:** 在 `.experience-index.yml` 中增加 `apply_records` 数组：

```yaml
experiences:
  - id: exp-xxx
    ...
    apply_records:
      - user: "operator-01"
        context: "#3 unit gearbox"
        result: "success"
        applied_at: "2026-07-03T08:55:16Z"
```

**影响文件:** `backend/app/services/experience_service.py` (apply_experience)

---

## Dimension 5: Agent/Skill 编排优化

### D5a — Archival 主动记忆持久化

**问题:** Archival 的操作和观察不跨 session。每次启动都需要重新认识整个 collection。

**方案:** 利用 OMC notepad 或 agentmemory：

```yaml
# In knowledge-admin.md Step 4 — 持久化:
After every operation that modifies >5 items:
  → Write session change log
  → Update .omc/project-memory.json with collection profile:
    - total_kbs, total_docs, total_experiences
    - known issues (broken refs, orphan tags)
    - state vectors for quick next-session recovery
```

**影响文件:** `.claude/agents/knowledge-admin.md` (Step 4 增强)

### D5b — 文档分类增强：自动注入领域标签

**问题:** `knowledge-ingest` A5 步骤依赖 agent 判断标签，但 agent 可能漏标某些领域的通用标签。

**方案:** 增加自动标签注入规则，在 A5b 阶段执行：

```yaml
# .claude/skills/knowledge-ingest/SKILL.md A5b 新增:
自动领域标签注入:
  - 含 "CNN"/"LSTM"/"深度学习"/"neural network" → 自动加 "deep-learning"
  - 含 "齿轮箱"/"gearbox"/"轴承"/"轴承故障" → 自动加 "mechanical-fault"
  - 含 "MSET"/"状态估计" → 自动加 "state-estimation"
```

**影响文件:** `.claude/skills/knowledge-ingest/SKILL.md`

### D5c — 批量操作的回滚安全网

**问题:** `knowledge-batch` B1/B3 如果中间失败（5/10 完成时），已完成的不回滚。这是正确的（部分完成 > 全部回滚），但需要更清晰地向用户报告。

**增强:** 增加明确的中断报告模板：

```
批量操作中断报告:
├── 已完成: 5/10
├── 失败: 2 (文件损坏、权限)
├── 待处理: 3
├── 建议: 解决失败项后重新运行，跳过已完成的
└── 风险: 无——已完成项已验证通过
```

**影响文件:** `.claude/skills/knowledge-batch/SKILL.md`

---

## 实现优先级

| 优先级 | 编号 | 任务 | 工作量 | 影响 |
|:------:|:----:|------|:------:|:----:|
| P0 | D1a | kb_content_search 描述增强 | 0.5人日 | 解决全文搜索盲区 |
| P0 | D2a | BM25 content 2000→8000 | 0.2人日 | 解决跨库召回不足 |
| P0 | D2b | 后端短文本过滤 | 0.5人日 | 硬性防御短文本虚高 |
| P1 | D1b | kb_search_hybrid RRF 融合 | 1人日 | 最终解决跨库盲区 |
| P1 | D1c | kb_collection_health | 1人日 | 索引健康可视化 |
| P1 | D2d | 搜索溯源 source 字段 | 0.5人日 | 搜索结果可解释性 |
| P1 | D4a | 经验可信度自动衰减 | 1人日 | 经验时效性保障 |
| P1 | D5a | Archival 持久化记忆 | 0.5人日 | 跨 session 连续性 |
| P2 | D3a | KB 导出/导入 | 2人日 | 批量迁移能力 |
| P2 | D3b | 文档版本管理 | 3人日 | 可回滚/可审计 |
| P2 | D4c | 经验应用历史 | 1人日 | 可追溯性 |
| P3 | D3c | 定期巡检 cron | 0.5人日 | 自动维护 |
| P3 | D3d | KB 备份恢复 | 1人日 | 灾备 |

## 关键设计决策

1. **不追求 YAML 转发 → 数据库**：当前 `.tree-fs.json` + `.knowledge-base.yml` 的存储模型足够好。加 DB 会增加复杂度而不解决核心问题。

2. **不重构为微服务**：当前一体化 MCP server + FastAPI backend 架构已经够轻量。不需要拆分。

3. **优先做后端硬性防护**：短文本过滤、BM25 content 长度、可信度衰减等应该在后端实现（agent 遵守规则是软性约束，后端强制是硬性保障）。

4. **MCP 工具作为最终统一接口**：所有新的企业级能力都应该通过 MCP 工具暴露，这样 agent 和开发者都可以调用。
