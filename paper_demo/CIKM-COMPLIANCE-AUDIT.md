# CIKM Demo compliance & style audit — QDCVR

> **2026-09-22 深夜布局修订（当前 build）**: 修复 §5 Conclusion 观感问题——此前
> preamble `topnumber=3` 让 Table 1+Table 2 全部堆进 p4 左栏顶（Fig3 下方），§4 正文
> 被挤成表格下的碎片、§5 Conclusion 顶死下边距。改为 **`topnumber=1`**（每栏顶最多
> 一个单栏浮动体）后 T1 落左栏顶、T2 落右栏顶，两栏对称，§5 作为正常章节收在文本块
> 内；同时删掉 `\enlargethispage{2\baselineskip}` 硬撑并微缩两句 §4 文字（"so the
> demonstration can show"→"so records exist"；"allowlist denials caused by an
> alternate tool prefix"→"tool-allowlist denials"，语义不变）。终态：5 页、正文 4 页、
> 0 Overfull、visual-judge p3/p4 复审 pass。

> **2026-09-22 晚间修订（前一版）**: 摘要 233→约 160 词并修正误导句（旧摘要把
> bare/dense 的 6/0 写成 grounding 对比，实为 part/section 引用粒度行）；Fig.3 从
> p3 移到 p4，恢复**每页一图**（p2/p3/p4 = Fig.1/2/3）；Scenario 2 弃用 2026-09-19
> 老 run 的 BQ02/NISQ 例，改用受控 run `experiment_chat_20260921-181449` 的
> R2Q05/MPO 轨迹（two-stage top score 0.683、part 1 of 3、direct read、verbatim
> 引文、四层地址 source block）——全篇现在只站在**一个**实验 run 上；
> §2.3 删除缩写展开句（移入 §1）与死记号 P₀/P₁；backmatter 补 "Competing
> interests: none declared." 与 Demo video URL（GenAI 块不占页数预算）；xurl 允许
> URL 断行；Table 2 表注定义 "Dense retr."。**0 Overfull；正文仍 4 页整**（§5
> Conclusion 收于 p4），p5 仅 GenAI 声明 + 参考文献 [1]–[8]。全部数字经
> `benchmark-suite/scripts/108_pipeline_evidence.py` 与 run 内 audit_paper_numbers.json
> 重算核验（grounded 9/10·10/10·10/10、citations 8/6/0、46.4/16.5/22.1s、8.6/4.1/2.7
> 次工具、$5.15/3.23/1.88；未 grounded 的 track-A 题已核实为 R2Q06）。visual-judge
> 5/5 页 pass（其非阻塞建议 Dense retr. 表注已落实）。作者占位符（姓名/单位/邮箱/
> funding）仍待作者填写。

Audited build: `tex/main.pdf`, 5 pages = **body 4 pp** (Abstract → §5 Conclusion
ends on p4) + p. 5 carries only the GenAI Usage Disclosure (with Data-availability,
competing-interests and demo-video lines) and references — the categories the CFP
allows to overflow.
Reference set: the six CIKM demo papers in `reference/`; distilled rules in
[`FIGURE-STYLE-GUIDE.md`](FIGURE-STYLE-GUIDE.md).

## 1. Hard requirements (CIKM 2026 Call for Demo Papers)

