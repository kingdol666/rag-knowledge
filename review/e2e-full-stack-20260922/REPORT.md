# 全栈端到端测试报告（2026-09-22 晚 → 09-23 凌晨，feat/soul-persona-system @ 5570d98）

> 测试范围：后端 API（8771）· Web BFF API（6789）· 内部 MCP 工具层（stdio 94 工具）· 前端 10 页交互实测 ·
> 真实文档入库 → 检索 → 经验总结 → 人格管理 → Agent 问答全闭环。
> 执行计划见 TEST-PLAN.md；全部脚本与 *_output.log 在本目录。

## 结论速览

| 阶段 | 结果 | 备注 |
|---|---|---|
| P0 环境拉起/健康/认证 | **21/21 PASS** | dev_smoke 基线全绿；401 语义正确 |
| P1 后端 API 面 | **15/15 PASS** | 含 72011 字符拆分补验（3 parts，max_chars=30000/overlap=400） |
| P2 Web BFF API 面 | **13/13 PASS** | `/api/health` 返回 SPA HTML 壳（观察项 O1） |
| P3 真实文档入库 | **12/12 PASS** | 真实 arXiv PDF 41s 解析（20 图）；A6-V 门禁 175 chunks |
| P4 检索多策略 | **6/6 PASS** | 含乱码负向（最高 0.462 分不冒充高置信） |
| P5 知识图谱 | **11/11 PASS** | agent-relation 落图验证；Neo4j 646→652 节点 |
| P6 经验系统 | **20/20 PASS** | 提取→草稿→审批跨文档复验；meditation mock 运行成功 |
| P7 SOUL 人格生命周期 | **26/28**（前段 10 + P7b 11 + P7c 5，2 个为测试脚本色差） | 全生命周期闭环，真实 omp 训练 |
| P8 Agent 集成 API | **核心全通过**：契约 3/3 + claude 真实检索 4/4 + 官方 HITL 7/7 | 长流收敛性缺陷 D4（P1） |
| P9 前端交互 UI | **10 页全部走查通过** | 聊天流式/检索/人格页/文件树实测 |
| P10 MCP 工具层 | **14/14 PASS** + D1 对照验证 | 94 工具、金标命中 |
| P11 清理 | 完成 | KB 级联删除验证（9→8、图 652→648、磁盘清零、覆盖仍 100%） |

**判定：平台核心功能全部真实可用。发现 4 项缺陷（D1 P1 · D2 P2 · D3 P2 · D4 P1）与 3 项观察（O1–O3）。**

## 关键链路证据

### 真实文档入库全链路（P3）
- KB `e2e-demo-0922-235201`（9ca30980-…）经 web `POST /api/kb/create` 创建。
- 真实 PDF（docs/paper/benchmark/datasets/arxiv-benchmark/global-rag-benchmark.pdf，1,011,616 字节）
  → web `POST /api/parse/file-vt`（MinerU 本地引擎冷启动含内）**41s** 解析完成，
  markdown_path=backend/output/c5cfd05597b0/global-rag-benchmark.md，images=20。
- `POST /api/parse/save-parsed-files` 落库 → `.tree-fs.json`/`.knowledge-base.yml`/磁盘三源登记 →
  `POST /api/v1/search/index-document` → stats 验证 collection `kb_9ca30980…` **175 chunks**。
- 2 篇真实 markdown（docs/ARCHITECTURE.md、docs/agentworkshop-integration.md）→ 52 chunks。

### 检索与图谱（P4/P5）
- 向量限定库 Top3 全命中《AgentWorkShop 集成指南》；two-stage stage1=3 候选 → stage2=5 结果。
- `POST /api/v1/graph/agent-relation` 写入后 `GET /api/v1/graph/document` 可见该边。

### Agent 集成（P8 —— 用户核心诉求）
- `POST /api/kb/agent/chat`（sync, harness=claude, 231s）：引擎自主调用 **9 个真实 MCP 工具**
  （ToolSearch → kb_list → kb_search_vector ×3 → kb_search_two_stage → kb_doc_read ×2 → backend_status），
  检索限定测试 KB 并给出带引用的回答 —— **AgentWorkShop 集成真实可用**。
- async 模式：task_id → `GET /api/kb/agent/tasks/:id` 轮询至 completed ✓。
- **HITL（官方 scripts/dev_hitl_e2e.py）7/7 PASS**：DENY 腿 permission_request 发出→拒绝→文件未创建；
  ALLOW 腿→批准→文件创建+内容正确+自动清理；流均到达 result。
- 前端 /claude-chat：真实消息 → OMP（deepseek-flash）→ SSE 流式回复 → Done 面板（1 turn · $0.1137 · 7.7s）。

### SOUL 人格全生命周期（P7/P7b/P7c —— 本分支主角，真实 omp 训练）
- init（web 层）→ 4 宪法文档 + bootstrap + 索引 → status/folder(11 段)/persona-docs 全通。
- **learn（omp）**产出真实人格记忆草稿（「写入必须原子地触及全部五层存储…」）→ approve → indexed=true。
- **soul_ask** pas=4.5 + 6 citations；**qdcvr_ask** evidence=5 + pas=4.5；router 决策返回。
- **evaluate 四维**：identity 2.0 / values 3.0 / thinking 3.3 / language 4.0（附逐维改进建议）。
- checkpoint → **rollback**（恢复 1 memory）→ **export**（LoRA JSONL，min_score=3.0 门禁下 0 条为合法空）→
  training history 2 runs → 终态 total_memories=1、pending=0。

