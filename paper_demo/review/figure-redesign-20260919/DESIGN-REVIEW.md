# 配图重设计依据与内容约束

日期：2026-09-19。状态：**方向初稿，尚未替换论文正式配图**。

## 检查范围
- 已通读 `paper_demo/tex/main.tex` 及摘要、引言、系统、演示、评估、结论/披露的全部章节；检查已编译的 5 页 PDF 和实际被引用的三张图片。
- 当前三图：`fig1_protocols.png`、`fig2_architecture_v2.png`、`fig3_answers.png`，不是目录中其他历史备选图。
- DeepRead 使用下载的 arXiv v3（2026-02-12）PDF，重点阅读方法、实验、Figure 1/2，并实际渲染查看第 1/3 页。不能把 DeepRead 自动当作 CIKM Demo 已发表论文；其元数据带占位 DOI，PDF 说明为 preview。
- 现有 FIGURE-STYLE-GUIDE.md 明示颜色/字体是从文本推断的，而且把 2026 预印本一并称为 published。本轮不沿用这种证据等级：以实际 PDF 图形和可核验的会议记录为依据。

## 原图的可重复观察

PyMuPDF 从现有 PDF 读取图片放置宽度：Fig1 353.0 pt、Fig2 393.4 pt、Fig3 363.2 pt。原 HTML 画布宽均为 2300 CSS px。

- Fig1 的 20px 文字缩放后约 3.07pt。
- Fig2 的 18–20px 说明缩放后约 3.08–3.42pt。
- Fig3 的 20–23px 说明缩放后约 3.16–3.63pt。

算法：CSS 字号 × PDF 中的图片宽度 / HTML 画布宽度。两倍像素 PNG 不能提升这些文字的物理字号。

## 绘制方案

采用纯 SVG（可选 HTML 内联展示），不用生成式位图绘制科学文字、公式、数值或控制流。已检测 gpt-image-2 skill，环境配置了 gpt-image-2.5；本轮未调用付费生图接口，未将稿件传给该第三方生图服务。

三种架构方向各自改变信息布局，不仅换色：
A. 横向过程与文档结构图；B. 离线/在线泳道与条件分支；C. 共享证据库与模块化协议。
另提供 Fig1/3 内容重构初稿，在方向确定后统一视觉系统。

印刷目标：全双栏约 178mm，1000 SVG 单位宽，正文标签建议 16px（约 8.1pt），最低 14px（约 7.1pt）。这是本次设计目标，不是声称 CIKM 官方规定最低字号。最终插入时若再次缩小到 0.7textwidth，必须重新检查物理字号。

## 各图只承担一个任务

### Figure 1：问题与方法差别
- 同一 NISQ 问题；平面固定块 vs 可定位的文档部分与章节。
- Dense baseline 的 800 字符、top-2、4000 字符窗限定为**本次复现配置**。
- “来源没有记录”限定为该 harness 的日志，不是 dense RAG 的必然缺陷。
- QDCVR 通过内容读取与 gate 后附可核查引用；不通过则才进入 fallback。
- 不将概念示意当作 verbatim 实验回答。

### Figure 2：真实数据流与控制流
- 离线：PDF → MinerU → 章节化 Markdown / 分片 → 内容分类 → 标签与索引。
- 三个存储对象：ChromaDB/BGE-M3、Neo4j、YAML 审计树。不要暗示图检索是本次 benchmark 的主路径。
- 接入面区分 Web、CLI、MCP；41 kb_* 是 MCP 工具数量，不能从论文的宽泛表达推断所有 Web 请求都穿过 MCP。
- 在线：rewrite → vector-first recall → read → 0–8 gate，≥6 为 pass。
- pass → cited five-section answer；fail → librarian → 新候选读取与再次判定；搜寻后仍无通过证据 → not-found。
- 五段答案：search paths / answer / sources / confidence / blind spots。
- experience lifecycle 是附属能力，不画成所有答案必须经过的最后一步。

