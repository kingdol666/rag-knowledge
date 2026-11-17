# 实验章节写作纲要（EXPERIMENT-SECTION-OUTLINE，2026-11-13）

> **性质**：实验章（Section "Evaluation"）的重写纲要，供用户确认后逐条落地。
> **输入**：①真实系统实验结果——`PAPER-RESULTS-20261113.md`（三族整理版）与
> `EXPERIMENT-RESULTS-MASTER.md` 冻结值；②论文证据需求——摘要 6 组数字主张、
> 4 条 contributions、RQ1–RQ5；③纪律——KBS-REVISION-20261112.md 保守化纪律、
> 主索引红线 #6（禁 RAG 向量对比）、未校正探索性措辞、配对方向显式、每句可回溯。
> **验收**：§6 验收门 A1–A6，全过后才交付。

---

## 1. 证据需求分析（论文主张 → 需要什么证据 → 现状判定）

| # | 论文主张（出处） | 所需证据 | 现有节 | 判定 |
|---|---|---|---|---|
| N1 | 管理模型三级可实现且状态可审计（摘要句1、贡献1） | 入库/组织/生命周期实测 | E1, E2 | ✅ 满足 |
| N2 | 描述层决定集合选择（摘要 72/72 vs 37/72；贡献2） | 有无描述的配对消融 | E2b | ⚠️ 数字在，但**未框成"描述层消融"**——三族之一的第一族需要一个显式框架句 |
| N3 | 逐级+内容组织优于平面/无导航（摘要 52/72 > 46/72 > 39/72；贡献3后半） | 内容层配置对比+自消融 | E4 | ✅ 满足（BM25 floor 已补） |
| N4 | 回答可溯源且底座决定溯源形态（60/60；贡献3前半） | 答案矩阵 + 组织方式对比 | E5 | ⚠️ 数字在，但"组织产生可溯源"论点（P 9/10 vs C 2/10 标记）**在结论无回响** |
| N5 | verdict 只可过滤不可排序（摘要 0.94→0.44；贡献4） | 同池角色诊断 | E6 | ✅ 满足 |
| N6 | 部署层契约与诚实拒答（RQ5） | 部署臂+诚实性电池+案例 | E5b, E5案例 | ✅ 满足（案例 8/8 在正文，结论无回响） |
| N7 | RQ3 "compares ... on document recall, **ranking** and retrieval cost" | — | — | ❌ **RQ3 措辞过期**：ranking 证据已随旧配置表移除，E4 量的是 containment+成本 |
| N8 | 章节编号 E2b/E5b 历史残留 | — | — | ⚠️ 投稿观感：建议重编号为连续 E1–E9 |

**缺口结论**：证据本体已齐（三族冻结值全部落位）；待办是**框架显式化**（N2/G2）、
**导览层**（章首 evidence-family map）、**措辞过期**（N7/G4）、**回响缺口**（N4/N6 在结论）、
**编号观感**（N8/G1）。

## 2. 目标架构（重编号 E1–E9；语义 label 不变，只改显示标题与汇总表行）

| 新号 | 旧号 | 标题 | 对位 | 角色（一句话） |
|---|---|---|---|---|
| — | — | Evaluation 总起 + Setup | — | 四语料+度量+控制；**新增三族导览句**（family map） |
| E1 | E1 | Acquisition and parsing | RQ1/管理层 | 入库可用、缺陷可测（79/21、0.875/1.0/1.0） |
| E2 | E2 | Organisation, consistency, and management operations | RQ1/管理层 | 三源一致性、rename 缺陷、生命周期 16 场景 |
| **E3** | E2b | **Paired route-card audit: the description-layer ablation** | **族①/RQ2** | 有无描述的配对消融：72/72 vs 37/72，McNemar p=5.82e-11；诚实限定保留 |
| E4 | E3 | Operational knowledge and automated distillation | RQ1/管理层 | 经验入库可检索（13 草稿、1 场景，证据近零如实报） |
| **E5** | E4 | **Content-layer configuration comparison** | **族②/RQ2+RQ3** | 八臂 containment：A0h 52/72 vs PD 46/72（7:1）vs A1b 39/72（13:0）；A2/A3 消融；BM25 floor 60%；R3 复现；归因 |
| **E6** | E5 | **Answer and trace checks, abstention and cost** | **族③/RQ5** | 30-cell 矩阵（P/F/C）、组织产生溯源标记（9/10 vs 2/10）、8/8 双 harness 案例、拒答 |
| E7 | E5b | Deployment-layer system arms and honesty contracts | 族③/RQ5 | 部署 3×3、S2 传输缺陷+修复、18 臂诚实性电池零编造 |
| E8 | E6 | When the verifier fails | RQ4/组件诊断 | 191 分数、排序 0.44 vs 融合序 0.94、NLI 复plays、阈值未激活 |
| **E9** | E7+E8 | **Operational boundaries: stability, concurrency, gate and scope ablations** | 边界 | 27-cell 稳定性、并发扫描、门控/范围消融——合并为单节两段 |

**不重编号的备选**：维持 E2b/E5b 现状（零 churn，观感略逊）。**建议采用重编号**：
显示标题改动约 8 处 + S9/S10 行标签约 10 处 + n8a 总起段，成本小、观感收益大。

## 3. Claim→Evidence→Section 映射总表（验收 A4 的对账基准）

