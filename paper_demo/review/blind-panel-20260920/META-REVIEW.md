# META-REVIEW — CIKM 2026 Demo 盲审面板汇聚

> 面板：三位互盲审稿人（R1 资深 IR/Agent 研究者 · R2 工业界 Demo 实践者 · R3 严格细节审稿人），
> 各自独立阅读 5 页稿件 + 三张提交图，未读彼此意见、未读仓库审计文档。
> 汇聚人：Archival（本文件只做汇整与事实核对，不改写审稿人判断）。
> 评审文件：`R1_review.md` · `R2_review.md` · `R3_review.md`

## 一、分数与推荐档

| 维度 | R1 | R2 | R3 |
|---|---|---|---|
| Novelty | **2** | 3 | 3 |
| Usefulness | 3 | 3 | 3 |
| Technical soundness | 3 | 3 | **4** |
| Demo quality | 3 | 3 | **4** |
| Presentation & compliance | 3 | 3 | 3 |
| **总评** | **3** | **3** | **3.5** |
| **推荐档** | borderline（可升 accept） | borderline 偏接受（补 2 项可升） | 边缘·有条件接受（修 W2/W3 → accept） |

**面板结论：borderline → 有条件接受带。** 三票无 reject；三位均给出明确可升级路径。

## 二、三方共识（全员独立命中 = 高置信）

1. **诚实克制的声明风格是最大优点**（R1-S1 / R2-S2 / R3-S1 不约而同）：门分=agent 判断、
   not a claim of accuracy superiority、完整限制小节 —— 在 demo 赛道罕见，应保持。
2. **可核对数字全部一致**（R3 独立核对：50/5/165、153 names、9/10、8/8、1/8、2 chunks·2,854≤4,000 chars、
   0–8 rubric 阈值 —— 与昨晚全量实测逐项吻合）。
3. **集成与可检查性是真实贡献**：base/document/part/section 四级寻址贯穿入库→检索→可检查回答
   （R1-S2），not-found 路径与 declared-unread 字段（R3-S3）。

## 三、三方共识缺陷（按修复优先级）

| # | 缺陷 | 提出者 | 严重度 | 修复方向 |
|---|---|---|---|---|
| 1 | **GenAI 声明溢出第 5 页**：违反"4 页正文 + 仅文献附加页" | R3-W1、R2 | P1 | 压缩声明 2–3 行，或移至参考文献页（按 CFP 口径） |
| 2 | **伪匿名矛盾**：作者栏占位符 vs 视频/工件链接指向真实账号 kingdol666 | R3-W3、R2-W4、R1-合规 | P1（若双盲）/ P2（单盲） | 按 CFP 匿名要求决定：或填作者名（单盲），或工件镜像匿名化（双盲） |
| 3 | **not-found 行为从未真机展示**：3 个 out-of-corpus 探针全是预置脚本 | R1-W2、R2-W3 | P1 | 补一条非脚本的真实 librarian-fallback 成功轨迹 + 真机 not-found 演示（rebuttal 或 camera-ready） |
| 4 | **新颖性受限**：门控+兜底≈CRAG/Self-RAG 的 evaluate–correct–abstain 的 prompt 化重实现 | R1-W1 | P1 | 定位改为"集成贡献"（正文已部分如此），rebuttal 明确区分点 |
| 5 | **复现包装不足**：LLM/harness 未命名、无 Docker/一键安装 | R2-W2 | P1 | artifact README 补环境说明 |
| 6 | **零延迟数据**：多步 agent 循环现场等待风险，无降级预案 | R2-W1 | P1 | 补实测时延表或准备预计算回放 |
| 7 | **P0/P1/P2 符号冲突**：证据分级与探针 ID 两用且正文未定义 | R3-W2 | P1 | 统一符号或首次出现处定义 |
| 8 | **165 条目 vs 153 名称未解释**（三方中 R3、R2 提及） | R3-W4 | P2 | 加一句括号解释（拆分导致重名） |
| 9 | fig1 "≈800-token" vs 4,000-char 预算单位不一致 | R1-合规 | P2 | 与独立审计结论一致：改 "≈800-character" |
| 10 | 摘要 "agent-authored" vs 正文 "templated" 措辞偏差 | R3 | P2 | 统一措辞 |

## 四、分歧点

- **新颖性评分（2 vs 3）**：R1 认为门控协议是 CRAG/Self-RAG 控制流的 prompt 化重实现（技术新颖性低）；
  R2/R3 更看重系统集成与可检查性的新颖性。Camera-ready 对策：在引言把贡献明确锚定为
  "integration + inspectability" 而非新技术协议。
- **Demo quality（3 vs 4）**：R3 因"诚实空态与可检查设计"给 4；R1/R2 因脚本化成分扣到 3。
  补真实 fallback 轨迹可同时提升两票。

## 五、与独立一致性审计（benchmark-consistency-review-20260920）的交叉验证

盲审面板与本审计**独立收敛**：R3 的逐数核对结果与审计的 15/17 匹配结论一致（R3 未发现数字造假，
仅 fig1 单位问题与 165/153 解释缺失，均为审计已记录项）。审计发现的 fig3 "8/8"（归档轮）vs 本轮 7/8
的漂移未被判扣——因提交稿与归档轨迹自洽；但 R1-W2 的"gate 合规率未测量"支持审计建议：固定轨迹快照
并在图中标注 trace id。

## 六、给作者的行动清单（合并排序）

1. 页 5 合规：压缩 GenAI 声明（R3-W1/R2）
2. 匿名策略二选一（R3-W3/R2-W4/R1）——按 CIKM demo 是否双盲定
3. 补 1 条真实 librarian-fallback 轨迹 + gate 合规率统计（R1-W2，audit R1 同项）
4. fig1 单位、165/153 括号、agent-authored 措辞统一（R1/R3 P2 批）
5. artifact README 补 LLM/harness 环境说明（R2-W2）
6. 现场演示降级预案 + 时延实测（R2-W1/R6）
