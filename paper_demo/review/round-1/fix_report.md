# Round-1 修复报告（CIKM demo paper）

日期：2026-09-19（编译与验证基于同一工作区）
范围：main.tex、sec0–sec4 共 7 个 tex 文件、3 个图 HTML、3 张 PNG、benchmark-suite/results/graph_stats.json

## 最终状态

| 项目 | 结果 |
| --- | --- |
| 编译 | pdflatex ×2 + bibtex ×1，**0 error**，11 条 warning（均为模板级：fancyhdr headheight、hyperref PDF-string、balance、acmart CCS/keywords/reference-format/image-description，全部为修复前已存在），**0 overfull box** |
| 总页数 | 5 页 |
| 正文结束位置 | **Abstract → Conclusion 在第 4 页内结束**（第 4 页末句为 Conclusion 末句 "…corpus-gap maps) follow the same contract."） |
| 第 5 页内容 | Acknowledgments、Data Availability、GenAI Usage Disclosure、Competing Interests（backmatter 声明，与 GenAI 同层级，非正文）、References |
| 重截图 | fig1_rag_vs_kb.png（2400×1270）、fig2_architecture.png（2300×1150）、fig3_benchmark.png（2200×1352），三张 PNG 时间戳均晚于对应 HTML 修改 |
| 数字溯源 | 逐项 grep 复核：10/10、9/10、8/10、2.38 s、78.8 s、12.2 s、6–8/8、5/8×2 rescue、1/8,1/8,0/8、0.59 s、1.57 s+0.81 s、BQ01/BQ03/BQ06/BQ10、165 indexed documents、860 typed relations（730+130）、graph_stats.json、1.6 s、35.5–165.3 s、5.8–28.6 s、immune evasion 全部在文/表中，未改动任何数值 |

## 逐条处置（26 条）

### A. 页数压缩
1. **done** — sec3_demo.tex 末尾 `\paragraph{Generalizability.}` 整段删除（§4 同文保留）。
2. **done** — §2.4 "Three decisions distinguish…" 压缩约 1/3：三个 contract 名称保留，重复解释删除，"Both kinds of system can say…" 并入 (iii) 收尾（"…named in a report, and stored --- which is what makes the traces in Section 3 replayable"）。
3. **done** — Scenario 2 压缩约 20%（保留 0.71、part 1 of 3、7/8、five-section 与 "Point proven"）；Scenario 3 压缩约 20%（保留 5/8→6/8、two of ten、1/8/1/8/0/8 与 "Point proven"）。
4. **done** — Results 两段压缩约 20%（与 Table 1 重复的数字表述从简；10/10、2/10 弃答、78.8/12.2/2.38、kw 10/10 与 9/10、两次 5/8 rescue 全部保留在文或表）。
5. **done** — Conclusion 第二段压缩 ≥25%（多轮精简；扩展方向压缩为括号列举）。
6. **done** — sec1_intro related-work 段压缩约 20–25%，全部 \cite（rag-lewis,dpr,langchain,llamaindex / siren / graphrag,lightrag,raptor / selfrag,flare,crag / kamath）保留。

### B. 两次运行口径
7. **done** — Abstract 改为规定措辞："a scripted 10-question keyword regression passes 9/10, and the live skill run answers 10/10 on target with gate scores of 6--8/8, two librarian rescues, and top-1 gold-document recall of 10/10 at 1.6 s mean vector recall"。
8. **done** — Intro Evidence bullet 同步两次测量口径（同措辞简短版）。
9. **done** — Results 中两次 miss 拆为两句：脚本回归 1 次 miss = BQ06 分块窗口伪象（续读子句同语料可解）；live 五段式回答 all-keyword 1 次 miss = BQ10 连字符分词伪象（"immune evasion" 在答案中带连字符）。未混为一句。
10. **done（保留）** — §2.2 末尾前向引用句保留（"These protocol steps are quantified in Section 4; low initial scores are the gate working as designed."）。

### C. 延迟口径
11. **done（等效精确表述）** — 规定的单行标签在单栏表格中超宽导致数值压入右栏（首次编译实测重叠），故拆为两行精确口径："Latency: retrieval + reads (A) = 2.38 s"、"Latency: end-to-end (B, C) = 78.8 s / 12.2 s"；"Latency range (B, C)" 同步标注。数值未变。
12. **done** — 正文改为 "Track C is the fastest end-to-end track at 12.2 s (0.59 s of it retrieval)"，并加括号说明 "(Track A's 2.38 s covers retrieval and evidence reads only; answer generation is agent-side in all tracks and untimed)"。
13. **done** — fig3 标题改 "LATENCY PER QUESTION"，small 注改 "scopes differ: A = retrieval + evidence reads; B, C = end-to-end — lower is better"；fig3_benchmark.png 已重截。

