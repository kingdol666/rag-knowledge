# 实验章节撰写总方案（EXPERIMENT-SECTION-PLAN，2026-11-12）

> **性质**：执行计划（blueprint working file），非稿件内容。产出方式：三席多 Agent 讨论
> （R1 方法学席 / R2 KBS 表达席 / R3 魔鬼代言人席）+ 主席合成裁定。下游 Agent 按本计划作业。
> **数据源**：final_bench 冻结值 + R3 后续轮（已并入本修订稿）+ QA-EVIDENCE-COMPENDIUM.md。
> **纪律基线**：KBS-REVISION-20261112.md 的 7 条保守化纪律全部继承，不可推翻。

---

## 0. 三席共识、分歧与主席裁定

**共识**：
1. E1→E2→routing→E3→E4→E5→sysarms→E6→E7→E8 骨架保留，按管理层级组织的叙事成立；
2. ladder-opt（现 E2c）的内部顺序改为**主结果→复现一致→配对计数→归因→A3 局限**（先结果后归因，
   归因引用 E4/E6 概念）；推荐整节移位至 E4 之后（E4b），若页流不容则原位保留+补前向引用；
3. 配对检验一律写"未校正探索性逐题记录"，禁写"显著优于/Holm 改善"；
4. 回答层证据分工：E5 独占方法学与逐题表；ladder-opt 只引用一次（8/8 + 域外拒答一句）；
   "8/8"全文 ≤3 次（E5、ladder、结论各一）；
5. 新增素材不进正文主表：八臂精确值+CI 入补充材料 S 表；稳定性=正文一句+S 表；
   13:0=正文一句；回答案例全表=S 材料；证据窗对照=正文 1 例机制插画+2 例 S 材料；
6. **新增图 8（fig:attribution）**：漏检归因瀑布/堆叠条（35=路由0/窗5/判卷30 → 杠杆+15/+8/+9），
   单栏 90mm 落 E6 之后——归因结构是论证核心，现有文字呈现不足；
7. 读取经济学一句话进 E7（309KB vs 24.3MB (1/80)、13.8s vs 253.7s）。

**分歧与裁定**：
- **R3 误读裁定**：R3 席将"A0h vs PD 1/7"读作 PD 占优。实际配对方向为 **A0h 7 胜 1 负**
  （p≈.0703，方向性有利、不显著）。裁定：正文表述必须**显式写方向**（"A0h leads 7:1"），
  不使用裸比例简写——本误读本身就证明了这条写作纪律的必要性。
- **R3 攻击#1 撤销重述**：真实攻击面不是"PD 更好"，而是"7:1 不显著 + A1b 是较弱竞争臂"。
  防御：主打 **A0h vs A1b 13:0 零回归（p≈2.4e-04，复现 12:0，p≈4.9e-04）**；PD 对比如实报告
  方向性优势+不显著，并披露多组件混淆（纪律 2）。
- **R3 攻击#5（A3 一致率矛盾）裁定**：94.4–100% 一致率的计算范围是 A0/A0f/A0h/PD/A1b/A2 六臂
  （A3=75% 被排除）。修复：稳定性声明必须**显式标明范围**（"six of seven arms"），A3 单独成段
  披露跨轮不稳（33↔25）及根因（name-only 薄卡路由的基础设施敏感性→路由重排级联），并注明
  路由塌陷（72/72→37/72）本身三轮稳定——把不稳定转化为"描述层是路由稳定性来源"的论据。
- **R3 攻击#2（多重比较）采纳**：补算 Holm 校正表入补充材料。13:0 在 Holm 下仍显著
  （8 个比较族内最小 p=6.1e-05 校正后 ≈4.9e-04，13:0 的 2.4e-04 校正后 ≈.002 仍 <.05——补算时按
  实际族大小 m=8 验算，若不满足则降级为"未校正探索性"表述）。
- **R3 攻击#6（归因是事后算术）采纳**：正文措辞改"descriptive decomposition"（描述性分解），
  不写"修复了 30 题"；可补算逐题修复重叠矩阵入 S 材料。

---

## 1. 目标章节结构（段落级大纲）