| Requirement | Status | Evidence |
|---|---|---|
| ≤ 4 pages incl. appendices **and acknowledgments** | ✅ | §5 Conclusion ends on p4; only GenAI disclosure + references on p5 |
| Unlimited references | ✅ | p5, [1]–[8] |
| GenAI Usage Disclosure **before** references, outside the page budget | ✅ | `sec4_backmatter.tex`; Data availability, competing interests, and demo-video URL live inside this block |
| ACM **sigconf**, two column | ✅ | `\documentclass[sigconf]{acmart}` |
| CCS concepts + keywords | ✅ | p1, two CCS concepts + 5 keywords |
| **Single-blind** — real names required | ⚠️ | `Author Name` / `Affiliation` are placeholders; **must be filled before submission** |
| 3-minute demo video, URL in the paper | ✅ | URL in the abstract **and** in the backmatter block (verified HTTP 200 on master) |
| Funding + competing-interest disclosure | ⚠️ | "Competing interests: none declared." present in backmatter; funding line still a placeholder |
| Intended audience | ✅ | §1 last paragraph + §3 opening |
| Innovative aspects | ✅ | §2.3 gate/librarian/not-found contracts |
| Contribution to SOTA | ✅ | §4 + Fig. 3 three-mode comparison |
| What attendees will experience | ✅ | §3 Scenarios 1–3, first sentence each |
| Functionality & user scenarios | ✅ | §3 Scenarios 1–3 |
| Interface / interaction options | ✅ | §2.1 web console / CLI / MCP; §3 demo setup |
| Comparison with existing systems | ✅ | §1 positioning + Fig. 1/Fig. 3 measured comparisons |
| **R&D challenges** (review criterion) | ✅ | §2.3 gate failure → librarian escalation design |

## 2. Layout — one figure per page (enforced 2026-09-22 evening build)

| Page | Content |
|---|---|
| p1 | Title, abstract (~160 words), CCS, keywords, §1 + contribution bullets |
| p2 | **Fig. 1** (teaser: dense RAG vs. QDCVR) + §2.1–§2.2 |
| p3 | **Fig. 2** (architecture + workflow) + §2.3 tail, §3 Scenarios 1–3, §4 opening |
| p4 | **Fig. 3** (three answering modes) top; **Table 1 tops the left column, Table 2 tops the right column**; §4 text flows beneath; §5 Conclusion ends the body within the text block |
| p5 | GenAI Usage Disclosure (+ data/competing/video lines) + References |

Mechanics: Fig. 1 and Fig. 2 are declared after `\input{sec1_intro}`;
**Fig. 3 is declared between `\input{sec3_demo}` and `\input{sec4_eval}`** so it is
met while p3 is typeset and becomes eligible for p4. **`topnumber=1`** is the load-bearing
setting for p4: it limits single-column top floats to one per column, which splits
Table 1 (left) and Table 2 (right) across the two column tops; raising it (an
earlier build used 3) stacks both tables over the left column, strands a §4 text
fragment beneath them, and pushes §5 Conclusion flush against the bottom margin.
Fig. 3 itself is a double-column float and queues separately (`dbltopnumber`).
`xurl` lets the two long URLs break; no `\enlargethispage` hacks remain.
Moving any declaration moves its float — re-check the page map after edits.

## 3. Evidence chain (all re-verified 2026-09-22 against artifacts)

- **Single experiment run**: `benchmark-suite/results/experiment_chat_20260921-181449/`
  (30 traces = 10 questions × 3 modes) feeds Table 2, Fig. 3 (`build_fig3_outcomes.py`,
  R2Q10), and Scenario 2 (R2Q05 track A: two-stage top score 0.683, part 1 of 3,
  direct `kb_doc_read`, verbatim quotation, base/document/part/section source block).
- Corpus: `r2_exp_corpus.json` → corpus_files=100, chunks=4528 (matches Table 1
  "Dense replica index 4,528"). The run's `SUMMARY.md` header says "50-paper" — a
  stale template string in the artifact; the corpus files are 100. Do not "fix" the
  paper to match the artifact header.
- Table 1 regenerated by `scripts/108_pipeline_evidence.py` → `r2_pipeline_100.json`
  (100/100 routed, 322 docs, 0 true duplicates, 4528 chunks; failure probes
  1/8·1/8·0/8 → three NOT_FOUND verdicts).
- Table 2 recomputed from the run's `audit_paper_numbers.json`: grounded 9/10/10/10
  (track-A miss = R2Q06, turn budget during verification re-read), citations 8/6/0
  (regex over saved answers), 46.4/16.5/22.1 s, 8.6/4.1/2.7 tool calls,
  $5.15/3.23/1.88.

## 4. Outstanding before submission

1. **Author names and affiliations** — single-blind, placeholders must go.
2. **Acknowledgments / funding** — replace or delete the bracket line; similar
   length is safe, longer text needs a recompile check.
