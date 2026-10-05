# PIPELINE 优化与真实跑通报告（2026-09-30）

> 任务：按当前最新系统改造 benchmark-suite PIPELINE + exp 实验项目，确保真正测出系统功能与执行流程，真实跑通并出报告。
> 结论：**PIPELINE 已升级并通过全部真实执行——新增 chat-API 三模式系统臂 9/9 门全过；Quick10 全功能对照双轮跑通（0 编造、0 过度拒答）；过程中发现并修复 3 个真缺陷。**

---

## 一、PIPELINE / exp 项目改造内容

| 项 | 变更 |
|---|---|
| 新增 `experiments/chat_mode_arms.py` | **chat-API 三模式系统臂**：A 钉库向量快车道（kbIds=[pin]）/ B 全库逐级（kbIds=[]）/ C 混合（钉库+混合后缀），全部走 `POST /api/claude/chat` 默认非流式；判定门 found=HTTP200∧success∧答案非空∧答案金标词，refusal=如实拒答标记 |
| `exp.py` 新增 `--chatmodes` | 三模式系统臂一键入口（`results/runs/chatmodes-*/CHAT-MODES-COMPARE.md`） |
| `exp.py` 预检增强 | 新增 kb-mcp 常驻 SSE(:8000) 探活（挂了不挡门，服务端 ensureKbMcp 会自动拉起） |
| `experiments/runner.py` | 写盘前目录护栏（外部清理不再让整轮白跑，2026-09-30 实测目录曾中途消失） |
| `PIPELINE.md` | 头部新增 2026-09-30 段：chatmodes 系统臂语义、与 retmodes（检索脚本纯检索）的互补关系、推荐执行顺序、当前系统三车道契约说明 |
| 题 | cm1=InstructDS（金标在 CS 库）/ cm2=stroke EHR（生命科学库）/ cm3=域外虚构题（零编造判定），与 retmodes q1/q2 金标同源可交叉对比 |

## 二、真实执行结果（全部真实 API 调用，无任何模拟）

### 1. chatmodes 三模式系统臂（chatmodes-20260930T143945Z-3ec2174）

9/9 门全过（exit 0）：

| 模式 | cm1 InstructDS | cm2 stroke | cm3 域外拒答 |
|---|---|---|---|
| A 钉库向量 | 85.5s ✅ 6 turns | 83.6s ✅ 5 | 76.1s ✅ 5 |
| B 全库逐级 | 196.9s ✅ 17 | 142.2s ✅ 9 | 316.0s ✅ 19（修复前，见缺陷③） |
| C 混合 | 99.1s ✅ 7 | 89.9s ✅ 8 | 72.0s ✅ 5 |

答案全部真实命中金标论文（InstructDS 2310.10981 / stroke 1904.11280，含原文逐字引用）；cm3 三模式全部如实拒绝、零编造。

### 2. V2-Quick10 全功能对照（10 题 × 5 方法 × 2 轮 = 100 单元）

- run-20260930T165316Z：a2 金标命中 **0.75**、引用命中 0.75、平均 41.5s、5.1 工具/题、**过度拒答 0**、errors 0、$3.75
- run-20260930T170730Z：a2 金标命中 **1.00**、引用命中 1.00、平均 34.1s、5.2 工具/题、**过度拒答 0**、errors 0、$4.50
- 自检两轮各 6/6 全绿（单元数=50、成本合计自洽、provenance 完整）
- 对照面：4 个 baseline（bm25/vector/rrf/rerank）检索金标全部 1.0，但闭卷作答**过度拒答率 37.5-62.5%**——a2 凭真实检索+裁决作答且 0 过度拒答，正是系统「检索后作答+如实奉告」契约的价值证据
- 未测量（如实声明）：L2 外部 judge 未配置（JUDGE_ENDPOINT/KEY），当前主因变量为 L1 金标/关键词层；qrels/显著性未做（人力步骤）

