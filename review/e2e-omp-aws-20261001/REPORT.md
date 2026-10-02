# E2E 验收报告：chat-API×OMP 全生命周期 + AWS(AgentWorkShop) 插件集成

日期：2026-10-01 ｜ 执行：chat API（engine=omp）+ web `/api/kb/agent/chat`（AWS 插件同款入口）
工件目录：`review/e2e-omp-aws-20261001/`（每次调用的完整请求/响应/时延 JSON 均已落盘）

## 结论

**20/22 项全过，发现 2 个真实缺陷（1 个已定位根因+可用绕行，1 个已当场修复），系统写入→索引→检索→经验→整理的全生命周期闭环成立；AWS 插件修复配置后全链路真实可用。**

## 环境预检（T0）

| 项 | 结果 |
|---|---|
| web:6789 / backend:8771 / kb-mcp:8000/sse | 全部 200 |
| 引擎清单（GET /api/claude/engines） | **omp=True**，dsh/hermes/codex/cursor=True；**claude=False**（backend 探测，见 DEF-3） |
| AgentWorkShop | 未运行 → `aw.mjs start --port 3996` 拉起，7 插件装载成功 |
| rag-bridge 插件 | 默认 base_url=:8770 过期（后端权威端口 8771）且 token 未配置 → 见 DEF-2 修复 |

## 生命周期测试（chat-API×OMP + agent/chat）

| # | 场景 | 入口 | 结果 | 关键证据 |
|---|---|---|---|---|
| T1 | 检索命中（InstructDS） | chat API×OMP，钉住 CS 库 | ✅ | 三步 QDS 流水线答案全对；129s/$0.06/3 turns；证据 `t1_omp_found.json` |
| T2 | 库外拒答 | chat API×OMP，钉住 CS 库 | ✅ | 结论先行"不存在任何相关记录，无法从本库回答"+检索事实表；48s；证据 `t2_omp_refusal.json` |
| T3 | 建库→入库→索引→自验证 | agent/chat async+轮询 | ✅ | KB `e32572e5` 创建、文档 `7fb670e5` 入库、向量检索自验证命中 0.668；证据 `t3_ingest_final.json` |
| T4 | 经验总结写入 | agent/chat | ⚠️→✅ | 首跑：派发的子 agent 会话**无 MCP**→诚实 BLOCKED（DEF-1）；主会话重跑（sync，明确不派子 agent）：`experience_create` 成功 34.3s，经验 API count=1（《固态电解质膜低温测试经验》）；类别自动映射到后端枚举 `troubleshooting`，原文案保留进 tags |
| T5a | 再检索-事实 | chat API×OMP，钉住沙箱库 | ✅ | "8.4 mS/cm（25 摄氏度）"+文档名+库 id 全对 |
| T5b | 再检索-经验补救 | chat API×OMP，全库 | ✅(重试后) | 阶梯检索 kb_list→描述层→`kb_laya_judge` 0.861→全文核验，命中补救方案"低温预处理 30 分钟" |
| T6 | 整理体检 | agent/chat async | ✅ | 查重+描述质量+三源一致性审计报告，kb_id 正确，"只报告不修复"契约遵守 |
| 清理 | 删库 | web DELETE /api/kb/delete | ✅ | catalog 21→19，存储目录移除（注意：请求体须 `kbId`，用 `name` 会 400） |

## AWS(AgentWorkShop) 插件集成（T7）

| # | 场景 | 结果 | 证据 |
|---|---|---|---|
| T7a | 插件 health | ✅ | backend 8771 healthy、token configured+accepted、kb `aw-industrial`(3aea5973) 解析、web 19 库 |
| T7b | 插件 /search（→backend two-stage） | ✅ | "产线 tempA 单变量试验" → **15 命中，Top-1 精确命中** `ln-c629b8ef 产线 tempA −6℃ 单变量试验闭环经验`（score 12.66） |
| T7c | 插件 /experience | ✅ | aw-industrial 经验 20 条列表正常 |
| T7d | kb_agent 工具等价性 | ✅ | 插件工具即 POST `/api/kb/agent/chat`（sync/async）——T3/T4 的 async 提交+轮询与 T4 重试的 sync 直等已完整覆盖同一入口 |