3. **`\acmConference`** — confirm exact CIKM '26 dates at camera-ready and
   re-enable the ACM reference/ISBN/DOI block.

## 5. Verdict

| Aspect | Verdict |
|---|---|
| Hard CIKM 2026 demo requirements | **passes**, modulo author-side placeholders (names, funding) |
| Page budget | **passes** — body incl. conclusion = 4 pp; p5 = GenAI disclosure + references only |
| One figure per page (p2/p3/p4) | **passes** (Fig. 3 moved off p3 in this build) |
| Writing-logic pass | **passes** — acronym expanded at first body use (§1); positioning and approach paragraphs de-duplicated; Scenario 2 on the same run as §4/Fig. 3; dead P₀/P₁ notation removed; abstract comparison sentence now matches Table 2's citation row |
| Content completeness | system, architecture, protocol, scenarios, evaluation, honesty checks present; all headline numbers re-verified against `benchmark-suite/results/` |
| Typesetting | 0 overfull boxes, 0 undefined references, 0 LaTeX errors |
| Visual acceptance | judge pass on all 5 rendered pages; its "Dense retr." caption suggestion applied |

> **2026-09-22 深夜图1重绘（当前 build）**: Fig.1 按顶刊风格用 HTML+SVG 重绘并经
> 7 轮严审 subagent 迭代收敛（每轮独立全新评审，R1-R6 均 revise、R7 后全部关键项
> 清零）。新图源码 `figures/submission-20260922/fig1-core.html` + 构建脚本
> `build_fig1_core.py`（playwright 门禁：最小字号 ≥11.9px、越界、文字重叠、
> box-overflow、边框穿越；矢量 PDF + 字体内嵌 + mediabox 750pt）。设计要点：
> 双面板 balanced（BASELINE: DENSE RAG 灰 vs QDCVR teal）、地址脊线面包屑
> （base▸document▸part▸section 于共享基线）、实线肘部=gate ≥ 6 直达、虚线
> fallback 回路+分叉节点+左缘干线=条件出口（=5/≤4 虚线边框呼应）、0–8 评分
> 入 gate 盒、takeaway 条。图内 scope note 改为 "Shown for contrast."（旧图
> "see Table 1" 是潜在错引——evaluated variant 在 Table 2，图注已写明）。
> 版面连锁：Fig.1 高度 284→240pt，正文前移——§3 提前至 p2、Table 1 提前至
> p3 右栏、§5 Conclusion 与 GenAI 声明均收于 p4（更紧凑且合规：正文 ≤4 页、
> p5 仅文献）。1 处 1.45pt Overfull vbox（p4 右栏，不可见）。visual-judge
> 5/5 页 pass、无 must-fix。**遗留风格债**：Fig.2/Fig.3 仍是旧暖色风格，与
> 新 Fig.1 的冷灰绿顶刊风格不一致——建议下一轮同法重绘（用户本轮仅要求 Fig.1）。

> **2026-09-23 前置章节重写（当前 build）**: 摘要/§1/§2/§3 按"两个 gap → 三个设计
> 决策 → 系统剖析 → 三场景走查"故事线重写，经双席并行评审（叙事合规席 + 魔鬼代言
> 人席，29 条 issue）+ 第二轮全新验收席（accept 8.5/10）收敛。关键修正：
> ①摘要 "all modes answer" → "substantively answer"（R2Q06 截断的严格口径），
> ②"only the platform's answers carry addresses" 自相矛盾句改为分列两个指标
> （part/section citations 8 vs 6 vs 0 + full address 对比），
> ③设计决策 ii 由 "Reading replaces scoring"（被自家 0.683 相似度分反证）改为
> "Ranking proposes, reading disposes"，④删无支撑的普适断言 "more vector
> queries would only re-rank the same near misses"（降级为设计理据），
> ⑤Table 1 两行标签纠偏（"Stored parts after 30k split ceiling"；"Content audit
> (first 1,000 chars per part)"——audit_manifest.json 实证每部分抽前 1,000 字符、
> 覆盖率 100%，旧标签 "Full-content audit (1,000 chars each)" 自相矛盾），
> ⑥删无工件支撑的 "permissions"，⑦§1 bullet 过度承诺修正（walk evidence +
> compare head to head），⑧"auditable"→"records the rubric judgment"（避免与
> "not an append-only audit log" 自相矛盾）。**保留 "scripted"**（场景 3 的诚实性
> 披露，拒绝叙事席的 "saved" 建议）。版面：正文 ≤4 页不变、每页一图、§5+GenAI
> 收 p4、文献 [1]-[6] p4 + [7][8] p5；1 处 1.15pt 不可见 vbox。visual-judge
> 5/5 pass。Table 1 行项已对照 scripts/108_pipeline_evidence.py 输出逐行核验。

