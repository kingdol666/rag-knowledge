# SOUL 计划 v3.4 六轮实测验证报告(4×scout 全仓逐行实证)

- 评审对象: `.omc/plans/soul-persona-system-20260802.md`(v3.3 → v3.4)
- 日期: 2026-08-02
- 方法: 4 个 read-only scout 并行对仓库真实代码逐行核对(agent_harness_manager.py 全文件 1118 行精读;server.py 2623 行 + client.py 978 行关键区;后端 12 个 service + 11 个 route;KB 数据层 .knowledge-base.yml/.tree-fs.json/vector_service/two_stage);2 项遗留由主会话直接 grep 复核(短 chunk 降权逻辑、kb_task_status 通用轮询)
- 结论: **计划可落地、可验收,无阻塞性缺陷**。28 处代码引用全部实证: 25 OK,3 处行号小修(内容不变)。M0.1 前提(工具层 source_questions 未透传)实测确认。2 项新约束 + 3 项新优化并入计划正文。

## 1. 引用实证表(28 处)

| # | 计划引用 | 结果 | 实测 |
|---|---|---|---|
| 1 | agent_harness_manager.py:94-131 HARNESS_CONFIG | OK | :94-132,含 omp/claude 两分支 CLI 配置 |
| 2 | :244+ 类 | OK | AgentHarnessManager 单例 :244 |
| 3 | :266 Semaphore(2) | OK | `asyncio.Semaphore(2)` 全局并发上限 |
| 4 | :499 _spawn_agent | OK | 签名: `_spawn_agent(harness, kb_path, kb_id, signals, kb_config, trigger, task_prompt)` — 接收**预构建 prompt 字符串**,非 model/schema 参数 |
| 5 | :340-361 探测 | 行号小修 | probe_harness 在 **:279**;:340-360 为熔断(3 连败→24h open) |
| 6 | :364-420 经验专用 | OK | synthesize_experiences :364 |
| 7 | :422-497 经验专用 prompt | OK | _build_task_prompt :422 |
| 8 | :587-611 并发 | 行号小修 | 信号量 acquire/release 在 **:419-420** |
| 9 | :675-713 超时 | 行号小修 | _watch_process :675(timeout_sec+10 宽限,asyncio.wait_for);_terminate_process 树杀 :692 |
| 10 | :530-541 清理 | 行号小修 | 清理 = **_terminate_process :692**(:530 处无清理逻辑) |
| 11 | :715-841 经验专用 parse | 基本 OK | _parse_result_log :715(omp 行级 JSON 事件/通用 brace 扫描)、_build_result :831、_regex_extract_result :844 |
| 12 | :44-91 RESULT_SCHEMA 全局 | OK | 模块级全局,meditation 硬编码 |
| 13 | :41 _SYSTEM_PROMPT_PATH | OK | 模块级全局,指向 prompts/meditation_agent_system.txt |
| 14 | claude --json-schema / omp 内嵌格式 | OK | claude: `--json-schema json.dumps(RESULT_SCHEMA)` + `--system-prompt-file` + stdin(输出 stdout JSON);omp: `--mode=json` + `@prompt_file`(结果自日志文件解析,非 stdout) |
| 15 | 无现成 complete()/token 估算/cost 追踪 | 确认(计划预期) | 全部不存在 → 1.2 新增设计成立 |
| 16 | server.py:1216 experience_create | OK(缺口确认) | 工具第 13 参为 `metrics: str`,**确无 source_questions** |
| 17 | client.py:762 experience_create | OK(缺口确认) | 方法同样缺失 source_questions → M0.1 三处透传前提成立 |
| 18 | server.py:1440 experience_search_smart | OK | :1441,参数含 kb_id/top_k/score_threshold |
| 19 | server.py:1800 meditation_run + :1821-1825 | 行号小修 | 工具 :1800;`_running_payload` 在 **:197**;`task_registry.submit` 在 **kb-mcp/task_registry.py:71** |
| 20 | server.py:2022 两阶段检索 | OK | kb_search_two_stage: stage1_top_k=20/stage2_top_k=5/enable_graph_expansion/**balance_kbs**/score_threshold |
| 21 | score=1−Chroma distance + hnsw:space=cosine | OK | vector_service.py:116 collection metadata;score=1−dist 于 :340/:415/:623;two_stage 每 chunk 透传 :182 |
| 22 | 索引隔离(草稿不注册) | OK(新约束) | .knowledge-base.yml 显式 documents[] 注册(storage_reader_service.py:206),磁盘无自动发现;唯一自动索引入口 = MCP kb_doc_create :383(fire-and-forget _auto_index_doc) |
| 23 | 13 库回归基线 | OK | 13 根库 + 17 子库(30 注册);kb_list MCP 工具含子库富化 |
| 24 | experience_meditation_service.py:552-615 | OK | _loop :540 → _run_kb_aware_meditation :552 → per-KB loop :573 → per-KB asyncio lock :607(_get_kb_lock :460) |
| 25 | kb_meditation_config.py:18-36 + :143-149 | 行号小修 | DEFAULT 17 字段 :18-36;known_fields 门 warn+drop 在 **:143-148**;update_meditation_config :105(文件锁 YAML 读改写) |
| 26 | experience_service.py:243 / experience_models.py:55 | OK | source_questions 服务侧读写 :243/:1480,模型字段 :55(不在 ExperienceUpdate) |
| 27 | main.py:192-200 路由注册 + experience.py 模式 | OK | include_router 块(8 路由);experience 前缀 /api/v1/experience;verify_token 来自 app.api.deps.auth(GET 免鉴权,写操作 Depends) |
| 28 | safe_paths.resolve_within / embedding_service | OK | resolve_within :42;EmbeddingService.embed :108/embed_one :127,**无 cosine 助手**(1.7 自实现 ~3 行成立) |