## API 集成矩阵（T8）

web catalog 200（20 库）｜backend /api/v1/health 200｜backend /api/v1/experience/{id} 200｜MCP SSE 200｜`/api/kb/agent/tasks/{不存在}` → 干净 404｜`/api/kb/delete` 缺 kbId → 400 带明确提示｜chat 引擎端点 200。

## 缺陷与修复

| 编号 | 缺陷 | 状态 |
|---|---|---|
| **DEF-1** | agent/chat 派发的**子 agent 会话不继承 MCP 挂载** → 子 agent 诚实 BLOCKED（未伪造，契约行为正确）。主会话不受影响。绕行：任务指令明确"本会话直行，不派子 agent" | **平台 bug 待修**（与已修的 a2 stdio 挂载竞态同族）；绕行已验证 |
| **DEF-2** | rag-bridge `DEFAULT_BASE=:8770` 过期（后端权威 8771），且 kv/settings 未持久化时必然落错端口 | **已修复**：`D:\codes\ABO\AgentWorkShop\.AgentWorkShop\plugins\rag-bridge\index.mjs` 默认值改 8771（AWS 仓库内改动未提交，由你决定何时提交）；并通过 AW `PATCH /api/system/settings` 热配置了 base_url+token |
| **DEF-3** | 引擎探测显示 claude=False，但当天凌晨 claude 引擎实验全部成功——backend 探测与实际状态可能漂移 | **待核查**（影响：claude 不可用时按此探针会误判降级路径） |

## 测试侧诚实记录

- T2 首轮判定 False 是**测试断言 bug**（拒答回显检索词被误判为编造），修正断言后 PASS——系统行为本身正确。
- T4 首轮判定 True 是**测试断言过弱**（"已"字误命中），复核 agent 回复后确认真实失败→重试→闭环——系统行为是诚实的 BLOCKED。

## 复跑指引

```
cd review/e2e-omp-aws-20261001
python -X utf8 t1_t2_retrieval.py     # T1/T2（约 3 分钟）
python -X utf8 t3_t6_lifecycle.py     # T3-T6（约 10-20 分钟；结束后手动删沙箱库）
# T7：见上方 curl（health/search/experience）；T8：见上表端点
```

前置：平台三服务健康 + AW 已启动 + rag-bridge 已配置 token（本次已持久化到 AW 设置）。


## 附：AWS 精确检索场景测试（kb_agent 同款调用，2026-10-01）

用户场景：AWS 侧用 `/api/kb/agent/chat` 做产线数据与产线优化知识的精确检索（sync、默认 harness，与 `kb_agent` 工具完全同参）。

| 场景 | 结果 | 证据要点 |
|---|---|---|
| S1 产线数据（ln-c629b8ef tempA −6℃ 试验） | ✅ 124s | 真实数值表（PRE/P1/P2 三窗 mean 168.006→167.849，Δmean −0.157/−0.089℃）、经验增益 ≈−0.019℃/℃、噪声底 0.53℃>判据上限 0.38℃、最终决策 `recipe_apply` 恢复 160℃（rr-d2780，09:28:02 双通道复核 160/160）；doc_id `e9e96920`、关联经验 `exp-058858ca09cd`；含强制结论边界（不得外推到膜厚） |
| S2 产线优化知识（注塑质量窗口寻优） | ✅ 96s（重跑） | P0 可复用知识表+精确 doc_path：保压→克重线性增益 0.053~0.057 g/bar（≤10s 滞后）、九步链式爬坡 46.8→61.2 bar（第 8 步入窗，克重 31.36→32.36 g）、副杠杆停用依据、"乒乓陷阱"治理经验（120s 观察窗孤立下发必被反向→60~90s 内复测 `dcw_judge=keep` 抢窗） |

