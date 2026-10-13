# ref-experiment-data.md — 维度1：本地实验工件结构化数据（图表可直接用）

- 主题：检索端到端三通道 Benchmark 实测（RAG Knowledge 平台，2026-10-12）
- 口径：**全部数据点均为本项目真实落盘工件**；本文件只做整编，不改数字。每个表下标注来源文件。
- commit `5f9faac` · 分支 feat/soul-persona-system · 问题集 cm1（InstructDS, 金标 arXiv:2310.10981, 库=计算机与人工智能/131 文档）· cm2（EHR 中风预测, 金标 arXiv:1904.11280, 库=生命科学与医学/53 文档）· cm3（Herbert-Moulton collider, **域外题**, 应拒答）
- 三模式：A=钉库向量快车道 · B=全库逐级检索（图书管理员 spine）· C=混合检索
- 本文件核对统计：**抽查数字 20+ 个，全部与落盘工件逐字一致**；3 处口径差异已单列于「§7 存疑与口径提示」，供 PPT 取舍。

---

## 1. 三通道总览（一张表讲清实验设计）

| 通道 | 运行主体 | 跑数 | 是否有 LLM 回答 | 门禁结果 | 结果均值（秒） | 来源 |
|---|---|---:|---|---|---|---|
| 通道1 | harness 对外 API 流式 SSE（`POST /api/claude/chat`, engine=claude, kbEnhanced=true） | 9 | 有（流式） | 8/9（修正口径） | A=47.0 · B=142.2 · C=51.2 | `review/retrieval-e2e-20261012/c1_*.json` + `channel1_summary.json` |
| 通道2 | `exp.py --chatmodes` 非流式系统臂，run `chatmodes-20261012T061102Z-5f9faac` | 9 | 有（阻塞 JSON） | 8/9（修正口径） | A=48.0 · B=66.4 · C=68.9 | `benchmark-suite/results/runs/chatmodes-20261012T061102Z-5f9faac/arm_*.json` |
| 通道3 | `exp.py --retmodes` 纯检索矩阵，run `run-20261012T062847Z-5f9faac`（无 LLM 回答） | 12（3 模式+3 baseline × 2 题） | 无 | 金标 12/12 | A 25.0/22.7 · B 25.0/10.2 · C 37.3/33.7 | `benchmark-suite/results/runs/run-20261012T062847Z-5f9faac/retmatrix.json` |

> 图表建议：3 页 deck 中「结果总览」页可用本表 + §2/§4 的端到端耗时（9 条序列）。

---

## 2. 通道1 逐跑明细（流式 SSE 时间线，9 跑）

| 模式 | 题 | 预期 | 端到端 s | 引擎报时长 ms | turns | 成本 $ | 检索工具净耗时 s | 门 |
|---|---|---|---:|---:|---:|---:|---:|:--:|
| A | cm1 | found | 55.7 | 53923 | 6 | 0.2376 | 17.9 | ✅ |
| A | cm2 | found | 48.8 | 47851 | 6 | 0.1930 | 21.2 | ✅ |
| A | cm3 | refusal | 36.4 | 35562 | 5 | 0.1218 | 3.6 | ✅ |
| B | cm1 | found | **353.5** | 352708 | 8 | 0.1784 | **319.5** | ❌ 假拒答 |
| B | cm2 | found | 43.2 | 42278 | 7 | 0.2501 | 13.2 | ✅ |
| B | cm3 | refusal | 29.9 | 29037 | 5 | 0.2001 | 2.0 | ✅ |
| C | cm1 | found | 43.1 | 42207 | 6 | 0.2039 | 11.7 | ✅ |
| C | cm2 | found | 45.6 | 44812 | 6 | 0.1936 | 19.8 | ✅ |
| C | cm3 | refusal | 65.0 | 64245 | 6 | 0.1590 | 21.8 | ✅ |