### D. tri-channel → vector-first
14. **done** — fig1 右栏 step 2 标题改 "Query rewrite → vector-first recall → content gate"，desc 改 "Dense recall across 5 routed KBs, cross-KB balanced, in ~1.5 s; agent reads candidates and scores evidence 0–8"；fig1_rag_vs_kb.png 已重截。
15. **done** — main.tex fig:teaser caption 改 "vector-first recall over five routed bases in about 1.5 s"。
16. **done** — §2.2 Phase 1 句后插入 "The platform also ships BM25 and graph channels (Figure 2); the benchmark protocol contracts vector-first recall with cross-base balancing (see §2.5)."。

### E. Scenario 3(a) 与工件一致
17. **done** — 改为 "the initial top chunk is a header-only part fragment; the gate scores it 5/8, the librarian fallback re-searches and locates the abstract and equilibrium-analysis sections at 6/8"。

### F. on-target 诚实表述
18. **done** — Table 1 caption 末尾加 "Two Track A answers declare blind spots on the precise ask (BQ01, BQ03); on-target counts evidenced answers, not completeness."（行值 10/10 (0) 不变）。
19. **done** — Results 第一段末尾加同义短句（BQ01、BQ03、evidenced answers, not completeness）。

### G. 860 relations 工件化 + Data Availability
20. **done** — curl 实测 `http://localhost:8771/api/v1/graph/stats`（Bearer token）返回 HTTP 200，响应体原样落盘 `benchmark-suite/results/graph_stats.json`：node_count 335、edge_count 1671、doc_count 165、kb_count 5、relation_by_reason {shared_tag 730, vector_similar 130} —— 与正文 860 typed relations（730+130）一致。未改动任何字段。
21. **done** — Data Availability 改为 "Every reported number traces to a repository artifact --- JSON results, recorded protocol traces, or live service stats --- in the repository's benchmark-suite results directory and figures directory: …"，列举补入 "the graph statistics snapshot (graph_stats.json)"。

### H. 其它 minor
22. **done** — §2.2 Phase 3 枚举改为 "(search paths, answer, sources, confidence, blind spots)"（与图 2 一致）。
23. **done** — sec4_backmatter "not-found.The" 缺空格已修；全源正则扫描（小写字母+句点+大写开头）无其它缺空格。
24. **done（核验为无操作）** — sec2/sec3 中不存在独立的 "165 parts"：sec2 为 "165 indexed documents --- 9 whole papers and 156 parts"，sec3 同口径。另将 §2.1 的 860 relations 句尾补注 "snapshot in graph_stats.json" 呼应工件。（fig1 HTML 中 "165 parts" chip 不在指令范围内，未动。）
25. **done** — fig2 "MCP Agent Harnesses (14 engines)" 改 "MCP Agent Harnesses"；fig2_architecture.png 已重截。
26. **done** — Table 1 caption 压缩至约 5–6 行内（同时容纳第 18 条新增句）。

## 为满足 4 页硬指标追加的措施（不改变任何数字）

清单 A 的压缩执行后正文仍溢出约 0.7 栏，故追加（全部为措辞/尺寸级，无事实删减）：
- 图宽下调：fig1 0.62→0.50、fig2 0.74→0.56、fig3 0.70→0.52（\textwidth）。
- 三个图 caption 精简（数字保留于正文/表格/图内）；`\textfloatsep`/`\dbltextfloatsep` 收紧至 12pt。
- §3 Demo setup 压缩；§3 重复的视频 URL 删除（abstract 与 Data Availability 各保留一次）；Conclusion 的 Code/video URL 移入 Data Availability（退出正文）。
- 分散微压缩：§1 三段与 bullet、§2.1/2.2/2.3/2.5、§4 Setup/Results/Honesty/Generalizability、Conclusion。结论 booth 体验句被删（booth 流程已由 §3 三个 Scenario 完整承载）。
- 修复过程中一处编辑曾造成 §4 Setup 断句（"…single LLM call. recorded verbatim…"），已修复为 "Every answer is recorded verbatim as a repository artifact; …"。

## 遗留说明
- Competing Interests 位于第 5 页：不在允许清单字面四项内，但属 backmatter 声明（与 GenAI 同层级），非正文内容。
- acmart 模板级 warning（CCS concepts / keywords / ACM reference format mandatory、image descriptions）为投稿前 camera-ready 事项，超出本轮修复范围。
- 图字号随图宽下调而变小（HTML 源为高分辨率 2× 截图，屏检仍清晰）；如担心印刷可读性，可在 camera-ready 阶段对 HTML 源放大字号后重截。
