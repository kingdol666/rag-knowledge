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
> ④**CR 字节损坏修复**：sec3_demo.tex 的 `Section~ef` 曾被 heredoc JSON 转义
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