> **2026-09-23 loop 循环（best-paper 收敛，当前 build）**: `/loop` 动态循环 3 轮双席
> 评审至收敛（R1 内容 9.0 accept + 视觉 6 revise → R2 8 revise → R3 **accept 9/10**，
> 剩余项全部为 minor 且已修）。本轮落地：
> ①**Fig2 整体重绘**（`figures/submission-20260922/fig2-architecture.html` +
> `build_fig2_architecture.py`，门禁同 fig1）：Fig1 视觉语言（冷灰绿/Helvetica/实心
> 箭头/Content gate 节点 + ≥6/=5/≤4 badge/虚线=条件出口）、基础设施通道
> （console/CLI/MCP → 41 kb_* 工具 → ChromaDB·Neo4j·Markdown/YAML）、六点检查
> 入图、**P0/P1 孤儿记号清除**、Lograrian 浏览条；
> ②**Fig3 重排**（`build_fig3_outcomes.py` 就地改版）：最小字号 13.5→15px
> （assert ≥14.9）、画布 372→344（全宽放置后 173pt，p4 预算内）、删除与图注重复的
> 大标题、三模式色重推导（teal A/slate B/amber C）、verbatim/时间线门禁保持全绿；
> ③fig1 面包屑 arXiv 号纠偏（2409.13354→2409.13934，对齐 R2Q10 轨迹与 Fig3）、
> ✗ 记号改家族琥珀色、fallback 上行腿重定向到 Read candidates（消除"重入向量召回
> = 更多向量查询"的语义张力）；
> ④**CR 字节损坏修复**：sec3_demo.tex 的 `Section~
ef` 曾被 heredoc JSON 转义
> 吃掉反斜杠变成 `Section~^Mef`（PDF 印出乱码）——bash 双引号会吞 `\`，含反斜杠
> 的 LaTeX 补丁必须走 Write 脚本文件；已修复并在 PDF 文本层验证无 `ef{`/`??`；
> ⑤指标命名统一 "part/section-level citations"（§4 与 Table 2/摘要一致）；
> ⑥rubric 三维操作化定义（逐字对照 .claude/skills/knowledgebase-search/SKILL.md）、
> shelves 补定义（per-base document listings）、§3 开头点明三场景=三设计决策、
> gap 句补 payoff、Table 1 标签纠偏（Stored parts / Content audit first 1,000
> chars per part）、Table 2 表注星号合并、"gate ≥ 6" 微标签、R2Q10 正文点名。
> **保留项**：图注全粗体 = stock acmart 默认（LinLibertineTB 8.9-9.0pt 实证），
> 不覆盖类行为；**遗留**：§4 "322 stored documents" vs 前文 "stored parts"
> （locked，camera-ready 备注）；作者占位符待填；改动未提交。

> **2026-09-23 深夜 Fig.1 分镜化 + 三图美化（当前 build）**: 应用户要求 Fig.1 改为
> **四格漫画分镜**（非动画/GIF——PDF 为静态介质；上排=BASELINE: DENSE RAG 四格
> 失败序列：文档→撕碎成 ≈800-char 块（琥珀裂纹）→top-2 检索+打包→单次生成无来源；
> 下排=QDCVR 四格：内容路由→地址面包屑 base▸document▸part▸section→阅读+0–8 评分
> 门控（6–8 高亮）→cited answer/虚线 scoped not-found），序号徽章+格间箭头+行标题，
> H=508（print 256pt）。Fig2 基础设施通道加内联 SVG 图标（browser/terminal/MCP-graph，
> text-anchor="start" 覆盖继承居中——图标压字事故的根因是 SVG g 继承
> text-anchor=middle）；Fig3 底部加量化优势条（"Part/section-level citations
> across the 10 monitored questions — A 8/10 · B 6/10 · C 0/10 (Table 2)"，H=368/
> print 185.5pt，p4 预算内）；Fig3 面包屑 ID 与 Fig1 对齐为 2409.13934；main.tex
> Fig1 caption/Description 改为 top/bottom 分镜叙事；**修复 CR 字节损坏**
> （heredoc/JSON 转义吞反斜杠 → `Section~
ef` 变 `Section~^Mef`，PDF 印乱码；
> 用 chr(92) 字节级脚本修复，PDF 文本层验证无 ef{/??）；"Section
ef" 缺 ~ 的
> 丢空格修复（definitions in Section 4）。0 Overfull；正文 ≤4 页；每页一图。
> **并行会话协同**：另一会话同期将 §4 切换至新 run experiment_chat_20260922-211000
> （7-4-1 citations、BQ04+BQ06 双问题 Fig3-dual、Costs and limitations 段、
> §5 Conclusion 并入 §4、GenAI 移 p5）并同步了摘要数字——本轮已核验新 run 工件
> （grounded 9/10·10/10·9/10、lat 113.0/42.7/48.0、cost $4.91/1.63/1.80、
> citations 7/4/1 经 re 复算）与摘要/§4 一致。**camera-ready 备注**：§4 若保留
> "322 stored documents" 措辞需与 §2/§3 的 "stored parts" 统一。

> **同轮验收补充**: visual-judge 复验通过——Fig2 图标位于标签左侧无压字、"41 kb_* tools"
> 注记可读（换行不碰 ChromaDB 芯片）、Fig3 图注 "(definitions in Section 4)" 空格恢复、
> 每页一图保持。临时调试渲染（cur_*/pg-*/check-*/fig2_infra_4x）未入库。

> **09-23 深夜终轮（字体纯化 + 分镜版全页验收，当前 build）**:
> ①**字体合规**: 三图内嵌字体统一为 Arial 族（ArialMT/Arial-BoldMT/Arial-ItalicMT），
> 消除 CambriaMath 回退（▸→›，Arial 自有字形）；图注粗体为 stock acmart
> （LinLibertineTB）勿改；图内 sans-serif 符合 ACM 配图规范。
> ②**遮挡复验**: fig2 基础通道 5x、fig1 全幅、fig3 双问题版均无文字压叠
> （根因修复 = SVG `<g text-anchor=middle>` 继承导致锚点改 x 不生效）。
> ③**Fig3 升级为双问题版**（并行会话 build_fig3_dual.py，H=934、0.92	extwidth）:
> BQ04（GO 本体，三模式全答）+ BQ06（降水极值，dense 测得弃答）真实 verbatim 作答
> 对比 + 内嵌 MONITORED RUN 聚合条（grounded 9/10·10/10·9/10；keyword-verified
> 9/6/6；latency 113.0/42.7/48.0s；tools 7.6/4.4/2.4；citations 7/4/1；cost/q
> $0.4911/0.1631/0.1803）——全部对 run 工件 re 复算一致；单题版 fig3-answers.pdf
> 保留为备用资产（未引用）。§4 正文同步新 run（"Measured Three-Mode Run and
> Limitations"，含 BQ02 邻居调查披露、Grading deliberately conservative 等）。
> ④**结构**: §5 Conclusion 由并行会话移除（正文止于 §4，p4 收）；GenAI + 文献
> [1]-[8] 在 p5；正文 ≤4 页 ✓；每页一图 ✓；0 Overfull ✓。
> ⑤段落空白: 全页目检 p1-p5 无过大空隙（6 处 underfull 为轻微拉伸，不可见）。

> **09-24 全系统评审 Loop（3 轮收敛，当前 build）**: 四席×2 轮 + 三席终审，
> JSON 在 review/full-system-20260924/（纪要 LOOP-SUMMARY.md，事实清单
> FACTSHEET.md）。要点：
> ① **Fig3 时间线造假修复（DA-1, P1）**: 五条轨迹核对发现时间线盒 5 处计数
> 错误（BQ06-A 凭空捏造 two-stage、×3 写成 ×2 等）；重写 build_fig3_dual.py
> 为全计数模式（每行显式 ×N 且总数必须精确划分轨迹 tool_use 事件），gate 从
> "非空断言"升级为逐计数对账；重建后 H=924。
> ② **BQ06 正字假象披露（R3-1/2, P1）**: bare agent 答案含连字符
> "precipitation-efficiency"，word-boundary 正则跨连字符不匹配 → 0/1，与
> 实质等价；caption 改 "matched no gold key fact under word-boundary
> grading"，§4 保守性句显式列 BQ06 0/1 + BQ08 0/2；摘要加
> "conservative word-boundary verification" 限定。
> ③ **页限 P0（四席一致）**: Round-1 加字把 §4 推上 p5；回收 ~15 行
> （caption 精简、冗余句删除、Fig3 0.92→0.885\textwidth）后正文收 p4，
> p5 仅 GenAI+文献。Fig3 字号 ~5-6.5pt 为已文档化取舍（V2-1）。
> ④ **8 vs 9 检查项（R5-2, P1）**: fig2 banner 去 "Nine-point" 计数改列
> 9 个可数记录（"vector probe (×2)"，A6V+C5 双记录属实）。
> ⑤ **Fig3 底条列标签（R5-3, P1）**: navy banner 右侧加
> "A Platform · B Bare agent · C Dense"。
> ⑥ **R6 34 条行级编辑**全应用（句子拆分/术语统一 organization skill/
> out-of-corpus/stored parts/平行结构/冠词/tie）；R5-6 拒绝（图注全粗体
> = stock acmart 勿改）；V2-2 修复（fig1 caption 删未绘制的
> "rewrite, cross-base recall" 枚举）。
> ⑦ **终审**: V1 8.5 accept、V3 9.0 accept（9/9 核验）、V2 7.9 minor
> （仅字号取舍）。数据经 DA+DA2 双独立审计（117+8 项）零造假。
> **用户待办**: 作者占位符；演示视频仍为旧 50 篇普查画面（需重录或加
> slate，video README 自查清单有此条）。

> **09-24 紧凑图版+正文扩写轮（huashu-design × academic-paper，当前 build）**：
> 应用户"图 2/3 占版过多、图小一些、正文多介绍、保持 4 页"要求。方向沿用已
> 定稿冷灰绿家族（huashu 三方向门的"已选定方向迭代"豁免，落档本段）。
> ① **Fig2 三横带重构**（1000×589→1000×442，-25%）：基础设施带压缩为单行
> 芯片组；ORGANIZE 六步竖链→五芯片横链+终检横幅（9 可数记录）；RETRIEVE
> 横向流+三出口徽章条+虚线 librarian 条；gate 节点保持签名尺寸；
> \textwidth 下 297→223pt。
> ② **Fig3 单卡三段式**（H 924→751，-19%）：每模式一张卡（时间线/verbatim
> 引文/来源，细分隔线），引文取更短精确子串（门禁仍逐条断言），来源行 3→2，
> 聚合条行距收紧；0.885→0.92\textwidth（字号反而回升）；413→349pt。
> ③ **释放 ~35 行栏空间全部投入正文**：新增 §5 Conclusion（回填；含
> gated-reading-route 措辞、3× 成本、"every number this paper reports"
> 限定）；§2.1 增同工具同可见性句；§2.2 增九项终检三例+ingest 期拦截；
> §2.3 增 ranking-vs-browsing 设计理据；§3 增控制台打开引文 part 句；
> §4 增工具调用计数句。正文仍收 p4，p5 仅 GenAI+文献。
> ④ **验收**：visual-judge 5/5 页 pass；内容席 CX1（7.5 minor）1 P1+4 P2
> 全采纳——P1="按行偏移在控制台打开"是过度声明（控制台预览固定 offset 0，
> 行偏移仅在 API/MCP 层）已改写；九项检查三例、7.6/4.4/2.4 归属、结论
> "only for gated reading route"、"every number this paper reports" 均
> 对 103_final_check.py / Vue 源码 / exp_r2_grade.json 核伪后落地。
> ⑤ 图注/Description 同步新构图；溢出=仅 p5 文献栏 1.3pt 不可见 vbox。

> **09-24 全系统 Loop 第二次收敛（紧凑图版复审，2 轮，当前 build）**：
> Round A 全新四席（F1 全文 9.0 accept / F2 视觉 7.5 / F3 方法 7.5 /
> F4 增量审计 9.0 accept·8/8）→ 13 项修复 → Round B 全新三席
> （G1 9.0 accept / G2 9.2 accept / G3 9.0 accept·10/10）收敛。
> **Round A 抓到的真伤**：①§2.2 误路证据错配——把 read-back 当错路检查，
> 实际验路由的是 base fit(C4_kb)（F3-1）；②§5 把失败门三出口压成两出口
> （漏 re-assessment→cited）；③"every number this paper reports"被论文自身
> 配置常量（41 工具/30k 上限=repo 事实而非 run 工件）证伪→限定为
> "every number in the measured run (Section 4)"；④fig2 措辞修复
> （dashed edges→outlines）改了 HTML 没重编译就被 F2 像素抓包——**改图必
> 重构建**；⑤Markdown·YAML 芯片距带边仅 2px（我重构时的真 bug）；
⑥fig3 \Description 声称的 "295 kelvin" 在缩短后的引文里已不存在；⑦时延
> 下限 10s 低于实测 13.8s→"about fifteen seconds"。Round B：G2 像素级验证
> 5 项图修复全落地（芯片 27px 对称边距/(b)链左对齐 x=55-56/图例措辞/引文
> 弯引号+省略号包裹/徽章 52px×3 等高）；G3 对 artifacts 验证 13 项文本修复
> 零回归。G2-1 拒绝并留档：引文内部直引号是 verbatim 原文，改即破坏逐字
> 门禁。终态：正文收 p4、p5 仅 GenAI+文献、图门禁全绿、0 可见 Overfull。

> **09-24 图2 内嵌真实控制台截图（demo 轨惯例补齐，当前 build）**：应用户
> "启动项目→截图拼接→放进图2、流程绘制正确"。①按仓库既有抓取脚本体系新写
> capture_figure_ui.py：英文 UI（localStorage kb-lang=en）、真实登录
> (paperdemo)、内容验证开关=搜索前置开关（开启后重搜才产出逐条校验行——
> 首轮点错开关的教训）。②三块 DOM 精确裁切（DOM bounding box×2 设备像素）：
> ①知识库行(库名+英文描述+131 docs)②检索策略+查询+范围 ③COMBINED/VECTOR
> 分道分数+part 地址+绿色 verified 行+relation graph；边缘切字修两轮。③集成：
> 基础设施带替换为"WHAT ATTENDEES SEE"截图带（①②③圆形徽章、右注保留
> 41 工具/存储信息），全图 442→512px；**Chromium 按 CSS 尺寸降采样(97dpi)
> → PyMuPDF replace_image 用全分辨率裁切原位替换 → 印刷 dpi 339/428/479
> 全部≥300（ACM TAPS 规则），builder 断言从"禁栅格"改为"逐图印刷 dpi≥300"**。
> ④页限再平衡：溢出 119 词 → Fig3 内衬压缩(-31px，间距回退 2 处避免
> 文字侵入矩形判定) + 22 处文字精修 → 正文收 p4、0 可见溢出。⑤徽章骑边框
> 触发 border_cross（文字跨矩形边）教训：徽章须完全在框内或完全在外。

> **09-24 图2 截图带终修（视觉席像素级验收后）**：视觉席 6 项判定 5 pass +
> 1 fail（badges_and_edges）——①徽章 ③ 压 "COMBINED" 首字母 1.5pt；②②/③
> 边框切字（"BM25 ("、"0.62|"、"arch Strategy:" 孤儿字形）；③②左缘 1px 蹭
> 字。**修法**：弃用圆形徽章，改条带下方 14px 编号标签行
> （"1 · the collection / 2 · the search / 3 · the evidence"，零遮挡零越界的
> 结构性解法）+ 逐块重裁（②左缘 x495 完整含 "Search Strategy:"/"KB Scope:"、
> 右缘收至 Result Count 框后 x1012；③ y656 起去掉顶部残留行边）+
> 间距重排（48px，右缘对齐 972 与流程芯片同列）。图注枚举改为 1:1 对应
> 三块裁切；\Description 重写（删除"first band lists the interfaces"旧句——
> 界面芯片带已被截图带替换，序号曾整体错位）。**教训**：门禁只查 SVG text
> 节点，栅格截图内容对 overlap/border-cross 不可见——截图边缘质量只能靠
> 裁切前对 DOM 坐标预留边距 + 人眼复合检查；徽章不得骑边框（border_cross），
> 也不得压在裁切内容上——把编号移出画面是最稳解。

> **09-24 图2 极简重构 + Agent 真实回答截图（用户第二轮要求，当前 build）**：
> 应用户"加 Agent 真实回答截图（标 4）、精简图2——元素太多"。①**截图 4**：
> 控制台 Claude Chat 页真实提问（与 §3 场景 2 同题 BQ04）→ 21s 得到真实
> 回答（GO 三本体 + 正交词汇说明），3× 设备像素重抓（2304px → 印刷 513dpi）。
> 抓取脚本 capture_agent_answer.py 入库（含 stop-button 生命周期判完成）。
> ②**极简重构**：520→448px，元素大幅删减——删掉界面芯片带/终检横幅/
> librarian 虚线带/三条全宽大徽章；新构图=顶部四张截图（1 collection /
> 2 search / 3 evidence / 4 answer，编号标签行）+ 答案旁 "the gate's outcomes"
> 三出口小票（虚线=回退语义保留）+ 底部单带两行流程（ORGANIZE/RETRIEVE，
> 每行 4 芯片，gate 为终点粗框）。所有细节移入 caption/Description。
> ③**技术坑**：PyMuPDF replace_image 的源序此前按 bbox x 排序——④与①同 x
> 导致错配（dpi 断言 231 抓到）；改按 (y, x) 排序。④页限：正文整体上提
> （GenAI 一度落 p4），恢复 §1 被裁的"walk an evidence from citation to
> source"演练句（审稿人曾赞赏），再以图注去冗余句平衡 → 正文仍收 p4、
> 0 可见溢出。四张截图印刷 dpi 均 ≥300（构建断言）。

> **09-24 图2 极简版像素终修（视觉席 5 项 3 pass/2 fail 后）**：fail(A)
> screenshot_crops——①边框发丝线②顶部上行色带③顶/底切字+字号 3.3pt 偏小
> ④左缘 0 内边距；fail(B) caption-像素不符三处（Description 称答案含
> Cellular Component 实际只到 item 2、"nine-check"句图内无对应物、
> console/CLI/MCP 注记与图内简注不符）。修法：①内缩 3px；②下移避开色带
> 并收在 "Vector Semantic" 后的干净断点；③放大到 354px 宽（4.0 宽高比）
> ——COMBINED+VECTOR 两值完整、字面 ~5pt；④以背景色画布补 30px 左内边距
> （气泡元素截图本身零内边距——元素级截图的边界=内容边界）；caption 删
> nine-check 句、Description 改"a numbered list of the three Gene Ontology
> namespaces"/"the same 41 kb_* tools run over vector, graph, and file
> storage"。终态四裁切印刷 343-505dpi、边缘干净、正文仍收 p4。
