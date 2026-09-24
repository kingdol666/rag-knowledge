# 知识库 Skill 测试报告

> 执行环境：当前 WorkBuddy 会话（仓库根 `rag_project/rag-knowledge`）
> 执行日期：2026-09-24 · 方式：**静态审计 + 只读冒烟**（经 kb-mcp 的 MCP stdio 通道）
> **未调用被测系统的对外问答 API**；未做任何写操作（无 create/update/delete/move/index）。

## 0 · 结论摘要

| 维度 | 工具 | 结果 |
|---|---|---|
| 跨 skill 一致性 | `node scripts/validate_skills.cjs` | **PASS** — 8 项检查通过，0 警告，0 问题 |
| 结构审计 | `python scripts/118_skill_audit.py` | **0 FAIL / 0 WARN**（19 个 skill） |
| 逐 skill 冒烟 | `python scripts/119_skill_smoke.py` | **16 skill / 22 次只读调用 / 0 失败** |
| 核心三 skill 结构 | 118 的 CORE 检查 | **ingest ✅ · search ✅ · organize ✅** |

**发现并修复 1 个真实缺陷**：`persona-augmented retrieval` 这一个触发词同时映射到
`Skill("soul")` 与 `Skill("soul-rag")` → 路由歧义（项目自带校验器报 FAIL）。
按项目约定（CLAUDE.md：检索+人格 → soul-rag）把它从 `soul` 的触发词表移除，保留在 `soul-rag`。
修复后两个校验器全绿。

---

## 1 · 规模与事实

| 项 | 值 |
|---|---|
| skill 目录 | **19**（14 个 `knowledgebase-*` + `soul` / `soul-rag` / `butian` / `nuwa-skill` / `dot-skill` / `musk-perspective`） |
| SKILL.md | 34 个（含 nuwa-skill 的 15 个 example 人格） |
| references 文件 | 128 |
| 注册 MCP 工具 | **94**（`kb_*` 41 · `experience_*` 26 · `soul_*` 20 · `fs_*` 3 · `parse_*` 3 · `backend_status` 1） |

---

## 2 · 核心三 skill 设计评估

### 2.1 `knowledgebase-ingest`（文档入库）—— 优秀

阶段：`A0` 去重（内容指纹）→ `A1` 全库现状普查 → `A2` 获取+解析 →
**`A2-Q` 解析质量门禁**（乱码/空正文/二进制残留 → 拒绝入库）→ `A2.5` 拆分门禁（脚本化强制）→
`A3` 结构化分析 → **`A3b` 标签质量门禁** → **`A3c` 描述质量门禁** →
**`A3d` KB 归属决策树** → `A4` 建/找 KB → `A5` 存储（解析路径必须走
`kb_doc_save_parsed`，整篇不截断）→ `A6-V` 索引验证 → `A7` 八项终检。

**为什么优秀**：每个质量点都是**显式门禁**（不是"建议"），且入库路径按来源分流
（解析 vs 上传），避免用错工具造成内容截断。这是本项目最成熟的一条链路。

### 2.2 `knowledgebase-search`（检索）—— 优秀，但有 1 个已知盲点

Phase 0 查询改写 → **Phase 1 向量优先**（`kb_search_vector` + `balance_kbs`）→
硬阈值 0.35 → 文档级去重 → **内容门控**（`kb_doc_read` 读正文，0–8 打分；≥6 快速退出）→
**Phase 2 图书馆员兜底**（`kb_list` 读**每个库的描述** → `fs_get_tree` 走目录 →
`kb_get_documents` 读**每篇文档的描述** → 定向多路召回）→ Phase 3 五段式作答或诚实 not-found。

**注意**：用户设想的"目录→描述→内容"顺序**确实存在**，但它是 **Phase 2 兜底**，
主路径是"向量先出手、内容门控裁决"。
**已知盲点（本会话实测）**：长文本场景下，把问题改写成自然语言陈述句会**丢掉词面锚点**，
导致关键 chunk 漏召回（《傲慢与偏见》part 13 近逐字探针 0.7418 可命中，改写查询却从未召回）。
建议：长文本保留一路**原句召回**，并给门控加"是否需要跨文档综合"维度。

