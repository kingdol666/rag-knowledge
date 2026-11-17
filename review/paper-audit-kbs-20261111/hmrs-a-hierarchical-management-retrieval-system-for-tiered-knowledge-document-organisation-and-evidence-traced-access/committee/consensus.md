# Committee Consensus — HMRS KBS Submission (deep-review, 2026-11-11)

**模式**: deep-review（native delegated 五席委员会 + 视觉评审代理 + 数值审计 lane 本席执行）
**论文**: paper-kbs/tex/journal_20p（main_20p.tex，编译稿 hmrs_kbs.pdf 24 页）
**问题包（合并后）**: 66 项 = 15 major / 31 moderate / 20 minor（61/66 引言经规范化机器验证，其余 5 条人工核实）

## 各席裁定

| 席位 | 分数 | 判定 | 主要发现 |
|---|---|---|---|
| 主编（desk-reject 筛查） | 5/10 | Conditional Pass（无 desk-reject 触发） | ef 断引用进 PDF p15；作者占位符块会被行政退回；KBS 卖点未闭合 |
| Reviewer 1 理论 | 4/10 | 贡献未立 | 核心架构收益未被正向建立；引言贡献④与 E4 直接矛盾；管理契约不可证伪 |
| Reviewer 2 方法 | 6.5/10 | 披露一流但设计有洞 | 无外部基线；72 题语料无答通层评估；路由头条=脚本匹配器+未记录回退；trace 非公开 |
| Reviewer 3 文献 | 7/10 | 综合式相关工作的诚实的 gap | DeepRead 被扁平化；RAPTOR/GraphRAG 差异化靠未引用断言；hmrs-demo 作者占位符 |
| Reviewer 4 逻辑 | 7/10 | 链条紧但新节未同步 | E2c 未传播到摘要/贡献/讨论/结论；~1/10 调用声明无任何报告的调用数支撑；19 vs 20 libraries |
| 视觉评审（10 页含图页） | 9/10 页 pass | p15 fail | Figure 6 图注声称派生 replay 不在图中重复，panel(b) 却画了 Judge-as-filter 柱 |
| 数值审计 lane（本席，脚本对账） | — | 主数字全对，派生声明两处失实 | 8 臂命中/rate/CI/p/归因/路由全部与冻结工件吻合；"~1/10 search calls" 实为 10.65 vs 17.00（1.6×）；floor 基线未报告；A3 泄漏未披露 |

## 评分

- 公式分（9.0 − 1.5×15 − 0.7×31 − 0.2×20，floor 1.0）= **1.0** —— 该公式按独立问题计数惩罚，66 项合并包存在跨席重叠（同一 E2c 脱节被三席独立命中），公式分被结构性压低，仅作参考。
- **委员会均值分：5.0/10（编辑 5 / 理论 4 / 方法 6.5 / 文献 7 / 逻辑 7）**
- **最终推荐：Major Revision（大修后重审；无 desk-reject）**

## Top 3 必修（按修复优先级）

1. **E2c 传播断链（major，五席中三席命中 + 本席脚本实证）**：新主结果（A0h 52/72=72.2% vs PD 46/72=63.9%，7:1, p=0.0703）只存在于 §8.3；摘要、四条贡献、RQ 列表、§9 讨论、§11 结论、highlights 全部未提，且讨论/结论仍把该对比列为"缺失的未来工作"——同一篇论文里自相矛盾。
2. **两处数字级失实（major，本席 traces 对账实证）**：① 头条表格与 E2c 正文声称逐级臂"约 1/10 搜索调用"，traces 实测 A0h 10.65 vs PD 17.00（1.6×，差 6 倍，全文无任何调用数报告）；② 引言贡献④"可测风险在排序而非过滤"与 E4"filter replay does not test filtering"直接矛盾。
3. **呈现级硬伤（major/moderate，编辑+视觉席）**：`n8b_eval.tex:134-135` 的 `Section~ef{...}` 断引用已渲染进 PDF 第 15 页；Figure 6 图注与 panel(b) 自相矛盾；作者/单位/CRediT 占位符块；参考文献压至 7.2pt。

## 次优先（major 组其余项）

4. 外部基线缺位 + 72 题语料的 floor 基线（BM25 60%/dense 47.5%/RRF 65%，已冻结于 s5_floor.json）全文未报告——72.2% 无参照点。
5. A3 候选池跨库泄漏（15/72 行，终审计披露项）未进论文 threats；A0h/PD 读入代价（~309KB/题）未披露；剩余 20 深部判卷缺口未入 threats。
6. 路由 72/72 头条的来源约束（脚本探针 + 未记录回退 + 52/72 自动扩展题）应至少在摘要层面披露一句。
7. "matches or exceeds" 需降格为方向性表述（p=0.0703 不显著）；"holding routing fixed" 措辞与 PD 弃用导航相悖；19 vs 20 libraries 口径统一。

## 附注

- 冻结清单 `.frozen-experiment-sha256.txt` 中 RESULTS.md 行哈希已失效（冻结后 RESULTS.md 追加了 A3 披露），重新冻结即可，其余 20 行全部 OK。
- 论文所有可冻结数字与 `artifacts/final_bench/` 冻结工件一致（本席独立对账通过）；问题不在数字而在传播与派生声明。
