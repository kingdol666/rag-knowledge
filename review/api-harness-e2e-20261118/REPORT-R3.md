# 对外 API R3 轮验收报告（2026-11-18 晚）

> **本轮三问**：① API 全链路能否真实操作分析系统？② 分析结果能否持久化到数据库并在前端显示？③ API 文档能否作为集成契约照抄调用？
> **执行**：PRD 故事 US-007~US-010（`.omc/prd.json`），工件全部落盘本目录。全部判定引用本 fresh run。

## 总裁定：三问全部成立

| 问题 | 裁定 | 一句话证据 |
|---|---|---|
| ① 全链路真实操作 | ✅ 成立 | 纯 HTTP 资源端点六步链（建库→写文档→索引→向量命中→关键词命中→目录可见）6/6 PASS，全程不经 Agent |
| ② 持久化 + 前端显示 | ✅ 成立 | 五层持久化 11/11 PASS（chat-db/用户库/chroma 向量库/树索引/SDK jsonl）；真实浏览器登录后测试库、测试文档、检索命中全部可见 |
| ③ 文档即契约 | ✅ 成立 | docs/api-web.md v2.0 的示例逐字执行：contract 13/13（含双拼写读回、错误壳、automation 三端点、两阶段断言、agent 三回合） |

## 1. US-007 纯 API 全链路（6/6 PASS）

链路：`POST /api/kb/create`（api-e2e-20261118-r3, kbId `796153b2-0504-4a85-9b0e-fd41610b7e01`）→ `POST /api/kb/documents/create`（R3链路验证文档.md，带金丝雀标记 R3-CHAIN-CANARY-20261118）→ `POST /api/search/reindex`（total_chunks=1）→ `POST /api/search/vector`（金丝雀查询命中）→ `GET /api/kb/search`（BM25 命中）→ `GET /api/kb/catalog`（documentCount=1 可见）。
工件：`r3_summary.json`（chain 段）。每步响应 schema 与文档一致。

## 2. US-008 持久化（11/11 PASS）

| 层 | 验证 | 结果 |
|---|---|---|
| claude-chat.db（SQLite） | 今日 3 个交互会话行 + b9585f1c 单会话 3631 条消息 | ✅ |
| auth.db（SQLite） | 57 active users / 302 live tokens | ✅ |
| **chroma 向量库** | **活库=仓库根 `chroma_db/chroma.sqlite3`**（backend `vector.persist_dir` 默认值；`storage/chroma/` 是 0 集合空壳，勿被骗）——R1/R2/R3 三个测试库 collection 全在册（kb_c286bb1c…/kb_4d0b401b…/kb_796153b2…），R2 集合 embedding 行=1 | ✅ |
| 树存储 | .tree-fs.json 含 r2+r3；r2 .knowledge-base.yml 含入库文档条目 | ✅ |
| Claude SDK jsonl | agent/chat 车道会话（90894e5a、3f03d1bd）持久化于 `~/.claude/projects/d--codes-…-rag-knowledge/` | ✅ |

工件：`r3_db_persistence.json`。SQL 全程只读+参数绑定。

## 3. US-009 前端界面显示（真实浏览器，截图证据在 `gui-test-screenshots/`）

| 测试点 | 结果 | 证据 |
|---|---|---|
| 路由守卫：未登录访问 /knowledge-base → 跳登录页 | ✅ | `t1_kb_page.png`（/login?redirect=/knowledge-base） |
| 本地测试账号登录 → 回跳目标页 | ✅ | 登录后 url=/knowledge-base |
| 知识库页显示 R1/R2/R3 测试库（含描述与文档数） | ✅ | DOM 三行（api-e2e-20261118/-r2/-r3）+ `t3_r3_card.png`：r3 卡片选中态 + 右侧面板"全部知识库/api-e2e-20261118-r3/1 篇文档 + R3链路验证文档.md" |
| 检索页关键词命中测试文档 | ✅ | 关键词策略：**检索结果 7 条/740ms，金丝雀文档列结果 #2、得分 4.0000（最高）、库标签 api-e2e-20261118-r3 + 完整路径**；`t5_keyword_search.png` + `t5d_canary_result.png`（得分与出库标签可视） |
| 两阶段策略对生僻 token 不敏感 | ⚠️ 记录 | 同查询两阶段返 148 条弱相关（金丝雀串无语义信号）——符合策略设计，关键词/向量策略可正确命中 |
| 会话历史 | ⚠️ 数据层✅ / 弹窗缺陷 | 数据层：claude-chat.db 今日 3 会话 + `GET /api/claude/history` DESC 第一条即今日（标题=求婚问题）+ `GET /api/claude/sessions` 第一条即今日 **agent/chat 会话**（自动标题《傲慢与偏见》班纳特夫妇女儿信息，firstPrompt=注入 preamble——agent 车道会话同样入库可查）。**UI 缺陷**：历史弹窗（"SQLite 持久化"）只列出 4 条 2026/10/12 旧会话，今日会话未显示（`t7_history_dialog.png`）——列表渲染与两个 API 均不符，属前端显示层缺陷，数据与 API 无碍 |

## 4. US-010 文档即契约（13/13）

照 docs/api-web.md 逐字执行（占位符替换）：login（响应含 token）✅ / agent meta 契约 ✅ / harnesses 契约 ✅ / catalog 字段集 ✅ / h3 错误壳（缺 prompt→400 {error:true,statusCode}）✅ / kb/search {success,query,count,hits} ✅ / search/vector 代理 200 ✅ / **two-stage 断言 body.success + body.stage2.results（60 条）** ✅ / automation GET+toggle+summarize 三连（summarize 真实建了一条经验 exp-b6a61a4c3525）✅ / **双拼写读回（kb_id/doc_path 与 kbId/docPath 均 200）** ✅×2 / 同步 agent 回合 ✅（151.7s）+ 异步提交（0.0s 即返 task_id+poll 字段）✅ + 异步轮询至 completed ✅（140.9s，金标 five daughters，遵守跳过 judge 约束）。
工件：`r3_summary.json`（contract 段）+ `r3_readback_fix.json`（readback 顺序修正证据：套件首跑时 r3 库尚不存在导致 400，建库后双拼写复验均 200——属测试脚本顺序 bug，非文档/实现缺陷）。

## 5. 本轮新发现

| # | 级别 | 说明 |
|---|---|---|
| R3-1 | UI 缺陷 | 历史会话弹窗列表与 history/sessions API 不一致（显示 4 条 10/12 旧会话，今日会话不显示）；数据层与 API 层验证无碍，前端渲染层待修 |
| R3-2 | 备忘 | 存在两个 chroma 目录：活库=根 `chroma_db/`，`storage/chroma/` 为空壳——排障时以防 `vector.persist_dir` 实配为准，勿被空壳误导 |
| R3-3 | 设计内 | 两阶段策略对唯一 token 串（金丝雀）不敏感属正常；精确 token 匹配走关键词策略 |

## 6. 集成结论（给外部系统）

按 `docs/api-web.md` v2.0 集成**可行且已经全文验证**：认证→资源端点→Agent 服务面（sync/async）→持久化→前端可见全链路在真实浏览器与真实数据库双重证据下闭环。文档即契约成立；AgentWorkShop 插件可直接按 §7 九条要点 + §7.4 prompt 模板实施。

**遗留**：R3-1 UI 弹窗缺陷（前端修复项）；F2 laya 模块恢复（沿用 R2）；测试库 api-e2e-20261118/-r2/-r3 三个留存（需要清理说一声）。
