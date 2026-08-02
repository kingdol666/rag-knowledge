# SOUL 人格训练系统实施计划 — 第二轮多维专家评审报告(终审)

- 评审对象: `.omc/plans/soul-persona-system-20260802.md`(v2,pending approval)
- 评审日期: 2026-08-02
- 评审团: 5 个并行独立子代理,全部对仓库真实代码实证,互不通信
- 总体结论: **APPROVE-WITH-CHANGES(5/5)** — 架构方向成立、复用主张 85% 实测吻合、无否决项;存在 4 项必须修复的 BLOCKER 级缺口,合并修订后可批准

---

## 1. 评审团构成与结论

| 专家 | 维度 | 结论 | 核心发现 |
|---|---|---|---|
| **ExecVerifier** 执行实证 | 逐条核对 25+ 处文件:行号引用与复用主张 | APPROVE-WITH-CHANGES | B1 `complete()` 受 RESULT_SCHEMA 全局绑定;AC9 实证通过;引用准确率 ≈85% |
| **ArchReviewer** 架构 | 架构决策表/ADR/里程碑切分/隔离与回滚设计 | APPROVE-WITH-CHANGES | C1 锁跨进程;C2 双写无事务;C3 检查点边界;soul_service 需拆分 |
| **ReqAuditor2** 需求符合度 | 5 需求 × AC × 实现任务三重映射 | APPROVE-WITH-CHANGES | GAP-C1 认知草稿审批入口缺失(唯一结构性缺口);覆盖率 5/5 但 3 个 MAJOR 前置条件未定义 |
| **EvalExpert** 测评 | 质量闸门链、四维自评、双判官、校准集、阈值、AC 可测性 | APPROVE-WITH-CHANGES | CR-1 PAS 无定义;CR-2 四维锚点/硬绑定/变更检测空白;双判官多模型不支持 |
| **RiskCost** 风险成本 | 成本模型(实测 153 篇文档 ≈1010 次 LLM 调用)、并发、失败原子性、运维 | APPROVE-WITH-CHANGES | R1 手动工具绕过预算(BLOCKER);R2 OMP 无原生预算;R7 cost_usd 从未写入 |

---

## 2. 已实证确认的事实(非推断)

- **引用准确度**: 计划 25+ 处文件:行号引用约 85% 与代码一致(ExecVerifier 逐条核对);`server.py:1440/1800/1821-1825/2022/213-216`、`experience_meditation_service.py:552-615`、`kb_meditation_config.py:18-36`、`main.py:192-200` 均准确;行号偏差 ≤3 行。
- **AC9 通过**: `grep backend/app` 无 openai/anthropic 直连调用(ExecVerifier 实证)。
- **AC15/AC1 可实现**: `kb_search_vector`/`kb_search_two_stage` 每 chunk 返回 `score`(= 1.0 − ChromaDB distance,`vector_service.py:340`)+ `doc_path`;`score_threshold` 参数已存在于 MCP 工具层。前置门可直接用 `score_threshold=0.5` 实现(需确认 collection `hnsw:space` 为 cosine)。
- **部署形态**: uvicorn 单 worker(`main.py:123-130` 无 workers 参数;`rate_limit.py:4` 注释 "single-process")→ 计划中的 per-soul `asyncio.Lock` + `Semaphore(2)` 当前有效;多 worker 部署下失效(需文件锁,`backend/app/utils/file_lock.py` 已有模式)。
- **规模实测**: 13 个真实 KB;知识文档 153 篇;M3 全库自举 ≈153×3×2.2 ≈ **1010 次 LLM 调用**(≈$1-4 deepseek / $10-50 sonnet 量级)。
- **预算机制现状**: `HARNESS_CONFIG["claude"]` 支持 `--max-budget-usd`;默认 harness `omp` **无此参数**(预算强制缺口);`meditation_runs.cost_usd` 字段存在但**从未写入**(`meditation_db.py:74`,`finish_run()` 不收该参数)。
- **增量判据现状**: `.knowledge-base.yml` 每文档有 `updated_at` 但**无 content_hash** → "基于 updated_at/hash" 的 hash 部分需运行时计算并落盘。
- **调度器现状**: `_run_kb_aware_meditation`(:552)中信号采集+判空+continue 在 :593-597 —— **soul KB 无 signals,按现结构永远不会被触发**;mode 分支必须放在 KB 循环入口(获取 config 后,:585-590 附近)。
- **配置门**: `kb_meditation_config.py:143-149` `known_fields = set(DEFAULT_MEDITATION_CONFIG.keys())`,新字段必须进 DEFAULT 常量,否则每次 update 刷 warning。