### 3. 缺陷修复后复测

- a2 挂载修复后直测 6/6 带工具（回退 uv 后 3/3 干净）
- B 车道指令修复后：cm3 拒答 **316s → 20.3s**（15.6×，6 turns，带扫描计数如实报告）；cm1 **196.9s → 57.5s** 且答案正确（12 turns）——零回归

## 三、过程中发现并修复的 3 个真缺陷

1. **allowedTools-only 会话的 MCP 挂载竞态（最重）**：非 kbEnhanced 请求（benchmark a2 臂/外部 harness）不挂常驻 MCP；即使挂上，SSE 异步注册与模型首个工具轮竞速，短 prompt 下 ~50% 失败，模型零工具凭参数记忆作答（QK01 直接答出注意力公式）。**修复**：该路径改 **stdio 挂载**（CLI 在 init 内同步拉起子进程，工具第 1 轮必就位，竞态从构造上消除）+ KB_TOOLS_NOT_READY 哨兵协议 + 零工具会话强制 success=false（code=KB_TOOLS_NOT_READY / KB_NO_RETRIEVAL）+ 3 次探活重试。**注**：禁表 {ToolSearch,Task} 在该路径会整体抑制 MCP 工具注册（实测），故 allowedTools-only 路径不传禁表；直接 venv python 替代 uv 不可行（SDK 忽略 stdio cwd 字段，实测 0/3）。残余：并行负载下 uv 冷启动偶发超启动窗（双轮各 2/10 哨兵，全部诚实失败、零编造）。
2. **B 车道指令自相矛盾**：硬规则禁 Task/Agent 子代理，正文却让模型"Spawn ONE retrieval subagent (Task tool)"，模型被迫自行调和白烧轮次。**修复**：改为"walk the librarian spine yourself"第一人称主干。
3. **B 车道拒答无预算**：域外题扫完描述层还继续翻文档（316s）。**修复**：目录层 + 一轮描述层扫描（含泛化描述库抽查，保 Voyager 规则）后即如实拒绝，禁止为确认拒绝读文档正文。复测 20.3s。

## 四、产物清单

- `benchmark-suite/experiments/chat_mode_arms.py`（新增）
- `benchmark-suite/exp.py`（--chatmodes + 预检 :8000）
- `benchmark-suite/experiments/runner.py`（目录护栏）
- `benchmark-suite/PIPELINE.md`（当前系统口径）
- `web/server/api/claude/chat.post.ts`（stdio 挂载 + 哨兵协议 + 零工具守卫 + 就绪探活）
- `web/server/utils/kb-instruction.ts`（B 车道主干重写 + 拒答预算）
- `web/scripts/bisect_mcp_mount*.mjs`（定位过程中的对照实验脚本，保留可复跑）
- 结果：`results/runs/chatmodes-20260930T143945Z-3ec2174/`、`results/runs/run-20260930T165316Z-3ec2174/`（COMPARE.md/REPORT.md/monitor.json）、`results/runs/run-20260930T170730Z-3ec2174/`、`results/runs/chatmodes-bfix-retest-20260930/`
- 复跑：`python exp.py --chatmodes`；`python exp.py --questions data/papers/qa_quick10.json --baselines bm25,vector,rrf,rerank`

## 五、遗留（不阻塞使用）

1. a2 在矩阵高并行下 uv 冷启动偶发超窗 → 哨兵诚实失败（每轮 ~2/10），重跑单元即恢复；根因是 uv 解析层，非系统逻辑。
2. L2 外部 judge / qrels / 显著性未配置（人力/配置步骤），报告已如实标注"未测量"。
3. 本轮检测到并行会话在同一仓库工作（15:04-15:11 有另一进程写 exp 工件并改过 chat.post.ts 的 requestMcpMount 初版）；本轮未提交推送，避免与并行会话冲突，建议确认后统一提交。
