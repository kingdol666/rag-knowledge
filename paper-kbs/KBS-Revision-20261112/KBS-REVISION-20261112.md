# KBS 双栏稿修订与证据说明（2026-11-12）

## 稿件与期刊规范核查

本稿使用 Elsevier `elsarticle` 的 `5p,twocolumn` 生成双栏审阅排版。Elsevier 官方提供该文档类、单/双栏模板和多种参考文献样式；具体期刊要求须查该刊作者指南。KBS 的 [Guide for Authors](https://www.sciencedirect.com/journal/knowledge-based-systems/publish/guide-for-authors) 本次返回 403，因此无法核实该刊是否要求双栏、具体篇幅、标题层级、公式或参考文献专属样式。本稿采用的双栏及数字编号参考文献是可编辑的工作稿选择，不能据此宣称已满足 KBS 的全部投稿规范。来源：[Elsevier LaTeX instructions](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions)；[elsarticle documentation](https://tug.ctan.org/macros/latex2e/contrib/elsarticle/doc/elsdoc.pdf)。

Elsevier 的通用图件指南建议文章内图件风格一致；普通图中文字以最终尺寸 7 pt 为经验参考而非硬性底线，单栏/双栏宽度示例分别为 90/190 mm。位图建议值为照片 300 dpi、组合图 500 dpi、线图 1000 dpi；出版商同时提醒应以期刊专属要求为准。[Elsevier artwork sizing](https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-sizing)。本稿正文图均为矢量 PDF；同时保留 PNG 预览。源稿使用可编辑 LaTeX 公式、表格及 BibTeX；具体题注、公式编号、标题层级、参考文献规范仍须以 KBS 指南确认。Elsevier 说明 Editorial Manager 的 LaTeX 上传文件应位于同一层，不使用子目录。

## 图表替换清单

| 成稿编号 | 内容及本轮处理 | 可编辑或可复现源 |
|---|---|---|
| 图 1 | 三级管理对象与可选的逐级访问路径；替换原图书馆类比图 | `paper-kbs/figures/build_fig_management_model.py` |
| 图 2 | 服务边界、模块职责与共享状态；去除过期工具数量和服务与管理层一一对应的误导 | `paper-kbs/figures/kbs_revision_20261112/fig1_architecture.drawio` |
| 图 3 | 文档入库及问答流程；区分可选门控、完成但无支持、执行失败 | `paper-kbs/figures/kbs_revision_20261112/fig2_workflow.drawio` |
| 图 4 | 路由、字符串包含、文本量与工具时间；提高印刷字号并使用原始逐题记录 | `paper-kbs/figures/build_fig3_origin.py` 及 `fig3_origin_*.csv` |
| 图 5 | 各配置字符串包含和成本；冻结汇总与后续记录分别标记 | `paper-kbs/figures/build_fig_ladder_optimization.py` 与 `fig_ladder_20261112_snapshot.json` |
| 图 6 | 两个语料上的检索指标对照；统一 Hit@5、Recall@5、MRR@5 和配置名称 | `paper-kbs/figures/build_fig_retrieval_comparison.py` |
| 图 7 | 191 个记录的判别分数分布；保留原矢量图 | `paper-kbs/tex/journal_20p/figs/fig4_inflation.pdf` |

表 1–6 分别为相关工作定位、管理层级、管理功能、访问策略、检索结果及答案检查。所有表格在 LaTeX 源中可编辑。当前图题、图注及表题的逐项原文见同目录的 `KBS-FIGURE-TABLE-CAPTIONS-20261112.md`；以最终生成的论文 PDF 编号为准。

补充材料分为两份：`supplementary.pdf` 包含图 S1–S5 和新增表 S9–S10；`supplementary-inventory.pdf` 保留详细实验记录和表 S1–S8。历史路由记录注明其旧协议及新发现的金标回退限制，正文比较以当前稿件为准。

## 关键内容和结果修订

1. 系统结构区分浏览器/Nuxt、FastAPI/MinerU、MCP 工具层、共享文件与索引。基于内容的分类是 Agent 工作流决策；不同操作更新不同状态；索引与门控并非所有路径自动执行。当前检索指令与历史实验配置分别说明。
2. A1b 是逐库合并后使用 reference-mode Laya judge 的平面配置；A2 才跳过判别器。A0h 与 A1b、PD 均改变多个组件，不能把差异单独归因于层级导航。A0、A3、A1b 的候选引用定位代码可能以 gold domain 回退；历史 trace 不足以量化触发次数和偏差，配对 p 值仅描述记录，不证明部署优势。A3 还存在跨评测范围候选。
3. 路由卡描述与部分题目包含相同标题或类别词；A3 的未记录回退仍可使用完整描述。72/72 对 37/72 是脚本路由结果，不能解释成独立 Agent 选库准确率或描述消融的因果效应。
4. 11 月 11 日冻结汇总：A0/A0f/A0h/PD/A1b/A2/A3/read-all 的 gold-string 命中依次为 37/45/52/46/39/25/33/72（每组 72 题）；不同组实际运行日期不尽相同。后续记录中前七组为 39/44/51/45/39/25/25；A3 在前六组之后补入，49/72 路由正确，13/72 首候选为空，23/72 证据包为空，原因未确定。后续 read-all 截至核查仍不完整，故没有显示完整命中率。两轮使用相同问题，不构成独立测试集；历史代码哈希与完整 judge 输入未在记录中逐行固定。图中的置信区间和成本仅对应冻结汇总。
5. 全文统一“总工具调用”和“trace-recorded 文本字节”，后者可能重复计数，既不是独立内容字节，也不是 LLM token 或判别器真实输入。机械 read-all 的 72/72 只是全量文本中的字符串检查，未生成答案，不是仔细阅读文档的 Agent 基线。
6. 原复现报告对部分双侧 McNemar p 值多乘了 2；本稿未引用该报告的跨轮 p 值。正文列出的组间 p 值为未校正的探索性比较；没有完整预注册的多重比较族，因此撤去原 Holm 结论。
7. 摘要、贡献、讨论和结论保留混合检索在工业语料落后 BM25、验证器排序损失、证据支持和语义答案质量未验证等结果。现有证据支持对系统和局部失败模式的描述，不足以证明总体检索优越性或系统创新性已达到录用标准。

## 待作者或期刊确认

- 用真实姓名、作者顺序、机构、通讯邮箱、CRediT、资金、利益冲突及致谢替换或确认占位信息；核实 AI 使用声明和前期 demo 的发表状态及增量。
- 获取可访问的 KBS 最新作者指南，核对版式、篇幅、标题、图表、公式、文献及提交文件类型；当前 24 页双栏 PDF 是本地预览。
- 在消除 gold-domain 回退后，以独立构造的问题和固定语料重跑同预算、单因素对照；完成真实 Agent 全文细读基线、语义答案及引用支持评价、重复运行和预先定义的统计比较。
- 本版仅用于审阅，不代表已达到期刊接收或投稿完成状态。BibTeX 仍有五条缺少页码警告，应按文献的实际类型核查。