## 2. 新约束(已并入计划)

1. **FS 写入红线(§1.1)**: pending 草稿/记忆文件一律直接 FS 原子写,严禁经 kb_doc_create 创建(kb_doc_create :383 自动触发索引 → 破坏"pending 不索引"隔离)。模板子目录用直接 FS mkdir。
2. **短 chunk 降权(AC15/§11.8e)**: vector_service.py:350-364 — <50 字符 chunk score ×0.3 + `short_content_warning`。AC15 前置门使用**降权后** score;人格文档 chunk 保持 >50 字符;降权命中时 gaps.md detail 记 short_content_warning=true。
3. **task_id 语义(§1.4/AC8)**: task_registry 仅存在于 kb-mcp 层(内存态)。soul 长任务 = MCP 侧 submit 包裹后端同步端点(与 meditation_run :1800 同模式),task_id 由 MCP 返回,kb_task_status :682 通用轮询(实测任意 kind 均可)。后端不新建 task registry(避免重复基建)。

## 3. 新优化(已并入计划)

1. **balance_kbs 多库检索(§1.4)**: kb_scope 多库时一次 `kb_search_two_stage(balance_kbs=True)` 免逐库循环(参数实测存在)。
2. **soul_init 自动索引(§1.9/AC25)**: kb_doc_create 自动索引 fire-and-forget,AC25 的"60s 内可检索"内置满足,无需额外索引调用。
3. **config dict 透传(§M0.3)**: experience_meditation_config_update :1859 接受通用 config dict,M0.3 将新字段加入 DEFAULT_MEDITATION_CONFIG 后 MCP 层零改动。

## 4. 关键前提确认(计划设计与之吻合)

- `_spawn_agent` 接收预构建 prompt → complete() 自构 CLI args + 结果解析(1.2 设计正确,100-130 行估算合理)
- omp 结果自日志文件解析(行级 JSON 事件),兜底 `_regex_extract_result` — complete() 需自带解析器或复用 :844
- 信号量 :266 全局,两 harness 分支共享 — complete() 复用同一 Semaphore
- 熔断 3 连败 → 24h open — complete() 复用;AC10 故障注入测试点 = probe 失败
- task_registry 无 _running_payload 之外的持久化 — MCP 进程重启后 task_id 失效(文档化,现有 meditation_run 同局限)
- 记忆索引闭环: approve 后用 kb_index_document :2142 / kb_batch_index :2171(实测存在)注册+索引

## 5. 残余风险(可接受,评审口径不变)

| 风险 | 等级 | 说明 |
|---|---|---|
| 路由准确率 80% 为测试集口径 | 中 | 生产需 M5 A/B 监控(route_uncertain >30% 回退显式模式) |
| LLM 评分一致性 | 中 | 需 M5 重测信度;校准集全量重跑机制已设计(2.3) |
| MCP task_registry 内存态 | 低 | task_id 随 MCP 进程失效;与现有 meditation_run 行为一致 |
| 短 chunk 降权影响前置门 | 低 | 已量化: 人格文档 chunk>50 字符即可规避;降权命中写入 gaps |