- 模式均值（端到端 s）：A=47.0 / B=142.2 / C=51.2；检索工具均值（s）：A=14.2 / B=111.6 / C=17.8（复算一致：46.97 / 142.20 / 51.23 与 14.23 / 111.57 / 17.77）
- 门禁：8/9；唯一 FAIL = B×cm1（修正口径「拒答优先」判定）
- 来源：`review/retrieval-e2e-20261012/channel1_summary.json`（rows 9 条，含 tool_sequence / tool_spans）；逐臂 SSE 全时间线在 `c1_A-cm1.json` … `c1_C-cm3.json`
- 每跑的检索工具序列（可直接做"流程条"图）：
  - A×cm1 `two_stage→vector→vector→judge`｜A×cm2 `two_stage→vector→judge→doc_read`｜A×cm3 `kb_list→two_stage→vector`
  - B×cm1 `kb_list→get_documents×3→vector(挂300s)→judge`｜B×cm2 `kb_list→get_documents×3→judge`｜B×cm3 `kb_list→get_documents×2`
  - C×cm1 `two_stage→vector→judge→doc_read`｜C×cm2 同左｜C×cm3 `two_stage→vector→judge→kb_list`

---

## 3. 通道2 逐跑明细（非流式机器门禁，9 跑）

| 模式 | cm1 s | cm2 s | cm3 s（拒答） | 模式均值 s | 成本均值 $/题 | turns 均值 | 门 |
|---|---:|---:|---:|---:|---:|---:|---|
| A | 53.0 ✅ | 65.3 ✅ | 25.7 ✅ | 48.0 | 0.182 | 5.3 | 3/3 |
| B | **41.4 ❌假拒答** | 91.9 ✅ | 66.0 ✅ | 66.4 | 0.300 | 8.3 | 2/3 |
| C | 58.3 ✅ | 100.0 ✅ | 48.3 ✅ | 68.9 | 0.219 | 7.0 | 3/3 |

- 逐臂原始值（复算一致）：A 53.0/65.3/25.7 · B 41.4/91.9/66.0 · C 58.3/100.0/48.3；单跑成本 $ 0.2088/0.2344/0.1034 · 0.1669/0.3023/0.4305 · 0.2097/0.2853/0.1606；turns 6/6/4 · 6/8/11 · 6/9/6
- **注意两种门禁口径**：`arm_B-cm1.json` 内 `gate_passed=true`（原始 marker 门被"问题回显"欺骗，拒答文本含 "InstructDS"）；修正为**拒答优先**后为 ❌（`REPORT.md` 全表按修正口径重算）。PPT 引用请用 8/9 修正口径，并可把"原始门 ✅→修正门 ❌"做成一张"判卷门修正"小图。
- 会话 ID（可做可复现性脚注）：A `44c01626/ed3a6fcf/ad186a66` · B `9631420d/92f9997a/7495ea7f` · C `3bc70319/8e25de47/6fe686f6`
- 来源：`benchmark-suite/results/runs/chatmodes-20261012T061102Z-5f9faac/arm_*.json`、`chatmodes.json`、`CHAT-MODES-COMPARE.md`

### 3b. 通道1 vs 通道2 同题同模式对照（同一系统两条测量路径）

| 模式×题 | 通道1（流式）s | 通道2（非流式）s | 差值 s |
|---|---:|---:|---:|
| A×cm1 | 55.7 | 53.0 | +2.7 |
| A×cm2 | 48.8 | 65.3 | −16.5 |
| A×cm3 | 36.4 | 25.7 | +10.7 |
| B×cm1 | 353.5（挂起） | 41.4 | +312.1 |
| B×cm2 | 43.2 | 91.9 | −48.7 |
| B×cm3 | 29.9 | 66.0 | −36.1 |
| C×cm1 | 43.1 | 58.3 | −15.2 |
| C×cm2 | 45.6 | 100.0 | −54.4 |
| C×cm3 | 65.0 | 48.3 | +16.7 |

> 图表建议：两通道均值柱状对比（A 47.0 vs 48.0 · B 142.2 vs 66.4 · C 51.2 vs 68.9），突出 B 的均值为**单点异常拉高**（去掉 B×cm1 后 B 流式均值≈36.6s）。

---

## 4. 通道3 纯检索矩阵（12 行全表，图表主力）