### n8a（保持骨架；ladder-opt 移位见 §1.1）
| 节 | label | 段落级角色 | 主判断句（证据锚） |
|---|---|---|---|
| §eval 总起 | sec:eval | 评估按管理层级组织+数字不跨语料合并声明 | （已有，微调 ladder 位置引用） |
| §eval-setup | sec:eval-setup | 四语料+题集+判卷+公平性契约 | （已有） |
| §E1 | sec:e1 | 解析底座可用且缺陷可测 | 解析失败率锚 |
| §E2 | sec:e2 | 生命周期一致性可复现 | V 系列一致性数字锚 |
| §routing-audit | sec:routing-audit | **缺口不在路由**（35 缺口路由=0）；确定性路由脚本命中全部 gold 域（脚本化复核，非 Agent 选库准确率） | fig:routing |
| §E3 | sec:e3 | 生命周期运营可自动化 | 蒸馏数字锚 |

### §ladder-opt（核心节，移位至 E4 之后作 E4b；label 保留 sec:ladder-opt）
| 段 | 角色 | 内容与证据锚 |
|---|---|---|
| L1 段落 | 设计声明 | 八臂定义一句话（每臂=一个设计开关）；**多组件披露前置**："A0h/A1b/PD 各改变多个组件，组间差异不归因单一组件"（纪律 2） |
| L2 主结果 | 冻结汇总 | 37/45/52/46/39/25/33/72 + readall 72（字符串包含口径）；图 5（fig:ladder）+ 正文一句 Wilson CI；精确值+CI → S 表 |
| L3 后续轮复现 | 稳定性 | "逐题一致率：A1b/A2 100%、A0f/A0h/PD 98.6%、A0 94.4%（六臂）；臂序两轮保持；A3 除外（见 L6）"；→ S 对照小表 |
| L4 配对记录 | 探索性检验 | "未校正探索性逐题记录：A0h vs A1b 13 胜 0 负（p≈2.4e-04；独立复现 12:0，p≈4.9e-04，零回归）；A0h vs PD **A0h leads 7:1**（p≈.07，不显著）"；脚注 owner_slug 回退限定；**Holm 实测（m=8 全族，已验证）**：A0h-vs-A0（adj=.00049）、A0h-vs-A1b（adj=.00168）、PD-vs-A0（adj=.0234）、A0f-vs-A0（adj=.039）四项存活；**A2-vs-A0 不存活（adj=.0908）**→ 证据门主张措辞="两点位一致复现（25/72 两轮逐题相同）+探索性显著+机制依据的收敛证据"，不写"Holm 校正后显著"；PD-vs-A0 在 Holm 下显著须如实写出（平面精确臂显著优于逐级基线） |
| L5 归因（描述性分解） | 35 缺口 | 图 8（fig:attribution）：路由 0/窗口 5/判卷 30 → 杠杆 +15/+8/+9；措辞=descriptive decomposition |
| L6 A3 与 readall 局限 | 诚实披露 | A3 路由塌陷稳定、端到端不稳+根因；readall=字符串包含≠Agent 精读；digest 6079s 为估算 |
| L7 读取经济学 | 一句 | 309KB(1/80)、13.8s vs 253.7s（或放 E7，按页流二选一，不许两处重复） |

### n8b / n8c
| 节 | 调整 |
|---|---|
| §E4 | 接收移入的 ladder-opt（若移位）；tab:retrieval+fig:retrieval 不动 |
| §E5 | 回答层方法学独占：四维判定定义、tab:e5-answers、域外拒答机制（NOT_FOUND）；引用 QA-EVIDENCE-COMPENDIUM 的 4×2 对照表 → S 材料；"8/8"第一次出现 |
| §sysarms | 部署层复制：omp 7/7 一句交叉引用 |
| §E6 | 判卷失效（fig:inflation）+ **新图 8 fig:attribution 紧随其后**（归因引用 E6 的段存活概念）——若 ladder-opt 已移到 E4b，则图 8 归 E4b，E6 只保留 fig:inflation |
| §E7 | 非功能：读取经济学一句（若 L7 未占用） |
| §E8 | 门控与范围消融：OOD 门控检索层数值如实报告（A0 2/4、A0h 0/4）+ "检索层门控非回答拒答率"声明；拒答主张只在 E5 |

