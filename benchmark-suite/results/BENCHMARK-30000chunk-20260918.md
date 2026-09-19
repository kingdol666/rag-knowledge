# KBQA Benchmark 测试报告 — 30000 字符分块 · 50 篇真实文献全链路

> 运行标识：2026-09-18 · PIPELINE.md Stage 0→4, 5b, 6, 7a 全部真实执行（Stage 5/7b 复现对照轨不在本轮范围）
> 分块约束：`ingestion.large_doc.max_chars = 30000`（设置页保存，入库存库生效点 = Stage 3c 的 kb_doc_create 大文档拆分层）
> 护栏声明：本报告所有数字与回答均来自本轮真实工具调用输出（90/91/60/61/62/72/75/76 号脚本产物 + Agent 判断件），无编造、无挑轮次。

---

## 1. 语料与入库统计（真实数字）

| 项目 | 数值 | 来源 |
|---|---|---|
| 语料 | 50 篇 arXiv 真实文献（26 领域，8 领域×3、4×2、14×1），manifest 全含 sha256 | `91_fetch_papers.py` / `data/papers/manifest.json` |
| 解析 | 50/50 MinerU 真实解析成功，逐篇 8.3–50.3s，总耗时 2672s | `results/ingest_survey.json` |
| 正文总量 | 3,798,446 字符 | survey 逐篇 chars 求和 |
| 中转库 | Papers-Inbox 整篇暂存 50 篇 → 路由后删除（A5） | `60`/`61` 运行日志 |
| 门类库 | 计算机与人工智能 18 / 自然科学与地球科学 15 / 生命科学与医学 10 / 经济与社会 5 / 工程与能源 2 | `results/ingest_report.json` |
| **30000 档分块结果** | **165 个入库文档 = 9 篇整文档 + 156 个 `(part k of N)`**（对比：2000 档同语料为 2713 个 part） | 磁盘实测 + ingest_report |
| 索引与验证 | batch-index 全量 + **A6-V 逐篇探针 50/50 verified** | `ingest_report.json` |
| 门类图谱 | 5/5 kb_graph_build success=true | `ingest_report.json` |
| 内容标签（A3b） | 165/165 打标 ok，fail=0，48s | `62_apply_tags.py` 输出 |

分类判断件（Stage 3b）：`data/papers/classification.json`，本轮对全新 survey 的 50 篇摘要逐篇复核；两处文件名先验与内容相反的条目维持内容判定（2001.10696 文件名 neuroscience 实为 SNN 算法 → 计算机；1311.6857 文件名 agriculture 实为 Neolithic 人口遗传学 → 生命科学）。

## 2. 十题检索回归（Stage 6，`72_bench10_verify.py`）

通道 = `kb_search_vector` 逐门类合并（QDCVR v2 skill Phase 1 规定工具）。**通过 9/10 = 90%（达标线 ≥90%）**。

| QID | 门类 | doc_hit | 金标词命中 | 结果 |
|---|---|---|---|---|
| BQ01 Transformer 注意力 | 计算机 | ✅ | multi-head, recurrence | PASS |
| BQ02 NISQ | 自然科学 | ✅ | noisy intermediate-scale | PASS |
| BQ03 MultiMedQA/Flan-PaLM | 生命科学 | ✅ | multimedqa | PASS |
| BQ04 Gene Ontology | 生命科学 | ✅ | 3/3 全中 | PASS |
| BQ05 Unified Growth Theory | 经济与社会 | ✅ | unified growth theory | PASS |
| BQ06 降水极值物理因子 | 自然科学 | ✅ | **无** | **FAIL** |
| BQ07 MameLoshnLM | 计算机 | ✅ | yiddish | PASS |
| BQ08 氧变价正极 | 自然科学 | ✅ | oxygen redox, cathode | PASS |
| BQ09 MLP-SLAM | 计算机 | ✅ | dynamic, multilayer perceptron | PASS |
| BQ10 肿瘤控制策略 | 生命科学 | ✅ | immune evasion, chemotherapy | PASS |

**BQ06 逐题归因**：金标文档 top3 命中（doc_hit=True），但 30000 档分块窗口内 top3 chunk 文本未包含字面词组 "precipitation efficiency"（答案语句位于摘要续段，被 chunk 边界截断）。这是**分块窗口效应**，非检索错库；Stage 7a 的 Phase 2 兜底（定向再检索 + 续读）当场解决，见下节。

