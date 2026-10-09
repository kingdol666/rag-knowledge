# Editorial Decision Letter — Round 4 (2026-10-09)

四席复审（Round-3 核销席 / 数据审计席 / KBS 主编终审席 / 魔鬼代言人新声明席）。

## EDITORIAL DECISION: **MINOR REVISION**（本轮发现已全部当场修复）

主编原话（节选）："The paper now does the rare thing honestly ... the science
is done and internally consistent. What remains is a structural seam ... all
fixable in days without new experiments."

### 数据-论文一致性审计（数据审计席）

- **重算全部负载性数字（含 144 格附录表逐格核对）：0 处不匹配。**
  LOO 15/16、改述集 BM25 0.875/0.755、NLI 0.3125/0.1375/ρ=-0.134/δ=0.229/
  p=0.120、Q6 符号 1/1 vs 0/11、分级探针 kept 12,12,11,10,11,11、
  Wilson CI、U=1726/p=0.256、8胜0负 p=0.0078 —— 全部与原始日志一致。
- **Benchmark 充足性判定：SUFFICIENT_WITH_CAVEATS** — 对 KBS 的
  "系统+量化负结果" 文体已可发表；caveats（16题/42文档/单引擎/无用户研究）
  论文已自行声明，scaling 工件已发布。

### 本轮抓出并已当场修复的问题

1. **[事实错误,DA] "两个模型信号都栽在 Q6"** — 日志显示 NLI 把 Q6 gold 排第
   1/12（0.9986），shipped judge 排第 10。摘要/§7.6/威胁节三处已改写为诚实
   版本（"NLI 是该题更强的模型信号排第一,judge 第十,符号规则完美解决"）。
2. **[反分离隐藏,DA]** NLI gold 中位 0.011 在非 gold 0.053 **之下**——表格与
   正文现明确写出 "anti-separates"，摘要补充 "by anti-separation"。
3. **[LOO pad 表述,DA]** 摘要与正文不再把 +0.02 安全垫说成 LOO 结论，明确
   "the pad is engineering judgment, not an LOO-selected value"；并写出
   Q11 fold 的真正教训（无 Q11 类训练题的校准会选 0.15 并丢 gold）。
4. **[截断混淆,DA]** NLI 配置写明（330M 单模型/单模板/tokenizer 后 ~500 字符、
   59/191 触顶），并加入反证：**10 个全可见 gold 中 6 个 <0.01**、Q7 判据在
   可见头部但 NLI 仍 0.011 → 截断不是主因。
5. **[结构,主编]** Robustness 小节从 Discussion 内迁至 **§7.6**（Results 内、
   Discussion 前），L3-L5 恢复连续。
6. **[标题,核销席/主编]** "over enterprise knowledge bases" →
   "--- a deployed industrial case study"。
7. **[残留修订痕迹]** "reviewers' suspicion"/"earlier n=1 hazardous
   middle"/"Four pre-registered (实为五行)"/过期注释 — 全部改写；
   "pre-registered"→如实的四实验五问题表述。
8. **[内部矛盾,核销席]** §6.2 "arms differ only in retrieval affordance" 补
   "plus one honesty instruction ... disclosed verbatim in §7.2"。
9. **[−8°C 残留,核销席]** §6 Setup 的 marker 示例句改为真实 marker
   （61–68% vs ≥85% 固化度对照），不再出现 −8°C。
10. **[Q16 循环性,核销席]** 威胁节新增点名：Q16 题干嵌入 gold 文件名 token
    （heatdecay092），改述集保留了该 token（未破坏该捷径）。
11. **[小项]** MRR@5 后 remaining "second-place gold" 措辞、12–15s→11.7–15.3s、
    §2.3 排序偏置归因改挂 MT-Bench、§4.4 补 judge 分数饱和（1.0000）说明、
    Q14 merge 12 vs 11 脚注、Data availability 增补四个新实验。
12. **[补充数据,数据审计席建议]** 三个 absent 探针补跑 agent 层：**3/3 显式
    not-found 且枚举检索范围**（48–114s）→ 分级弃答矩阵补全
    （exp8b_absent_agent.json）。

### 核销矩阵摘要（16 R 项 + 12 C 项）

- R3/R6/R7/R8/R9/R10/R11/R12/R13/R14/R15/R16 与 C5/C6/C7/C8/C9/C11/C12：
  **ADDRESSED_FULLY**（14 项）
- 其余 8 项为 PARTIAL → 本轮全部补齐（标题/−8°C/affordance/Q16/Wang 归因改挂/
  摘要词数自然回落/model-card 类说明已加/余项见上）。
- 唯一保留为 roadmap 的：用户研究、span 级 NLI、判卷集成、benchmark-suite
  扩容、第二 agent 引擎。

### 投稿阻断项（不变，AUTHOR ACTION）

作者姓名/单位/ORCID、CRediT 真名、funding、qdcvr-demo bib 作者占位符。

### 发表预判

- 数据审计席：**SUFFICIENT_WITH_CAVEATS**（可发表）。
- 主编席：**MINOR_REVISIONS**，且列出的 4 条修改（结构/痕迹语/claim 强度/
  case-study 标注）本轮已全部执行。
- DA 席："Otherwise: accept with minor revisions."
- 结论：按 KBS 案例研究类稿件标准，当前 41 页稿在科学内容、数据可复现性、
  声明-证据对齐三个维度均已达到可送审并有望录用的状态；剩余风险集中在
  统计功效（n=16/42）——已通过稳健层与 CI 显式管理。
