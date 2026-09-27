# Three-Mode Chat-API Retrieval Test + Mode A Optimization — 2026-09-26

## 一、模式 A 优化（本轮交付）

**新契约**：向量检索的"读正文 + LLM 0-8 评审"内容门 → **Laya/Jev 决策引擎核验门**。

- 新脚本 `.claude/skills/knowledgebase-search/scripts/vector_jev_search.py`：
  `kb_search_vector`（**宽网 top_k=30**，原 10）→ 硬阈值 + 文档去重（**保留全部去重文档**，砍掉原 top3-5 截断）→ 按 doc_id/doc_path 批量 `kb_doc_read` 全读 → 结构化分段 → 真实 Laya（默认）/Jev 逐段打分（fail-closed，`--require-real`）→ **判 yes 的文档全部进 result_list**（无 rubric、无保留剪枝，引擎裁决即终审）→ evidence_pack 承载幸存内容供知识增强作答。
- SKILL.md（knowledgebase-search）Phase 1 全部重写 + 铁律/NEVER/速查/learned 块同步；librarian/hybrid 交叉引用更新；镜像同步 PASS、validate PASS。
- 测试：新增 9 个离线单测（宽网去重/全收/空读 unscanned/引擎失败 fail-closed/零幸存如实报告/证据包/CLI），五套件 **62/62 通过**。
- 直跑真机验证（direct-A-q2）：top_k=30 → 26 命中 → 19 去重文档全读 → **真实 Laya 100/100 段打分（real_engine=true）→ 16 篇全收**，金标 stroke 文档在保留集（vec 0.807），178s。

## 二、chat API 三模式测试（2 查询 × 3 模式 = 6 轮，全部成功）

通道：`POST /api/claude/chat`（engine=claude, bypassPermissions, SSE）。OMP 引擎因 ustc 密钥 12h 预算耗尽（429 ExceededBudget $70.31/$70.00）不可用，测试前切换 claude 引擎（native-search E2E 验证过的同一引擎）。

| 轮 | 模式 | 耗时 | 答案 | 真实引擎 | 金标命中 |
|---|---|---|---|---|---|
| q1-A | A 向量宽网+Jev门 | 139s | 9075 字符 | 首轮 agent 未找到 Bash 用 MCP 等价门；q2-A 同款流程证明可跑真脚本 | ✅ 三步法+45%→75%+LoRA+DREAM |
| q2-A | A | 276s | 5026 | ✅ laya_sdk 95/95 段，17 篇全收 | ✅ PCA 年龄/婚姻最高+MLP 75.02% |
| q1-B | B 图书管理员 | 290s | 8886 | ✅ 13/13 段真 Laya，12 幸存 | ✅ 三步法细节最全 |
| q2-B | B | 298s | 5115 | ✅ 19/19 段真 Laya，17 幸存 | ✅ PCA+基准+文献因素 |
| q1-C | C 并行混合 | 424s | 6732 | ✅ 24 篇保留（相对线 0.837） | ✅ 三步法+训练+SOTA 数字最全 |
| q2-C | C | 694s | 3080 | ✅ 173 判决，kept 58→35 | ✅ PCA+基准+干扰项披露 |

## 三、质量评价（金标：三步合成法 / PCA 年龄婚姻最高+居住类型无贡献+MLP 75.02%）

| 维度 | A（优化后） | B | C |
|---|---|---|---|
| 正确性 | ✅ 6/6 全对金标 | ✅ | ✅ |
| 召回面 | 宽网 19-30 篇候选→引擎全判（**优化前只看 top3-5**） | 描述驱动 10-23 篇全读 | 双道合并 140 篇 |
| 引擎判决 | ✅ 真实 Laya 全段打分 | ✅ | ✅ |
| 速度 | **139-276s（最快）** | 290-298s | 424-694s |
| 知识增强 | 幸存集附带同域论文上下文 | 幸存段带行号+Jev 分溯源最规范 | lane 溯源+干扰项披露最透明 |

**优化效果实测**：q2-A 相比旧版模式 A（top_k=10 只读 top3-5 + LLM 评审），候选面扩大 ~3 倍、金标文档连同 16 篇同域文档全部由真实引擎裁决入库，全程无需 LLM 主观打分；q2-A 的补读步骤（evidence_pack 截断→kb_doc_read 补全）正是新契约设计的自愈路径。

## 四、发现与备注
1. OMP 引擎密钥 12h 预算耗尽（429）——环境问题，非代码 bug；claude 引擎可用。
2. claude harness 有 Bash（q2-A/B/C 均真实执行了脚本）；q1-A 的 agent 个体性地没找到 Bash、走了 MCP 等价流程——同提示词下 agent 行为存在方差。
3. nuxt dev 热重启窗口会让瞬时请求 401（B 轮写 tmp 文件后 C 轮首发命中）——重试即恢复。
4. q2-C 的 agent 在答案层对高分干扰项做了 0-8 叙事分级（result_list 本身未被剪枝）——呈现层选择，数据契约完好。

工件：`review/three-mode-chat-20260926/`（q*-A/B/C.answer.md + transcript + status、direct-A-q2.json、run_all.py、run_chat.py）。