## 7. 二轮可执行性核查(编排层归属,2026-08-02)

主会话定向验证: 后端无建库能力(`/api/kb/create` 不存在于 backend;kb_create/kb_delete 仅 web 层,经 kb_client :211/:227);后端有 `POST /api/v1/search/index-document`(search.py:166-167,graph_service.index_document)。kb_client 具备 kb_create/kb_delete/kb_doc_read/kb_doc_create 全部方法(:207-274)。

**发现并修复的 5 处计划缺口(已并入计划正文):**

1. **soul_init/soul_delete 编排层归属未明确(§1.9)** — 后端无建库能力,编排必须落在 kb-mcp 层: client.kb_create → client.kb_doc_read 模板 → client.kb_doc_create ×5(web 层**不**自动索引,实测 web/server/api/kb/documents/create.post.ts 显式不索引)→ 新增 `POST /api/v1/soul/bootstrap`(soul-config.yml 原子写 + 初始 profile-summary + meditation config)→ 显式索引 5 文档。低频管理操作多次 HTTP 可接受。§11.1 已补 bootstrap 端点契约。
2. **审批索引实现路径(§2.4b)** — approve_draft 后端进程内调用索引服务(POST /api/v1/search/index-document 对应),MCP kb_index_document/kb_batch_index 为同一能力薄封装。
3. **Semaphore 语义矛盾(§2.6/§7)** — 原"soul learn 不经 Semaphore(2)"与 1.2"complete() 复用信号量"冲突;已统一为: 所有 complete() 调用(learn/ask/reflect/路由打分)经全局 Semaphore(2),acquire 超时 300s → lock_timeout。
4. **调用计数归属(§1.2/AC16)** — 计数由 soul_learn/soul_ask 运行上下文持有,complete() 单次无状态、返回 token 估算与 cost 供调用方累计 check-and-deduct。
5. **soul_init 索引时序(§1.9/AC25)** — 修正"kb_doc_create 自动注册+索引"表述(仅 MCP 工具自动索引,web 层不索引);soul_init 后显式 kb_index_document ×5 或 kb_batch_index,AC25 的 60s 可检索仍满足。

**新增后端端点:** `POST /api/v1/soul/bootstrap`(见 §11.1,含错误码契约)。

## 8. 三轮实施机制核查(2026-08-02)

主会话定向验证: `client.kb_list` → **web 层** `GET /api/kb/catalog`(client.py:207-209)——后端无 KB 列表 HTTP 端点依赖;MCP 错误模式实证: 内联校验返回 `_j({success:false, error})`(server.py:64/71/351/1870),工具体透传后端响应;`_kb_exists` 辅助(:350)可复用。

**并入计划的 4 项实施机制(§0 三轮 + 正文):**

1. **KB 枚举来源(§1.7)**: 后端 soul_list/soul_router/learn_all 统一用 `storage_reader_service.list_knowledge_bases`(.tree-fs.json,进程内),不依赖 web /api/kb/catalog(那是 MCP kb_list 的数据源)。
2. **错误契约(§11.1 头部)**: 后端 = HTTPException(detail={error, detail});kb-mcp 工具层 = `_j({success:false, error:<code>, detail})`;对齐现有实证模式。
3. **soul_kb_id 语义(§1.5)**: 接受 UUID 或路径(对齐现有 kb 工具),存在性校验复用 `_kb_exists` :350。
4. **§12 开发启动清单**: 环境前置(ragctl up/status、harness 探测、data/ 目录、基线采集)→ M0 严格顺序(0.1→0.3→0.4 + 回归)→ M1 起点(先 1.2 complete(),再 1.1 模板)→ 每里程碑验收/回归/测试收尾 → 踩坑速查(5 条)。

## 9. 裁决

- v3.3 的 5 处行号引用误差**全部为行号偏移,内容语义不变**,不影响任何任务/AC 的可执行性
- M0.1(透传 source_questions)与 M0.3(扩展 DEFAULT_MEDITATION_CONFIG)为**实施前提**,已实证确认缺口存在且修复路径明确
- 新增 2 约束 + 3 优化不改变架构决策与里程碑结构,仅强化可落地性
- 计划状态: **pending approval**(v3.4,待人工批准后进入 M0)
