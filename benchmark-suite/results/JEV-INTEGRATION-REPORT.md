# Jev 判断层集成报告 — 逐级检索的「穷尽召回 → 判断剔除」

> 日期：2026-09-24 19:15 · 问题：*"List every scene in the novel where Darcy and Elizabeth meet
> in person, in order, and say what changes in their relationship at each."*
> KB `Novel-PridePrejudice`（26 parts / 28 docs）· 真值：**20 个场景，分布在 10 个 part** {2,3,5,7,12,13,17,18,22,24}

---

## 1 · Jev 是什么（已核实，非猜测）

**Jev = TypeSafe.AI 的 "System One" 模型** —— 它不是聊天模型，也不写文章；它做**快速结构化决策**，
一次往返返回**带类型的答案**。这正是检索门控需要的：一个判断，不是一段文字。

| 项 | 值 |
|---|---|
| 官方端点 | `POST https://api.typesafe.ai/v1/systemone`（Bearer `TYPESAFE_API_KEY`） |
| 托管端点 | `POST https://jevtypesafeai.com/api/v1/decide`（Bearer `JEV_API_KEY`，预付，≈$0.00003/次决策） |
| Python SDK | `pip install jev-reranker`（Python 3.11+），`JevReranker().relevance_rerank(...)` |
| 模型 | `jev-latest`（生产建议锁版本，如 `jev-1.13.0`） |
| 请求体 | `{model, state, questions}`，`state` 可为字符串/对象/数组 |
| **三种问题类型** | `choice`（≤255 选项）· `score`（2–10 有序等级）· **`noul`（校准的是/否，返回 0–1 概率）** |
| 响应 | `{model, answers:{name:{...}}, usage:{input_tokens, output_tokens}}` |
| 限额 | 250k tokens/s · 1200 req/min；state+问题 ≤64k tokens |
| 计费/托管 | 按用量计费；**模型本身不能自托管**（只有 tokenizer 可本地） |

**本 skill 的用法**：对每个候选文本问 **一个 `noul` 问题** ——
*"这段文字是否包含能直接帮助回答该问题的具体证据？"* —— 保留 `noul ≥ 阈值` 的候选，
只把存活者深读并放进上下文。完整说明见
`.claude/skills/knowledgebase-librarian/references/jev-judgment-layer.md`。

---

## 2 · 已落地的东西

| 产物 | 作用 |
|---|---|
| `benchmark-suite/experiments/jev_judge.py` | Jev 判断层。后端自动探测 `sdk` / `http` / `llm` / `none`，**每次都报告实际用了哪个**；无 key 时降级为 LLM 替代门（**明确标注不是 Jev**） |
| `benchmark-suite/scripts/122_jev_exhaustive_pipeline.py` | 完整管线：L0 目录 → L2 文档描述 → **L4 穷尽召回（读每一篇，无相似度筛选）** → **L5.5 Jev 判断** → L5 深读存活者 → L7 作答 |
| `knowledgebase-librarian` SKILL.md | 新增 **L4 穷尽召回** + **L5.5 Jev 门**；新增"委托子 Agent 做机械召回"的模式 |
| `references/jev-judgment-layer.md` | Jev 的 API 形态、SDK、限额、成本、诚实规则（禁止把替代品说成 Jev） |

---

## 3 · 实测：三轮迭代的真实召回

**同一问题、同一语料**，只改门控设计：

| # | 设计 | 保留的 part | **真值 part 召回** |
|---|---|---|---|
| 1 | 头部单窗 + 严格"证据"判据 | {5,13,14}（3 篇，含 1 个假阳） | **20%**（2/10） |
| 2 | **窗口级**（头/中/尾 3 窗）+ 严格判据 | {13,17,24} | **30%**（3/10） |
| 3 | **窗口级 + 枚举判据 + 阈值 0.4** | {4,5,7,8,13,14,16,17,18,22,24,25} | **70%**（7/10） |
| — | **向量 top-10 基线** | {5,6,13,15,17,18,22,24} | **60%**（6/10） |

### 两个根因（都是实测出来的，不是猜的）

1. **按整篇判断是错的** —— 一个 30k 字符的 part 只看 1200 字符的头部，证据在深处的 part 会被
   **误杀**。改成**窗口级**（每篇头/中/尾 3 窗，任一窗通过即保留该篇）后，召回 20%→30%。
2. **判据对"枚举型问题"过严** —— 问"列出每一个场景"时，一个只含**一个**场景的 1200 字符窗口
   其实是命中，但严格判据（"必须能引用具体事实/数字"）把它打了低分（实测分数 0.0–0.1）。
   改成**枚举判据**（"是否包含该类别的任意一个实例？"）后，召回 30%→**70%**，**反超向量基线（60%）**。

→ 因此 `jev_judge.py` 现在会**按问题形态自动选判据**（`criterion_for()`）：
`evidence`（查找型） vs `instance`（枚举型）。

---

## 4 · 诚实结论

**能证明**
- 逐级检索 + **窗口级 Jev 门**在本问题上把真值 part 召回从 20% 提到 **70%**，**高于向量 top-10 的 60%**。
- 召回是**穷尽的**：L4 真的读了全部 28 篇（不是 top-k），**没有因为相似度而预先丢弃任何 part**。
- 判据必须**按问题形态选择**——这是本次最有价值的发现，与用什么模型无关。

**不能证明 / 必须标注**
- **本次跑的是 `llm` 替代门，不是 Jev**（本机无 `TYPESAFE_API_KEY`/`JEV_API_KEY`，`jev-reranker` 未安装）。
  真实 Jev 的 `noul` 是**校准概率**，阈值语义会比 LLM 打分更稳定——但**判据设计问题与模型无关**，
  换真 Jev 也仍需按问题形态选判据。
- **仍是 70% 不是 100%**：漏了 part 2/3/12（初遇舞会、Lucas Lodge/Netherfield、Rosings 群）。
  单次运行、LLM 打分未校准，**需要多次重复**才能给稳定结论。
- 两个最终答案在早期设计下都是**诚实拒答**（证据被截断），这也是"门控过严"的代价。

**启用真 Jev**：`pip install jev-reranker` + `export TYPESAFE_API_KEY=...`（或 `JEV_API_KEY=jv_live_...`），
然后 `python benchmark-suite/experiments/jev_judge.py` 应显示 `real_jev_ready: true`。

---

## 5 · 建议

1. **默认用真 Jev**（校准概率比 LLM 打分更适合固定阈值），并按问题形态选判据。
2. 对"要求完整性"的问题，**门控做加法而不是过滤**：`保留 = Jev 通过 ∪ 向量 top-k`，
   用两个不同机制互相兜底（本次实测两者漏的 part 不同：向量漏 2/3/7/12，门控漏 2/3/12）。
3. 窗口数从 3 提到 5，或对通过率低的 part 做**二次深读再判**。
4. 每条结论**至少 3 次重复**。