| 方法 | q1 耗时 s | q2 耗时 s | q1 金标 | q2 金标 | q1 docs | q2 docs | 性质 | 来源 |
|---|---:|---:|:--:|:--:|---:|---:|---|---|
| mode_A | 25.0 | 22.7 | ✅ | ✅ | 18 | 18 | 活库 + Laya 判卷 | `retmatrix.json` |
| mode_B | 25.0 | 10.2 | ✅ | ✅ | 23 | 11 | 脚本化图书管理员 | `retmatrix.json` |
| mode_C | 37.3 | 33.7 | ✅ | ✅ | 12 | 12 | A∥B 并行合并 | `retmatrix.json` |
| bm25 | 0.0 | 0.0 | ✅ rank-1 | ✅ rank-1 | 10 | 10 | 本地静态 100 篇 | `retmatrix.json` |
| vector | 0.1 | 0.1 | ✅ rank-1 | ✅ rank-1 | 1 | 3 | 平台向量 chunk 级（跨库口径） | `retmatrix.json` |
| rrf | 0.0 | 0.0 | ✅ rank-1 | ✅ rank-1 | 10 | 10 | bm25+vector 融合 | `retmatrix.json` |

- rank-1 金标 ID（可做"检索命中"示意）：bm25/rrf q1 首位 `2310.10981`，q2 首位 `1904.11280`；vector q1 `["2310.10981"]`，q2 `["1904.11280","2201.03675","2110.08918"]`
- Laya 环境（判决 GPU 化，C 与 A/B 同环境）：torch `2.12.1+cu130`，cuda=true（`retmatrix.json: laya_env`）
- mode_B 的 q1 榜首为 `计算机与人工智能/large-language-models__2312.10793__demystifying-instruction-mixing-for-fine-tun.md (part 1 of 2).md`（脚本臂能命中 NLP 指令微调文档；对照 LLM 版 B 却假拒答 —— 关键对照点）
- **首跑失败 → 跨库口径重跑**：首跑 `run-20261012T062223Z-5f9faac` 金标 10/12（vector q1/q2 均 `gold=False, docs=0`，0.0s）；设 `RAG_BENCH_VECTOR_KB=""` 后重跑 `run-20261012T062847Z-5f9faac` 12/12。首跑逐值：A 26.3/24.7 · B 25.2/9.6 · C 36.1/33.3
  - 来源：`review/retrieval-e2e-20261012/channel3_exp.log`（首跑 + 10/12）、`channel3_exp_rerun.log`（重跑 + 12/12）、`benchmark-suite/results/runs/run-20261012T062223Z-5f9faac/retmatrix.json`

---

## 5. 历史提速对照（2026-09-26 基线 → 2026-10-12）

| 方法 | 09-26 基线（q1/q2, s） | 10-12 当前（q1/q2, s） | 提速倍数 | 来源 |
|---|---|---|---|---|
| B（全库逐级） | ~342 / ~234 | 25.0 / 10.2 | 13~23× | `benchmark-suite/results/runs/retmodes-20260926T202450Z-47cc948/THREE-MODE-REPORT.md`（§3 基线列）+ `retmatrix.json` |
| C（混合） | ~1152 / ~1818 | 37.3 / 33.7 | 31~54× | 同上 |
| A（钉库） | ~13.3 / ~7.4 | 25.0 / 22.7 | 不可直接比（契约变更） | 同上 |

- 复算：342/25.0=13.7、234/10.2=22.9 → "13~23×"；1152/37.3=30.9、1818/33.7=53.9 → "31~54×"
- **引用注意**：基线列原文带 `~`（约值），且 09-26 报告明确标注——A 臂基线是**旧契约**（纯向量无判决），新契约含真实 Laya 逐段判决，"耗时不可直接比"；B 臂书架内文档数未变、幸存段数逐段一致（128/77），可比性最强。语料已漂移（09-26：11 KB/367 docs → 本轮 18 KB/379 docs）。
- 另有一条更近的参照（09-26 同报告第 2 节本轮值，真机单次）：A 117.1/124.5s · B 171.3/89.3s · C 576.5/541.7s（同一文件），可作"连续改进曲线"的第二点。

