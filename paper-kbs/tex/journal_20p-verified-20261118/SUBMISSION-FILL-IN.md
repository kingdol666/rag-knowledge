# KBS 首次投稿核对单

适用于 Research Article。2026-11-19 已直接读取 KBS 官网作者指南及 Elsevier 通用 AI 政策。期刊专属要求以 [KBS 作者指南](https://www.sciencedirect.com/journal/knowledge-based-systems/publish/guide-for-authors) 为准，实际上传项目以 Editorial Manager 当时的界面为准。

## 稿件与附件

- 正文摘要最多 250 个词，提供 1–7 个英文关键词。Research Article 推荐不超过 20 页双倍行距，页数包括图表。当前双栏 LaTeX 样稿采用期刊排版，按双倍行距计算篇幅应使用同源的 `main_20p_review.tex`。
- KBS 对 Word 稿要求单栏，允许 LaTeX 稿采用双栏。提供可编辑源文件。若由 Editorial Manager 编译 LaTeX，正文、图件和参考文献文件放在同一层，保留 `.bbl`，并检查生成的审稿 PDF。Overleaf 工程包括子目录，适用于本地和 Overleaf 编译。 [Elsevier LaTeX 上传说明](https://www.elsevier.support/publishing/answer/how-to-submit-a-latex-file-in-editorial-manager)
- KBS 鼓励提供独立的 Highlights 文件。`highlights_november.docx` 包含 5 条，每条最多 85 个字符（含空格）。 [Elsevier Highlights 指南](https://www.elsevier.com/researcher/author/tools-and-resources/highlights)
- KBS 采用研究数据指南 Option C：在适当存储库归档可共享的研究数据，并在投稿时提供数据集链接；无法分享的部分应解释原因。正文数据声明区分可复算导出、未留存的完整证据包与受限服务记录。源码 ZIP 中附带数据并不等于已经完成数据存储库归档，项目 GitHub 链接也不等于数据集永久链接。 [Elsevier 研究数据指南](https://www.elsevier.com/en-in/researcher/author/tools-and-resources/research-data/data-guidelines)
- 现行 KBS 指南允许生成式 AI 辅助制作流程图、概念图等解释性图片，以及用可复现方法直接从数据生成的可视化；不得据此生成或修改并非直接获取的原始观测或实验图像（研究方法中的明确例外另行说明）。若使用 AI 工具创作稿中图片，须在相应图注及参考文献前的通用 AI 声明中披露。作者仍须核实真实性、原创性及版权。 [Elsevier 生成式 AI 政策](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals)

## 由作者确认或补齐

1. **作者页**。KBS 采用单匿名评审，作者信息随正文提供。在 `main_20p.tex` 填写真实作者姓名及顺序、工作完成时的单位及完整邮政地址（含国家）、通讯作者和联系方式。投稿系统中的名单保持一致。
2. **作者贡献与基金**。在 `n_back.tex` 逐人确认 CRediT 角色，填写真实基金机构和项目编号，或确认无专项资助。致谢如适用，由作者确认措辞。
3. **利益冲突声明**。确认所有作者的披露内容，使用投稿页面提供的 Elsevier declarations tool 生成并上传 `.doc` 或 `.docx`。正文声明与上传文件保持一致。
4. **投稿批准**。全体作者审批稿件、确认原创性和一稿一投，并核实同一系统的 CIKM Demo 草稿是否曾投递或发表，再按实际状态向编辑说明两稿关系。如另附投稿信，应签署并按实际状态说明与既有工作的关系。 [Elsevier 出版伦理](https://www.elsevier.com/about/policies-and-standards/publishing-ethics)
5. **图稿来源**。逐图记录最终图稿所用素材、工具和用途。尤其核实图 1–3 的 AI 概念原型是否进入最终成图；如确实用 AI 制作了稿中图片，在各对应图注和通用声明中填写真实工具及用途。对照现行图件政策检查原创性、权限、可复现性及对比面板的可读性；不得把概念原型的使用一概写成最终出图，也不得以通用披露替代应有的逐图披露。

[Knowledge-Based Systems 投稿系统](https://www.editorialmanager.com/knosys/default2.aspx)