### 跨节一致性规则
- 同一发现最多出现三处（paper-writer 规则）：8/8 → E5/ladder/结论；13:0 → ladder/S 表/结论（可选）；
- "gold containment=证据覆盖率代理，非回答正确率"随主表与 E5 两次出现；
- readall 双口径声明（字符串包含+digest 估算）在 ladder-opt L6 一次、结论引用一次。

## 2. Claim→Evidence→位置映射总表

| # | Claim（安全句式） | 证据 | 位置 |
|---|---|---|---|
| C1 | 冻结汇总八臂 37/45/52/46/39/25/33/72（各 n=72） | final_bench/s6_stats.json | L2 + 图 5 |
| C2 | 后续轮逐题一致率 six-arm 94.4–100%，臂序保持 | replication s4_traces_r3 + s6d | L3 + S 表 |
| C3 | A0h vs A1b 13:0 零回归，未校正 p≈2.4e-04（复现 12:0） | traces 配对计算（本日已算） | L4 + S Holm 表 |
| C4 | A0h vs PD 7:1 方向性有利，不显著（多组件混淆披露） | 同上 | L4 |
| C5 | 35 缺口描述性分解（路由0/窗5/判卷30；+15/+8/+9） | attribution_a0_misses.json | L5 + 图 8 |
| C6 | 路由：确定性脚本 72/72 vs A3 剥描述 37/72 散布（脚本结果口径） | traces route_correct | routing-audit + L6 |
| C7 | 回答层：双 harness 8/8 四维全对（十会话未观察到幻觉）；域外拒答 NOT_FOUND + $294K 边界 | QA-EVIDENCE-COMPENDIUM | E5（主）+ ladder 一句 + 结论 |
| C8 | 读取经济学 309KB/13.8s vs 24.3MB/253.7s | traces | L7 或 E7（单点） |
| C9 | floor BM25 24/40 三轮零翻转（平台无关锚）；dense/RRF 平台组成敏感不横比 | s5_floor×3 | S 材料 + setup 一句 |

## 3. 图表规格书（含编号、位置、尺寸、题注草案）

| 编号 | label | 内容 | 数据源/脚本 | 位置与尺寸 | 题注草案（一行式） |
|---|---|---|---|---|---|
| 图1-3 | fig:levels/arch/workflow | （已有，不动） | — | n3，figure* 190mm[t] | （见 CAPTIONS 文档） |
| 图4 | fig:routing | 路由四联 | build_fig3_origin.py | n8a routing-audit 后，figure* 190mm[t]；勿与图5同页 | （已有） |
| 图5 | fig:ladder | 八臂冻结 vs 后续 + Wilson CI | build_fig_ladder_optimization.py | ladder-opt L2 段后，figure* 190mm[t] | "Eight-arm ladder: frozen vs. follow-up gold-coverage with Wilson 95% CIs" |
| 图6 | fig:retrieval | 两语料检索对照 | build_fig_retrieval_comparison.py | E4，figure* 190mm[t] | （已有） |
| 图7 | fig:inflation | 判分分布 | 旧矢量 | E6，单栏 90mm[!t] | （已有） |
| **图8（新）** | fig:attribution | 35 缺口归因瀑布 + 修复杠杆 | attribution_a0_misses.json；新脚本 build_fig_attribution.py（figures/ 目录，平铺输出） | E6 后（或 E4b L5），单栏 90mm[!t]，高≤60mm | "Attribution of 35 ladder misses (routing 0 / window 5 / grading 30) and the repair leverage of the content-layer arms (+15/+8/+9)" |
| 表5 | tab:retrieval | 检索结果 | （已有） | E4，table* 190mm | （已有；resizebox 后校验 ≥7pt） |
| 表6 | tab:e5-answers | 逐题答案检查 | （已有） | E5，table* 190mm[t] | （已有；描述列宽已近极限，勿再缩） |
| **S 表（新）** | tab:s-arms | 八臂精确值+CI+两轮对照+13:0/7:1 配对计数+Holm 列 | s6_stats.json + 本日配对计算 | 补充材料 | "Per-arm gold coverage with Wilson CIs, two-run agreement, and paired records (exploratory, uncorrected; Holm-adjusted column for reference)" |
| **S 表（新）** | tab:s-answer | 4 题×双 harness 回答对照 | QA-EVIDENCE-COMPENDIUM | 补充材料 | "End-to-end demonstration: identical questions answered by two harnesses (verbatim quotes and provenance preserved)" |
| **S 图（可选）** | fig:s-window | 证据窗对照机制插画（正文 1 例用，其余 2 例入 S） | final_bench/responses | 正文 1 例=单栏引文块（非图）；S 材料放另 2 例 | — |