---

## 6. 关键发现 B×cm1（缺陷 / 根因 / 三连证据）

### 6.1 三连证据（同一缺陷两次独立复现 + 一次挂起）

| # | 通道/工件 | 结果 | wall | 关键细节 |
|---|---|---|---:|---|
| 1 | 通道1 `c1_B-cm1.json` | 假拒答（答案=“知识库中没有覆盖 InstructDS…”），而金标文档名就在库内 | 353.5s | `kb_search_vector` 兜底调用 **挂起 300.0s**（t+21.5→t+321.5，恰为 MCP 300s 超时） |
| 2 | 通道2 `arm_B-cm1.json`（独立会话、非流式） | 同样假拒答 → 系统性复现，非偶发 | 41.4s | 原始门 ✅（marker 被拒答文本中的 "InstructDS" 欺骗）；修正口径 ❌ |
| 3 | `extra_B-cm1_confirm3.json`（第三次确认） | 601s 级挂起、无答案产出（`answer_chars=0`, `gate_passed=false`） | **602.0** | `kb_list`→`kb_get_documents`→**`kb_search_two_stage` 挂 300.0s**（t+48.9→348.9）；`permission_request` 事件出现在 t=48.9 与 t=371.8 |

### 6.2 对照对照组（同模式、不同书架规模）

| 对照 | 书架 | 结果 | wall | catalog 记录 |
|---|---|---:|---:|---|
| B×cm1 | 计算机与人工智能 **131 文档** | ❌ 假拒答 | 353.5 | `kb_get_documents` 记录 payload **2,460** 字符 |
| B×cm2 | 生命科学与医学 **53 文档** | ✅ 双金标、答出全部关键细节 | 43.2 | `kb_get_documents` 记录 payload **33,089** 字符 |
| B×cm3 | 自然科学与地球科学（域外） | ✅ 如实拒答 | 29.9 | `kb_get_documents` 记录 payload **46,685** 字符 |

### 6.3 脚本化图书管理员对照（论文"逐级检索+判卷"叙事的直接证据）

- 通道3 `mode_B`（脚本化：词法扫描 + 字典序拼包）同题 **q1 25.0s / q2 10.2s 双金标命中**，q1 docs=23、q2 docs=11 —— 与"裸 LLM 注意力"版 B×cm1 形成成败对照

### 6.4 判卷门修正（可做成一张"证据链"小图）

- 原 marker 门：found 题只查答案是否含金标词 → 被**问题回显**欺骗（拒答文本也含 "InstructDS"）→ 原始门 ✅
- 修正：**拒答优先**（found 题答案构成拒答即 FAIL）+ 结论窗口取前 500 字，实现在 `benchmark-suite/experiments/chat_mode_arms.py`；本报告全部门禁按修正口径重算
- 来源：`REPORT.md:198-201`、`arm_B-cm1.json`（`gate_passed` 字段）、`channel1_summary.json`

---

## 7. 回答质量抽证（回答可验证细节，PPT"质量"页素材）

| # | 臂 | 抽证内容（逐字核对通过） | 来源工件 |
|---|---|---|---|
| 1 | A×cm2 | “**29,072 条 EHR 记录**；高血压/心脏病/年龄/平均血糖/BMI/吸烟/婚姻状况为主要风险因素；**特征彼此弱相关（不应做特征降维）**，全部 10 个特征都应用于建模” | `c1_A-cm2.json` answer（含 "29,072" ✓、"BMI" ✓、"降维" ✓） |
| 2 | A×cm1 | 逐字英文引用论文 §3.2：`three-step approach … summary-anchored query generation, query filtering and query-based summary generation`；含 **Flan-T5-XL** | `c1_A-cm1.json` answer（三个关键串均命中 ✓） |
| 3 | C×cm1 | 中文三步合成管线（摘要锚定查询生成→查询过滤→基于查询的摘要生成）+ **Flan-T5-XL** | `c1_C-cm1.json` answer ✓ |
| 4 | B×cm2 | “**Laya 引擎 8/8 段全部存活，最高分 0.94**”；“**PCA 年龄+婚姻状态贡献最大**、居住类型几乎无贡献；**MLP 最高 75.02%**” | `c1_B-cm2.json` answer（"8/8"✓ "0.94"✓ "75.02"✓ "婚姻"✓） |
| 5 | C×cm3 | 域外题如实拒答 + 自曝检索事实：“`kb_search_vector` 最高分 **0.500** —— 仅为 SLAM 'drift' 语义近邻”、“**36 段**评分、4 篇有存活段但无一段相关”、“honest not-found” | `c1_C-cm3.json` answer ✓ |
| 6 | 三模式×cm3 | A 36.4s / B 29.9s / C 65.0s **全部如实拒答**（弃答延迟即"诚实成本"） | `channel1_summary.json`（refusal=true ×3） |