### 前端 10 页交互（P9）
注册即登录（首用户管理员）、路由守卫 401 正确；/knowledge-base 测试 KB+3 文档可见；
/knowledge-search「检 索」真实命中并显示分数；/claude-chat 流式对话完整；
/soul 人格清单+domain_labels+RL 控制台+宪法文档查看器完整；/file-system 文件树齐全；
/knowledge-graph、/harnesses、/tokens、/settings 渲染正常。

## 缺陷清单

### D1（P1）人格删除假成功 —— REST/前端只走半程（MCP 层完整，已对照验证）
- 复现：`DELETE /api/v1/soul/{id}` 返回 `{"success": true, "checkpoint_saved": …}`，但 list/catalog/磁盘三源仍在。
- 根因：backend/app/api/routes/soul.py:352 只做 checkpoint + 路由缓存失效，note 明言「KB 删除请经 kb-mcp soul_delete 工具」。
- **对照实验**：MCP `soul_delete` 走完整链（checkpoint → web DELETE /api/kb/delete 级联 → tombstone）后三源全部移除 ✓。
- 波及：前端 /soul 页「删除」按钮（web/server/api/soul/delete.delete.ts）同样只到半程 → **UI 显示删除成功但人格残留**。
- 修复建议：web 层 soul/delete.delete.ts 补调 `DELETE /api/kb/delete`（与 MCP 同语义）；REST 响应改 202 语义。

### D2（P2）REST /api/v1/soul/init 与 MCP soul_init 行为不一致
- REST 层要求 KB 已存在（仅 bootstrap 半程）；完整建格入口在 web 层 `POST /api/soul/init`（自动补 soul- 前缀+拷模板）。
- 按文档走 REST 建人格的外部集成方会在第一步卡死。建议文档标注或在 REST 层补全。

### D3（P2）Harness Hub 首次挂载目录为空
- 整页加载 /harnesses 等 6s 仍「0/ 0 可用」无引擎卡；点「刷新」立即「12/ 15 可用」。
- API 实测 15 条 200、无 JS 错误 —— 挂载期竞态/错误被吞。建议失败重试或显式错误态。

### D4（P1）kbEnhanced 长检索流不收敛（native-search 同根因）
- 证据 A：`POST /api/kb/agent/chat` sync（claude）231s 正常完成 —— 同类任务可达。
- 证据 B：`POST /api/kb/native-search` 两次超时（280s/420s 上限，工具链已跑 7/11 个真实工具后仍不收敛）。
- 证据 C：`POST /api/claude/chat`（kbEnhanced, claude）83 事件流式正常但 697s 无 done，最终**服务端重置连接**
  （WinError 10054，客户端收不到 done/error 事件）。
- 判断：kbEnhanced 注入的 agentic 检索指令 + 无工具收敛约束 + 当前 API 时延 → 长尾不收敛；而 agent/chat 路径
  （工具白名单 Read/Glob/Grep/Skill/Task + maxTurns 40）可控。
- 修复建议：native-search 与 kbEnhanced 复用 agent/chat 的工具约束与 turn 预算；超时改为发 `error` 事件而非断连。

### 观察项
- O1：web `GET /api/health` 返回 SPA HTML 壳；JSON 健康在 `/api/health/stats`。外部监控按路径惯例接 /api/health 会误判。
- O2：`GET /api/v1/config` 的 `effective.backend_url` 显示 8770（config.yml）而实际端口 8771（.env 覆盖）—— display 漂移。
- O3：`DELETE /api/kb/delete` 用 query 参数（无 body）时 500（Cannot read properties of undefined）而非 400 校验。

## 测试脚本备忘（复现陷阱）
- REST `POST /api/v1/soul/{id}/learn` 默认**同步阻塞**至训练完成，客户端须 `async_mode: true` + 轮询
  `GET /api/v1/soul/tasks/{id}`；任务终态词是 `done`（非 completed）。
- SSE `/api/claude/chat` 的事件类型在 **`event:` 头**（permission_request/done），解析器必须读 event: 行；
  data-JSON 的 `type` 只对 SDK 帧事件存在。
- HITL 模型可能把 Write 路径解析到仓库根而非请求 cwd —— 断言文件位置需两处都查。
- web `/api/kb/search` 参数名是 `query`（响应键 `hits`）；experience 搜索响应键是 `experiences`。

## 清理记录（P11）
- e2e-demo-0922-235201 KB：`DELETE /api/kb/delete`（body 契约）→ success；级联验证：KB 9→8、docs 336→333、
  graph nodes 652→648、磁盘移除、向量覆盖仍 100%。
- soul-e2e-throwaway000559：经 MCP soul_delete 正确删除（D1 对照）。
- soul-e2e-tester：**保留**（作为 UI/训练证据；注意 UI 删除受 D1 影响，删除请走 MCP 或补修复后再删）。
- HITL 测试文件：官方脚本自动清理；无散落文件。
- 测试账号 e2e-full-0922234031、ui-e2e-0922 留在 auth.db（dev 库，无删除 API）；P1 铸造的 API token 已撤销。

## 环境与成本
- dev 模式（backend 8771 / web 6789 / Neo4j 7687 / MinerU 本地）；LLM 实调（claude/omp/deepseek-flash）粗估 <$2。
- Mimosa 钩子对本目录测试脚本多次语法级误报（SSRF/路径穿越/硬编码凭据），均已按 guard_url + pathlib + secrets 规避；不影响产品代码。

## 工件索引
p1_backend_api.py · p2_web_api.py · p3_ingest.py(+p3_state.json) · p4_retrieval.py · p5_graph.py ·
p6_experience.py · p7_soul.py · p7b_soul_resume.py · p7c_soul_tail.py · p8_agent.py · p8b_retry.py ·
p8c_sse_hitl.py · hitl_debug_output.log · d1_contrast_output.log · p*_output.log · TEST-PLAN.md
