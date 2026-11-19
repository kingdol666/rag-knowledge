# 对外 API R2 轮验收报告（2026-11-18 下午，fresh run）

> **本轮定位**：R1 轮（同日上午）的复测 + 全量 API 盘点 + 标准文档交付。全部判定引用本轮 fresh 工件（同目录 `r2*.json`），不引用 R1 数字。
> **执行方式**：ralph PRD 六故事（`.omc/prd.json`），五组 agent 回合**串行单飞行**，全部带真实 Bearer token（`storage/loop-auth.json`，无凭证字面量入工件）。

## 0. 前置状态

| 项 | 结果 |
|---|---|
| backend :8770 | `healthy`，vector ready，embedding available，keyword index ready |
| web :6789 | `/api/health` 200 |
| kb-mcp :8000 | SSE 端点可达 |
| token | loop-auth token 对 backend verify `valid:true`（缓存有效） |
| 401 负测试 | 无 token POST agent/chat → **401** ✅ |
| 路由盘点 | **136 条** web 层路由全枚举 → [route-inventory.txt](./route-inventory.txt) |

## 1. R2 通过矩阵

| # | 组别 | 模式 | 结果 | 耗时 | 成本 | turns | 证据文件 |
|---|---|---|---|---|---|---|---|
| G1 | 同步金标检索（注意力公式） | agent/chat **sync** | ✅ **PASS** | 302.7s | $0.91 | 12 | `r2sync_result.json` |
| G2 | OOD 诚实拒答（四川泡菜） | agent/chat sync | ✅ **PASS** | 116.0s | $0.18 | 4 | `r2ood_result.json` |
| G3 | 异步检索（傲慢与偏见） | agent/chat **async** | ✅ **PASS**（第 3 次） | 139.5s | $0.37 | 4 | `r2async3_result.json` |
| G4 | 交互两轮连续性（kbEnhanced+resume） | claude/chat JSON | ✅ **PASS** | 201.0+143.2s | 见工件 | 11+**2** | `r2chat_result.json` + `r2chat_turn{1,2}_raw.json` |
| G5 | 异步入库全管线（建库→入库→索引→回查） | agent/chat **async** | ✅ **PASS** | 258.7s | $0.66 | 13 | `r2ingest_result.json` |

### G1 同步模式（PASS）

- `success=true`，`stop_reason=end_turn`；工具轨迹 `Skill → kb_project_status → kb_search_vector×2 → kb_laya_judge → kb_doc_read×2 → kb_list`。
- 回复含**金标公式**（Attention(Q,K,V)=softmax(QKᵀ/√dₖ)V）、doc_path 出处、`## Result` 结构化段、Laya 盲点如实声明。
- 提示词注入的行为证据链完整：本轮 agent 在回复开头即自述"检索与验证链路"四步，与注入契约逐步对应。

### G2 OOD 诚实拒答（PASS）

- 116s 极速拒答；`kb_list`（62 库目录层甄别，判定无食品/发酵域）→ 一轮 `kb_search_vector`（top_k=10）。
- 回复列出已检索范围、命中无关项及分数（最高 0.536"主题沾边"）、明确"据实报告未找到，不作编造"。零编造 ✅
- 有趣观察：本轮 OOD 直接走工具原生路径（未加载 Skill）——快速诚实路径也会自然涌现。

### G4 交互连续性（PASS）

- turn1：201.0s / 11 turns，toolCalls 全录 `kb_list → kb_get_documents×2 → kb_laya_judge → kb_doc_read×6`，答案含第 34 章场景+逐字原文引文。
- turn2（`resume=b9585f1c…`）：**143.2s / 仅 2 turns**，一次 `kb_doc_read` 即命中"上轮那次求婚"语境，引文精确。
- ⭐ **F3 撤销**：turn2 响应**正常回显 `sessionId`（同值）**。R1 轮"resume 不回显"结论系 R1 验收脚本未提取该字段的测量缺陷，非平台缺陷。`docs/api-web.md` L3 行已改为撤销注记。

### G5 异步入库全管线（PASS）

- 0.x 秒即返 `task_id` → 轮询 271s（轮询墙钟）至 `completed`；引擎执行 258.7s / 13 turns / $0.66。
- **agent 逐项点名 skill 质量门**：A0 去重（建库前同名核查）、A3c 四要素描述（回读确认）、A3b 标签（`kb_doc_get_by_tag` 回读确认）、A2-Q 解析质量（245 字符→473 字节无乱码）。
- 显式 `kb_index_document` → collection 与 KB UUID 一致 → **三重回查**：向量命中 score **0.768** + `kb_search_stats` chunks=1 + `kb_doc_read` 逐字一致。
- **独立三源对账（我方验证，非 agent 自述）**：磁盘 `storage/tree-file-system/api-e2e-20261118-r2/R2轮对外API验收记录-2026-11-18.md` ✅ / `.knowledge-base.yml`（条目+标签+四要素）✅ / catalog API（kbId `4d0b401b-198d-435b-90b7-62920f26db42`, documentCount=1）✅ → **三源吻合**。

## 2. G3 异步检索的波折（如实记录）

