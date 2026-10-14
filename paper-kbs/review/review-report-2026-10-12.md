# KBS 投稿评审报告 — QDCVR 系统论文（2026-10-12）

评审对象：`paper-kbs/tex/main2.tex`（elsarticle `[preprint,12pt]`），四个构建：
preprint 80 页 / journal 双栏 37 页 / review 双倍行距 115 页 / 扁平投稿包 80 页；
补充材料 30 页。构建状态：0 error、0 undefined、1 overfull（1.09 pt）。

评审形式：**六席评审面板**（native delegated subagent，全部只读），席位为
Editor-in-Chief（KBS 形式/退稿筛查）、Theory & Novelty（理论与定位）、Methodology
（实验设计）、Results-verification（数字核对）、Presentation & Figures（解释与图表）、
Devil's Advocate（致命缺陷）。每条结论均由主 Agent 独立复核（见
`paper-kbs/review/panel_ledger.md` 的仲裁表），未采信任何未经复核的指控。

**取证边界（重要）**：本会话脚本层不可用——`pwsh` 以 Windows job-runner
`0xC0000142` 失败、`grep` 报 ripgrep provider failure、`glob` 同样不可用。因此本次评审
**未编译、未重跑任何实验、未重新测量页面/字数、未抓取网页**；所有条目均为
`[LLM]` 阅读型发现（有引文与 file:line 锚点），不是 `[Script]` 脚本型发现。
唯一例外是主 Agent 在本会话早前用在线 MCP `tools/list` 实测到 **95 个工具**。

---

## 1. 总判定（gate）

**不通过（DESK-REJECT-RISK-HIGH）**：以当前版本直接投 KBS，退稿/送审前退回风险高。
三条硬理由，按严重度排序：

1. **结论的核心主张被自己的表推翻。** `n11_conclusion.tex:18-21` 写
   "Staged, multi-channel retrieval with content adjudication reaches documents that
   one-shot vector top-$k$ misses"，而 `n8b_eval.tex:85-91` 的九配置表里
   BM25 1.00 / RRF 1.00 / Dense 0.94 / QDCVR-Hybrid（judged）0.44，
   且 `n8b_eval.tex:259-260` 自己写着 "Nothing here is a retrieval advance"。
   摘要、RQ3 行、结论三处同句，无法作为单段笔误解释。
2. **两个被设计章论证的机制在配对消融中都是零效应。** 内容门：10 题中 9 题两臂收到
   完全相同的文档（`n8c_eval.tex:379-380`，sign test p = 1.0）；内容路由分区：分区
   与全局检索结果完全相同（`n8c_eval.tex:411-413`）。唯一被真正隔离出来的正结果是
   **filter vs re-ranker 的角色不对称**（0.94 vs 0.44），但它是 post-hoc、n = 16。
3. **形式层面三条可见硬伤**：111 页双倍行距（KBS Guide "preferably no more than 20
   double line spaced manuscript pages, including tables and figures"）；标题页仍是
   `main2.tex:49-54` 的 "Author Name"/`author@example.com`、CRediT "Author 1/2"、
   `refs.bib:185` 的 `%% AUTHOR ACTION` 注释；21 个 table 环境。

**可救之处（同样重要）**：本稿的诚实性与可追溯性远高于同类投稿——负结果写进摘要、
21/100 缺口主动披露未归因、每个数字带 artifact 路径、补充材料逐项列出"零测试证据"的
能力。评审席一致认为存在一条**窄化重定位**的路径：把论文从"检索进步"改写为
"判定角色的分解 + 可审计的失败关闭溯源"，并补齐一项作者独立评测。

---

## 2. 跨席一致问题（consensus，全部席位独立命中）