**诚实行为记录**：S2 首跑会话 MCP 未挂载（DEF-1 间歇形态），agent 走文档化直读路径并**自报盲区**（跨库向量召回未执行）；重跑后全能力路径可用，但仍诚实披露向量通道语义盲区（最高分 0.598 落无关论文），命中由元数据+逐篇实读完成并全部经真实内容验证。证据：`aw_scn1_line_data.json`、`aw_scn2_opt_knowledge.json`、`aw_scn2_retry.json`。

**给 AWS 侧的使用建议**：产线数据/知识问答用 `mode=sync`；检索面以 kb-mcp 全套为准，若会话未挂载 MCP，提示词要求"本会话直行、不派子 agent"即可规避 DEF-1。


## 附二：全功能穿透套件（全部经 `/api/kb/agent/chat`，2026-10-01）

**11/11 格全过**。沙箱库 `e2e-agent-20261001`（kb_id `ce6f057a`）测试完成后已删除（catalog 20→19）。证据逐格落盘（`r1…w8*.json` + `_call`/`_final` 完整载荷），任务存储回查补齐异步格的 session/tools/cost。

| 格 | 功能 | 判分 | 工具数 | 耗时 | 成本 | 过程证据（工具序列要点） |
|---|---|---|---|---|---|---|
| R1 | 产线精确检索（ln-b0413f88） | ✅ 克重 32.36g/61.2bar/入窗时刻全中 | n/a* | 76s | — | API 未回传帧（见观察①）；回答交叉确认两份文档 |
| R2 | 库外诚实拒答 | ✅ 无编造 | n/a* | 93s | — | 诚实"未覆盖"语义 |
| W1 | 建库+双文档入库+索引 | ✅ | 11 | ~6min | $0.89 | **设计管线逐字落地**：backend_status→kb_project_status→kb_list(查重)→kb_create→kb_doc_create×2→kb_index_document×2→kb_get_documents→kb_search_stats（session 258ebd08） |
| R3 | 新库事实检索 | ✅ 160℃/±0.4℃/5s/TT-90 | 18 | 87s | $1.12 | 混合路径（Agent 派发+repo Grep/Read+kb 读取）——答对但非最短车道（见观察②） |
| W2 | 文档更新+重建索引 | ✅ | 10 | — | $1.49 | session 6e0da2d1 |
| R4 | 更新后事实检索 | ✅ 15,000 次（更新→重索引→检索闭环） | 9 | 50s | $0.47 | **标准阶梯**：kb_list→kb_get_documents→kb_doc_read→kb_search_vector→kb_laya_judge |
| W3 | 经验写入 | ✅ | 5 | 62s | $0.67 | backend_status→kb_list→kb_get_documents→experience_create（session 085a23bf） |
| R5 | 经验检索 | ✅ | 8 | 36s | $0.33 | **设计经验流**：kb_project_status→experience_search_smart→experience_search_global→kb_list→experience_read |
| W6 | 图谱构建+关系查询 | ✅ | 26 | — | $2.78 | session bb35abcd |
| W7 | 整理体检 | ✅ | 19 | — | $1.38 | session 95e3dc44 |
| W8 | 三层一致性核验 | ✅ | 21 | — | $1.13 | session 1c361a0e |

\* n/a = 该格 API 响应未携带工具帧（见观察①），质量由确定性金标判分，过程由回答自述+产物复核佐证。

**总计**：11 格约合 **$12.0**、平均每格 ~90s（写入格 2-6 分钟）。

### 观察（给平台与 AWS 集成的改进输入）

① **异步格的 final 帧不回传 tools_used/session_id**，同步格正常回传——建议 tasks/:id 的 result 补齐这两个字段，否则 AWS 侧无法监控异步任务的过程。
② R3 出现"Agent 派发 + 仓库 Grep/Read"混合路径（答对但绕远）——agent/chat 的提示词契约可加"知识库问答仅用 kb 工具、禁仓库旁路"。
③ 写入格成本（$0.9-2.8/次）显著高于问答格（$0.3-1.1），主要在多文档全量索引——可考虑批量索引降耗。


