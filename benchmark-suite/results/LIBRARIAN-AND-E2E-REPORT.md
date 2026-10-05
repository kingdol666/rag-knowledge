# Skill 端到端测试 + 长篇小说长弧问答 + 图书馆员拆分报告

> 日期：2026-09-24 · 环境：当前 WorkBuddy 会话 · 经 kb-mcp MCP stdio 通道
> 关联产物：`SKILL-E2E-REPORT.md`（子 Agent 全链路测试）、`LIBRARIAN-PHASE2-TEST.md`（三路对照）、`NOVEL-LONGTEXT-TEST.md`（首次小说测试）

---

## 0 · 结论摘要

| 事项 | 结果 |
|---|---|
| **全 skill 端到端测试** | 16 个 skill · **109 次真实 MCP 调用** · 13 PASS / 2 PARTIAL / 1 FAIL |
| 测试 KB 清理 | ✅ 两个测试库已删除，10 个原有库未被修改 |
| **长弧问答（小说）** | 向量优先答案覆盖 3–6/7（**波动大**）；图书馆员+L3 达 6/7 |
| **Phase 2 机制能否直接用** | ❌ 不能——**文档描述本身是错的**（26 个 part 中 24 个描述错误） |
| **拆分** | ✅ 已拆出 `knowledgebase-librarian`（L0–L7），并集成进调度器与检索 skill |
| 校验器 | `validate_skills.cjs` **PASS**（14 skill / 8 项）· `118_skill_audit.py` **0 FAIL / 0 WARN**（20 skill） |

---

## 1 · 全 skill 端到端测试（子 Agent 执行，109 次真实调用）

**PASS（13）**：knowledgebase-init / knowledgebase（调度器）/ ingest / list / search / manage /
organize / verify / graph / experience / batch / soul / butian。

**PARTIAL（2）**
- `knowledgebase-experience-summarize`：草稿池为空 → `experience_draft_read/approve` 无从触发（环境使然，非缺陷）。
- `soul-rag`：`soul_qdcvr_ask` 运行 6 分钟仍未返回答案；`soul_router` 正常（confidence 0.62）。

**FAIL（1）**
- `knowledgebase-update`：`kb_project_update(show_version=true)` 返回 `success:false`，
  `"error":"ragctl version --json timed out after 30s"`（`local.version=2.3.0`）。

### 发现的实际缺陷

| ID | 缺陷 | 证据 |
|---|---|---|
| **D1** | **`kb_doc_move` 后索引重复**：rename + move + `kb_batch_index(force=true)` 后 `kb_search_stats` 报 `chunk_count=18`（该文档实际 9 chunk）；`kb_search_vector` 把每个 chunk 返回两次（新旧路径、分数相同）；`kb_find_duplicates` 报出**自重复** `similarity=0.9738`。与 manage skill "move 会自动重建索引"的表述矛盾。`kb_reindex(force=true)` 可修复（异步）。 | 见 `SKILL-E2E-REPORT.md` |
| **D2** | `kb_project_status(show_version=True)` 静默忽略该参数 | 同上 |
| **D3** | 版本检查超时（见上 FAIL） | 同上 |
| **D4** | `kb_task_status` 状态自相矛盾：`status:"running"` 同时 `finished_at` 已设置、`success:true`，`elapsed_seconds=21.4` 与时间戳不符 | 同上 |
| **D5** | `kb_search` 子串误匹配："ZQ-7731 quality factor" 返回 5 篇经济学文档（`quality` ⊂ `inequality`）；受控复测证明索引本身正常 | 同上 |

---

## 2 · 长篇小说长弧问答：向量优先 vs 图书馆员

**问题**：*Trace how Elizabeth Bennet's opinion of Fitzwilliam Darcy changes across the whole
novel — from the Meryton assembly to their final engagement. Which scenes are the turning points,
and how does Darcy himself change?*（KB `Novel-PridePrejudice`，26 part，同一 chat API，12 000 字符预算）

| 路径 | 选中 part | **检索召回（真值 part）** | 答案覆盖 | 成本 |
|---|---|:--:|:--:|---:|
| P1 向量优先 | [6,8,15,17,18,21,23,24,25] | **0.571** | 4/7 | $0.025 |
| P2 图书馆员（**只信描述**） | [1,18] | **0.143** | 5/7 | $0.025 |
| P3 图书馆员 + **L3 描述信任检查** | [2,7,12,15,17,25] | **0.429** | 6/7 | $0.040 |

> 检索召回 = 选中的 part 是否覆盖 7 个关键情节的**真值 part**（由内容核对得出，与答案措辞无关）。
> **答案覆盖列不可靠**：同一检索在三次运行中给出 3/7、5/7、6/7 —— **LLM 单次运行方差**很大，
> 不能作为机制优劣的判据。这是本次测试最重要的方法学发现之一。