### Figure 3：可审计案例而非营销结论
- Transformer 案例的三个轨道：A 的章节证据与当前记录声明的未读位置编码公式/训练细节；B 的完整公式表述与自报文件名；C 的证据不足与 abstention。
- 重要数据一致性修正：当前 skill_track_answers.json 的 BQ01 gate=8；对应读取为 part 1/2、2/2。原图 gate=7 与未读注意力公式来自 archive-20260917-10000chunk 归档，该归档引用 part 11/26、25/26。草图只使用当前 run，不拼接。
- 不画“C 故意/必然错误”；其 abstention 本身属于合理保守行为。
- chunking 是正文所称 plausible explanation，不能在图上升级为已证实的唯一因果。
- trap 展示 query → BERT near miss 1/8 → librarian scope → NOT_FOUND，而不是重复一大段回答文本。
- 改写必须标明 paraphrased，不冒充 recorded verbatim。
- 不比较 A 的 retrieval+read 时间和 B/C 的 end-to-end 时间；图中不加误导性速度柱状图。

## 正式替换时的建议图注（待选定风格后再修改 TeX）

**Figure 1. Retrieval and evidence contracts.** Under the reproduced dense baseline, fixed-size chunks are packed for a single generation call; chunk provenance is not retained by this harness. QDCVR retrieves section-addressed evidence, reads candidate text, and applies an explicit content gate. A passing candidate supports a cited answer; otherwise the protocol invokes the librarian and may return a scoped not-found report. The NISQ example is paraphrased.

**Figure 2. QDCVR platform and conditional retrieval protocol.** Offline ingestion preserves section addresses, classifies documents by content, and indexes tagged parts. Online retrieval reads recalled candidates before applying the content gate. Passing evidence yields a five-section cited answer; failed recall invokes a librarian search and re-verification. If no evidence passes after the search, the output names the search scope, near miss, and reason for not answering. Optional platform capabilities are distinguished from the benchmark path.

**Figure 3. Recorded behavior on an in-corpus question and an out-of-corpus probe.** Paraphrased Transformer answers compare section-addressed evidence and declared unread positional-encoding and training details (A), a self-reported source filename (B), and abstention under the reproduced dense baseline (C). The lower trace illustrates a not-found report after rejecting a BERT near miss for a fictitious-paper query. This case illustrates provenance differences, not a general accuracy ranking.

## 可核查外部来源
- DeepRead v3: `https://arxiv.org/abs/2602.05014v3` 与 `https://arxiv.org/html/2602.05014v3`。
- CIKM 2026 Demo CFP: `https://cikm2026.diag.uniroma1.it/demonstration-papers/`。要求 sigconf、4 页正文（含附录与致谢），披露/参考文献可另计；没有唯一的官方配色或图形风格。
- 已发表 CIKM Demo 的实际视觉检查由独立参考资料检查记录补充。

## 当前交付边界
原图、原 TeX、原 PDF 不改动。先查看真实方向稿并确定方向，再做三图统一、正式 PDF 导出、TeX 图注同步与四页正文排版验证。不能把本轮方向稿称为已经完成投稿版替换。


## 追加：记录一致性检查
独立核对还发现 BQ02（NISQ）的当前 `skill_track_answers.json` 与 `track_a_e2e_spot.json` 均为 8/8，而正文 Scenario 2 与旧图写 7/8。方向稿 Figure 1 因此只展示通用阈值 ≥6，不复制该存在冲突的实例分数。具体字段与当前/归档记录比较见 `../../figures/redesign-20260919/SOURCE-AUDIT.md`。

Track C 的“parsing / Table 4”内容描述来自该轨道生成的回答，并非独立保存的 evidence window；`evidence_docs=[]`。新图明确归因为“C reports”，不得声称已直接检查输入窗口。实验 gate 分值标为 LLM self-assessments，而非正确率。
