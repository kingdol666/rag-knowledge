# Skill 驱动全功能验收报告（2026-11-13）

**验收方式**：不手动启动任何服务；由 `knowledgebase` skill 的 Step 0（`scripts/ensure_stack.py`）从死栈自动拉起，并全程以 MCP/HTTP 真实调用执行作业。
**结论**：**ACCEPT（有条件）**。核心链路全部真实通过；发现 3 项需要修复的运行时问题（见 §5）。

## 0. 死栈自启（本轮核心验收项）

| 步骤 | 证据 |
|---|---|
| 预置状态 | `ragctl stop-all` 停 web/backend；归因 PID 11900（`python server.py --http`）后终止 kb-mcp；8000/8771/6789 均无监听 |
| 冷检查 | `backend=False web=False mcp_kblist=False catalog=0` |
| 自动拉起 | actions = `["start_backend","start_web","start_kbmcp"]` |
| 终态 | `ready=true`，`e2e_vector_search=true`，`catalog_n=53`，耗时 **1m55s** |

**判定：PASS。skill 可以零人工驱动项目启动并连通知识库。**

## 1. API / 服务面

- `GET :8771/api/v1/health` → `{"status":"healthy","vector":{"ready":true,"embedding_available":true}}`
- `GET :6789/api/health` → `status ok`
- `GET :6789/` → HTTP 200
- `kb_project_status` → backend UP(:8771) · web UP(:6789) · neo4j UP(:7687) · mineru up

## 2. 管理（Manage）

| 操作 | 结果 |
|---|---|
| `kb_create` ×2（A/B 测试库） | success，返回 kb_id |
| `kb_doc_create`（带 tags） | success，`_tags_applied=true`，`_auto_index.triggered=true` |
| `kb_doc_update_meta` 改名 | success，`persistence` 回执 |
| `kb_doc_move` A→B | success，`index_hygiene` 迁移旧路径 |
| `kb_doc_delete` / `kb_delete` ×2 | success，磁盘与目录无残留（kb_list 回到 53） |

## 3. 入库与五层状态

- 自动索引任务 `80a303228810`：`status=done`，2 chunks，`bge-m3`，collection `kb_db5d...`
- 磁盘：`storage/tree-file-system/验收测试库-20261113-A/验收文档-alpha.md` 存在
- `.tree-fs.json`：条目存在（line 22143+）
- `.knowledge-base.yml`：`vector_index`（2 chunks / bge-m3 / chunk_id_prefix）+ `graph_doc_id`
- Chroma：向量检索 top-1 命中该 chunk（score 0.6394）
- Neo4j：需显式 `kb_graph_build` 后 `kb_graph_document` 才 `found=true`（1 doc / 10 relations / tags 正确）

## 4. 检索与 Agent

| 通道 | 结果 |
|---|---|
| `kb_search_vector` | PASS：top-1 0.6394，`degraded=false` |
| `kb_search_two_stage`（冷） | **504 timeout，`degraded=true`，`error_kind=timeout`**（诚实降级） |
| 根因 | 后端日志：冷启动全库 BM25 构建 2288 docs，23:03:19→23:04:38（约 79s） |
| `kb_search_two_stage`（热） | **PASS 0.79s**：stage1 keyword 命中，stage2 vector 0.6394 |
| `kb_search`（关键词） | PASS：本库文档 score 4 排第一 |
| `kb_doc_read` | PASS：逐字返回，`totalLines=10` |
| 移动后旧库检索 | 0 hits（索引卫生 PASS） |
| 移动后新库检索 | 0.6386 命中新路径 |
| OOD 检索（阈值 0.5） | 0 hits，`status=completed` |
| Agent Q&A（omp） | **PASS**：250s / 7 turns；工具链 `kb_list→kb_search_vector→kb_get_documents→kb_doc_read→kb_laya_judge×2→kb_search_two_stage→kb_search_stats`；正确给出文档名与逐字引文，并主动披露“随机唯一串向量通道 0 命中”的限制 |
| Agent OOD（omp） | **PASS（耗时超默认预算）**：452.8s / 14 turns；明确“未找到”，列出全部检索范围（1 文档 / 0 子库 / 2 chunks 100% 读取 / 多阈值向量 + 两阶段 + Laya） |

## 5. 发现的问题（按严重度）

1. **[高] 两阶段冷启动超时**：后端重启后首次调用触发 2288 文档 BM25 全量构建（约 79s），超过 MCP 5s 等待预算 → `504 + degraded=true`。建议：ensure_stack 完成后预热 BM25，或将两阶段改为 async task / 提高 wait budget。
2. **[中] Agent OOD 单回合超过默认硬超时**：实测 452.8s，而 `agent/chat` 默认 `timeout_ms=420000`，默认配置下会超时失败。建议提高默认值或为 OOD 扫描设置早退预算。
3. **[低] 偶发 mojibake**：`kb_doc_move` 响应与随后一次检索响应出现 UTF-8→GBK 解码乱码；磁盘文件、`kb_doc_read`、复检 Chroma 均为正确中文 → 传输/展示层问题，非数据损坏。

## 6. 清理

测试文档、两个测试库、测试 chunk 与图谱节点均已删除；`kb_list` 恢复 53 个知识库；无残留目录。

## 7. 修复轮复审补记（2026-11-14，architect 评审 REJECTED 后闭环）

- **Blocker 修复（US-001）**：`keyword_index_status()` 去掉 `_keyword_lock` 获取（构建全程持锁 71-79s，原实现会冻结 async 健康端点且 building:true 不可观测）。实测：冷重启后 poll2-7 连续观测 `building:true`，mineru 端点在构建期间正常应答（事件循环未冻结），poll10 `ready:true`；首调 two-stage success=true。
- **US-003 加固**：`scripts/mcp_call.py` main() 入口 `sys.stdout/stderr.reconfigure(encoding="utf-8")`——关闭中文 Windows 管道 cp936 通道（唯一一次乱码的疑似形态）。验证：不带 `-X utf8` 直调 kb_list 输出正确 UTF-8；repro 轮全干净。
- **一致性备注落地**：`_keyword_building` 改为实例属性（与 `_keyword_built` 对齐）。
- **测试**：test_keyword_index_status.py 增至 4 项（新增"构建者持锁时 status 读取不得阻塞"）；全量 test_unit.py 115 passed。