## 3. Track A — QDCVR v2 检索 skill 十题回答（Stage 7a）

执行模型：Phase 0 查询改写（REWRITES 表留痕）→ Phase 1 `kb_search_vector` 五门类合并 + 文档去重 + `kb_doc_read` 头窗门控（0-8 评分：主题 0-3/场景 0-3/证据 0-2；≥6 快速退出）→ 门控 <6 触发 Phase 2 图书管理员定向兜底 → 五段式回答。

| QID | Phase1 向量 top-1 分数 | 门控 | 决策 | Phase 2 |
|---|---|---|---|---|
| BQ01 | 0.713 | 7 | 快速退出 | — |
| BQ02 | 0.709 | 7 | 快速退出 | — |
| BQ03 | 0.732 | 7 | 快速退出 | — |
| BQ04 | 0.764 | 8 | 快速退出 | — |
| BQ05 | 0.806 | 7 | 快速退出（并排除 0.537 异库近似干扰项） | — |
| BQ06 | 0.783 | 5→7 | **Phase 2 兜底后解决** | ✅ 续读摘要全文 |
| BQ07 | 0.815 | 8 | 快速退出 | — |
| BQ08 | 0.707 | 6 | 快速退出（量化数字留盲区） | — |
| BQ09 | 0.720 | 7 | 快速退出 | — |
| BQ10 | 0.780 | 5→6 | **Phase 2 兜底后解决** | ✅ 续读 §3.1 平衡态 |

- 十题 top-1 **全部命中金标文档**；向量检索时延 ~1.5s/题，文档读取 ~0.8s/题（`skill_track_evidence.json` timings）。
- 门控分布：8 分×2、7 分×6、6 分×2；**Phase 2 兜底 2/10**（BQ06、BQ10，均为答案语句落在头窗/分块窗口之外的情形——兜底机制按设计生效）。
- 十题五段式回答全文见 `results/skill_track_answers.json`（Search Paths / Answer / Sources / Confidence / Blind Spots）；回答仅引用实际读到的正文，未读到的（如 BQ03 的 67.6%、BQ08 的 mAh/g 数字、BQ10 的最优控制结论）一律如实写入 Blind Spots。

## 4. 与上一轮（10000 档，2026-09-17 存档）对照

| 维度 | 上一轮（10000 档） | 本轮（30000 档） |
|---|---|---|
| 入库文档数 | （归档于 `results/archive-20260917-10000chunk/`） | 165（9 整篇 + 156 part） |
| bench10 | 10/10 | 9/10（BQ06 窗口效应，Phase 2 可解） |
| Track A top-1 金标命中 | 10/10 | 10/10 |
| Phase 2 兜底 | BQ06、BQ10 | BQ06、BQ10（同一分块窗口根因） |

上一轮完整工件已归档，本轮未覆盖（results 只增不改；脚本级 JSON 按 PIPELINE 约定由新一轮刷新，git 可追溯）。

## 5. 运行事故与处置（诚实披露）

1. **2000 档→30000 档需求变更**：首次 Stage 3c（2000 档）已完成路由并删除 Inbox 后叫停，门类库随之删除重建。Inbox 时序事故导致 Stage 3a 重跑一次（50 篇重新真实解析，2672s）——两轮解析均为真实执行，无缓存复用。
2. **save-parsed-files 拆分改为显式 opt-in**：本轮实测发现解析保存端点的自动拆分会破坏"中转库整篇暂存→内容分类路由→终库分块入库"的流水线模式（Inbox 曾被拆成 800 part，且 30s MCP 默认超时不够）。已改为仅当请求显式携带 `split: true` 时拆分（web 解析直存 UI 传入；MCP/管线暂存默认整篇），并同步修正 `web/composables/usePDFParser.ts`。该修正属于产品代码修复，随本轮 bench 一起验证。
3. **MCP_HTTP_TIMEOUT=300**：大文档保存/索引调用超过 kb-mcp 客户端默认 30s，按环境变量放宽（运行参数，非代码改动）。
4. **证据窗口截断**：所有回答基于 3000 字符头窗 + chunk 片段；窗口外的精确数字一律进入 Blind Spots，未读不引。
5. **Track B/C 未运行**：本轮范围不含复现项目建库（Stage 5）与裸 Agent/dense 对照轨（Stage 7b），故 `74/78` 三轨对照报告不适用；Track A 的技能流程回归已按 Stage 6+7a 完整执行。