> 图表建议："质量页"用 4 条引文 + 一行"拒答纪律 3/3"；引文最长不超过一行半，关键数字放大（29,072 / 0.94 / 75.02% / 0.500）。

---

## 8. 存疑与口径提示（抽查中发现的 3 处不一致，PPT 引用前请取舍）

> 以下 3 条**不是**数据错误，而是"报告表述与其落盘工件不完全对齐"。建议 PPT 采用右列更稳的口径。

| # | 报告/主摘要表述 | 工件核对结果 | 建议口径 |
|---|---|---|---|
| 1 | 「131 文档书架 `kb_get_documents(lightweight)` 返回 **65.5KB** catalog；对照 53 文档≈**25KB**」（`REPORT.md:199`、`_user_materials.md:68`；数值仅见于报告与其生成脚本 `gen_report.py:293/378/408`，**无独立测量工件**） | 我用 KB 元数据独立复测（`storage/tree-file-system/计算机与人工智能/.knowledge-base.yml`，131 文档 = `total_documents: 131`）：全量 lightweight catalog JSON = **73,741 字符 ≈ 72.0KB**；字段变体 name+doc_path+description = **60,417 ≈ 59.0KB**；仅 descriptions = **29,498 ≈ 28.8KB**。53 文档库：全量 **29,476 ≈ 28.8KB**、name+doc_path+description **24,031 ≈ 23.5KB**（对应"约 25KB"）。→ **65.5KB 未复现**（最接近的变体为 59.0KB） | 说「131 文档全量 catalog 达 **数十 KB**（按字段口径实测 59–72KB）」，或改用仅描述口径 **28.8KB**；若必须用 65.5KB，请注明"报告口径，未附测量工件" |
| 2 | 同上是"载荷灌爆上下文 → 注意力扫漏"机制 | 通道1 记录的该次调用 payload **仅 2,460 字符**（`c1_B-cm1.json`；`extra_B-cm1_confirm3.json` 复现同一值 2,460），而同一 run 内 53/75 文档库分别记录 33,089 / 46,685 字符 —— 即"文档更多的库返回的 payload 反而小 2 个数量级"。2,460 字符装不下 131 条目录（仅金标所在 4 篇的名称就 >600 字符，金标位于目录第 12–15 条）。B×cm1 答案自述只看到 MARL/Transformer 类主题，且**看不到任何 nlp__\* 条目** | 根因可写为「描述层扫描**未拿到完整 catalog**（记录 payload 仅 2,460 字符）→ 模型在残缺目录上判无」；同时保留"全量目录数十 KB 超出裸注意力可靠扫描范围"作为**架构性**论据（脚本臂 25.0s 双金标即机械化的证据）。建议 PPT 用「payload 异常：131 文档目录仅 2,460 字符（应 ≥ 数十 KB）」作缺陷证据，比 65.5KB 更硬 |
| 3 | confirm3「卡点为 t+371.8s 的 `kb_search_vector` 触发 permission_request」（`REPORT.md:198`） | 工件显示挂起的是 **`kb_search_two_stage`**（t+48.9→348.9s，300.0s）；`permission_request` 事件在 t=48.9 与 t=371.8；总 wall **602.0s**（报告写"600s 客户端超时"） | 写「第三次确认试验：`kb_search_two_stage` 挂起 300s + permission_request 无人审批，客户端 600s 超时（实测 wall 602.0s，无答案）」 |

