# Skill 标准化 + chat-API 双车道检索测试报告

> 日期：2026-09-24 18:40 · 环境：当前 WorkBuddy 会话
> 关联产物：`CHAT-TWO-LANE-TEST.md`（逐题全文）、`laneB-retest.json`（补测）、`SKILL-AUDIT.md`

---

## 0 · 结论摘要

| 事项 | 结果 |
|---|---|
| **Skill 标准化** | **20/20 通过 skill-creator 的 `quick_validate.py`**（此前 0/20） |
| 项目状态 | `ragctl status` → **DEV READY**（Backend 8771 / Web 6789 / Neo4j / MinerU），**无需启动** |
| **chat API 是否支持知识库操作** | **支持**——实测调用 `backend_status` + `kb_list`，返回 10 个 KB / 364 docs，`denied=0` |
| 双车道检索测试 | 4 题 × 2 车道，**全部经同一个 chat API** |
| 车道隔离是否真实 | ✅ 车道 A 每题都用向量工具；**车道 B 全程 0 次向量工具**（脚本核对调用轨迹） |
| 车道 A 答案 | 4/4 **完整且正确**（7–13 次工具调用，43–133s） |
| 车道 B 答案 | 首轮 4/4 返回的是**过程叙述而非答案**（未在会话内收束）；补测**正确**（见 §4） |

---

## 1 · 按 skill-creator 标准规范化（20/20 通过）

读 `skill-creator/scripts/quick_validate.py` 得到**硬性格式要求**：

1. frontmatter 必须有 `name` + `description`；
2. **`description` 必须写在同一行**——`description: >` 块标量会被正则 `description:\s*(.+)` 解析成 `>`，含 `>` 直接判失败（**这是全项目 20 个 skill 的通病**）；
3. description 不得含尖括号 `<` `>`；
4. `name` 必须 hyphen-case；
5. `agent_created: true`（skill_manage 后续可修改）。

**新增 `scripts/skill_normalize.py`**：块标量 description → 单行双引号标量（转义 `\` 与 `"`）；
去掉尖括号；补 `agent_created: true`；保留其余键与正文；支持 `--check`。

```
skill                               规范化     校验
knowledgebase-librarian             ✓        ✓
knowledgebase-search                ✓        ✓
…（共 20 个）…
共 20 个 skill · 不达标 0 个
```

**回归验证**（改 frontmatter 不能弄坏别的检查器）：
- `node scripts/validate_skills.cjs` → **PASS**（8 项 / 0 警告 / 0 问题）
- `python scripts/118_skill_audit.py` → **0 FAIL / 0 WARN**（20 skill · 94 工具）
- `python scripts/sync_skills.py` → **PASS**（跨 harness 符号链接已重新同步）

---

## 2 · 项目启动状态

```
══ DEV MODE ══  ✓ READY
● Backend  :8771  healthy      ● Web :6789 healthy
● Neo4j    :7687  listening    ● MinerU up
```
**项目本来就在运行**，无需重启（`ragctl up` 未执行）。

---

## 3 · chat API 的知识库能力验证（先测 `kb_list`）

用 `chat_stream(prompt, allowed_tools=<平台 kb 工具>)` 发一条指令：
*"Use the knowledge-base tools to LIST every knowledge base…"*

| 项 | 实测 |
|---|---|
| 实际调用 | `backend_status` → `kb_list` |
| 返回 | **10 个 KB / 364 docs**（含 `Novel-PridePrejudice` 28 docs） |
| `permission_denied` | **0** |
| `is_error` | **False** |

**结论：chat API 完全支持按具体情况操作知识库**（可列库、可读文档、可检索），不是只能纯聊天。

---

## 4 · 双车道检索测试（4 题，全部经 chat API）

**车道定义（唯一差别 = 允许的工具集 + 流程指令）**
- **A · 向量 + 内容**：平台完整 kb 工具（26 个，含 `kb_search_vector` / `kb_search_two_stage`）→ 系统自带 QDCVR 流程
- **B · 纯内容（无向量）**：**剔除** `kb_search_vector` / `kb_search_two_stage` / `kb_search_stats`（20 个）→ 只能 `kb_list` → `kb_get_documents` → `kb_doc_read` 逐级读