## 6. 结论

- **PIPELINE 真实执行闭环达成**：Stage 0-4 + 5b + 6 + 7a 全部真实跑通，入库 A6-V 50/50、标签 165/165、检索回归 90% 达标、skill 十题回答 10/10 落盘且金标命中 10/10。
- **30000 字符分块语义验证**：同一 380 万字符语料在 30000 档下收敛为 165 个入库文档（2000 档为 2713），拆分数量随阈值收敛的设计目标成立；大文档拆分层（设置页 max_chars → kb_doc_create 拆分 → part 独立索引/检索/打标）端到端工作正常。
- **改进方向**：①BQ06 类"答案语句跨 chunk 边界"场景可考虑头窗预算随 chunk 档位放大（30000 档下 3000 字符头窗覆盖率下降）；②Phase 2 兜底是分块窗口效应的有效解，建议在检索 skill 文档中把"门控 5 必兜底"的示例补充 30000 档实测；③`ingestion.large_doc.max_chars` 当前保持 30000（本轮作业配置），如需回到日常默认可在设置页调整。

---

# 三轨对照（Stage 5 / 5b / 7b / 8 补充轮）— 复现算法系统 vs 裸 Agent vs 本知识库系统

> 应用户要求补齐对比轨：Stage 5 真实建复现算法库（`70_repro_ingest.py` exit=0：导出 50 篇 md → Corpus-Chunks800（800 字符固定分块）/ Corpus-Struct（1385 chunks）/ Corpus-Paras（10219 chunks）三库）→ Stage 5b 重启后端 → dense 冒烟 top_score=0.77 → `77_tracks_bc.py` 逐题独立子会话（**每题各 spawn 一个独立裸 Agent 子进程 / 一次 dense 检索+独立 omp oneshot**，逐题依次执行，无一并生成）→ `78_replication_report.py` 生成三轨全文对照 `results/skill_threeway_replication.md`（41 KB，三轨回答逐题 verbatim 完整记录）。

## 运行形态与总量

| 维度 | Track A · 本知识库系统（QDCVR v2 skill） | Track B · 裸 Agent | Track C · baseline RAG（dense 复刻） |
|---|---|---|---|
| 检索源 | 平台 5 门类库（30000 档 165 part，向量+BM25+图谱） | 无索引，直接在 50 篇 md 目录用文件工具自搜 | Corpus-Chunks800（固定 800 字符分块）dense top→4000 字符证据包 |
| 回答者 | Archival（本会话 Agent，五段式） | 每题独立 omp 子进程（JSON 答案） | 每题独立 omp oneshot（统一 prompt） |
| 时延 | 检索 ~1.5s + 读 ~0.8s/题（回答由会话 Agent 生成，未计时入轨） | **均值 78.8s**（35.5–165.3s） | **均值 12.2s**（5.8–28.6s） |
| 金标命中 | 10/10（检索层 doc_hit） | 10/10（files_used 全部指向金标文档；BQ08 额外引用了第二篇电池论文） | 回答内容与金标一致，但 evidence_docs 字段全为空（复刻系统 chunks 未携带 doc_path 元数据，无法程序化核验——如实披露） |

## 逐题对照结论（完整原文见 `skill_threeway_replication.md`）

