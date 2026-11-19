# 五席盲审终审与修复记录（2026-11-19）

评审协议：academic-paper-reviewer 五席（期刊契合 EIC / 方法学 R1 / 领域专家 R2 /
跨学科视角 R3 / 魔鬼代言人 DA），角色分离并行独立评审，编辑综合裁决。

## 裁决

**Minor–Major Revision 之间 → 修复后达到初稿投递标准。** R1/R2/R3 均 Minor；
EIC Major（证据泛化性）；DA 三条 CRITICAL 经裁决：1 条可数拒衡（见下）、
2 条属"需新实验"的已披露限制（开发者出题/多跑分散，在 Threats 中如实限定）。

## 已实施修复（16 处编辑，未跑任何新实验，全部基于既有数据与措辞校准）

| # | 来源 | 修复 |
|---|---|---|
| 1 | DA-C1/EIC-1 | **预算匹配对照入正文**：A0h vs A0f（两臂均 ~300 kB）frozen 52–45、followup 51–44，各 7/0 零逆转（p=0.016，由 supp_traces_frozen.csv 逐题重算）——直接回应"52 vs 37 只是读得多"的最强反方论点 |
| 2 | R1-1 | Threats 补偏倚方向句：gold-domain 解引用偏袒 reference-mode 臂（A0/A1b/A3），A0h-over-A0f 对照对该路径保守 |
| 3 | EIC-5 | 摘要重构：主打对比前置、预算匹配句、词数 237（≤250），去运营日志腔 |
| 4 | R1-2/DA | 摘要与结论补"developer-authored questions"与"under recorded corpus changes"限定 |
| 5 | EIC-6 | RQ4 改写：明确阈值效应未被观测（191 分全过 0.5 阈） |
| 6 | EIC-8/R2-6 | 贡献4 锐化为"server-side gate with separated admission and ordering" |
| 7 | R2-1 | 新增 RAG 综述引用（Gao et al. 2023, arXiv:2005.11401）于 §1/§2 |
| 8 | R2-2 | 新增联邦检索综述（Shokouhi 2007, FnTIR）+ catalogue 路由 ↔ 选择/合并两子问题映射句 |
| 9 | R2-5 | Gap 节补 2 句预先防御（curation/ECM 治理的是状态本身，未研究"状态↔证据访问"耦合） |
| 10 | R3-1/7 | MCP 首现全展开（摘要+引言）；HMRS 展开提前 |
| 11 | R3-2/R2-7 | route card 摘要+E3 首现处释义（"pairing name with description"） |
| 12 | R3-3 | E5 加臂名解码句（f/h/b/PD 助记）+ 指向 Table S12 |
| 13 | R2-3 | §3.1 加 collection≡library(knowledge base) 映射定义句 |
| 14 | R2-4/R3-6 | chunk=存储 segment 的对齐句；Laya 首现定义（平台本地段落评分器） |
| 15 | R3-8 | BQ04 加 "(Table S7)" 指针 |
| 16 | — | 结论补预算匹配对照与语料变化限定 |

## 未采纳（需新实验，已在 Threats 如实披露）

外部基准臂、多跑分散度、held-out 非开发者问题集、阈值生效扫描、
gold-document-only containment 分臂报告、A3 fallback 计数、全生命周期覆盖。
这些是审稿人可能追问的后续实验方向，初稿以限制披露方式处理。

## 验证链

- 编译：17 页 / 0 错误 / 0 未定义 / 0 overfull；评审版 42 页 / 0 错误
- 视觉门：visual-judge 全 17 页 PASS（两处疑似异常均为非缺陷）
- 附件一致性：S1–S8→inventory PDF（42 页）、S9–S17→supplementary PDF（7 页）、
  27 项 CSV↔正文数字对账通过（52/45/37/46/39/25、discordant 四组、Wilson、
  McNemar、路由 72/72+37、体积/成本口径）

## 附：paper-audit 终检轮（同日）

脚本层 217 项 → 裁决后 3 项真内核修复，其余为假信号（Critical“无 Methods 章”=
系统型论文结构误判；121 条拆句建议多为 LaTeX 表格行误切；@dpr/@budur“缺 author”
=重音命令误解析；破折号问题全在注释行；IEEE 风格建议不适用于 elsarticle-num）。

| 真问题 | 修复 |
|---|---|
| Shokouhi 条目事实错误（2007/独著/Vol.1 → 实为 **Shokouhi & Si, 2011, FnTIR 5(1), 1–102, DOI 10.1561/1500000010**，经 ACM DL/DBLP 核验） | refs.bib 更正 + 引用键同步 n2 |
| Gao RAG 综述缺 DOI | 补 10.48550/arXiv.2005.11401 |
| 结论缺展望句（脚本 Major） | 补“one installation / developer-authored / lexical containment”三重限定 + 独立问题集/多部署/语义支持验证为下一步 |

修后编译：17 页 / 0 错误 / 0 未定义 / 0 overfull。

## 附 2：re-review 复核终裁轮（同日）

8/8 既往修复验证在位；写作逻辑/编排/表述三评估全过；**裁决=满足初稿提交质量、无阻断项**。
顺手清掉 4 个校样级瑕疵：KB→kB 单位统一（3 处，保留 n7 合法 KB agent）、
对比臂统一命名 read-all（mechanical full scan/full-read comparator 消除）、
normalization→normalisation（英式统一）、图注 A0f/PD 前向引用改中性表述。
修后 17 页 / 0 错误 / 0 未定义 / 0 overfull，7 项探针全入 PDF。