### 监控

| QID | 车道 | 时延 s | 工具数 | 被拒工具 |
|---|---|---:|---:|---:|
| NQ1 | A | 132.9 | 13 | 0 |
| NQ1 | B | 75.2 | 12 | 0 |
| NQ2 | A | 58.3 | 9 | 0 |
| NQ2 | B | 59.3 | 15 | 0 |
| NQ3 | A | 55.8 | 8 | 0 |
| NQ3 | B | 50.0 | 12 | 0 |
| NQ4 | A | 43.4 | 7 | 0 |
| NQ4 | B | 59.1 | 19 | 0 |

### 车道隔离（防作弊核对）

脚本逐条检查调用轨迹：
- **车道 A**：每题都出现 `kb_search_vector` / `kb_search_two_stage` ✓
- **车道 B**：**4 题全部 0 次向量工具**，只有 `kb_list` / `kb_get_documents` / `kb_doc_read` ✓

### 答案质量

**车道 A（向量+内容）—— 4/4 完整且正确**，例如 NQ1：
> …Darcy refuses, saying Elizabeth is *"tolerable; but not handsome enough to tempt me."* …
> Elizabeth overhears this remark and is left with no very cordial feelings toward him…

**车道 B（纯内容）—— 首轮 4/4 返回的是过程叙述，不是答案**，例如：
> "Chapter III should follow. Let me read the next section."
> "The offset behaves unexpectedly… let me read the letter's latter portion…"

即：**它读到了正确的位置，但在会话结束前没有收束成答案**（首轮 prompt 未要求"必须在本会话内给出最终答案"，它就一直探索到回合上限）。

### 补测（关键结论）

给车道 B 加上**与车道 A 同等明确的收束要求**（"You MUST finish with a final answer in this session"），同一题重跑：

| 项 | 结果 |
|---|---|
| 工具调用 | **11** 次 |
| 回合 | **12**（上限 30，**自然结束，未撞上限**） |
| 时延 | 106s |
| 答案 | **完全正确**，逐字命中原文：*"She is tolerable: but not handsome enough to tempt me; and I am in no humour at present to give consequence to young ladies who are slighted by other men."* … *"Elizabeth remained with no very cordial feelings toward him."* |

**所以首轮车道 B 的"空答案"不是能力问题，是 prompt 契约问题**——纯内容车道是**开放式探索**（可以一直读下去），必须显式告诉它"读完就给答案"。

---

## 5 · 能证明什么 / 不能证明什么

**能证明**
- 20 个 skill 已符合 skill-creator 的标准格式（含我新建的 `knowledgebase-librarian`）。
- **chat API 可以真实驱动知识库操作**（列库/读文档/检索），不是纯对话。
- **两种检索方式都能通过 chat API 跑通**，且**工具面隔离是真实的**（车道 B 零向量调用）。
- 车道 A 在 4 道小说情节题上 **4/4 完整正确**，并给出具体 part 文件来源。
- 车道 B **有能力**给出同样正确的答案（补测逐字命中原文）。

**不能证明**
- 车道 B 与 A 的**质量高下**：首轮 B 是"未收束"而非"答错"；补测只做了 1 题，且**单次运行方差大**，不能当结论。
- 车道 B 的**效率**：它需要读多个 part，工具调用数（12–19）普遍高于车道 A（7–13），且对回合预算更敏感。
- 小说库 **24 条错误描述仍未修复**——车道 B 目前靠"读头部按内容判断"绕过，属于 workaround。

---

## 6 · 建议下一步

1. **把"必须在本会话内给出最终答案"写进车道 B 的调用契约**（skill 的 L7 已有此意，但 chat 调用侧要显式带上）——这是本次最便宜、收益最大的修复。
2. **给车道 B 更大的回合预算**（≥20）或教它"先定位 2–3 个候选 part 再精读"，避免开放式探索。
3. **重跑小说库 A3c 修复 24 条描述**，再复测车道 B（预期工具调用数下降、稳定性提升）。
4. 每条结论**至少 3 次重复**再下定论。