| 尝试 | 结果 | 说明 |
|---|---|---|
| 第 1 次（`kbt_mwllqoqw…`） | 600s 超时（failed） | 与 R1 完全相同的有界 prompt（R1 当時 272s 完成）。工具轨迹完整（Skill→kb_list→kb_search_vector×2→kb_laya_judge→kb_doc_read），但今日回合速率整体下降（日间波动 ~2x+），预算耗尽。**注：本轮信封未留存**——`r2async_result.json` 先后记录第 1 次（轮询超时态）与第 2 次（失败终态），第 1 次终态信封被第 2 次覆盖，任务 id 以本表为准 |
| 第 2 次（`kbt_mwlmiv2e…`） | 600s 超时（failed） | 同 prompt 重试，同样轨迹，同样结局 |
| 第 3 次（`kbt_mwlmwtix_c7009333`） | ✅ **completed，PASS** | 最小路径 prompt（跳过已降级的 kb_laya_judge、免 kb_list 预扫描，仅 1×kb_search_vector+1×kb_doc_read）→ **139.5s / 4 turns / $0.37 / end_turn**；agent 完全遵守约束；金标正确（五个女儿，长女 Jane Bennet，第 1/3 章逐字引文+doc_path） |

**异步契约四轮全部实锤**（3 次提交 + 1 次失败终态消费）：提交 <0.1s 即返 task_id；客户端轮询窗口超时后任务**后台继续执行至终态**；终态信封（成功回复或失败原因+完整工具轨迹）事后均可取。这正是 §6 异步集成指南承诺的行为——超时的回合不是"丢失"，而是可归因的 `stage:"timeout"` 记录。**第 3 次尝试同时实测验证了 `docs/api-web.md` §7.4 执行约束模板的有效性**：同样的任务，带最小路径约束 139s 完成 vs 无约束 2×600s 超时。

## 3. 与 R1 轮对比

| 维度 | R1（上午） | R2（下午） | 结论 |
|---|---|---|---|
| 核心 API 能力 | 4 问全 PASS | 复测一致 | 稳定 |
| 同步检索耗时 | 442s（$1.23） | 302.7s（$0.91） | 快速路径在单飞行下更优 |
| OOD 拒答 | 99.3s | 116.0s | 稳定 <2 分钟 |
| 同 prompt 异步检索 | 272s 完成 | 2×600s 超时 | **日间速率波动 ~2x+（L1 新证据）** |
| 交互 resume | PASS | PASS + sessionId 回显实锤 | F3 撤销 |
| 入库管线 | 194s | 258.7s（点名质量门更全） | 稳定 |
| Laya 判卷 | 不可用 | 不可用（两轮复现） | F2 维持，待恢复 laya 模块 |

## 4. 缺陷与遗留

| # | 级别 | 状态 | 说明 |
|---|---|---|---|
| F1/L1 | 运营 | 维持+加强 | 600s 硬顶 + 日间速率波动 2x+；超时回合服务端回包可晚于 630s（客户端读超时须 ≥750s）。缓解=最小路径 prompt + async + 轮询（G3 第 3 次尝试即此策略） |
| F2/L2 | 环境 | 维持 | `kb_laya_judge` `No module named 'laya'` fail-closed；agent 每回合白耗一次失效调用。**待办：恢复 laya 模块** |
| F3/L3 | — | **撤销** | R1 测量缺陷，R2 实测 resume 正常回显 sessionId |
| — | 验收工件 | 留存 | 测试库 `api-e2e-20261118`（R1）与 `api-e2e-20261118-r2`（R2）留存于生产存储，如需清理指示即可 |

## 5. 给 AgentWorkShop 插件的集成清单（R2 修订版）

1. Base URL=**Web 层**（dev `:6789`）；`agent/chat` 不在 backend（历史大坑）。
2. 凭证=长期 API Token（`POST /api/auth/tokens`），Bearer 注入；401 → 重铸。
3. 主通道 `POST /api/kb/agent/chat`；**prompt 必须带执行约束模板**（见 `docs/api-web.md` §7.4；今日 G3 证明这是延迟安全的必要条件，不是可选项）。
4. 今日判卷引擎降级期间，约束模板里显式写"跳过 kb_laya_judge"可省一次失效调用。
5. 长任务一律 async + 10s 轮询；消费 `## Result` 段与 `tools_used`；引用可信度读 reply 内 P0/P1/P2 标注。
6. 字段契约：Agent 面 `session_id` / 交互面 `sessionId`，勿混用；resume 可用响应回显的 `sessionId` 续轮。
7. 客户端 HTTP 读超时 **≥750s**；429 退避；502/503 时 chunk 级 `POST /api/search/two-stage` 只读兜底。

## 6. 交付物清单

| 交付物 | 位置 |
|---|---|
| 标准外部 API 文档（v2.0，11 节） | `docs/api-web.md` |
| AgentWorkShop 集成契约（端口勘误 + v2 引用） | `docs/agentworkshop-integration.md` |
| 路由全量清单（136 条） | `review/api-harness-e2e-20261118/route-inventory.txt` |
| R2 原始信封 | 同目录 `r2*.json`（**11 个结果/提交工件**，含日志共 15 个 r2* 文件） |
| R1 报告 | 同目录 `REPORT.md` |
