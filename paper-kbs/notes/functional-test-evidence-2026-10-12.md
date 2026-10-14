# 功能/技能测试证据清点（2026-10-12）

> 来源：并行清点任务（functional/skill test evidence inventory）。所有路径相对仓库根。
> 用途：新稿 §8 评测章「系统功能证据组」的取数表。**引用任何数字时须同时引用其 caveat 列。**

| 功能 / 被验证的主张 | n | 结果 | 关键指标 | 出处 | 报告自述的 caveat |
|---|---|---|---|---|---|
| 🟢 入库与解析（上传→解析→索引→图谱→标签） | 50 篇 / 26 领域 | 50/50 解析、50 验证、图谱 5/5 | 总 1115.5 s；单篇解析 16.3–40.4 s；202 标签；`all_probes_ok:true`；batch_indexed 50 | `benchmark-suite/results/upload_parse.json` | 路由运行 `ingest_report.json`（187.1 s，50/50 verified，CS-AI 19/NS 14/LifeSci 9/Econ 4/Eng 4）中 43/50 篇 `tag_ok:false`（`verify_ok:true` 全过） |
| 🟢 入库，30000 字符分块档，A0–A9 全流程 | 50 篇 / 165 文档 | A6-V 50/50；标签 165/165 失败 0 | 3,798,446 字符；165 文档 = 9 整篇 + 156 个 `(part k of N)`（2000 档时为 2713 片）；解析 2672 s | `benchmark-suite/results/BENCHMARK-30000chunk-20260918.md` | 阶段 3a 因 Inbox 顺序意外重跑；补丁把 parse-save 自动拆分改为显式 `split:true`（Inbox 曾被拆成 800 片）；`MCP_HTTP_TIMEOUT=300`；800+ 图片**未**上传 |
| 🟢 入库+索引（隔离环境，真实 MCP） | 2 库 / 1×2942 字符文档 | PASS；A6-V 探针命中 | 索引 9 chunks，`collection=kb_95f4e9a1…`；探针得分 **0.7778**，chunk_index 2；two-stage 0.6549 | `benchmark-suite/results/SKILL-E2E-REPORT.md:19,52-63` | `parse_doc`/`kb_doc_save_parsed`/A2.5 拆分门**未被行使**（全部经 `kb_doc_create` 入库） |
| 🔴 去重 / 重复检测 | 重命名后 1 文档，1 组近重 | **真实缺陷 D1** | `kb_find_duplicates` 相似度 **0.9738**（文档 vs 自身旧路径）；1 组 | `benchmark-suite/results/SKILL-E2E-REPORT.md:23,74,130-142`（弱点 D5 见 `:165-169`） | move/rename 后的自动重建索引**不清除旧 chunk**；`force=true` 批量索引也不清；只有手工 `kb_reindex(force=true)`（任务 8214ad7d4a12）才修复 |
| 🔴 去重（组织层，真重复） | 322 文档，35 组「疑似」 | 真实重复 **0** | 相似度 0.90–0.975，**全部为同一论文不同 part 的相邻对**；L0 删除未执行 | `benchmark-suite/results/R2-SCALING-20260921.md:21` | —— |
| 🟡 标签管理与注册表卫生 | 316 个活标签 | PASS，0 失败 | A3b 165 ok/0 fail/47.6 s；`kb_doc_get_by_tag` count 1；E2E `kb_tags_list` → 316 标签 | `benchmark-suite/results/tags_report.json`；`SKILL-E2E-REPORT.md:75-77` | 标签注册表累积孤儿标签（测试标签、章节标题）；E2E 测试库标签泄漏进正式注册表 |
| 🟡 三源一致性（磁盘 ↔ `.tree-fs.json` ↔ `.knowledge-base.yml`） | 1 文档三源比对；O5b 33/33 | 发现不一致（D1） | 文档数 1 vs `chunk_count=`**18**（应为 9）；向量探针把每个 chunk 返回两次，得分完全相同 `[0.8,0.689,0.641,0.505,0.172]` | `benchmark-suite/results/SKILL-E2E-REPORT.md:24,80-85` | 向量层持有元数据 2 倍 chunk；R2 的 O5b 只抽样 33 篇（非 322）——`R2-SCALING-20260921.md:26` |
| 🟢 库组织 / 生命周期（建/改名/移动/合并/删除/重建索引） | 16 技能，109 次真实工具调用 | 13 PASS，2 PARTIAL，1 **FAIL** | 计数 1→0→1（源）/ 0→1→0（目标）；重索引 `chunk_count` 18→9；batch_delete 1/1 成功；两个测试库最终完全删除 | `benchmark-suite/results/SKILL-E2E-REPORT.md:22,28,34,66-70,184-189` | #13 `knowledgebase-update` FAIL（`ragctl version --json timed out after 30s`，`success:false`，D3）；D2 `kb_project_status` 静默忽略 `show_version`；D4 `kb_task_status` 在 `finished_at` 已置时仍报 `status:"running"` |
| 🟢 库组织，完整 O1–O8 重构 | 322 文档 / 5 库 | O2-M 322/322 PASS；L1 165/165；O5 165 ok/0 bad；O5b 33/33；O5-C 15/15 | L2 标签去重 4/4；L7 批量索引 322 文档；**15/15 检索回归探针通过（零退化）** | `benchmark-suite/results/R2-SCALING-20260921.md:21-27` | L4 子库拆分 + L6 层级 + mathematics 边界**全部待用户确认、未执行**（`:47-52`） |
| 🟢 图谱构建与查询 | 1 库构建；5/5 库有图 | PASS | 边 **4675→4679**（Δ+4 = 该文档的 4 条标签边）；节点 658、文档 333、标签 316；R2 图谱统计 节点 335 / 边 1671 / 文档 165 / 库 5 / schema v4 | `benchmark-suite/results/SKILL-E2E-REPORT.md:25,88-93`；`benchmark-suite/results/graph_stats.json` | `total_relations=0` 非 bug（只计新建边）；R2 改用 Neo4j 节点核对替代任务状态，因 `kb_graph_build` 留下**卡在 "running"** 的行（`:56`） |
| 🟡 经验库（提取/评审/检索/衰减/过期） | 13 条候选；dashboard 0 | 建/查/列 PASS；草稿 **PARTIAL** | drafts_created 13、create_ok、search_hit、list_count 1、0.8 s；dashboard total 0；全局检索 0 命中 | `benchmark-suite/results/experience_smoke.json`；`SKILL-E2E-REPORT.md:26-27,96-100` | #11 experience-summarize PARTIAL——**草稿池为空**，`draft_read`/`draft_approve` 未被行使；启发式 `experience_extract` 返回原始 dump，会被 E2 质量门拒绝；`experience_search_global` 报文「向量+关键词召回均为空（阈值=0.189）— 无语义相关经验，不编造」 |
| 🟢 规模 / 语料量 vs 延迟与精度 | 50→100 篇（163→322 文档） | 精度**保持**（无退化） | t0 old50 向量 48/50=0.96、MRR 0.98、top1 0.7595 → t1 **49/50=0.98、MRR 1.00**；new50 两通道 50/50；bq10 恒 9/10；ts 通道 48→47→48 | `benchmark-suite/results/R2-SCALING-20260921.md:33-45`；`benchmark-suite/results/scaling/compare.json` | 判定字段字面为 `"保持(±5pp 内)"`，delta_pp 2.0（old50）/0.0（bq10）；Q08 三轮全败但 gold_rank=1（严格关键词检查所致，非检索失败） |
| 🟡 检索模式消融（3 模式 + 基线） | 2 题 × 6 方法 | 6/6 金标命中 | mode_A 82.7/52.4 s（17/15 文档，24000 证据字符）；mode_B 78.5/29.8 s（23/11，40001）；mode_C **235.1/123.4 s**（36/38，12000）；bm25 0.0 s（10）；vector 0.4/0.0 s（1/3）；rrf 0.0 s（10） | `benchmark-suite/results/runs/run-20260927T094215Z-47cc948/RETRIEVAL-COMPARE.md:7-14` | 基线臂是 `retrieval_only`（`answer=None`、零 token 成本、`real_engine:null`、`gate_passed:null`）；仅 2 题；mode_C 的排序按 part 扇出（36/38）。**路径注意**：`benchmark-suite/results/RETRIEVAL-COMPARE.md` **不存在**，只在 `runs/run-20260927T094215Z-47cc948/` 下；`retmatrix.json` 同理 |
| 🟢 检索模式消融（三轨带答案） | 10 题 × 3 轨 | A2 10/10、B 8/10、C 6/10 | A2 116.2 s / 6.8 工具 / $0.5457；B 47.6 s / 4.9 / $0.6346；C 41.1 s / 3.7 / $0.2784；C gold_hit 8/10 | `benchmark-suite/results/exp_r2_grade.json`；`benchmark-suite/results/R2-EXP-3TRACK-REPORT.md` | C 在 BQ03、BQ10 金标失败；B 在 BQ08/BQ10 关键词检查失败（BQ10 `insufficient_evidence:true`） |
| 🟢 检索模式消融（更早，分层，判卷关闭） | 10 题 × 3 轨，judge OFF | A 9/10、B 6/10、C 5/10 | 延迟 113.0/42.7/48.0 s；成本 $0.4911/$0.1631/$0.1803；过度拒答 0.0（三轨）；`notfound_accuracy:null` | `benchmark-suite/results/stratified_grade_smoke.md`/`.json` | 只有 `single` 层被填（10/10）；**判卷正确性 = None**（L2 judge 未配置）；「两个方向必须同时报告——只报拒答正确率的规则，等价于『永远拒答』」 |
| 🟢 智能体 harness 集成，全生命周期 | 18 场景 | **18/18 PASS，零幻觉** | Stage A 7 场景 50.5–175.9 s、$0.87–1.80；Stage B（claude）23.2–52.4 s、$0.11–0.36；Stage C（omp）33.5–171.4 s、$0.027–0.065 | `review/fulltest-20261012/SUMMARY.md:8-44` | 第 7 项：OMP 入库的文档**缺图节点**（`graph kb-overview doc_count=2/3`）；OMP 墙钟 ≈ 2× 引擎时间（冷启动 50–90 s）；SSE 帧为裸 `data:` 无事件名 |
| 🟢 智能体 harness + 诚实拒答 | 3 条伪造/域外 + 10 题双跑 | chatmodes 9/9 门全过；零编造 | cm1 85.5 s ✅6 轮 / cm2 83.6 s ✅5 / cm3 76.1 s ✅5（mode A）；Quick10 两轮：gold 0.75→1.00、过度拒答 0、错误 0、41.5/34.1 s、$3.75/$4.50 | `benchmark-suite/results/PIPELINE-REPORT-20260930.md` | 发现并修复 3 个真实缺陷（MCP 挂载竞态使约 50% 短提示失败；B 道自相矛盾的子代理规则；B 道无界拒答 316 s→20.3 s）。残留：uv 冷启动 → 每轮约 2/10 哨兵诚实失败；L2 judge/qrels/显著性**未测** |
| 🟡 诚实拒答 / 域外探针 | 100 篇、322 文档、5 库 | 脚本化协议轨迹 | P1 Herbert–Moulton 对撞机：phase1 前三得分 0.497/0.4948/0.4937（近失被拒） | `benchmark-suite/results/honest_failure_probe.json` | 「门控得分与报告是执行代理的评分判断……是**记录下来的协议轨迹，不是独立评测**」 |
| 🟡 双道隔离（向量道 vs 纯内容道） | 4 题 × 2 道；+1 复测 | A 4/4 正确；B 首轮 0/4，复测正确 | A 43.4–132.9 s（7–13 工具）；B 50.0–75.2 s（12–19 工具）；**B 道零向量工具调用**；复测 106 s、11 工具、12 轮 | `benchmark-suite/results/SKILL-STANDARD-AND-CHAT-LANE-TEST.md:85-125` | B 的「空答案」是提示契约问题（「MUST finish with a final answer in this session」），非能力问题；复测仅 1 题、方差大；24 条坏 novel 描述未修 |
| 🟡 双道（机制增强，L4/L5.5 Jev 门） | 6 题 | A 5 正确/1 部分；**B 0 正确/2 部分/4 拒答** | A 29.2–69.0 s、$0.54–1.03；B 28.6–50.4 s、11–22 候选/33–64 窗/0–6 保留 part | `benchmark-suite/results/DESC-FIX-AND-TWO-LANE-MULTI-TEST.md`；`benchmark-suite/results/TWO-LANE-MULTI-TEST.md` | 已测结构性原因：B 的证据窗跨越不相连的 part 区间；「在这个语料上向量的『精确指向 chunk』仍然更强」；替代道是 workaround |
| 🟡 智能体 harness 集成（harness 矩阵） | 试过 omp/claude/codex/cursor/gemini/crush/opencode/goose/qwen/pi/copilot | 探针有记录，无汇总判定 | 最大探针日志 `probes/pi.txt` 83,957 B、`probes/copilot.txt` 50,479 B | `review/fulltest-20261012/probes/` | 若干探针只有 109–370 B 的桩（crush/cursor/goose/opencode/qwen）——harness 覆盖不均 |
| 🟢 静态证据链（技能 ↔ 94 工具） | 20 技能、94 工具 | 20/20 `quick_validate` PASS（原为 0/20）；0 FAIL/0 WARN；冒烟 22 调用 0 失败 | 最慢 `kb_find_duplicates` 15.8 s；其余 9–3751 ms | `benchmark-suite/results/SKILL-STANDARD-AND-CHAT-LANE-TEST.md:12-46`；`benchmark-suite/results/SKILL-AUDIT.md`；`benchmark-suite/results/SKILL-SMOKE.md` | 首轮 6 次冒烟失败是测试者自己的坏 `kb_id` 输入，重跑归零；只读，写链未证；触发词冲突只修了 1 处 |
| 🔴 面向论文的数字审计（非系统功能） | 核 24 条主张 | TRUE/STALE/UNVERIFIABLE/FALSE 混合 | 「139 后端测试」实为 **233**；「57 MCP E2E」实为 **39**；「106 端点」实为 **114 路径/121 操作**；「122 web 路由」实为 **124**；「19 Agent Skills」实为 **20** | `.audit/README-FACT-AUDIT.md` | README 基准表（P@5 0.590/FPR 12.0%/84 ms；QDCVR 0.630/3.0%/38 ms）**无法核实**，且被可追溯的 `module_b_retrieval_r2.json`（P@5 0.21 staged / 0.20 vector，1.33 s/0.081 s）反驳；`tmp/test_full_smoke.py` 不存在；「Auth is off」**为假**（认证开启、401 实测、116/121 操作需 bearer） |