| # | 问题 | 位置 | 修法 |
|---|---|---|---|
| C1 | 结论/RQ3 宣称分阶段检索的可达性优势 | `n11_conclusion.tex:18-21`；`tab:ataglance` RQ3 行；`main2.tex:69-77` | 重写为数据支持的表述（判定角色 + filter/reranker 不对称 + fail-closed provenance），删除 "reaches documents that one-shot vector top-$k$ misses" |
| C2 | 门的"最佳角色"与无门不可区分：filter 0.94 = Fusion-only 0.94 = Dense 0.94；191/191 候选全部通过 0.5（最低 0.589）；三个阈值在本语料从未触发 | `n8b_eval.tex:193-196`；`n6_retrieval.tex:83-92` | 要么构造阈值真正生效的候选池（跨库负例、低边际），要么把门改写为 provenance-only 并删去 filter 卖点 |
| C3 | 门消融**设计上零功效**：gold 在三臂都排第 1，两臂文档相同；segment 臂还被给了不同证据预算（QK09：2,806 vs 4,000 字符） | `n8c_eval.tex:376-380`；`exp11_gate_ablation.json` | 重建消融：gold 放在它实际得到的融合排名、三臂证据字节完全一致、segment 作为独立预算条件 |
| C4 | 第二语料同时移动了领域、语言、规模、混淆密度四个变量，且与第一语料共享管线与领域族，所以"混淆密度"机制未被识别 | `n8c_eval.tex:173-177`；`supplementary-material.md:1088-1091` | 增补**单变量**第三语料（同域同语、每簇只留一篇），或把机制降级为"关联" |
| C5 | 唯一的显著性结果 p = 0.008 是 post-hoc、从九配置中挑出、无多重比较校正；guardrail 在正文 250 行之后，摘要与表 1 不带它 | `n8b_eval.tex:121-124`、`:170-174` | 摘要与表 1 处即标注 descriptive；预注册一次新问题集上的复现 |
| C6 | 所有答案质量数字来自单一本地 grader，无人工裁决、无一致性统计；同时 4/8 零分（QK02/04/05/08）与 12/12 引用金标并存而未并置解释 | `supplementary-material.md:1093-1102`；`n8c_eval.tex:392-395` | 报告 grader prompt 与 rubric；做 50–100 项盲评并给一致性；明确两个数字各测什么 |
| C7 | 基准循环性：问题由作者撰写、gold 是"唯一文件名片段"，且 arXiv 语料 322/322 带 `{domain}__{arxiv_id}__{slug}` 前缀（`prefix_leak_fraction` 1.0） | `n8a_eval.tex:11`；`n8c_eval.tex:418-420` | 掩蔽前缀与 slug 重跑全部检索路径；引入作者独立问题集（公开语料 + qrels 最佳） |
| C8 | 采集漏斗无逐论文账：100 提交 / 91 入状态文件 / 79 可检索，21 篇未归因，且 9 篇"既通过检查又未记录" | `n10_threats.tex:43-47`；`n8a_eval.tex:44-50` | 仪器化 per-paper parse status + 错误文本并重跑；在那之前把 21% 从摘要降到 limitations |
| C9 | 投稿元数据占位 + 长度 ≈5× 偏好值（111 页双倍行距、21 表、30 页补充材料） | `main2.tex:4,49-54`；`n_back.tex:32-34` | 填真实作者/单位/ORCID/CRediT/funding；把诊断类表格移入补充材料，正文压到 ~13k 词 |
| C10 | 图表：Fig. 1 caption 描述"左/右"布局而图是四层堆叠；图内工具层写 **eight** groups 而正文写 twelve；三源一致性框**没有向量库**（而论文自己举的反例正是向量库 18 vs 9 chunks）；Fig. 3 caption 承载了画在 Fig. 6(b) 的 filter 结论；Fig. 6 caption 把 (b) 说成 "paraphrase collapse" 而画的是三判定角色；9 图中 5 张是拼图（KBS 明确不建议）；Fig. 9 是 2×2、0.80\textheight | `n3_overview.tex:114-121`；`figures.py fig_architecture()`；`n5_organization.tex:63-71`；`n8b_eval.tex:267-291`；`n8c_eval.tex:252-267` | 逐条见 §4 的 P0 清单 |
| C11 | 两条参考文献著录错误 + 一条自引不可核验 | `refs.bib:255-260`（`sun-urara` 标题被写成 "…Investigating Relevance Reasoning with LLM-as-a-Judge"）、`refs.bib:248-253`（`rankgpt` 标题 "Are Large Language Models Good at Listwise Rerankers?" 语法错误、作者名单不符）、`refs.bib:186-192`（CIKM demo `note = {To appear}` 与正文 "was published" 矛盾且作者占位） | 按 ACL Anthology / 出版方更正 |
| C12 | 经验子系统被列为贡献（C3）但审批/衰退/冥想路径从未运行，草稿池查询为空 | `n8b_eval.tex:28-33`；`n5_organization.tex:220-229` | 要么跑通 approve→apply→decay 闭环，要么从贡献句与摘要中降级为设计描述 |