---

## 3. 分级发现(跨专家合并去重后)

### BLOCKER — 批准前必须修复(4 项)

| ID | 发现 | 证据 | 修复要求 |
|---|---|---|---|
| **B1** | **PAS 无定义**: 全文 6 处出现(需求4/AC1/1.3/3.2)均无缩写展开与计算方式 | 计划 l.15/69/99/100/110/120 | §2 新增: PAS = Persona Alignment Score(人格一致性分),0-5,由独立提示词经 `complete()` 产出,与四维答案质量评分**正交** |
| **B2** | **四维评分不可实现**: 无评分锚点;"接地性与引用锚点硬绑定"未指定机制;提示词变更检测/校准集重跑触发机制空白 | 计划 2.3;prompts/ 下无 soul_eval 文件 | 2.3 补 5 级锚点表;硬绑定 = `min(代码校验引用路径存在性, LLM 评估关联度)`;`soul_eval_v{N}.txt` SHA256 存 checkpoints,learn 启动对比,变更自动重跑校准集 |
| **B3** | **手动工具绕过预算**: `soul_learn`/`soul_learn_all` 不经过调度器,AC16 预算约束对其无效;OMP(默认 harness)无原生 budget 参数 | RiskCost 实测;`HARNESS_CONFIG["omp"].build_args` 仅 `--max-time` | 工具入口预算检查(累计 cost 超限拒绝);`soul_learn_all` 加 `max_docs`(默认 20)+ dry-run;`complete()` 内加调用计数上限(每 run ≤30)+ token 估算累计(OMP 路径) |
| **B4** | **`complete()` 估算错**: `HARNESS_CONFIG["claude"].build_args` 模块级绑定全局 `RESULT_SCHEMA`(:44-91)与 `_SYSTEM_PROMPT_PATH`(:41),无法不改造直接复用 | agent_harness_manager.py:41/44-91/94-131 | 1.2 改为 90-120 行: 自行构造 CLI args;claude 动态 `--json-schema`、omp prompt 内嵌格式 + `_regex_extract_result` 解析 |

### CRITICAL — 设计期必须定案(6 项)

| ID | 发现 | 修复要求 |
|---|---|---|
| **C1** | **认知草稿审批入口缺失**(需求 3 闭环缺口): `soul_review_drafts` 只管记忆草稿,`cognition-drafts/` 无审批工具 | `soul_review_drafts` 加 `type: memory\|cognition` 参数(或新增工具);AC14 扩展 |
| **C2** | **调度 mode 分支位置错误**: 放在 :595-597 信号采集处 → soul KB 因 signals 为空在 :596 被 `continue`,永不触发 | 重构 `_run_kb_aware_meditation`: KB 循环入口读 `meditation_mode`;mode=='soul' → 跳过信号采集/harness/mark_derived,直接 `soul_learn_incremental`;独立 `_run_soul_meditation` 方法;report 加 `mode` 字段 |
| **C3** | **新 config 字段缺默认值**: `meditation_mode`/`max_questions_per_run`/`min_pas_auto_approve`/`max_budget_usd` 不在 `DEFAULT_MEDITATION_CONFIG`(:18-36),known_fields 门刷 warning,现有 13 库取到 None | 四个字段带默认值入 DEFAULT(experience/10/4.0/0.05);代码 `.get(key, "experience")` 双重防御 |
| **C4** | **增量判据无 content_hash**: `.knowledge-base.yml` 仅 `updated_at`,touch 时间戳可伪造"变更" | M3.1: updated_at 变更后运行时 SHA256 比对,一致则跳过;hash 存入文档 metadata 供后续比对 |
| **C5** | **蒸馏双写无事务**: 人格记忆写入成功但共享经验 `experience_create` 失败 → 长期不一致 | 记忆优先 + frontmatter `pending_sync` 字段,后续增量 run 重试;或降级为仅写人格记忆 |
| **C6** | **检查点/回滚边界未定义**: 快照只含"4 文档 SHA256+记忆索引";`cognition/`/`reports/`/`training/` 是否回滚?已导出训练数据回滚后残存会污染训练 | 快照明细化: 4 文档 SHA256 + `memories/` 清单+hash + `cognition-drafts/` 清单+hash + last_run_at;回滚范围 = `memories/` + `cognition-drafts/`;`cognition/`(已批认知)、`reports/`、`training/` 不可回滚;检查点保留最近 N 个(默认 30,可配)+ 自动淘汰 |

