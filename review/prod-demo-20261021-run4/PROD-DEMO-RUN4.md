# 生产就绪实机演示报告 Run 4（prod demo, 2026-10-21, ralph run 4）

> 任务：系统设计与功能完整审视 → 实验结果可靠性判定（论文论据边界）→ 全功能真实实机演示
> （管理作业 + 三种检索方式 + 图书管理员逐级重点测试，逐题给出问题与回复并判定）
> → 修复 rename 已知缺陷 → 生产就绪结论。
> 本轮相对 Run 3 的定位：**全部证据当日全新取证**，并把 Run 3 遗留的"投产前唯一必改项"
> （rename 溯源缺陷）修复落地，纠正了 Run 3 的一处测量伪影。
> 工件目录：`review/prod-demo-20261021-run4/`。

## 1. 系统设计总览（US-301，活体取证）

**拓扑**：三服务 + MCP 层，单一 `config.yml`——
Browser → Nuxt3 Web(6789, 代理 + KB 存储层/文档路由) → FastAPI Backend(8771, 解析调度/向量/图/经验/SOUL) → MinerU(按需拉起)；kb-mcp(stdio 供 agent harness + HTTP :8000) 暴露 95 工具。
当日进程核实：`node nuxt.mjs dev --port 6789` · `python main.py`(8771) · `python server.py --http`(8000)。

**工具面（当日 tools/list 实测）**：**95 个 = kb_* 42 + experience 26 + soul 20 + 项目/文件系统 7**——与论文披露口径（95 工具）完全一致；对账过 Run 1 验收记录。

**库存（当日 kb_list）**：21 库 / 433 文档。五大门类生产库：计算机与人工智能 131 · 自然科学与地球科学 75 · 生命科学与医学 53 · 工程与能源 39 · 经济与社会 24（=322，与 paper_report 闸门口径一致）；另有 aw-industrial 53、Novel 28 及演示/测试库。

**五层存储**：L1 Markdown 文件（storage/tree-file-system）· L2 `.tree-fs.json` 全局树 · L3 `.knowledge-base.yml` 库注册表 · L4 ChromaDB 向量（BGE-M3，按库 collection `kb_<uuid>`，父库递归解析）· L5 Neo4j 文档图。三源一致性（L1↔L2↔L3）是组织层核心不变量。

**管理功能面（12 组，全部当日活体验证）**：KB 生命周期（建/改/删，支持子库嵌套）· 文档 CRUD + **改名（本轮起带内联索引卫生）** · 跨库移动（三步卫生鼻祖）· 标签（打标/注册表/孤儿 dry-run）· 去重（只报不删）· 索引维护（单篇/批量/force 重索引 + 后验证 `_verify:ok`）· 知识图谱 7 查询 · 检索原语（关键词/向量/两阶段/统计/Laya 内容裁决 fail-closed）· 经验库 26 工具 · MinerU 采集链 · SOUL 20 工具。

**检索流程分层（论文 C1–C3 机制/检验分离）**：gather/judge/read/传输预算（28K 目录预算门 + 分组视图）为**服务端强制**；rewrite/merge/弃答为 workflow 提示层。检索层返回的 doc_path 统一正斜杠（存储层为反斜杠，读取时归一化——本轮实证确认）。

## 2. 实验结果可靠性判定与论文论据边界（US-302）

**当日复验（全部本机新证据）**：
- `TEST-RESULTS/verify.py` → **PASS**：论文每个 grounded/strict/cited/chunk/时延/成本主张都从冻结 run `run-20261013T094350Z-5f9faac` 落盘工件复算命中；30 格成本求和 17.2454 = manifest，分毫不差。
- 冻结 manifest `sha256sum -c` → 注解集/判分器/题集 OK；n8a/n8b/n8c_eval.tex 3 处漂移为**既知遗留且未扩大**（freeze 10-17 20:53 < commit a8273b5 23:14 < worktree 10-18）——投稿前作者须重冻结或回退，属论文操作，不动摇实验数据。
- `paper_report.json` 19/19 verification checks 全 PASS。
- **检索回归探针（新故事）**：当日全新复跑 `158_a_retrieval_regression.py` 得 **13/15**——两发金标（2604.01385 免疫学、2207.08146 电网）跌出 top-40。取证结论（`regression_drift_diagnosis.json`）：chunk 没丢、路径形式无恙（存储统一反斜杠、检索层归一化返回），**是存量 embedding 陈旧导致排序衰减**（Chroma 在 10-14~10-20 审计/测试密集窗口有写入）。用系统自维护命令 `kb_reindex(force=true)` 修复两库（53 docs/55s、39 docs/40s，`_verify:ok`）后复跑 **15/15 全过**，两金标双双回到 rank=1。⇠ 同时**纠正 Run 3 的一处取证瑕疵**：Run 3 报告的"检索回归探针 15/15 当日复验"按本轮 15:35 的活体状态不可能为真，应定性为"读取了 10-13 的落盘工件"而非当日新跑。