| QID | A · KB 系统（skill） | B · 裸 Agent | C · baseline RAG | 谁更准/证据链更强 |
|---|---|---|---|---|
| BQ01 | multi-head 三用法 + 替代原因，§3.2.3/§7 verbatim；公式留盲区 | **最细**：scaled dot-product 机制、compatibility/weighted-sum 全给出 | **弃答**（证据包只含 parsing 段，无注意力内容） | B 内容最全；A 证据链最规范；C 检索覆盖失败 |
| BQ02 | NISQ 定义 + no-QEC verbatim | Preskill 造词 + 50–几百 qubits | 同样给出 50–几百 qubits + imperfect control | 三轨同准；B/C 细节略多 |
| BQ03 | 用途 + 97.8%/76.3% verbatim；67.6% 留盲区 | **最完整**：六数据集 + 第七 HealthSearchQA(3375 条) | 数据集组合 + HealthSearchQA 第七个（Flan-PaLM 具体分被截断） | B 最全；A 稳准；C 概括正确 |
| BQ04 | 三本体 verbatim（8/8） | MF/BP/CC + 标识符空间 | **弃答**（证据包未含三本体名） | A/B 对；C 检索覆盖失败 |
| BQ05 | 矛盾论点（标题级，保守） | Maddison 数据、双曲增长 vs 三阶段（最具体） | "无停滞、无 Malthusian 陷阱"（具体） | B 机制最细；C 亦准；A 偏保守 |
| BQ06 | 热力贡献 primary（Phase 2 兜底后 verbatim） | 热力学水汽响应 primary（机制最完整） | 热力学贡献 primary + "若动力学/降水效率可忽略"条件句 | 三轨同准；C 的条件表述最严谨；A 有 Phase 2 过程留痕 |
| BQ07 | 8B verbatim（最高分 0.815） | Llama 3.1 续训 + Oytser 语料 + 基准（最完整） | 8B + Llama 续训 | 三轨全对；B 最细 |
| BQ08 | 机制框架 + 材料依赖 | O2− 供电子机制 + 更多 Li+/Na+ 脱嵌（最具体） | "orphan" 电子态机制描述 | B 最细；A 稳；C 亦准 |
| BQ09 | 动态退化 + MLP 过滤 + KITTI | ORB-SLAM2/3 假设失效、行人车辆、MLP 判别器（最具体） | 动态对象退化描述 | B 最完整；A/C 正确但浅 |
| BQ10 | 模型框架 + 四平衡态（策略结论留盲区） | 联合免疫化疗 + 参数区域扩张 | **表型/机制特异策略**：checkpoint 抑制剂 vs 化疗分而论之 | C 最贴题；A 最保守；B 次之 |

## 证据链充分性与准确性总评

1. **证据链可追溯性：Track A 最强**。五段式回答自带检索路径（query 改写→各库分数→part 路径→verbatim 引文）、置信分级与 Blind Spots；每个论断可回溯到 `skill_track_evidence.json` 的具体 chunk 与分数。B 只有 `files_used` 文件级溯源（无段落级引用）；C 原始记录中 `evidence_docs` 全为空（复刻系统 chunk 未带 doc_path 元数据），证据链只能靠回答文本反推——**这是复刻系统记录面的真实缺陷，如实指出**。
2. **事实准确性**：三轨在 BQ02/03/06/07/08/09 上结论一致（相互印证，无幻觉冲突）。差异集中在两类：**B（裸 Agent）细节最丰富**——它按题读全文（每题 35–165s 的代价换来最完整的机制描述）；**A 稳定正确但最保守**——凡头窗未读到的数字一律写入 Blind Spots（BQ03 的 67.6%、BQ08 的 mAh/g、BQ10 的最优控制结论），零编造。
3. **检索覆盖的直接后果**：C 出现 **2/10 诚实弃答**（BQ01、BQ04）——4000 字符证据包未检到答案段（800 字符固定分块切散了答案句），弃答行为本身诚实，但暴露固定分块 + 纯 dense 的召回上限。A 的 Phase 2 兜底（2/10 触发、2/10 解决）与 B 的全文自搜在本轮均无漏答。
4. **综合判断**：**证据链充分性 A > B > C；单题答案细节丰富度 B ≥ A > C；稳定性（不弃答、可追溯）A > C ≥ B（B 时延与答案长度方差最大）**。本知识库系统（Track A）是唯一同时做到"零弃答 + 段落级 verbatim 引用 + 诚实盲区标注 + 秒级检索"的轨道；baseline RAG 的 2 次弃答与不可追溯证据包说明固定 800 字符分块 + 4000 字符证据包在该语料上召回不足。
5. **完整记录承诺**：三轨每题的 Agent 最终输出全文（A 五段式 / B raw JSON 答案 + 原始模型输出 2400 字符 / C 答案 + 原始输出）均已 verbatim 落盘于 `results/skill_threeway_replication.md` 与 `results/track_bc.json`，未做任何评价性删改。
