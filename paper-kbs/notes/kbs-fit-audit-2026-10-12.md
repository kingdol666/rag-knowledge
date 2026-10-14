# KBS 投稿适配性审计（2026-10-12）

用两篇**已发表的 KBS 论文作者版 PDF** 对当前稿子做逐项实测对比，回答一个问题：**这稿子现在满足 KBS 的发表要求吗？**

- 范文① **LLM-based IR-system for Bank Supervisors**，Knowledge-Based Systems **310** (2025) 112914，DOI `10.1016/j.knosys.2024.112914`，arXiv `2508.02945`。选它的理由：与本文最同类——真实机构部署的检索系统 + 真实语料 + MAP/MRR + 与 BM25/BERT 基线对比。
- 范文② **SurveyAgent-HKA**，Knowledge-Based Systems 2026，arXiv `2609.05938`。选它的理由：KBS 另一主流形态（多智能体 LLM 系统），提供篇幅上限参照。

本地文件：`paper-kbs/notes/kbs-exemplars/`（两篇 PDF + `pdftotext -layout` 全文 + 渲染页 PNG + `analyze_pdf.py` 指纹脚本）。
复现命令：

```powershell
$py = 'backend\.venv\Scripts\python.exe'      # pypdf 6.14.2 可用；fitz/pymupdf 未安装
& $py paper-kbs\notes\kbs-exemplars\analyze_pdf.py <pdf...>
# 渲染：C:\texlive\2025\bin\windows\pdftoppm.exe -png -r 90 -f <page> -l <page> <pdf> <out>
# 取文：D:\Git\mingw64\bin\pdftotext.exe -layout <pdf> <txt>
```

## 1 实测硬指标

| 指标 | 范文① 银行 IR | 范文② 多智能体 | **本稿 main2.pdf** | 判定 |
|---|---|---|---|---|
| 页数 | 19 | 38 | **76** | 约 4× / 2× |
| 正文词数（提取） | 10,281 | 20,004 | **25,544** | 2.5× / 1.3× |
| 每页词密度 | 541 | 526 | **336** | 版式偏大（12pt vs 范文约 10pt） |
| 一级章节 | 8 | 7 | **11** | 偏多但可接受 |
| 图 | 6 | 12 | 9 | 正常 |
| 表 | **5** | 0 | **19** | 明显超载 |
| 参考文献 | ~36（作者-年制） | 79（编号制） | 59（编号制） | 正常 |
| 编号公式行 | 8 | 1 | 0 | 系统类论文可不含公式 |

**页数结论有一半是版式而非内容**：本稿用 `elsarticle` preprint **12pt**，范文用同模板约 **10pt**。仅换字号，76 页 → 约 45 页；叠加正在进行的压缩（17,891 → ≈13,000 词），预期落到 **25–30 页**，进入 KBS 正常区间。

## 2 写作架构对比

- 范文①：`1 Introduction` / `2 Related work` / `3 Data` / `4 Methodology & Experimental Setup` / `5 Evaluation methodology`（5.1 metrics、5.2 validation） / `6 Results & Discussion` / `7 Limitations & Future Work` / `8 Conclusion`
- 范文②：`1 Introduction` / `2 Related work` / `3 Methodology`（3.1 问题形式化 → 3.2 总体架构 → 3.3 各模块） / `4 Experiments`（baselines/dataset/metrics/implementation） / `5 Results`（5.1 总体 → 5.2–5.6 分项 → 5.7 成本效率 → **5.8 Ablation study**） / `6 Discussion` / `7 Conclusion`
- 本稿：`1 Introduction` / `2 Related work` / `3 System overview` / `4 Knowledge acquisition` / `5 Knowledge organization` / `6 Content-verified retrieval` / `7 Implementation` / `8 Evaluation` / `9 Discussion` / `10 Threats to validity` / `11 Conclusion`

判定：架构同源、判断一致。差异有三处：
1. 系统设计拆成 §3/§4/§5 三章 + §7 实现章（范文是 1 章 Method 内嵌子节）。**可接受**（系统论文常见），但这是页数膨胀主因之一：每章只应保留"设计决策 + 证据"。
2. `10 Threats to validity` 独立成章。范文①同样把局限独立成 `7. Limitations`，**因此不构成偏离**，无需降级（此前一度考虑降为子节，按范文证据撤回该建议）。
3. 范文②设有专门的 **`5.8 Ablation study`**，与 KBS 的退稿偏好一致（"缺少隔离知识组件的消融"是四大常见早期退稿理由之一）。本稿的 E-A 关闸消融、E-B 分区消融必须在 §8 中占据显眼位置。

