# 全栈端到端测试计划（2026-09-22，feat/soul-persona-system @ 5570d98）

> 目标：验证当前知识库平台全部功能 —— 后端 API、Web BFF API、内部 MCP 工具层、前端 Agent 界面集成，
> 以真实文档走通「入库 → 检索 → 经验总结 → 人格管理 → Agent 问答」完整闭环，并修复/记录所有发现的问题。

## 0. 环境基线（已核实）

| 项 | 值 |
|---|---|
| 后端 | FastAPI http://127.0.0.1:**8771**（`.env BACKEND_PORT` 覆盖 config.yml 的 8770） |
| 前端 | Nuxt 3 http://127.0.0.1:**6789**（BFF，~120 条 /api 路由） |
| Neo4j | bolt 7687 / http 7474（**已在运行** ✓） |
| MinerU | mode=local，模型已缓存（HF_HUB_OFFLINE=1） |
| 认证 | **已启用**；服务令牌 `MCP_AUTH_TOKEN`（.env）；用户令牌 sk-（storage/auth.db） |
| 测试材料 | docs/paper/benchmark/datasets/arxiv-benchmark/*.pdf（10 篇真实论文）+ 自制真实 markdown |
| 存储根 | storage/tree-file-system/（当前无 soul-template，需从 scripts/soul/templates/ 恢复） |
| 现成脚本 | scripts/dev_restart.py · dev_smoke.py · dev_mcp_test.py · dev_hitl_e2e.py · e2e_agentworkshop_api.py 等 |

**陷阱备忘**：dev 模式 watchfiles 重载风暴（长跑用 NO_RELOAD=1）；孤儿 uvicorn worker 占端口（dev_restart.py 负责清）；
速率限制 600 req/60s（heavy 60）； soul_init 强依赖 `storage/tree-file-system/soul-template/`；LLM 类任务用 harness=mock 或 limit=1 控制时长与成本。

## P0 环境拉起与预检
1. `python scripts/dev_restart.py` 干净拉起 backend(8771)+web(6789)，确认无孤儿进程。
2. 健康检查：`GET :8771/api/v1/health`（vector.ready）、`GET :8771/api/v1/graph/health`、`GET :8771/api/v1/mineru/status`、`GET :6789/api/health/stats`（聚合面板）。
3. 认证预检：MCP token 过 `/api/v1/auth/verify`；无 token 访问 `/api/kb/catalog` 必须 401（负向）。
4. 恢复 `soul-template/`（4 宪法文档 + soul-config.yml ← scripts/soul/templates/）。
5. 基线冒烟：跑 `scripts/dev_smoke.py`（21 项检查）记录基线。

## P1 后端 API 面实测（8771，Bearer token）
| 组 | 端点与动作 | 通过标准 |
|---|---|---|
| 元 | GET / · /openapi.json · /api/v1/config/schema · /api/v1/config | 200，schema 含 env_schema |
| 认证 | register(新用户 e2e-full-\<ts>) → login → verify → tokens 创建/列表/撤销 | 全链 200，明文 token 仅一次 |
| 文档工具 | POST /api/v1/documents/split（30000 字符长文） | part_count>1，纯计算无 IO |
| 系统 | POST /api/v1/system/clean {dry_run:true} | 列出可清理项不删除 |

## P2 Web BFF API 面实测（6789）
- GET /api/kb/catalog、/api/kb/search?q=、/api/config/frontend、/api/harnesses、/api/soul/list、/api/claude/engines、/api/claude/skills、/api/claude/history
- 通过标准：200 且字段完整；harnesses 返回 14 引擎 + heuristic；负向 401 语义正确。

## P3 真实文档入库全链路（核心）
1. 建测试 KB：`e2e-demo-<ts>`（web /api/kb/create）。
2. **PDF 解析轨**：`global-rag-benchmark.pdf` → web `POST /api/parse/file-vt`（MinerU OCR，后台任务轮询，预计 1–5 分钟）→ 验证 markdown_path + images。
3. **解析落库**：`POST /api/parse/save-parsed-files` 落入测试 KB → 自动注册 .tree-fs.json + .knowledge-base.yml。
4. **Markdown 直建轨**：2 篇真实 markdown（取自 docs/）→ `POST /api/kb/documents/create` → **显式** `POST /api/v1/search/index-document`（A6-V 门禁：collection 正确 + chunks≥1，用 /api/v1/search/stats 验证）。
5. 元数据闭环：tags PATCH → by-tag 查询；doc content PUT → 重新索引 → 向量可搜新内容；doc read 分页。
6. 汇总登记：验证磁盘 ↔ .tree-fs.json ↔ .knowledge-base.yml 三源一致。

## P4 检索多策略实测
- `POST /api/v1/search/vector`（kb 内 + 跨库）→ 命中入库文档。
- `POST /api/v1/search/two-stage`（BM25→graph→vector）→ stage1/stage2 结构完整。
- `POST /api/v1/search/batch-vector`；`GET /api/kb/search`（关键字，本地文件索引）。
- **负向**：乱码查询 → QDCVR 如实弃答（不高分硬凑）。

## P5 知识图谱（Neo4j）
- `POST /api/v1/graph/build-kb`（测试 KB，非阻塞 task）→ 轮询完成。
- GET kb-overview / document / document-related / document-paths / central-documents / cross-kb-documents。
- `POST /api/v1/graph/agent-relation` 写入一条 agent_judged 关系 → GET document 验证。

## P6 经验系统全生命周期
1. `POST /api/v1/experience/{kb}/init` → create 1 条真实运维经验（问题/方案/结果齐全）。
2. list / read / update / review(rating) / apply → credibility 状态变化。
3. `POST .../extract {mode:"prepare"}` → drafts_list → **draft_approve** → search_smart 命中。
4. dashboard / check_stale / apply_decay。
5. 冥想：GET/PUT meditation config（harness=mock）→ `POST /api/v1/meditation/run {harness:"mock"}` → history 有记录。
6. 全局：`POST /api/v1/experience/global-search`（QDCVR 全库）。

## P7 SOUL 人格全生命周期（本分支主角）
1. `POST /api/v1/soul/init {soul_name:"e2e-tester"}` → 轮询 bootstrap 任务 → 验证 4 宪法文档 + soul-config.yml + 已索引。
2. list / status / folder / persona-docs / settings。
3. `PUT .../config`（domain_labels、kb_scope 指向测试 KB）。
4. 训练：`POST .../learn {limit:1, rounds:1, async}` → 轮询 → memories 产出 → **review-drafts approve** → 索引可搜。
5. 问答：`POST /api/v1/soul/ask`（验证 citations + pas_score）；`POST /api/v1/soul/qdcvr-ask`（evidence_count）；`POST /api/v1/soul/router`（路由决策）。
6. 评估：`POST .../evaluate`（identity/values/thinking/language 四维）→ `POST .../checkpoint` → `POST .../cognition-drafts` → review-drafts(cognition) → `POST .../rollback`（回归检查点）→ `POST .../export`（LoRA JSONL）。
7. 清理：`DELETE /api/v1/soul/{id}`（checkpoint 先行，router-log 留 tombstone）。

## P8 Agent 集成 API（AgentWorkShop 契约）
1. `GET /api/kb/agent/meta`（发现文档）。
2. `POST /api/kb/agent/chat` **sync**：harness=mock（契约）+ harness=claude（真实 LLM，提关于入库文档的问题，验证 tools_used 非空、reply 引用真实内容）。
3. `POST /api/kb/agent/chat` **async** → task_id → `GET /api/kb/agent/tasks/:id` 轮询至 completed。
4. `POST /api/kb/native-search`：真实 QDCVR 检索（验证 answer/kb_ids/duration_ms）。
5. `POST /api/claude/chat`（SSE）：kbEnhanced=true 限定测试 KB → 验证 meta/done 事件流 + 落库 claude-chat.db → `GET /api/claude/history/:sid` 回放。
6. HITL：permission_request → `POST /api/claude/permission`（allow/deny 两腿，复用 scripts/dev_hitl_e2e.py 思路）。

## P9 前端交互式 UI 实测（浏览器，http://localhost:6789）
逐页走查 + 截图：登录 → /(首页) → /file-system（树+上传+解析队列）→ /knowledge-base（建 KB/传文档/标签）→
/knowledge-search（检索+预览）→ /knowledge-graph（图探索）→ **/soul（人格页：选择人格/提问/训练历史）** →
**/claude-chat（Agent 界面：选引擎、kbEnhanced 开关、发真实消息、验证 SSE 流式渲染、HITL 弹窗审批）** →
/harnesses（引擎健康卡）→ /settings（配置加载）→ /tokens（令牌管理）。
通过标准：无控制台致命错误、核心交互闭环可用、会话历史持久化。

## P10 内部 MCP 工具层实测（kb-mcp stdio）
- `python scripts/dev_mcp_test.py`：94 工具清单、kb_list、向量金标命中、graph stats。
- 补充实测：kb_doc_create → kb_index_document → kb_search_two_stage MCP 链路（stdio JSON-RPC）。

## P11 清理与报告
- 删除测试 KB/人格/令牌（KB delete 级联向量+图谱清理，验证 stats 回落）。
- 产出 `review/e2e-full-stack-20260922/REPORT.md`：P0–P10 逐项 PASS/FAIL 矩阵 + 缺陷清单（P0/P1/P2）+ 证据摘录。

## 预算与风险
- LLM 实调预算：agent chat（claude）×3–4 次、soul learn/train-rl 各 1 轮（limit=1）、native-search ×1 —— 预计 <$1。
- 风险：MinerU 本地解析慢（后台轮询不阻塞其它阶段）；dev 重载风暴（备选 NO_RELOAD=1）；mock harness 保证确定性。