其余说明（非异议，供脚注）：
- vector baseline 的 **0.756/0.842** 分数不在 `retmatrix.json`（该 run 未记录 cosine 分）；同值出现在 `benchmark-suite/results/runs/retmodes-20260926T202450Z-47cc948/arm_B-q1.json`（`0.7569` / `0.8428`）。引用该分数时建议标注来源为 09-26 retmodes 工件，或只讲"rank-1"。
- 通道3 的"金标 6/6"（`REPORT.md`）与"12/12"（`_user_materials.md`）是两个层级：**三模式脚本臂 6/6 + baseline 6/6 = 12/12**，同一 run，不矛盾。

---

## 9. 全部数据来源文件清单（可核查）

| 用途 | 绝对路径 |
|---|---|
| 主摘要 | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\retrieval-e2e-20261012\ppt_workspace\references\_user_materials.md` |
| 完整报告 | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\retrieval-e2e-20261012\REPORT.md`（+ `REPORT.html`） |
| 通道1 汇总 | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\retrieval-e2e-20261012\channel1_summary.json` |
| 通道1 逐臂 SSE | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\retrieval-e2e-20261012\c1_A-cm1.json` … `c1_C-cm3.json`（9 个）+ `extra_B-cm1_confirm3.json` |
| 通道2 | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\runs\chatmodes-20261012T061102Z-5f9faac\{arm_*.json, chatmodes.json, CHAT-MODES-COMPARE.md}` |
| 通道3 | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\runs\run-20261012T062847Z-5f9faac\{retmatrix.json, arm_*-q*.json, RETRIEVAL-COMPARE.md}` |
| 通道3 首跑（10/12） | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\runs\run-20261012T062223Z-5f9faac\retmatrix.json` + `review\...\channel3_exp.log` / `channel3_exp_rerun.log` |
| 历史基线（09-26） | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\results\runs\retmodes-20260926T202450Z-47cc948\THREE-MODE-REPORT.md`（§2 本轮值、§3 基线列） |
| KB 目录实测（§8#1） | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\storage\tree-file-system\计算机与人工智能\.knowledge-base.yml`（131 文档）、`…\生命科学与医学\.knowledge-base.yml`（53 文档） |
| 判卷门实现 | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\benchmark-suite\experiments\chat_mode_arms.py` |
| 报告生成脚本（含 65.5KB 表述） | `D:\codes\ClaudeGPT\rag_project\rag-knowledge\review\retrieval-e2e-20261012\gen_report.py` |

## §9 根因最终裁定（2026-10-12 晚，主 agent 会话转录取证）

§8 的存疑全部解决——两套数字都是对的，只是量的是不同层：
- **运行时真实发生的事（决定性证据）**：B×cm1 会话转录 `9631420d-*.jsonl` 中 kb_get_documents(b1199132) 的 tool_result 实际为
  `<persisted-output> Output too large (74.9KB). Full output saved to: …	ool-results\call_083862a61d774ca7985b9caf.txt  Preview (first 2KB)`
  —— 131 文档书架 catalog 74.9KB **超过引擎工具输出预算**，引擎落盘全文、仅透传 **2KB 预览**；模型只见约 2-3 个文档 → 假拒答。
  对应记录值 2,460 字符 = 2KB 预览 + 包裹字段。persisted 文件现存 101,970 字节。
- **在预算内的对照**：53 文档书架 33,089 字符（B×cm2 成功）、75 文档书架 46,685 字符（B×cm3 正常），均未触发 persisted。
- **现场复测**：MCP 同形轻量 catalog 72.0KB（含 file_id 双写字段）。
- **一句话机制**：面向 LLM 的工具返回大小预算是一层隐藏的检索依赖——平台最大书架静默超限。
- 早前"65.5KB 灌入上下文被注意力扫漏"的表述已废弃；REPORT.md 发现 1 与 PLAN.md slide-03 已按本裁定更新。
