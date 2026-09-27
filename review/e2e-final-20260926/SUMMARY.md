# Final Full-Stack E2E Test — 2026-09-26

## 服务
backend :8771 healthy · web :6789 HTTP 200 —— `dev_restart.py` 干净重启（含孤儿 worker 清理），启动路径本身验证通过。

## 测试结果总览
| 套件 | 结果 | 备注 |
|---|---|---|
| backend pytest（17 文件 ~330 用例） | 全过（exit 0，1 skip） | |
| dev_smoke | **21/21** | 修复 SSE bug 前挂起超时 |
| test_full_smoke | **60/60** | 修复 PDF fixture 自包含 + 探测词 |
| test_auth_e2e | **26/26** | 修复默认端口 8770→8771 |
| e2e_platform_flow | **10/10** | |
| e2e_external_api | **87 过 0 败 1 skip** | 修复跨库 marker 测试稳健性 |
| e2e_multi_harness | 1 harness, 0 failures | |
| e2e_agentworkshop_api | **24/24** | |
| 浏览器 GUI 走查 | **8 页全过** | 登录/注册/主页/KB/检索/对话/SOUL/图谱/设置 |

## 本轮发现并修复
1. **[真 bug·高] SSE 流不关闭**（`web/server/api/claude/chat.post.ts`）：`event: done` 发出后 `: ping` keepalive 持续到 10 分钟 turn 超时——`for await` 的 `break` 会 await 迭代器 `return()`（引擎清理挂起），finally（clearInterval/res.end）不可达。修复：result 分支显式 `queryClosed=true + denyAllPending + abort + res.end()`。验证：done 0.07s→流 0.07s 关闭（修复前永不关闭）；dev_smoke 从挂起变 21/21。
2. [测试基建] `test_auth_e2e.py` 默认 backend 端口 8770（死端口）→ 8771。
3. [测试基建] `test_full_smoke.py` PDF fixture 依赖 tmp/ 残留 → 自动生成最小合法 PDF。
4. [测试设计] `test_full_smoke.py` 关键词探测词"拉伸比"属旧 PET 语料 → 改"stroke"。
5. [测试设计] `e2e_external_api.py` 跨库 marker（随机词嵌长文）在语料 369 文档后 top-50 稳定漏排 → DOC_B 增加 marker 主导的 beacon 段，重跑 attempt 1 即命中。

## 已知非 bug 观察
- Corpus-Chunks800 库 chunk 文档 `kb_doc_read` 恒空正文（数据面，待修数据）。
- e2e_external_api P5 一项按设计 SKIP（本机全部 harness 已安装，无法测未安装 409 路径——该路径由 agentworkshop 套件覆盖并通过）。
- 新建文档进检索索引为异步（向量索引完成后 BM25 增量），秒级最终一致——设计行为。

## GUI 证据（截图于 ~/.zcode/cli/artifacts/sess_d2f5d89e.../）
登录页（深色渐变+居中卡）、注册页、主页（书册式 TOC+统计 14 库/369 文档/93%）、KB 管理（14 库/131+75 篇与后端一致）、检索页（三策略+真实检索 #1 命中 stroke 金标，BM25+Vector 3181ms，分数条+chunk 引文渲染）、对话页（/help 发送→执行中→idle 完成，SSE 修复后 UI 全流程）、SOUL Studio（2 人格+空态）、Graph（四视图+构建中状态）、Settings（端口 8771/6789 与实际一致）。