### MAJOR — 建议在对应里程碑内修复(11 项)

| ID | 发现 | 修复要求 |
|---|---|---|
| **M1** | **双判官多模型配置不支持**: config 单 harness/单 model;`complete()` 单次调用无法并行双判 | config 增 `secondary_harness`/`secondary_model`/`judge_sample_rate=0.10`/`judge_divergence_max=1.5`;eval_answer 对抽样条二次调用 `complete()`,role 描述不同(严格评审者 vs 质疑者) |
| **M2** | **人工审批无底线闸门**: approve 可无门槛放行接地性=0 草稿,整条闸门链被绕过 | approve 时接地性<3 或四维均分<3 → 需 `force=True`,记录审计日志(操作人/时间/理由)至 `soul-<name>/audit/approval-log.jsonl` |
| **M3** | **校准集生命周期空白**: 格式/位置/责任人/来源/初始 20 条均未定义 | 新增 2.3b: `soul-<name>/calibration/calibration.jsonl`(question/answer/evidence_paths/human_scores/pas_score/scored_by/scored_at);`soul_calibrate` 工具;初始 20 条由实施者+reviewer 从 soul_learn 前 30 条产出中选极值共同标注 |
| **M4** | **阈值 0.5 未实证校准**: 冥想场景仅用 0.3(experience_meditation_service.py:777),0.5 可能拦掉 50%+ 合法问题 | 阈值可配置 `soul_retrieval_score_threshold`(默认 0.5);M2 验收加指标: gaps.md 中 retrieval_failure 占比 ≤30%,超标则调低;确认 `hnsw:space=cosine`(score=1−dist) |
| **M5** | **AC1 子串匹配对中文脆弱** + language-style 无格式约定 | 1.1 约定: `## language-style` 每行一个短语、不含标点;断言前对 answer 与短语清单做标准化(去标点/统一全半角)后匹配 |
| **M6** | **soul_service ~800 行低估**: 14+ 方法实际 ≥1200 行 | 拆 4 模块: `soul_profile.py`(~150,load_profile/bundle/宪法断言)、`soul_learn.py`(~400,questions/answer/eval/distill/incremental/all)、`soul_memory.py`(~300,checkpoint/rollback/reflect/drafts/status)、`soul_service.py` 门面(~150,soul_ask 编排+pas_score) |
| **M7** | **M0 只改 1 处,实际 3 处**: 计划只提工具签名,漏 server.py body 构造与 client 方法 | M0.1 三处: `kb-mcp/server.py:1216` 签名加 `source_questions: list = None`;`kb-mcp/kb_client/client.py:762` 方法签名与 body;server.py 工具内 body 构造透传 |
| **M8** | **two_stage "图谱融合"描述不精确**: graph 邻居仅进 Stage1 候选,Stage2 纯向量 | §2 表改为 "Stage1: BM25+图谱扩展→候选文档;Stage2: 向量精细检索" |
| **M9** | **`meditation_runs` 表无 run_type + cost_usd 不可观测**: soul run 写 experience 专用字段;成本永不上报 | 表加 `run_type`(experience\|soul)或 soul 独立表;`finish_run()` 加 `cost_usd` 参数,解析 CLI stdout 费用/按 token 估算写入;`soul_status` 加累计成本 |
| **M10** | **失败原子性无保障**: harness 中断留下半截 frontmatter/半程记忆 | 写文件用 write-tmp-then-rename;learn 循环 accumulate-then-flush(全部 LLM 调用完成后批量写,失败全丢);gaps.md append-only + 时间戳前缀 |
| **M11** | **AC17 基线无前置任务**: "与上线前基线一致"但无基线捕获步骤 | M0 新增任务: 上线前基线快照(回归 8 项输出 + 经验检索/草稿列表样本落盘 `reports/soul-baseline-*.json`),M3 末对照 |