## 可引用的原话（逐字，含 file:line）

- `review/fulltest-20261012/SUMMARY.md:8` —— 「**总判定:18/18 场景 PASS,回答质量全金标命中,零幻觉**」
- `review/fulltest-20261012/SUMMARY.md:54` —— 「**图节点缺口(轻)**:OMP harness 入库的《青鸾-7 复测纪要-C》未建图节点(graph kb-overview doc_count=2/3)」
- `benchmark-suite/results/SKILL-E2E-REPORT.md:34` —— 「**Tally:** 13 PASS, 2 PARTIAL (#11, #15), 1 FAIL (#13). 1 real defect class (D1) + 3 secondary defects (D2/D3/D4) + 1 weakness (D5).」
- `benchmark-suite/results/SKILL-E2E-REPORT.md:142` —— 「a caller who trusts auto-reindex will silently double their index」
- `benchmark-suite/results/R2-SCALING-20260921.md:43` —— 「**整理阶段带来真实 +2pp**: old50 96%→98%,MRR 0.98→1.00」
- `benchmark-suite/results/R2-SCALING-20260921.md:21` —— 「`kb_find_duplicates` 35 组"疑似重复"**全部为同一论文不同 part 的相邻对**(sim 0.90-0.975)……**真实重复 0 组,不执行 L0 删除**」
- `benchmark-suite/results/BENCHMARK-30000chunk-20260918.md:27` —— 「**通过 9/10 = 90%(达标线 ≥90%)**」
- `benchmark-suite/results/BENCHMARK-30000chunk-20260918.md:125` —— 「本知识库系统(Track A)是唯一同时做到"零弃答 + 段落级 verbatim 引用 + 诚实盲区标注 + 秒级检索"的轨道」
- `benchmark-suite/results/BENCHMARK-30000chunk-20260918.md:124` —— 「C 出现 **2/10 诚实弃答**(BQ01、BQ04)」
- `benchmark-suite/results/PIPELINE-REPORT-20260930.md:4` —— 「**PIPELINE 已升级并通过全部真实执行——新增 chat-API 三模式系统臂 9/9 门全过**」
- `benchmark-suite/results/DESC-FIX-AND-TWO-LANE-MULTI-TEST.md:64` —— 「**你的设想是对的,但落地后在这个语料上向量的"精确指向 chunk"仍然更强。**」
- `benchmark-suite/results/SKILL-STANDARD-AND-CHAT-LANE-TEST.md:18` —— 「车道 B 答案 | 首轮 4/4 返回的是**过程叙述而非答案**(未在会话内收束)」
- `benchmark-suite/results/NOVEL-DESC-REPAIR.md:5-6` —— 「**修复前**坏描述:`front/back matter` 命中 **24** 篇 / **修复后**坏描述:**0** 篇」
- `benchmark-suite/results/NOVEL-LONGTEXT-TEST.md:201` —— 「One sub-query (B2) retrieved a *nearby but wrong* passage for Wickham's account; the evidence pack therefore mislabels that beat (part 7 c36 instead of part 6).」
- `.audit/README-FACT-AUDIT.md:33` —— 「The README's numbers **contradict** the reproducible data」（P@5 0.590/0.630 vs 0.21/0.20）
- `.audit/README-FACT-AUDIT.md:57` —— 「**"Auth is off for trusted networks"** (EN:407) | **FALSE**」

## 失败 / 未了事项（不得隐藏，写稿时须逐条处置）

1. `knowledgebase-update` **FAIL** —— `ragctl version --json timed out after 30s`（`SKILL-E2E-REPORT.md:29,147-155`）；根因是推断，未证明。
2. **D1 改名/移动后留旧 chunk** —— 假近重 0.9738、`chunk_count` 18 vs 9（`SKILL-E2E-REPORT.md:130-142`）；只有手工异步 `kb_reindex` 能修。
3. `kb_project_status(show_version=True)` 被静默忽略（D2）；`kb_task_status` 字段自相矛盾（D4）——只轮询 `status` 的消费者「could loop indefinitely」。
4. `kb_search` 关键词相关性噪声：「quality」⊂「inequality」返回 5 篇无关经济学文档（D5）；用 `XYLOPHONE-9912` 的受控复测排第 1。
5. `soul-rag` **PARTIAL** —— `soul_qdcvr_ask` 353.2 s 后仍 `running`；未见答案/引用/PAS 分。
6. 经验草稿审批链**从未被行使**（草稿池空）；经验 CRUD、人格训练/RL/冥想、补天蒸馏、`parse_doc`/`kb_doc_save_parsed` 均**未被行使**。
7. 双道 B 道在该语料上 6/6、首轮 4/4 零正确答案——未解决。
8. `kb_graph_build` 留下卡在 `"running"` 的任务行；任务状态不能作为图谱完成证据。
9. README 基准表无法核实/被反驳；「60/60 passed」引用了不存在的脚本；测试/端点/路由计数过期。

## 在这些工件中**完全没有**测试证据的功能

- **库合并 / 拆分**（L5 merge、L4 子库拆分）——只有分析，执行明确推迟到用户确认（`R2-SCALING-20260921.md:47-52`）。
- **在父库下建库 / 层级嵌套（L6）**——仅提案，从未运行。
- **经验衰减 / 过期检测 / `apply_decay` 与冥想（`meditation_run`）**——所列工件中无任何战役。
- **崩溃/并发下的写入与持久性**——无对抗或中断测试；`.audit/README-FACT-AUDIT.md:180-183` 提到「a concurrent writer in this working tree」。
- **KB 面的认证/限流端到端**——只有 README 的认证主张被证伪（`:57`）；无正向认证测试。
- **嵌入与 MinerU（非 LLM）工作的成本/token 计量**——只记录了每次运行的 LLM 美元；解析/索引只有墙钟。
- 另有约 24 个 `review/` 战役目录（`retrieval-matrix-20260928`、`skill-fulltest-20260927`、`e2e-final-20260926`、`stress-20260923`、`three-mode-*`、`answer-compare-20260926`、`loop-e2e-20260927`、`stability-multiround-20260930` 等）各自有 REPORT.md/SUMMARY.md，但**不在本次读取集内**，其数字未进本表。`review/*.md` 与 `review/*.log` 顶层**不存在**（只有 34 个子目录）。