---

## 3. 必须用新实验（不能在文本层解决）才能修的问题

按性价比排序，任一完成都会显著提升可发表性：

1. **作者独立评测集 + 负对照**（一举修 C5/C6/C7 与设计评分）：公开语料 + 发布 qrels，
   或至少由非作者撰写、不从语料词汇取材的问题集；含"故意不可答""故意重复""故意不可解析"
   的负对照项；固定协议跑一次。
2. **让阈值真正生效的候选池**（修 C2/C3）：跨库负例 + 低边际候选，使 0.5/0.35/0.15 三个
   阈值至少在一个条件下改变候选集。
3. **单变量第三语料**（修 C4）：同域同语、按近重复簇各留一篇，只改混淆密度。
4. **人工盲评样本 + 一致性统计**（修 C6）：优先覆盖 10 个消融单元与分层抽样的 grounding 单元。
5. **真 off-switch 重跑门消融**（修 C3）：现在的不受门控制臂是重建的融合序控制。
6. **逐论文 parse status 采集重跑**（修 C8）：把 100 篇拆成 parse 失败 / 门拒绝 / 记录丢失。
7. **经验闭环**（修 C12）：种子草稿池 → approve → apply → decay → 分层检索。

---

## 4. 文本层可立即修改的清单（不改数据，带 file:line）

**P0（投稿前必做）**

- `n11_conclusion.tex:18-21`：重写 RQ3 结论文案；`n1_intro.tex:163-166` 的 RQ3 行与
  `tab:ataglance` 同步（现为 "Yes on reachability"）。
- `n6_retrieval.tex:72-74`：把门的三种角色显式命名——verify-and-re-rank（shipped）、
  verify-only（filter）、verify-and-cut（relative margin），各写决策规则、是否使用顺序、
  各证明什么；`n6_retrieval.tex:83-92` 那段"常数/来源/从未触发/需重调"拆成三句并点名
  三个阈值（0.35 dense、0.5 evidence、0.15 margin）。
- `main2.tex:69-77`（摘要）：C2 的"21% retrievability gap"改为 limitations 级表述；
  C3 的经验库降级；ablation 句保留 but 加 "post-hoc, n = 16, uncorrected" 限定。
- `n8b_eval.tex:161-162`（E4）："the only ranking movement is Q7" 与所引 artifact 不符——
  `exp5_judge_filter.json` 里 Q1 的 gold 由第 4 升到第 1（recall 0.5→1.0）、Q10 由第 3 升到第 1；
  且 MRR 算术上不可回避（filter 侧 13.7 中至少 5.7 来自 Hit@5 相同的七题，judged 侧仅 3.62）。
  改为只声明不利方向："the only gold the filter demotes inside the top-5 is Q7 (third to fifth);
  it promotes Q1 (fourth to first) and Q10 (third to first)"，或直接删去该从句。
- `n8c_eval.tex:48-62`（Fig. 7 caption）：删掉 "0.5 refusal threshold"（系统里没有拒绝阈值），
  改为"候选相似度 0.397–0.596 全部高于 0.35 dense 下限，检索层从不拒绝，拒绝发生在答题层"。
- `n3_overview.tex:114-121`（Fig. 1 caption）：按实际几何重写（四层堆叠 + 底部采集带）；
  `figures.py` 工具层 8 组 → 12 组（与 `n3_overview.tex:92-95`、`n7_implementation.tex:8-12` 一致）；
  三源一致性框加入向量库；删掉正文未解释的 "Content checks (quotes and units)" 面板或补两句。
- `n5_organization.tex:63-65`：三源一致性 → **四源**（磁盘 / tree registry / library metadata /
  向量 collection），并说明前三者由一次写入保证、第四者不然（论文自己举的 18 vs 9 chunks 就是它）。