**可作为论文实验部分论据的（强，全部有冻结工件+verify.py 再生路径）**：两个 30 单元三臂网格（gold 60/60，strict/alias/cited 逐格可复算）、E4 检索矩阵与派生行、E6 判定器角色诊断（0.94→0.44→0.94）、E7 稳定性 27/27、E5b 部署臂 + 18 臂诚实性、E1/E2 管理层测量、Table 1 的"回归探针 15/15"行（本日起有可执行再生脚本且当日真实通过）。
**只能作补充材料/工程证据的（弱）**：本轮实机演示（n=1 一次性库）、dev_smoke、管线自检——它们证明"平台功能合约真实可用"，不改变统计结论。
**不可写入的**：单次演示的绝对时延/成本（无重复运行；本轮九宫格 $2.86 只作运维参考）。
**注意**：论文正文如引用"15/15"应保持"冻结 run + 可再生脚本"双口径；n8a/b/c 漂移项重冻结前不得声称"工作区与冻结一致"。

## 3. rename→doc_path 缺陷：根因、修复、与对 Run 3 的纠正（US-306）

**根因（代码行级）**：`web/server/api/kb/documents/update.patch.ts` 改名只调 `treeService.updateFile`（注册表+磁盘），**没有任何向量/图卫生**；对照组 `move.post.ts` 自 2026-09-24 起就有完整三步卫生（删旧向量→删旧图节点→新路径重索引，`index_hygiene` 回执）。

**修复**：update.patch.ts 镜像 move 的三步卫生，仅在路径实际变化时触发（纯描述/元数据更新零开销），best-effort 不致命、回执上报。nuxt dev 热重载即时生效，实机走通即语法/类型实证。

**实机双取证**（`rename_probe_before2.json` / `rename_probe_after.json`，一次性库）：
- 修复前：rename 后检索新标签命中 **0**、旧标签 **1**（旧路径已不可解析，溯源失真）；
- 修复后：rename 响应带完整 `index_hygiene` 回执（vectors cleaned=1 + graph 删除 + 重索引），检索**新标签 1 / 旧标签 0**，force reindex 后保持正确，desc-only 更新无副作用，清理零残留。

**对 Run 3 的纠正（重要）**：Run 3 结论"force re-index 也不修向量 doc_path 标签"是**测量伪影**——`vector_service.search` 有 30s TTL 结果缓存，Run 3 在 reindex 后 30 秒内用**相同查询串**复测，读到缓存旧行。cache-proof 复测（每次换查询串）证明 force reindex 本来就能修复。真实缺陷因此收窄为：**rename 后到下次 force reindex 之间，检索溯源指向不可解析旧路径**（窗口内失真）。本轮修复使窗口归零。
**伴生发现（未修，记录在案）**：向量检索 30s 结果缓存不被索引变更失效——rename/move/reindex 后最长 30s 内同查询可能返回旧行；自愈，无一致性风险，建议列入运维手册。

## 4. 知识库管理作业全量实机测试（US-303）