### MINOR(8 项,并入 v3 文字修订)

- **m1** soul-模板 → 真实 soul KB 创建流程未说明(复制模板说明)
- **m2** soul_kb 身份校验(命名 soul-<name> + 库存在性)未落为具体工具层任务(1.5)
- **m3** AC11 只读路径未显式包含 `soul_ask`(soul_ask 也不得写 values.md/soul-definition.md)
- **m4** MCP 工具计数不一致: §2/§8 说 6 个,实际 10 个(soul_ask/status/learn/eval/checkpoint/review_drafts/learn_all/reflect/rollback/export)——改为分阶段表述 "M1+M2 新增 6,M3 新增 3,M4 新增 1"
- **m5** soul_ask chunk 组装细节: graph 邻居与 two_stage 结果按 doc_path 合并去重;每 chunk 携 `{path, chunk_text, score}` 三元组入 prompt;PAS 校验引用锚点 ∈ 传入 path 集合
- **m6** 问题 hash 去重与向量 chunk 粒度: 语义 hash(前 100 字符+文档路径+问题类型);文档 updated_at 未变但重新索引 → 跳过
- **m7** AC7 五字段与 M2 frontmatter 命名对齐: `evidence`(文本摘要)+`evidence_paths`(路径列表),JSONL 用 `evidence_paths`
- **m8** 1.1 目录表述统一: 模板库预建完整目录(含 .gitkeep);新 soul KB 由 soul_service 首用自动 mkdir

---

## 4. v3 修订清单(合并后,可直接并入计划)