- `n8b_eval.tex:267-291`：Fig. 3 caption 只描述自己画的东西；filter 那句移到 Fig. 6 caption；
  Fig. 6 的 (b) 改称 "three verdict roles"。
- `n8c_eval.tex:252-267`：Fig. 9 拆成单面板图（或把 (c)(d) 移到补充材料，它们与
  `tab:robustness`/`tab:ablations` 重复）。
- `refs.bib:248-260` 两条著录更正；`refs.bib:186-192` demo 条目补真实作者与正确发表状态，
  并与正文 "was published" 对齐。
- `main2.tex:4,49-54`、`n_back.tex:32-34`、`refs.bib:185`：作者元数据、ORCID、CRediT、
  funding、承诺声明 `.docx`；删除全部 3 处 `AUTHOR ACTION`。
- 跨语种：在 `n8a_eval.tex:9` 或 `tab:acq-crosslang` 处加一句"跨语言**查询**未测，
  本表只测多语入库与同语自检索"。
- 投稿长度策略：把诊断类表（采集审计、分区消融、27 轮稳定性、失败目录）移入已有 30 页
  补充材料，正文压到 ~13k 词；cover letter 里说明长度理由。

**P1（提升可读性与可复现性）**

- 术语冲突：设计原则 `P1–P6`（`n3_overview.tex:33-75`）、Lane C 阶段 `P1–P5`
  （`n6_retrieval.tex:170-179`）、经验可信度 `P0/P1/P2` 三套同名字符 → 分别改为 `D1–D6`、
  `C1–C5`、`T0/T1/T2`。
- 九配置单点复现：在 §8.4 加一张表（配置名 / 精确工具调用与参数 / 实测还是离线重放 /
  结果），并说明其中两条是离线重放日志候选池而来。
- `n6_retrieval.tex:206` 的 `kb_search_two_stage` 八个参数各给一句解释，并说明为何该入口
  `score_threshold=0.0` 而 lane 用 0.35/0.5。
- `n7_implementation.tex:5-40` 与 `:83-105` 两段巨型段落按"决策/证据"边界拆分并加 run-in 标题；
  给 §7 补一句与 §3–§6 同风格的开篇问题句。
- 术语表：catalog / shelf / survivor / evidence pack / meditation 五条在 §3 数据模型处定义。

---

## 5. KBS 形式合规状态（对照 Guide for Authors）

**已合规**：elsarticle 投稿类；摘要 248 词（≤250）；关键词 6 个（1–7）；highlights 5 条 ×
≤76 字符并已生成 `highlights.docx`（3–5 条、≤85 字符）；59 条编号引用按出现顺序（未用
`doubleblind`）；21 个表全部有 label/caption/正文引用且无竖线；9 张图各自独立文件、纯矢量、
RGB、字体内嵌、有效最小字号 8.02–8.03 pt（≥7 pt 要求）；Data availability、GenAI 声明
（标题逐字一致、位于参考文献之前）、competing interest、CRediT、Acknowledgments 齐全；
`.bbl` 已随扁平包上传（0 子目录、43 文件）；`elsarticle-num` 为期刊编号样式（journal 变体已用）。

**未合规 / 风险**：① 长度 ≈5× 偏好值（111 页双倍行距，且 21 表 + 30 页补充材料）；
② 标题页占位元数据（可被编辑部免送审退回）；③ 9 图中 5 张为拼图，KBS 明确不建议；
④ 关键词全为多词短语（Guide 建议避免）；⑤ 投稿副本 `unsrtnat`（review 变体）而期刊
样式为 `elsarticle-num`——投稿允许"任何一致样式"，但建议 final 用期刊样式；
⑥ CRediT 标题措辞与 funding 位置可再对齐 Elsevier 规范措辞。
补充材料 30 页结构完整（Part A.1–A.16 系统测试、Part B.1–B.16 检索测试、Part C 局限），
但此前记录的 13 页版本在本仓库不可复现（无构建脚本），已记录在合规档案中。

---

## 6. 结论与建议路径

**不建议**按当前版本直接投 KBS。**建议**两段式推进：