### 为什么 Phase 2 会失败：根因是**描述本身是错的**

```
part 13 描述: 【Part 13/26 · Gutenberg front/back matter】…
part 13 正文: "But why Mr. Darcy came so often to the Parsonage it was more difficult to
              understand…"        ← 第 32 章正文（首次求婚前夕）
```

26 个 part 中 **24 个**的描述标签是 `Gutenberg front/back matter`（实际是小说正文），
另有两个区间畸形（`Chapter XV–I` 倒置、`XLVI–XLVI` 退化）。
→ 图书馆员按描述选 part 必然选错：**只选出 2 个 part，漏掉 5 个关键情节**（召回 0.143）。

**这是 ingest 侧 A3c 描述质量门禁的漏网**：门禁校验了"四要素 + 回查"，但没有校验
**split part 的 `【Part i/N · 范围】` 标签是否可信**（是否样板化、是否退化、是否来自本 part 内容）。

---

## 3 · 拆分与集成（已完成）

### 新 skill：`knowledgebase-librarian`（L0–L7）

```
L0 CATALOG   kb_list(lightweight)  读每个库的描述
L1 SHELF     主体×属性×约束 打分 → 保留 top 2-3 个库
L2 SHELF SCAN kb_get_documents(lightweight) 读每个库内每篇文档的描述（part 感知）
L3 ⭐ TRUST  描述会撒谎：样板化/无信息/退化区间 → 不按描述选，改读文档头部按内容判断
L4 SELECT    显式候选清单 + **预算感知上限**（≈budget/2000 个 part；超选会稀释证据、降低质量）
L5 FINE      只在候选内做 kb_doc_read / kb_search_two_stage / kb_doc_get_by_tag
L6 VERIFY    与 knowledgebase-search 同一 0-8 评分
L7 HANDOFF   五段式作答；全失败 → 诚实 not-found
```

### 集成点
1. **调度器** `knowledgebase/SKILL.md`：新增 **Librarian** 路由行（触发词与 Search 行不冲突）。
2. **检索 skill** `knowledgebase-search/SKILL.md`：Phase 2 标题下注明"本阶段已独立为
   `skill://knowledgebase-librarian`"，并引入 L3 描述信任检查。
3. **入库 skill** `knowledgebase-ingest/SKILL.md`：A3c 新增 **A3c-P part 标签完整性检查**
   （非样板化 / 非退化 / 必须来自本 part 内容；违规必须重生成后再存）。
4. 校验：`validate_skills.cjs` **PASS**（14 skill，0 问题）· `118_skill_audit.py` **0 FAIL / 0 WARN**（20 skill）。

---

## 4 · 能证明什么 / 不能证明什么

**能证明**
- 16 个知识库 skill 的主用工具**全部可真实调用**（109 次调用），测试 KB 可创建/写入/索引/检索/图谱/删除并清理干净。
- 长文本长弧问题**可以**被回答：三条路径都产出了跨全书多情节的答案，且都能引用具体 part。
- 图书馆员机制**设计成立但依赖描述质量**；加上 L3 信任检查后，P2 的召回从 0.143 提升到 0.429、答案覆盖从 5/7 到 6/7。
- 向量优先**仍然是召回最强的单路**（0.571）——这反过来验证了 `knowledgebase-search` "向量先行"的排序是正确的。

**不能证明 / 尚未闭环**
- **答案质量受单次运行方差支配**（同一检索 3/7↔6/7）→ 任何"某机制答案更好"的结论都需要多次重复 + 统计检验。
- 图书馆员+L3 **没有在稳健指标上超过向量优先**（0.429 < 0.571）→ 它应当作为**兜底与路由**，不能替代主路径。
- 小说库的**描述缺陷尚未修复**（本次只做了检测与门禁加固，未重跑 A3c 重建描述）。
- E2E 测试**未覆盖**：`parse_doc`/MinerU 解析链路、A2.5 拆分门禁、`kb_doc_save_parsed`、经验 CRUD、soul 训练/RL、butian 蒸馏。
- D1（move 后索引重复）是**平台侧缺陷**，本次未修（需改后端），已记录证据。

---

## 5 · 建议的下一步（按性价比）

1. **修 D1**（move 后自动 reindex 或 `kb_batch_index` 清理旧路径 chunk）——影响所有移动类操作。
2. **重跑小说库 A3c**（按新增的 A3c-P）修复 24 个错误标签 → 再测 P2，预期召回大幅提升。
3. **答案评估改为多次重复**（≥3 次取均值/多数），否则任何质量对比都不可信。
4. **修 D5**（`kb_search` 词边界匹配）与 **D2/D3**（version 参数与超时）。