| Claim（安全句式） | 冻结证据 | 正文位置 | 回响位置（≤3 次纪律） |
|---|---|---|---|
| 路由：有描述 72/72 vs name-only 37/72 | s4_traces_final | E3 | 摘要✓、贡献2✓、结论✓（现状已 3 处，封顶） |
| containment：A0h 52/72 > PD 46/72 > A1b 39/72 | s6_stats | E5 | 摘要✓、贡献3✓、结论✓（封顶） |
| A0h vs A1b 13:0（p=0.00024）；A0h vs PD 7:1（p=0.0703 显式方向） | traces 配对 | E5 | 摘要（无比例简写）✓、结论✓ |
| BM25 词汇内容基线 60.0%（非配对） | s5_floor | E5 | S10 行✓（不进摘要/结论） |
| 证据门：A2 34.7% 显著劣（未校正 p=0.0227） | s6_stats | E5 | 结论可不提；n9 可提 |
| 溯源标记：P 9/10 vs C 2/10（底座绑定） | run-20261013+rerun5 | E6 | **新增：结论一句定性回响**（G5） |
| 60/60 gold-ID | 两网格 | E6 | 摘要✓、结论✓（封顶） |
| 双 harness 案例 8/8 四维（Table S14） | QA-EVIDENCE-COMPENDIUM | E6 案例段 | **新增：结论一句定性回响**（不重复 8/8 数字则不占次数） |
| verdict 排序 0.94→0.44→0.94、191 分数阈值未拒绝 | hybrid pools | E8 | 摘要✓、贡献4✓、结论✓（封顶） |
| 部署：18 臂零编造、S2 缺陷修复 | 公开 API 战役 | E7 | 结论不提（保持封顶） |
| 复现：六臂一致率 94.4–100%、臂序保持 | R3 | E5 | n10✓ |

## 4. 每节修改卡（落地作业）

| 节 | 修改点 |
|---|---|
| 总起段 | 重写：管理层（E1/E2/E4）→ 访问路径两族（E3 描述消融、E5 内容层对比）→ 回答层（E6/E7）→ 诊断与边界（E8/E9）；保留 per-corpus 不合并声明 |
| Setup | 增一句 evidence-family 导览（三族与 RQ 对位）；其余不动 |
| E3（原E2b） | 段首加框架句：本节=描述层的配对消融（有无描述路由卡），是集合选择证据；诚实限定原样保留 |
| E5（原E4） | 基本不动；标题改"E5: ..."；确认 BM25 floor 句与 R3 段在位 |
| E6（原E5） | 标题改"E6: ..."；案例段保持；C 臂框架句保持 |
| E7（原E5b） | 标题改"E7: ..." |
| E9（原E7+E8合并） | 新节"E9: Operational boundaries: stability, concurrency, gate and scope ablations"，两段（稳定性/并发 + 门控/范围消融），内容原样搬迁 |
| RQ3（n1） | 重写："compares the tested content-layer configurations on gold-evidence containment and retrieval cost ... whether the tiered path contains more gold evidence than flat or navigation-free alternatives"（去 ranking） |
| 结论（n11） | 增两句：①溯源标记底座效应定性回响（9/10 vs 2/10 不重复数字也可，建议带数字一次）；②双 harness 案例定性回响（引用 Table S14） |
| S9/S10（supplementary） | 行标签同步新编号；S10 行次序对齐 E1–E9 |
| 图表 | fig3_routing 留 E3；fig_ladder/fig_miss_overlap 留 E5；fig4_inflation 留 E8；tab:e5-answers 留 E6；float 引用齐全性验收 |

## 5. KBS 合规影响（依据 notes/kbs-requirements-compliance 记录）

| 项 | 现状（2026-11-13） | 本轮影响 |
|---|---|---|
| 篇幅（"preferably" ≤20 双栏页；本地门 ≤24） | **17 页** ✅ | 重编号+合并后预计 16–17 页，更宽裕 |
| 摘要 ≤250 词 | 244 ✅ | 不动摘要（数字主张已对齐三族） |
| 关键词 1–7 | 6 ✅ | 不动 |
| Highlights 3–5×≤85 字符 | 5 条 ✅ | 需核对是否提及已删的配置对比（若有则改写） |
| 图 ≥7pt/字体/多面板 #16 标记 | ✅ / Arial / 3 处 flagged | fig3_routing 四面板仍在（#16 保留 flagged，作者决定项） |
| 浮动体引用齐全 | ✅ | 重编号后复验 |
| 数据可用性/GenAI 声明/CRediT | n_back 在位；作者占位符待用户 | 不动 |
| 补充材料两件套 | S1–S8 inventory + S9–S14 | 行标签同步 |

## 6. 验收门（全过才交付）

- **A1 编译门**：main 0 error / 0 undefined ref / 0 overfull 新增；supplementary 0 error；页数 ≤24。
- **A2 数字门**：冻结值逐位对账 ≥25 项（§3 表全部行 + S9/S10 行数字 vs PAPER-RESULTS-20261113.md vs 成品 PDF 提取文本）。
- **A3 禁令门**：成品 PDF 全文 grep RAG 对比残留（Dense (BGE / RRF ( / RRF-fuse / HMRS-Hybrid 对比语境 / Fusion-only / Judge-as-filter / D (dense / 47.5）= 0 命中（溯源性提及除外且逐条列出）。
- **A4 闭环门**：RQ1–5 ↔ 节、4 contributions ↔ 节、摘要 6 组数字 ↔ 节、n9/n11 ↔ 节 数字一致；每条 claim 出现次数 ≤3。
- **A5 合规章**：摘要词数、highlights、float 引用、artwork 字号抽检、补充材料编号连续（S1–S14）。
- **A6 独立评审**：方法学子代理对实验章做 fresh 评审（证据充分性+措辞纪律+KBS fit），发现项修复后复验。

## 7. 落地顺序

T1 重编号与 E7+E8 合并 → T2 总起段+Setup 导览 → T3 E3 框架句 → T4 RQ3 重写 →
T5 结论回响两句 → T6 S9/S10 同步 → T7 编译+A1–A5 → T8 A6 独立评审+修复。