`management_full_test.py`（run 4 版）：一次性库 **28/28 步 PASS**（`mgmt_result.json`）。
覆盖：KB 建库/改描述、fs 上传+children、文档创建/**改名（新断言：内联卫生回执 + 无需手动 reindex 即新标签命中、旧标签归零 + reindex 后稳定）**、批量索引/批量删除、标签注册表+孤儿 dry-run、**图家族 7 项**（建图/统计/库概览/文档相关/中心度/跨库桥/路径）、`kb_search_stats`、经验五连（create/list/read/summary/check_stale/delete）、`soul_list` 只读面、清理零残留。
测试脚本自身一次过滤器误报（把同库另一合法文档算作"旧路径"）已修正后重跑全绿——记录在案以保持证据诚实。

**采集链闭环**（`parse_result.json` 全 PASS）：真实 26KB PDF（wind-energy.pdf）→ `parse_doc`（MinerU 按需拉起）→ task done → `kb_doc_save_parsed`（task_id 模式，批量形状 files[]）→ 索引 → 检索命中 → 全文读取 → 清理零残留。

## 5. 三种检索方式真机对照（US-304）

`benchmark-suite/experiments/chat_mode_arms.py`，生产语料，`POST /api/claude/chat` 非流式真跑。
Run: `chatmodes-20261021T075009Z-run4`。**9/9 全部 HTTP 200、0 执行错误，总成本 $2.86；闸门 8/9**（唯一 ❌ 为拒答启发式误报，甄别见下）。

题面：
- **cm1（found）**：How does InstructDS generate high-quality query-based dialogue summaries?（InstructDS 对话摘要的查询式指令数据合成）
- **cm2（found）**：基于电子健康记录（EHR）数据用机器学习预测中风风险：关键风险因素及影响分析
- **cm3（refusal/域外虚构）**：Herbert-Moulton 对撞机基准如何量化粒子物理实验的探测器漂移？

| 模式 | 题 | 预期 | 耗时/turns | 闸门 | 实质判定 |
|---|---|---|---|:--:|---|
| A 钉库向量 | cm1 | found | 182.9s / 4 | ✅ | 金标 instructds 命中；"摘要锚定三步合成流水线"开头即正确 |
| A | cm2 | found | 208.2s / 6 | ✅ | 金标 stroke 命中；唯一直接对口文献 1904.11280 |
| A | cm3 | refusal | 217.7s / 7 | ✅ | 如实拒答 |
| B 全库逐级 | cm1 | found | 335.1s / 11 | ✅ | 金标命中（阶梯最深，11 turns） |
| B | cm2 | found | 242.5s / 6 | ✅ | 金标命中 |
| B | cm3 | refusal | 172.0s / 8 | ✅ | 如实拒答 |
| C 混合 | cm1 | found | **104.0s** / 4 | ✅ | 三车道最快；金标命中 |
| C | cm2 | found | 222.4s / 9 | ❌→实质 PASS | **闸门误报**：答案命中金标 stroke、给出 1904.11280 与 75.02/74.53/74.31% 逐字引用，仅因句中"**无法**压缩特征空间"触发"无法"关键词。与 Run 3 的 A×cm1 同类（闸门粒度缺陷，非系统错误；单元格只存 answer_head 无法离线复核，Run 1 验收已记录为测试工件粒度缺口） |
| C | cm3 | refusal | 100.5s / 6 | ✅ | 教科书式拒答：显式"不存在任何内容"+列出三次检索及命中表+检索范围 |

**车道画像（run 4）**：C 在 found 题最快（cm1 104s）、拒答题也快（cm3 100.5s）；A 均衡；B 最深（cm1 11 turns 走全阶梯）。三车道对同一对金标论文（2310.10981 / 1904.11280）给出相互一致的事实数字，交叉印证检索可靠性。

## 6. 图书管理员逐级检索重点测试（US-305）——逐题问题与回复

`librarian_probe.py`：`kbEnhanced=true, kbIds=[]`（注入完整逐级阶梯指令），SSE 流捕获**完整工具轨迹**（`librarian_results.json`）。**3/3 PASS**（LIB3 初判 FAIL 系探针拒绝词表漏检 "no content/no recipe" 一族，已按 Run 3 同款流程离线改判并把词表补进脚本）。

---

**题 1 · LIB1-lookup（查找型）**：
> "How does InstructDS generate high-quality query-based dialogue summaries? (InstructDS dialogue summarization, query-based instruction tuning data synthesis)"

轨迹：`kb_list`×1 → `kb_get_documents`×4（描述层）→ `kb_laya_judge`×1（未读正文即裁出幸存段）｜192.4s / 7 turns / $0.32。
回复要点（1469 字，判定 **PASS-gold**）：InstructDS 用 Flan-T5-XL 从对话-摘要对反向合成 QDS 三元组——摘要锚定生成 5 候选查询 → 文本过滤（剔 ~45%）+ BERTScore>0.65 语义去重（再剔 ~50%）→ 查询+完整摘要生成；质量数字（可答 94% vs 76%、唯一且正确 75% vs 45%、每对 1.3 条）与出处（arXiv 2310.10981，计算机与人工智能库，P0 强）齐备。

**题 2 · LIB2-enumerative（枚举型）**：
> "Which papers in this knowledge base study precipitation extremes under climate change? List each paper and its main finding."

轨迹：`kb_list`×1 → `kb_get_documents`×6 → `kb_laya_judge`×1 → `kb_doc_read`×4（完整四级阶梯）｜224.4s / 13 turns / $0.46。
回复要点（4251 字，判定 **PASS-gold**）：精确枚举——库内**恰好两篇**直接对口（O'Gorman《Precipitation extremes under climate change》arXiv:1503.07557，P0 强，含 HadEX2 回归引文；Rampal 等 GAN 降尺度研究）+ **1 篇明确排除在外的邻接论文**（MJO 驱动，"not climate change"）——枚举边界意识正确。

**题 3 · LIB3-absent（域外验谎）**：
> "What is the traditional home recipe for Sichuan pickled vegetables (泡菜), including salt ratios and fermentation days?"

轨迹：`kb_list`×1 → `kb_get_documents`×5（按预算规则扫演示架）→ `kb_laya_judge`×1（两份不透明文档裁决，survivor=0，**未读任何正文**）｜139.3s / 8 turns / $0.17。
回复判定 **PASS-诚实拒答**，答案原文关键句："**The knowledge base contains no content on Sichuan pickled vegetables (泡菜) — no recipe, salt ratio, or fermentation-days information exists in any of the 21 shelves.**" → 逐架列出 21 库扫描范围 → 裁决证据链（candidate 2 → survivor 0）→ **盲点声明**（"verified absence… not proof that no such text exists on disk"）→ **拒用模型记忆补写**（"I am deliberately not answering from model memory"）。零编造。

**车道纪律**：三题轨迹均无 `kb_search_vector`/`kb_search` 等越车道工具——纯 catalog→描述→judge(→read) 阶梯；拒答路径遵守"目录层+描述层即停"预算规则。

## 7. 生产就绪结论（US-307）

**判定：在"单机自托管、单团队"设计边界内，系统具备投入真实生产运行的功能完整性与行为可靠性——且本轮起，Run 3 遗留的"投产前唯一必改项"（rename 溯源失真）已修复并实机验证，该项不再是拦路石。** 企业级（多机/多租户）缺口维持 Run 3 定性。

Run 4 当日证据链（全部全新取证）：
- 管理作业 **28/28 PASS** + 采集链闭环 PASS（一次性库，清理零残留）。
- 三车道九宫格 **9/9 HTTP 200 零错误**，闸门 8/9（唯一失败=闸门启发式误报，实质 PASS）。
- 图书管理员逐级车道 **3/3 PASS**（含完整四级阶梯枚举与契约式拒答）。
- 实验面：verify.py PASS · 19/19 管线闸门 · 冻结 manifest 漂移未扩大 · 回归探针 13/15→**修复→15/15**。
- 回归：`scripts/dev_smoke.py` **21/21 PASS** · `scripts/validate_skills.cjs` **PASS**（reviewer 独立复跑亦通过）。
- 缺陷修复：rename 内联索引卫生上线并双探针取证；Run 3 的 reindex 伪影已纠正。

**遗留事项（按优先级）**：
1. **论文操作项**：n8a/n8b/n8c_eval.tex 冻结漂移——投稿前重冻结或回退（作者决策，不动数据）。
2. **运维建议**：把 `158_a_retrieval_regression.py` 列为周期健康检查（exit code 即 CI 判据）；本轮实证 embedding 陈旧类漂移可用 `kb_reindex(force=true)` 一键治愈。
3. **测试工件粒度**：拒答启发式闸门存在"无法/不能"字面误报（本轮 C×cm2、Run 3 A×cm1）——答案单元格若存全文可离线甄别；已两次实锤，建议排期。
4. 向量检索 30s 结果缓存不被索引变更失效（自愈，运维手册记录即可）。
5. 沿袭 Run 3 的边界清单：秒级后台索引竞态（最终一致）、`kb_task_status` 完成态短暂滞后、经验库审批/衰减/冥想未规模化验证、SOUL 域只读验证、并发 ~4-5 RPS、无 HA/备份/多租户/审计。

**与 Run 3 报告的差异清单**（供引用者选择口径）：
| 项 | Run 3 | Run 4（本轮，以此为准） |
|---|---|---|
| rename 缺陷 | "force re-index 也不修标签，投产前唯一必改项" | 已修复（update.patch.ts 内联卫生）；Run 3 的"reindex 不修标签"系 30s 缓存测量伪影 |
| 回归探针 | "15/15 当日复验"（实为读 10-13 工件） | 当日真跑 13/15 → 诊断（embedding 陈旧）→ force reindex 修复 → 15/15 |
| 管理测试 | 29/29（缺陷确认型断言） | 28/28（修复验证型断言）+ 采集链闭环 |
| 三车道 | 8/9 闸门（A×cm1 误报） | 8/9 闸门（C×cm2 误报，同族） |
| 图书管理员 | 3/3（词表漏检 NOT_FOUND 族） | 3/3（词表漏检 no-content 族，词表已补三轮） |