交叉引用落点：E1→图4？否——图4 归 routing-audit 节；ladder→图5+图8；E4→图6/表5；E5→表6；E6→图7（+图8 若在）；sysarms→b/c 一句。所有新图文件平铺同目录（EM 不收子目录）。

## 4. 语言纪律对照表（危险句式→安全句式，全文强制）

| 危险句式 | 安全句式 |
|---|---|
| 实现零幻觉 | 在 10 个对照会话中未观察到幻觉 |
| 显著优于向量检索 | 未校正探索性逐题记录下优于十库向量并集（13:0 零回归）；对无导航精确检索为 7:1 方向性优势，未达显著 |
| 路由准确率 72/72（Agent 能力） | 确定性路由脚本命中全部 gold 域（脚本化复核，非独立 Agent 选库准确率） |
| 验证层修复了 30 题 | 缺口的描述性分解中 30 题与判卷阶段相关 |
| 层级组织带来检索提升 | chunk 窗口并集贡献主要增益；导航的独立增益未获证实（多组件混淆披露） |
| 四语料验证了泛化性 | 四个小规模自建语料上呈现一致趋势 |
| readall 证明通读可用 | readall 的 72/72 为字符串包含口径，是上下文上限诊断而非精读基线 |
| 全文任何位置 | "gold coverage"（证据覆盖率代理）≠"answer correctness"；代理声明随主表+E5 出现 |

## 5. 补算作业清单（全部可从落盘产物完成，无需新实验）

| # | 作业 | 数据源 | 产出 | 优先级 |
|---|---|---|---|---|
| W1 | 八臂 Wilson CI 验算（n=72） | s6_stats.json 复算 | S 表列 | 高 |
| W2 | 13:0/12:0 与 7:1 精确 McNemar 全式（含 Holm 列，m=8 族） | traces | S 表 + L4 句 | 高 |
| W3 | 判卷 30 缺口逐题 ID 清单 | attribution_a0_misses.json + traces | S 材料 | 高 |
| W4 | A3 跨轮逐题 diff 审计（33→25 翻转清单+路由重排对照） | 两轮 traces | S 材料 + L6 段素材 | 高 |
| W5 | 六臂一致率矩阵脚本化（范围显式化） | s6d_compare.json | L3 句 + S 表 | 中 |
| W6 | 修复重叠矩阵（+15/+8/+9 的逐题归属） | traces | S 材料 | 中 |
| W7 | 20 实体型金标未命中清单与错因分类 | traces + 题集 | S 材料 | 中 |
| W8 | gold-fallback（owner_slug 回退）——**降级为代码级披露**：修订轮已裁定历史 trace 不足以量化触发率；量化需带 instrumentation 的重跑（列 G7 缺口） | s4_run_ablation.py refs_list 构造段 | 脚注素材（定性） | 中 |
| W9 | OOD 4 题逐臂门控行为表 | traces is_refusal 行 | E8 句 + S | 低 |

---

## 9. 验证记录（2026-11-12 计划可行性实测）

**已实测通过**：
1. Holm m=8 全族复算：存活四项（A0h-vs-A0 adj=.00049 / A0h-vs-A1b adj=.00168 / PD-vs-A0 adj=.0234 / A0f-vs-A0 adj=.039）；A2-vs-A0 adj=.0908 不存活（→ L4 与证据门措辞已按此更新）；
2. Wilson CI 复算 A0h 52/72 = [.610,.812]，与 s6_stats.json 逐位一致；
3. 13:0 / 7:1 配对第三遍独立重算：final 13胜0负 p=2.441e-04、7胜1负 p=.07031；R3 12胜0负 p=4.883e-04、7胜1负 p=.07031——与计划 §2 C3/C4 完全一致；
4. W4 可行性：A3 跨轮 diff 18 翻转（13↓/5↑）可从落盘 traces 直接复算；
5. W5 一致率矩阵：六臂 94.4/98.6/98.6/98.6/100/100% 逐位复现；
6. 数据源完备性：计划 §2 全部 10 个证据路径存在；attribution json 含 35/30/5/15/8/9 全部数字；8 个 qa JSON + gold_text(229,423 chars) 在位；figures 构建脚本（build_fig3_origin / build_fig_ladder_optimization）在位；n8a ladder-opt + fig:ladder label 在位。

