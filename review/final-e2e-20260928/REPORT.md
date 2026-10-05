# 最终全链路验收（2026-09-28 深夜）— 电脑操作 UI + 外部 API 面

## 结论
**全部通过。** 前后端交互（浏览器实测）与对外 API 接口均按需完成任务，
执行过程无致命异常（日志仅两类已知非致命旧账）。

## 外部 API 面（4 接口 5/5 功能通过）
| 接口 | 结果 |
|---|---|
| GET /api/kb/catalog | ✅ 200 · 19 KBs · 0.1s |
| POST /api/kb/native-search（rag-bridge 一次性检索） | ✅ 200 · 25.9s 暖/56.3s 冷 · 答案 1006-1096ch · 129,326 数值命中 |
| POST /api/kb/agent/chat (async) → GET /api/kb/agent/tasks/:id | ✅ 提交 task_id → 393.7s completed · reply 2494ch（BERT WordPiece/30,000 逐字验证）· 56 工具 · 11 turns · $5.34 |
| POST /api/claude/chat (kbEnhanced SSE) | ✅ done=True · 51.3s · 1325ch · "2013" 命中 |

注：agent/chat 的 **sync 长连接**在 6 分钟级任务上会被 RST（外部集成应使用
平台提供的 async 提交+轮询契约——本次即按该模式验证通过）；验收脚本首版
轮询预算 398s < 任务实际 393s 且提取字段应为 `result.reply`，均已修正。

## 浏览器 UI（电脑操作，截图取证）
1. 首页渲染：19 知识库 / 390 文档 / 95% 索引覆盖，导航 10 页完整。
2. 路由守卫：直接点导航进受保护页 → 正确跳登录页；loop-auth 测试凭据登录
   成功并跳转 /knowledge-base。
3. 知识库管理页：19 库侧栏（CS 131/自然 75/生命 53/工程 39…）+ 文档面板，
   catalog/documents 接口正常（截图）。
4. KB Search 页：三种策略单选；CoRoT 查询 → **150 结果 / 4161ms，第 1 名即
   金标 1105.1887**（截图）。
5. Claude Chat：kbEnhanced 开关（database 按钮）→ 提问 → "回答中…"执行态 →
   完成。答案**双事实 P0**（延伸至 2013 年 3 月；129,326 条为 2010 夏时点值，
   正确指出非任务终值），并**如实披露 Laya 门矛盾**（gate 0.3929<0.5 拒绝 +
   重跑 survivor=0，而答案两处为逐字原文——"矛盾一并披露供你判断"）。
   10 turns · $0.0396 · 438.5s · deepseek-flash（截图）。

## 执行过程观察
- web dev 进程一次中断：起因是测试者用 shell `&` 启动（随 Bash 会话回收被
  杀），换受管后台任务后稳定全程——启动方式问题，非平台缺陷。
- 日志仅两类已知非致命旧账：Corpus-Chunks800 空库向量 warning（索引残留）、
  soul-template 目录缺 .knowledge-base.yml（ENOENT，catalog 正确跳过）。
- CLAUDE_SDK_CAN_USE_TOOL_SHADOWED 提示 = 只读工具预授权设计的预期日志。
- h3 statusMessage 弃用 warning：cosmetic。

## 工件
- external_apis.py / external_apis_result.json（5/5）
- simple-claude2.log 等检索日志见 ../retrieval-matrix-20260928/
- UI 截图：ZCode 会话 artifacts（首页/KB 目录/检索结果/聊天完成态）
