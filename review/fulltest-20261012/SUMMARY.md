# 全链路完整测试报告 — 2026-10-12

**范围**:AWS 集成面 `/api/kb/agent/chat` 全生命周期 + 对外 harness API `/api/claude/chat` 双引擎(claude/omp)三模式 × (检索+入库)。
**环境**:web:6789 · backend:8771 · kb-mcp:8000 全活;测试账号 `fulltest-*` 临时铸 token(scopes=read,write)。
**金标**:Q1 语言模型事实学习(arXiv 2503.21676) · Q2 CoRoT(1105.1887, 129,326 光变曲线) · Q3 分子模拟多文档(1911.02792+2011.07200, 16.34%→6.71%, R² 0.16→0.75)。
**沙箱库**:`fulltest-e2e-20261012-112507`(7e70e4d8),4 篇虚构标定文档,测试后删除。

## 总判定:18/18 场景 PASS,回答质量全金标命中,零幻觉

## Stage A — agent/chat(AWS 集成面,原生全技能,7 场景)

| 场景 | wall | engine | turns | cost | 质量门 |
|---|---|---|---|---|---|
| A1 检索命中(Q1) | 140.1s | 137.4s | 4 | $1.77 | 2503.21676+平台期+微调 全中,P0 分级+作者级引用 |
| A2 如实拒答(K8s canary) | 105.9s | 104.1s | 3 | $1.25 | 明确 not-found + 近失候选逐条否证表(向量分+内容分 1/8) |
| A3 入库《蓝鹊-47》 | 97.9s | 96.1s | 2 | $0.98 | 文档落盘+向量索引确认 |
| A4 入库后回查 | 53.8s | 51.9s | 9 | $1.18 | 47.3/0.0837/沈砚 全中+出处 |
| A5 跨库(Q2 CoRoT) | 142.1s | 140.3s | 6 | $1.83 | 1105.1887+129,326 精确命中 |
| A6 经验沉淀 | 50.5s | 48.6s | 2 | $0.87 | exp-d6f4d47ae3d6 落库;本地向量 0.711;global-search top1 |
| A7 二次入库+图谱关联 | 175.9s | 173.9s | 2 | $1.80 | 《灰隼-19》落盘;related_to 边落盘(graph related 接口实证) |

过程形态(tools_used):agent 面真走 Skill×N + Agent 子代理 + kb_* 全套 + SendMessage/TaskOutput 编排,
还挂了用户域 MCP(fetch/agentmemory)。买的是全自主,代价是 $0.87-1.83/次、50-176s。

## Stage B — /api/claude/chat engine=claude(5+1 场景)

| 场景(模式) | wall | turns | cost | 质量门 |
|---|---|---|---|---|
| B_A 指定库向量快车道(SSE 监控) | 52.4s | 8 | $0.25 | Q1 金标全中;工具序列 two_stage→vector→laya_judge→doc_read×3 = QDCVR 设计原样 |
| B_B 全库逐级(图书管理员) | 40.3s | 7 | $0.36 | 1105.1887 命中 |
| B_C hybrid 全原生 | 45.9s | 8 | $0.30 | 6.71+0.75 双金标命中 |
| B_IN 入库(内容重复→查重) | 23.2s | 5 | $0.13 | **deduped:true** 复用 A7 同文,如实报告,查重管线正常 |
| B_IN2 干净建库《沧羽-88》 | 30.5s | 6 | $0.15 | 落盘+向量 0.747 命中 |
| B_VF 回查 | 25.0s | 5 | $0.11 | 0.0042+19.6 全中 |

## Stage C — engine=omp(5 场景)

| 场景(模式) | wall(引擎) | turns | cost | 质量门 |
|---|---|---|---|---|
| C_A 向量快车道 | 112.0s(47.3s) | 3 | $0.065 | Q1 金标全中 |
| C_B 全库逐级 | 101.2s(48.0s) | 6 | $0.042 | 1105.1887 命中 |
| C_C hybrid | 171.4s(82.7s) | 9 | $0.058 | 6.71+0.75 双命中 |
| C_IN 入库《青鸾-7 复测纪要-C》 | 74.6s(41.9s) | 5 | $0.040 | 落盘+向量 0.834 命中 |
| C_VF 回查 | 33.5s(15.0s) | 2 | $0.027 | 47.4+0.0837 全中 |

## 关键发现

1. **功能完备**:检索/拒答/入库/查重/经验/图谱/async 任务契约全部真机可用,全部落盘实证(不采信 agent 自述,逐一用 documents/graph/experience/vector 接口回查)。
2. **三引擎成本差 1-2 个数量级**:agent 面 $0.9-1.8 ≫ claude harness $0.11-0.36 ≫ omp $0.03-0.07。quality 同档。
3. **OMP wall≈2×引擎时长**(如 C_A 112s wall vs 47.3s 引擎):每次调用 ~50-90s 的 harness 冷启动开销;claude harness wall≈引擎时长。
4. **SSE 过程监控**:消息流为裸 `data:` 帧(无 event 名,chat.post.ts:723),解析时须按 data-only 帧处理;B_A 实抓 573 事件完整时间线。
5. **门禁有效**:模型第 1 轮尝试 EndConversation 被禁用清单拦截,未影响后续检索。
6. **ping 类琐碎 prompt** 会触发 6 连 Skill 预检(A0 探针,30s 超时被杀)—生产调用应给足 timeout_ms(默认 420s)。
7. **图节点缺口(轻)**:OMP harness 入库的《青鸾-7 复测纪要-C》未建图节点(graph kb-overview doc_count=2/3);agent 面 A7 入库的有节点。
8. **汇总脚本教训**:global-search 返回键是 `experiences`(非 results/hits),首轮"0 命中"为校验脚本读错字段,复测为 top1 命中。

## 复跑

```bash
python review/fulltest-20261012/run_fulltest.py          # 全量(断点续跑)
python review/fulltest-20261012/run_fulltest.py b_a c_c  # 单场景
```
前置:三服务存活;`python -c` 注册临时账号铸 token 存 `storage/fulltest-auth.json`(或改脚本 AUTH 段)。
