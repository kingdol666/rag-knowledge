KBS 投稿填写清单（AUTHOR ACTION 六处落点）
================================================
日期：2026-11-16 ｜ 依据：KBS Guide for Authors（sciencedirect.com/journal/
knowledge-based-systems/publish/guide-for-authors，本轮已核验）

以下【方括号】内容必须由作者提供真实值；AI 不得代填。
把真实值发给助手后，助手负责写入并重新编译打包。

--------------------------------------------------------------------
1) 标题页作者块 — main_20p.tex 第 82–87 行附近
--------------------------------------------------------------------
当前占位：
  \author[inst1]{Author Name\corref{cor1}}
  \ead{author@example.com}
  \author[inst1]{Co-author Name}
  \cortext[cor1]{Corresponding author.}
  \affiliation[inst1]{organization={Affiliation Department, University,
  City, Country}, city={City}, country={Country}}

填写模板（可增删作者；每位作者一行；通讯作者保留 \corref+\ead）：
  \author[inst1]{【姓名1 全名】\corref{cor1}}
  \ead{【通讯作者邮箱】}
  \author[inst1]{【姓名2 全名】}
  \author[inst2]{【姓名3 全名】}          % 如有多单位
  \cortext[cor1]{Corresponding author.}
  \affiliation[inst1]{organization={【系/院, 大学全称】},
    city={【城市】}, country={【国家】}}
  \affiliation[inst2]{organization={【第二单位全称, 含完整邮政地址】},
    city={【城市】}, country={【国家】}}

指南要求：作者顺序与投稿系统一致；单位用小写上标字母标注并给
完整邮政地址（含国家）；通讯作者邮箱将随文发表。

--------------------------------------------------------------------
2) CRediT — n_back.tex（"Author 1"/"Author 2" 两行）
--------------------------------------------------------------------
建议角色分配（按实际工作确认后替换姓名；14 角色可多选，用逗号连接）：
  【姓名1】: Conceptualization, Methodology, Software, Validation,
  Investigation, Data curation, Writing – original draft,
  Writing – review & editing, Visualization.
  【姓名2】: Methodology, Validation, Investigation,
  Writing – review & editing.

指南原文要点：通讯作者须用 CRediT 声明共同作者贡献。

--------------------------------------------------------------------
3) 基金 — n_back.tex Funding 段
--------------------------------------------------------------------
若有基金（替换【】）：
  This work was supported by 【基金机构】 (grant number 【编号】).
若无基金（指南官方措辞，直接可用）：
  This research did not receive any specific grant from funding agencies
  in the public, commercial, or not-for-profit sectors.

--------------------------------------------------------------------
4) 致谢 — n_back.tex Acknowledgements 段
--------------------------------------------------------------------
模板（无具体对象可整段删除该小节）：
  The authors thank 【致谢对象/机构】 for 【具体支持】.
（致谢不得早于投稿前写入未参与贡献者；指南无强制内容。）

--------------------------------------------------------------------
5) GenAI 声明版本号 — n_back.tex
--------------------------------------------------------------------
状态：已满足指南要求（声明"作者使用 [工具] 做 [用途]"格式、置于
参考文献前、作者担责）。工具版本号指南未要求，仅当编辑来信索要时
补写，例如在工具名后加 (version 【版本】)。→ 本项投稿前无需动作。

--------------------------------------------------------------------
6) 投稿门户步骤（非稿件内容，提交时在 Editorial Manager 完成）
--------------------------------------------------------------------
- Declaration of Interests：用 Elsevier declarations tool 生成
  .doc/.docx 并在上传页提交（即使稿件内已有声明段）。
- Research data（Option B/C）：选择数据选项；本稿随附
  experiment_data/ 三份 trace CSV + SHA256 + manifest；工业语料
  不可公开的理由已写在 Data Availability 声明中。
- Highlights：单独可编辑文件（highlights.tex 已就绪，5 条 ≤71 字符）。
- 篇幅口径：指南为"建议不超过 20 页双倍行距（含图表）"——针对
  Word 口径、措辞为 preferably；elsarticle 双栏 LaTeX 投稿为标准
  路径。若编辑要求压缩，再按意见处理。