1. **§1**: 需求 4 后新增 PAS 定义行(见 B1)。
2. **§2 架构决策表**: two_stage 行改为 "Stage1: BM25+图谱扩展→候选;Stage2: 向量精细"(M8);complete() 行补 "自行构造 CLI args 绕过 RESULT_SCHEMA/_SYSTEM_PROMPT_PATH 绑定,估算 90-120 行"(B4);新增 "四维评分锚点" 与 "校准集" 两行(B2/M3)。
3. **§4 AC1**: 追加语言风格标准化匹配规则(去标点/全半角统一)(M5)。
4. **§4 AC7**: 五字段改为 `question/evidence_paths/answer/scores/persona`(m7)。
5. **§4 AC12**: 快照与回滚范围明细化 + 检查点保留策略(C6)。
6. **§4 AC13**: 双判官多模型字段、校准集存放与触发、`eval_drift_alert` 标记(B2/M1/M3)。
7. **§4 AC14**: 认知草稿审批并入 soul_review_drafts(type 参数);approve 底线闸门 force=True + 审计日志(C1/M2)。
8. **§4 AC15**: 阈值可配置 + score=1−dist 语义注记 + M2 校准步骤(≤30% retrieval_failure)(M4)。
9. **§4 AC16**: 预算约束扩展到手动工具入口;OMP 用调用计数上限(B3)。
10. **§5 M0**: 0.1 三处透传(M7);新增 0.2 基线快照任务(M11);新增 0.3 DEFAULT_MEDITATION_CONFIG 四字段(meditation_mode/max_questions_per_run/min_pas_auto_approve/max_budget_usd)(C3)。
11. **§5 1.2**: complete() 90-120 行,双 harness schema 机制(B4)。
12. **§5 1.3**: soul_service 拆 4 模块(M6);锁约束注明单 worker 有效、多 worker 需文件锁(M12,见下)。
13. **§5 1.4**: soul_ask chunk 合并与引用链细节(m5)。
14. **§5 2.3**: 四维锚点表 + 硬绑定 = min(代码,LLM) + 提示词 SHA256 变更检测与校准重跑(B2)。
15. **§5 2.3b(新增)**: 校准集基础设施 + 双判官多模型字段(M3/M1)。
16. **§5 2.4**: 双写事务策略 pending_sync(C5);原子写入 accumulate-then-flush(M10)。
17. **§5 2.4b**: type 参数 + approve 底线闸门(C1/M2)。
18. **§5 2.5**: soul_learn 入口预算检查 + 单次 ≤5 篇;checkpoint 保留策略(B3/C6)。
19. **§5 2.6**: 调度重构(mode 分支在循环入口,独立 _run_soul_meditation,report mode 字段)(C2);config 默认值(C3)。
20. **§5 3.1**: soul_learn_all 加 max_docs(默认 20)+ dry-run + 预算检查;增量判据补 content SHA256(C4/B3)。
21. **§5 3.3/3.4**: reflect 前自动 checkpoint(已有);rollback 范围 = memories/+cognition-drafts/(C6)。
22. **§7 风险表**: 成本行补手动工具与 OMP 计数上限(B3);并发行注明单 worker 约束,多 worker 需文件锁(复用 backend/app/utils/file_lock.py),标 M4+ 向前兼容(M12)。
23. **§8 ADR**: Consequences 补 "预算仅在 Claude harness 原生强制,OMP 靠调用计数;cost_usd 可观测性修复入 M3"(B3/M9)。
24. **§9 Changelog**: 记录第二轮 5 专家评审合并项。

> 注: ArchReviewer 提出的 "计划引用 models/kb_meditation_config.py 路径错误" 经查为误报(计划原文为相对路径 `kb_meditation_config.py:18-36`,正确),不并入。

---

## 5. 最终裁决与后续

- **裁决**: **APPROVE-WITH-CHANGES** — 修复 B1-B4 + C1-C6(10 项)后可批准实施;M1-M4 里程碑结构、选项 A 选型、复用路线均获 5/5 确认,无需推翻重来。
- **关键判断汇总**:
  - 架构方向正确: 单端点进程内编排、人格记忆物理隔离、复用两阶段检索/经验草稿审批/冥想调度器——5 位专家一致确认,选项 B/C/D/E 否决理由经代码实证成立。
  - 质量闸门链(检索前置门→四维自评→双判官→人工审批)结构合理,但 PAS、锚点、硬绑定、校准集四处定义空白必须补齐,否则"自嗨入库"无法被有效拦截。
  - 并发: 当前单 worker 下锁安全;多 worker 需文件锁(可复用 `backend/app/utils/file_lock.py`),已确认为向前兼容项(M4+)。
  - 成本: 0.15 预算仅在 Claude harness 下由 CLI 原生强制;OMP 靠 complete() 内调用计数+token 估算(≤30 calls/run);`cost_usd` 可观测性需修复(`finish_run()` 加参数 + CLI 输出解析)。
  - 调度接入必须按 C2 重构而非"跳过信号采集",否则 soul KB 永不触发——这是 2.6 的最关键实现点。
- **后续**: 由主 agent 将 §4 修订清单合并为 `soul-persona-system-20260802.md` v3(状态 pending approval),随后按 M0 → M1 顺序实施;M2 含阈值校准步骤(2.3b),M3 含基线对照与 cost 可观测修复。

---

*附: 各专家原始报告 — ExecVerifier(agent://ExecVerifier)、ArchReviewer(agent://ArchReviewer)、ReqAuditor2(agent://ReqAuditor2)、EvalExpert(agent://EvalExpert)、RiskCost(agent://RiskCost)*