- **第一段（1–2 天，纯文本层）**：执行 §4 P0 清单（RQ3/门框架/摘要/图表 caption/拆图/
  四条参考文献/元数据/长度压缩）。完成后论文不再自相矛盾，形式风险降到可送审水平。
- **第二段（需要新数据）**：至少完成 §3 的第 1、2 项（作者独立问题集 + 负对照；让阈值
  生效的候选池）与第 4 项（人工盲评样本）。这三项把论文从"我们造了系统并报告了自己的
  负结果"提升为"我们量化了验证在已部署管线中的角色"，这才是 KBS 会收的知识贡献。

若第二段不可行，替代方案是把稿件重定位为 **design-and-deployment report**：删去所有
超出 n=16 单语料的定量主张，把 21/100 与两个零消融作为主要发现，投 KBS 的
system/experience 类目或改投工程向期刊。

---

## 7. 取证边界（不可验证项）

- 脚本层不可用（`0xC0000142`）：未编译、未重跑实验、未复核 JSON 数字、未渲染图像、
  未抓取网页；页数/字数/摘要词数取自本会话早前的 readiness 记录而非现场重测。
- 六席报告中所有条目均标 `[LLM]`；每条均有引文与 file:line，可由人工复跑复核。
- 两条参考文献更正依据评审席的领域知识（ACL Anthology），**未能在线复核**——本会话
  网络工具未用于该条目核对，投稿前须逐条对照出版方页面确认。

---

## 8. 第六席：数字核对账本（Results-verification）

**结论：数字健康状况良好。** 在不使用脚本、纯手工从 JSON 重算的条件下，**所有能触及的
头条数字都从 artifact 复现**，包括：九配置表的 Hit@5 / Recall@5 / MRR / 延迟
（`exp1_retrieval.json` 112 行 = 7 方法 × 16 题，逐题核对）、两条离线重放行
（`exp5_judge_filter.json`）、摘要的 0.94 → 0.44 → 0.94 与符号检验
（8 个不一致对全同向，2·0.5⁸ = 0.0078125；另有 8 个 Hit@5 平局）、Wilson 区间
[0.2310, 0.6682] / [0.7167, 0.9889] / [0.8064, 1.0000]、采集漏斗的 91（`exp10_ingest_state.json`
`saved_all`）与 79（`exp10_papers_toollayer.json` `n_docs`）、两个消融表的全部均值/文档数/延迟
（含 9×12+4 = 112 → 11.2 与 QK09 12→4）、分区消融的 rank 1.75 = 14/8 与 235.75 候选、
`prefix_leak_fraction` 1.0 与 131+75+53+39+24 = 322，以及 2026-10-12 三通道战役的四个 artifact
（路径全部存在；ch1 均值 46.967/142.2/51.233、8/9 门、单次调用内 300.0 s、ch3 12/12 gold 逐格复现）。

**唯一成立的数字类发现（moderate，非 gate blocker）**：E4 的
"the only ranking movement is Q7" —— 见 §4 P0 清单已加入的修法。方向性结论与其他所有
头条数字不受影响。

**因脚本层缺失而无法核对（不是发现，是缺证）**：191 候选的 Mann–Whitney p = 0.26 与中位数
0.876/0.863（需完整分数列表）、191 = 17 gold + 174 non-gold 的 gold 标记（191 与 174 本身可复现）、
"8,031 chunks"、"100 submitted"（artifact 中无逐篇清单）、Q6 的 "1/1 vs 0/11" 符号检查、
"two of thirty gate cells re-run"、两个 per-run 目录（`exp11/exp11-20261012-full/`、
`exp12/exp12-20261012-full/`）的逐格内容（需目录枚举）、"六篇整篇装入上下文窗口"、
"95 MCP tools"（此项本会话早前已由在线 `tools/list` 实测为 95）。

**已检查、判定为非问题**：`exp1_retrieval.json` 存 `latency_mean` 0.001 s 而表内印 0.9 ms——
表值是该均值的原始值，存储值是三位小数舍入，二者一致；改写行 "(n=16)" 与
"pooled over 32 variants" 并存属标签歧义（同段已给出 32 分母），非数字错误。
