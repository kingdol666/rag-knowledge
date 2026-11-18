# KBS 首次投稿核对单

适用于 Research Article。本轮直连期刊指南返回 403。期刊专属要求依据 2026-03-04 公开打印副本（第 3–4、9–11 页）和仓库内 2026-10-12 核对记录，上传、数据和 AI 政策另查 Elsevier 当前通用说明。实际上传项目以 Editorial Manager 当时的界面为准。 [KBS 作者指南](https://www.sciencedirect.com/journal/knowledge-based-systems/publish/guide-for-authors) [公开打印副本节选](https://www.studypool.com/discuss/82267917/scopus-article-writing-knowledge-system-journal) [仓库核对记录](../../notes/kbs-requirements-compliance-2026-10-12.md)

## 稿件与附件

- 正文摘要最多 250 个词，提供 1–7 个英文关键词。Research Article 推荐不超过 20 页双倍行距，页数包括图表。当前双栏 LaTeX 样稿采用期刊排版，按双倍行距计算篇幅应使用同源的 `main_20p_review.tex`。
- KBS 对 Word 稿要求单栏，允许 LaTeX 稿采用双栏。提供可编辑源文件。若由 Editorial Manager 编译 LaTeX，正文、图件和参考文献文件放在同一层，保留 `.bbl`，并检查生成的审稿 PDF。Overleaf 工程包括子目录，适用于本地和 Overleaf 编译。 [Elsevier LaTeX 上传说明](https://www.elsevier.support/publishing/answer/how-to-submit-a-latex-file-in-editorial-manager)
- KBS 鼓励提供独立的 Highlights 文件。`highlights.docx` 包含 5 条，每条最多 85 个字符（含空格）。 [Elsevier Highlights 指南](https://www.elsevier.com/researcher/author/tools-and-resources/highlights)
- 数据声明列出可分享的实验记录及受限源材料的具体范围。随稿上传补充材料和可共享记录，并为任何已经公开存档的数据提供实际可访问的链接。 [Elsevier 研究数据指南](https://www.elsevier.com/en-in/researcher/author/tools-and-resources/research-data/data-guidelines)
- 生成式 AI 声明置于参考文献前，写明工具和用途。采用 AI 生成或修改的解释性图件应在对应图注和总声明中披露。纳入研究方法的 AI 使用应在方法中写明工具和版本等复现信息。 [Elsevier 生成式 AI 政策](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals)

## 由作者确认或补齐

1. **作者页**。KBS 采用单匿名评审，作者信息随正文提供。在 `main_20p.tex` 填写真实作者姓名及顺序、工作完成时的单位及完整邮政地址（含国家）、通讯作者和联系方式。投稿系统中的名单保持一致。
2. **作者贡献与基金**。在 `n_back.tex` 逐人确认 CRediT 角色，填写真实基金机构和项目编号，或确认无专项资助。致谢如适用，由作者确认措辞。
3. **利益冲突声明**。确认所有作者的披露内容，使用投稿页面提供的 Elsevier declarations tool 生成并上传 `.doc` 或 `.docx`。正文声明与上传文件保持一致。
4. **投稿批准**。全体作者审批稿件、确认原创性和一稿一投，并核实同一系统的 CIKM Demo 草稿是否曾投递或发表，再按实际状态向编辑说明两稿关系。使用 `cover_letter.txt` 前移除草稿提示并填写实际签名。 [Elsevier 出版伦理](https://www.elsevier.com/about/policies-and-standards/publishing-ethics)
5. **图稿披露**。图 1–3 的矢量文件由设计原型重建。核实每张原型是否使用生成式 AI 及其工具，再补齐对应图注和参考文献前的总声明。

[Knowledge-Based Systems 投稿系统](https://www.editorialmanager.com/knosys/default2.aspx)