### 2.3 `knowledgebase-organize`（整理）—— 优秀

`O1` 全局普查 → **`O2` 深度内容审计**（全量清单，O2-M 断言 audited/total=100%）→
**`O3` 层级拓扑分析**（子库拆分检测 / 跨库合并检测 / 层级分析）→ `O4` 按层修复（L1…L7）→
**`O5-C` 检索回归探针（强制：整理后不得检索退化）** → `O5/O5b` 逐层验证 + 三层一致性 →
`O6` 经验联动 → `O7` 合规策略。

**为什么优秀**：它带**回归门禁**——整理动作做完必须证明"检索没变差"，这正是
"整理"这类破坏性操作最该有的护栏。

### 2.4 其余 skill

`verify`（V1 三源一致 → V2 文档完整 → V3 解析质量 → V4 索引覆盖+修复 → V5 计分卡(115) → V6 报告）、
`manage` / `list` / `batch` / `graph` / `experience*` / `init` / `update` / `soul` / `soul-rag` / `butian`
结构均完整（frontmatter、引用、工具名全部可解析）。

---

## 3 · 逐 skill 冒烟结果（只读）

覆盖 16 个 skill、22 次调用、**0 失败**。完整表见 `SKILL-SMOKE.md`。要点：

| skill | 主用工具 | 结果 |
|---|---|---|
| knowledgebase（调度器） | `kb_list(lightweight)` | ✅ 540ms |
| knowledgebase-search | `kb_search_vector` / `kb_search_stats` / `kb_search` | ✅ 3/3 |
| knowledgebase-ingest | `kb_get_documents` / `fs_get_tree` | ✅ |
| knowledgebase-organize | `kb_find_duplicates` | ✅ 15.8s |
| knowledgebase-verify | `kb_search_stats` / `kb_graph_stats` | ✅ |
| knowledgebase-graph | `kb_graph_stats` / `kb_graph_central_documents` | ✅ |
| knowledgebase-experience | `experience_search_global` / `experience_dashboard` | ✅ |
| knowledgebase-experience-summarize | `experience_list` | ✅ |
| knowledgebase-init / update | `kb_project_status` | ✅ |
| soul / soul-rag | `soul_list` | ✅ |
| butian | `kb_list` | ✅ |

**说明**：首轮 6 个失败**全部是本测试的入参错误**（这些工具**按设计**要求非空 `kb_id`），
不是 skill/工具缺陷；改为传入真实 `kb_id` 后 0 失败。

---

## 4 · 复现命令

```bash
cd rag_project/rag-knowledge
node scripts/validate_skills.cjs                    # 跨 skill 一致性（8 项）
python scripts/118_skill_audit.py \
    --out benchmark-suite/results/SKILL-AUDIT.md    # 结构审计（frontmatter/引用/工具名）
python scripts/119_skill_smoke.py \
    --out benchmark-suite/results/SKILL-SMOKE.md    # 逐 skill 只读冒烟
```

---

## 5 · 诚实局限

1. **静态 + 只读**：本报告证明"skill 结构完整、其主用工具可真实调用"，**不证明**各 skill 的
   完整业务流程（如 ingest 的 A0–A9、organize 的 O1–O8）端到端跑通——那需要真实写操作，本次按要求未做。
2. **未覆盖写路径**：`kb_doc_create` / `kb_doc_save_parsed` / `kb_doc_move` / `kb_batch_index` /
   `parse_doc` 等写工具本次**未调用**（只读原则），因此"入库/整理的写链路"未在本次验证。
3. **触发词冲突只修了 1 处**：项目校验器覆盖 13 个 skill；`nuwa-skill` / `dot-skill` /
   `musk-perspective` 等非 KB skill 不在其检查范围。
4. **未做人工/模型评审**：skill 的"设计是否优秀"是本次的定性判断（基于结构 + 门禁设计），
   未做 A/B 效果对比。
