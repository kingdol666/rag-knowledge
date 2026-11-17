# Review Panel Record — 2026-11-04 revision round (post-restructure review)

> 三席独立评审（互不可见）+ 编辑综合 + 修订应用记录。
> 输入：paper_demo/tex（2026-11-04 重构版）+ review/experiment-redesign-20261101 全部工件。
> 结论：**MINOR REVISION**，2 项 DA CRITICAL（均经编辑独立复算实锤）已修复。

## Phase 1 — 三席发现摘要

### R1 方法论+最新性审计（verdict: MINOR REVISION）
- ✅ **最新性全过**：摘要/Table 2/宏/图注每个数字从工件重推导成功；旧三轮 run
  （run-20261013：10/10/10·10/9/9·9/7/2·$0.71/0.49/0.53·53/22/24s）零残留（grep 全 tex）。
- MAJOR-1 Finding 4 分母错配（=DA Attack 1，R1 独立复算 A0@floor40=23/40=57.5%）
- MAJOR-2 **floor 索引混库**（新发现）：F-dense top1 前缀普查 = A3无描述孪生库 37/40、
  MD语料-* 原始集合 6/40、Corpus-Chunks800 副本 1/40 → floor 搜的是跨集合混合库
- MAJOR-3 **拒答归因错误**：A3 有判卷门但拒答 0/4 → 拒答跟踪的是描述层剪枝的
  早期退出，不是片段门（"only gated arms decline" 表述被自家 trace 证伪）
- MAJOR-4 agent 提示范围预限定未披露（=DA Attack 4）
- MINOR：median→mean（6,078 是均值非中位）；first-hit 470→466(n=57)；14/14 工件
  在 api-demo 轮而非五臂轮；Table 1 数字溯源未点名；demo 延迟无 trace 源；单轮+
  未校正 McNemar 未声明；"matches"→"statistically indistinguishable (underpowered)"

### EIC 期刊契合+叙事（verdict: MINOR REVISION）
- CRITICAL-1 作者占位符（单盲硬门槛，用户侧待办）
- MAJOR-2 GenAI 声明在文献后，与审计文档自定要求矛盾 → 已改 main.tex 顺序
- MAJOR-3 **Fig1 行标题仍 "QDCVR — TWO LOOPS"**，与全篇平台降级叙事冲突 → 已改
  "THE PLATFORM — ..." 并过五重门禁重建
- MAJOR-4 阶梯/车道分类学矛盾（fast lane 在 ladder 内 vs librarian lane=无向量 ladder）
  → ladder=共享契约，车道实例化 recall 层
- MAJOR-5 视频仍是旧 50 篇画面（demo 可信度硬伤，用户侧待办）
- MAJOR-6 管理支柱（图谱/经验/批量）一句话孤悬 → 摘要从句+场景1图谱拍点+场景3
  经验蒸馏拍点+§2.2 原句
- MINOR ×11：QDCVR 未展开（已补 query-driven content-verified retrieval）、
  engine/layer 术语、34/66 分母、23.9vs24.3MB、165/165 无拆分（**拒绝虚构拆分**）、
  去重门缺失、延迟口径、general vs compact、texttt、审计文档陈旧、README 徽章
  41→42（已同步 95/42）

### DA 魔鬼代言人（verdict: 3 must-do）
- CRITICAL 攻击1+2（containment 跨分母 + 无能力匹配基线）：**编辑复算实锤**
  A0@floor40=57.5%>dense 52.5%，但 <BM25 60%<RRF 67.5% → Finding 4 重写
  （matched 数字+让步+capability-matched 基线列 pending）
- CRITICAL 攻击4（scope hints）：**编辑直读 AG1-6 prompt 实锤**（六条全部带
  "限定范围提示：优先在「X」…"）→ 披露+降格 illustrative，零提示证据改引 5 案例
- MAJOR 攻击5+3（路由分母+摘要隐瞒 null）：分母如实带出+摘要补 null+on-this-corpus
- MINOR 攻击7（金标串中位 16 字符，已核）→ 代理指标声明；攻击8（demo 定位）→
  "demonstration datum, not a benchmark"

## Phase 2 — 编辑综合与修订应用

**裁决**：DA-CRITICAL×2 validated（阻断静默 accept）→ 全部修复；
R1-2（floor 混库）validated（编辑普查实锤）→ Setup 披露；
R1-3（拒答归因）validated（臂定义即证）→ 摘要/Finding2/图注重写为
"description-scoped early exit" 口径；EIC 全部可执行项采纳；
**拒绝项**：EIC-11 的 165/165 构成拆分（工件无据，不虚构）；
R1-6 first-hit 改报 466(57 可恢复)。

**应用清单**（本轮 40+ 处编辑，全部工件溯源）：
1. 摘要：null 如实入摘（48.7 vs 55.3 indistinguishable）+ 拒答改描述层口径 +
   管理支柱从句 + Hint-sampled 限定 + on-this-corpus + 删 52-68% 混分母句
2. §4 Setup：金标串长度声明、routing-correct 定义、floor 混库披露、单轮+
   uncorrected McNemar+proxy 声明
3. §4 Findings(1)：mean（非 median）+466(n=57)+packing-overhead 括注
4. §4 Findings(2)：indistinguishable+bytes parity 诚实句+描述层归因重写（A3 反例）
5. §4 Findings(3)：34/66 分母带出
6. §4 Findings(4)：整段重写为 matched-subset（57.5/52.5/60/67.5）+让步+
   capability-matched pending
7. §4 机制段：scope-hint 披露+illustrative 降格
8. §4 Costs：capability-matched 入 pending+demonstration datum 框定
9. main.tex：GenAI 声明移至文献前；fig1 Description 平台化；fig4 图注
   matched-subset；tab:ablation 声明点前移；fig4 0.75\textwidth
10. fig1-core.html：行标题 THE PLATFORM+aria-label → 五重门禁重建 PASS
11. fig4：字号全面抬升（7.4-8.5pt 设计值）+警示色 #c05a28 琥珀族
12. README：badge 41→42、94/41→95/42 同步
13. 页限工程：正文恰收 p4（p5=GenAI 声明[文献前]+文献），三轮措辞收紧+
    浮动间距 8pt+双表降号+looseness，0 内容损失

**终态验证**：5 页、正文恰 4 页、声明先于文献、0 未定义引用；
visual-judge 全 5 页复审（fig1 平台行标题/表 2 scriptsize 4x 全 CI 完整/
声明顺序均实证），唯一 fail=fig4 琥珀色静默失配 → 已修复重建。

## 遗留给用户的硬门槛（非本轮可修）
1. 作者占位符+基金行（单盲必填）
2. 演示视频重录（当前为旧 50 篇画面，与论文两实例不符）
3. 目标届次确认（官网 2026 届 demo 截止已过；下届格式口径不变）
4. commit（全部改动未提交）

## floor 重跑建议（下轮可选）
R1-2 混库披露是诚实兜底；根治=按十库范围重跑 floor（LLM-free，成本低），
重跑后数字须重新过审计再入论文。