**计划修正项（已回写）**：L4 Holm 实测值与 A2 措辞降级；W8 降级为代码级披露（新增实验缺口 G7）。

**数据量充分性评估（诚实口径）**：
- 检索臂：72 题 × 8 臂 × 2-3 轮——对已发现效应量（13:0、20.8pp）配对检验功效充足；A0h 的 CI 半宽 ±10pp，不支持亚组级细分主张；
- 回答层：10 会话 + 8 题——案例研究级，计划已限定（不进统计主张）；
- floor：n=40 单子集——描述性；
- 结论：**对 KBS 系统类论文（探索性统计框架）数据量充分；对"基准竞赛/泛化主张"不充分**——计划已把后者全部路由到 limitations（G1-G7）。


## 6. 实验缺口（诚实列入 limitations/future work，不投稿前补跑也可）

G1 因子化导航消融（单开关）；G2 扩题 ≥200 + 域内误拒率测量；G3 同语料 BM25/hybrid 外部基线；
G4 LLM 精读版 readall 基线；G5 CRAG/LightRAG 内容认知基线（LLM endpoint）；
G6 重复运行 ≥5 的预注册统计族。→ n10_threats 按此更新。

## 7. 执行作业单（给下游 Agent 的顺序）

| 步 | 作业 | 产出 | 验证 |
|---|---|---|---|
| T1 | 跑 W1-W5 补算脚本（只读落盘产物，输出 JSON+MD 到 notes/） | notes/computed-20261112/*.json | 数字与 s6_stats/s6d 逐位核对 |
| T2 | 写 S 表两件（tab:s-arms/tab:s-answer LaTeX）+ supplementary 增补 | supplementary.tex 增量 | \ref 双向、列宽、7pt 校验 |
| T3 | ladder-opt 重写（按 §1 L1-L7 段落卡；先结果后归因；句式过 §4 对照表） | n8a/n8b 相应 .tex | 每句证据可回溯；纪律 1-7 逐条自查 |
| T4 | 移位执行（ladder→E4b）或原位+前向引用（按编译页流决定） | n8a/n8b \input 顺序 | 编译 0 错误；图4/图5 不同页顶 |
| T5 | 新图 8：写 build_fig_attribution.py（90mm 单栏，字号≥7pt，冻结/后续分标） | figures/build_fig_attribution.py + fig_attribution.pdf 平铺输出 | 视觉验收：无压字/无溢出 |
| T6 | E5/E8 按映射表微调（8/8 首次出现、拒答主张归位、OOD 门控句） | n8c_eval.tex | 跨节三次上限检查 |
| T7 | n10_threats 增补 G1-G6 + A3 敏感性披露 | n10_threats.tex | 与纪律措辞一致 |
| T8 | 全稿编译+页数+overfull+交叉引用三查 | PDF | ≤25 页双栏；0 未解析引用；r3 一致性：正文数字 vs 本计划 §2 表逐条对账 |

**页数预算**：当前 24 页；新增正文≈0.3 页（一句+引文块）+图 8（0.25 页）→ 预计 24-25 页，
超页时先压缩 E3/E7 各 2-3 行，不动 E5/ladder。

## 8. 红线汇总（任何执行 Agent 不可越过）
1. 纪律 1-7（KBS-REVISION-20261112.md）全文有效；
2. 配对方向必须显式（"A0h leads 7:1"式），禁裸比例；
3. 稳定性声明必须标范围（six of seven arms）；
4. 归因=描述性分解，禁因果动词；
5. 拒答主张只在 E5（回答层），检索层门控数值仅报告；
6. 数字一律引冻结值，后续轮只进复现段；两轮口径不混表；
7. 新增文本每句可回溯到本计划 §2 表中的证据行。