## 3 绘图风格对比

- 范文：小尺寸、灰度/低饱和 matplotlib 折线图，caption 统一 `Figure N: ...`，正文内联（见 `kbs-exemplars/bankir_p7-07.png`）。
- 本稿：Okabe-Ito 色盲安全配色、300 dpi、框图+箭头架构图，尺寸更大、信息密度更高。

判定：**本稿绘图规范高于范文，无需向范文靠拢**。KBS 的实质要求只有三条：灰度可打印、以单独高清文件提交、单文件 < 10 MB。真正的问题不是图而是**表**：19 张表 ≈ 每 4 页一张，范文①整篇仅 5 张；且多张表 caption 是整段说明（Table 1/11/12/16）。

## 4 KBS 要求逐条核对

| 要求 | 状态 | 依据 |
|---|---|---|
| 知识驱动贡献（非"把 X 应用到 Y"） | ✅ | 内容治理三承诺 + 契约式验证；§1 贡献 C1–C6 |
| 隔离知识组件的消融 | ✅ 待写入 | E-A（关闸）+ E-B（分区）+ 裁决角色分解（fusion 0.94 / re-rank 0.44 / filter 0.94） |
| 真实系统与语料 | ✅ | 5 库 322 文档 + 100 篇 arXiv 采集 + 6 场景跨语言 |
| 负面结果/失败分析 | ✅ 加分 | 21/100 未可检索、同域打分膨胀 p=0.26、gate 零过滤力 |
| Data availability | ✅ | `n_back.tex` |
| Ethics statement | ✅ | `n_back.tex` |
| CRediT / competing interest / funding / GenAI 声明 | ✅ 占位 | 作者真实信息仍为 `AUTHOR ACTION` |
| Highlights（≤85 字符 ×5） | ✅ | `highlights.tex` |
| 独立高清图文件 | ⚠️ 待打包 | `tex/figs/fig1..fig9.pdf` 已具备，投稿时另附 |
| Cover letter / suggested reviewers / ORCID | ❌ 未做 | 投稿前必须补 |
| 篇幅（≈6–9k 词惯例，无硬性上限） | ⚠️ 超 | 25.5k → 目标 13k |
| 表数量 | ❌ 超 | 19 → 目标 ≈9 |
| 语言门槛（triage 阶段即拒） | ⚠️ 待校 | 需母语级润色或语言编辑证明 |

## 5 结论与处置清单

**结论：内容层面满足 KBS，形式层面（篇幅 + 表量）当前不满足，且全部可控。**

按优先级：
1. 🔴 **压缩正文**至 ≈13,000 词（进行中：§3 与 §5 已完成，§1/§2/§4/§6 在跑）；压缩只删冗余，数字/警示语/标签/浮动体一律不动。
2. 🔴 **表 19 → ≈9**：把采集审计、分区消融、27 次稳定性、失败目录等诊断表移入附录或随代码仓库发布（KBS 允许 supplementary material）。
3. 🟡 **一级章节 11 → 10**：可选的 §3/§4/§5 合并（仅当页数仍超）；Threats 保持独立章（与范文①一致）。
4. 🟡 **表 caption 瘦身**：整段式 caption 压到 2–3 行，细节移入正文或附录。
5. 🔴 **作者信息**：姓名/单位/ORCID/CRediT/基金（`AUTHOR ACTION` 占位，投稿阻塞项）。
6. 🟢 删除零引用 bib 条目（`comaikg`、`rrpdg`；以最终引用审计为准）。
7. 🟡 投稿包：cover letter（突出知识驱动贡献 + 消融 + 负面结果）、suggested reviewers、单独图文件、ORCID。

**预期达标形态**：约 25–30 页 / 13k 词 / 9 图 9 表，与范文①（19 页 / 10.3k 词 / 6 图 5 表）同量级，属"投得出去、审稿人不会一眼嫌长"。