## 附三：双工况按需检索隔离验证（2026-10-01）

目的：验证同一产线库（aw-industrial）中**不同工况的知识能否按问题场景隔离召回**——各命中本工况金标事实，且不混入另一工况数据。入口：`/api/kb/agent/chat`（sync，与 kb_agent 同参）。

| 工况 | 问题指向 | 金标命中 | 交叉污染 | 耗时 |
|---|---|---|---|---|
| **A 温度设定试验**（mp1-tempA −6℃） | 增益/判据/最终决策 | ✅ Δmean −0.157/−0.089℃、无可测增益、门限 0.55℃、恢复 160℃，且 `kb_doc_read` 97 行全文核对命中源文档 | **无**（保压/克重数据 0 出现） | 实测 |
| **B 保压-克重优化**（ln-b0413f88 链式爬坡） | 线性增益/入窗步/入窗克重 | ✅ 0.0574 g/bar、第 8 步 61.2 bar（14:40:00）、入窗克重 32.197 g，另给出 45→63.9 bar 无饱和与机理标定点 | **无**（温度试验数据 0 出现） | 实测 |

**结论：同一库内两组工况知识实现了真正的按需隔离检索**——问题语义决定召回边界，未出现跨工况知识混答。测试断言备注：A 首轮误判系模型输出用 Unicode 负号（−）而断言查 ASCII 连字符，修正后通过（测试侧问题，非系统问题）。证据：`condA_temp_trial.json`、`condB_pack_opt.json`、`cond_verdict.json`。


## 附四：跨知识库按产线隔离检索验证（2026-10-01，可行性确认 ✅）

目的：验证"根据不同产品产线情况**建立不同的知识库**，检索时**逐级检索到对应的知识**"是否可行。方法：经 `/api/kb/agent/chat` 为两条产品产线分别建库并入库各自参数文档，随后**不指定知识库**直接提问，检验目录级路由与跨线隔离。

### 执行记录

| 步骤 | 结果 |
|---|---|
| 建库 A：`e2e-lnA2-温控模块产线-r3`（产品 PX-777 温控模块） | ✅ 入库《PX-777 温控模块产线验证记录》（172℃ / ±0.25℃ / 采样 2s） |
| 建库 B：`e2e-lnB2-注塑单元产线-r3`（产品 PY-888 注塑单元） | ✅ 入库《PY-888 注塑单元产线调参记录》（58 bar / 33.05 g / 周期 28s） |
| Q1（不指定库，问 PX-777 参数） | ✅ 逐级路由到**库 A**（kb_id 87125617），向量分 0.81 + Laya 判定 0.531，172℃/±0.25℃/2s 逐字命中；并正确分析 r2 旧库文档不含这三项参数（跨库歧义消解） |
| Q2（不指定库，问 PY-888 参数） | ✅ 逐级路由到**库 B**（kb_id 6b68c6fb），向量分 0.855，58 bar/33.05 g/28s 逐字命中；且做了质量分诊——r2 旧参数文档降级 P1、不同产线的 PB-5000 文档判为干扰项剔除 |

### 结论

**可行。** 按产品产线建独立知识库后，不指定库的提问经"目录层 → 描述层 → 逐篇判卷"逐级收敛到正确的库与文档，两条产线双向零串扰；面对同产品旧版本（r2）与不同产线（PB-5000）的干扰文档，检索层给出了 P0/P1 分级与剔除结论，而非混答。

### 测试过程诚实记录（两轮迭代）

第一/二轮的"内容不符"由**测试脚本自身缺陷**造成：入库提示词只给了标题未嵌正文，入库 agent 依据标题自行生成了合理内容（内容生成 ≠ 逐字入库）；归因"并行会话碰撞"是误判，实际全部为本脚本产物。第三轮起正文逐字嵌入提示词，验证即通过。由此得出 **AWS 侧入库契约**：经 kb_agent 入库必须给出完整正文；只给标题时知识库会代写内容（该行为适合"帮我写文档"场景，不适合存档场景）。六个测试沙箱库已全部删除（catalog 回到 19）。
