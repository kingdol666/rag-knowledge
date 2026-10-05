# 三模式检索回答对比 + gold 判定（2026-09-26）

数据：`review/answer-compare-20260926/`（6 组运行转录 + 证据包，全部真实本地 Laya）。
回答生成契约：A 按 search skill Phase 1（仅已读文档）；B 按 librarian L5.1（kept 集 + survivor 补读）；C 按 hybrid SKILL（result_list + survivor 补读）。

## gold 判定（先立标准）

| 题 | gold 文档 | gold 事实（原文核对） |
|---|---|---|
| Q1 span 采样率与 p99 | **AI 基础设施/tracelens-deployment-notes.md** | 基础采样率 **7.3%**（目标 7.5%，一致性采样 -0.2pp）；查询 p99 **847ms → 412ms**（降幅 **51.4%**） |
| Q2 增量重建/删除标记阈值 | **AI 基础设施/vector-index-tuning-guide (part 1 of 2).md（第 5 节）** | 增量条数达全量 **15%** → 调度全量重建；删除标记比例达 **25%** → 安排重建（辅助：经验 exp-c2a2 同含两数字，属合法次级来源） |

## 检索层对比

| | A 向量+内容门 | B 逐级（peek+agreement） | C 并行混合 |
|---|---|---|---|
| Q1 gold 判到/保留/进证据 | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ |
| Q2 gold 判到/保留/进证据 | **✗ / ✗ / ✗** | ✓ / ✓ / ✓ | ✓ / ✓ / ✓（agreement 接线修复后复测） |
| 耗时 | 69s / 35s | 695s / 1196s | 1196s / 790s |
| 证据包 | 9.7KB，精，含全部 gold 事实 | 12KB 满，31-35 篇，gold 事实在 survivor 补读层 | 12KB 满，31-37 篇，同左 |

## 三模式回答（Q1）

- **A**：TraceLens 生产环境基础采样率为 **7.3%**（一致性采样哈希削峰，较 7.5% 目标低 0.2pp）；查询 p99 从旧系统的 **847ms 降至 412ms，降幅 51.4%**。✅ 四个 gold 事实全部命中，引用 tracelens-deployment-notes.md。
- **B**：同上全部数字正确 ✅（gold 在 kept 集，survivor 补读后引用 part 头部+第 2/3 节）。
- **C**：同上全部数字正确 ✅（gold 在 result_list，lane=catalog，双通道归并后补读）。

## 三模式回答（Q2）

- **A**：已读的 3 篇（GPT-3、multiverseg、e2e 架构总览）均不含阈值——按 search skill 契约此为 **gate ≤5 → 升级 Phase 2（librarian）** 的场景；A 单独回答 = 如实"未找到"。❌ gold 未召回。
- **B**：增量占比达全量 **15%** 触发全量重建；删除标记比例 **25%** 才安排重建（另附每月约 0.4pp 的劣化速率与双索引热切换背景）。✅ gold（part 1 第 5 节）命中。
- **C**：同 B，两数字正确 ✅，且额外带入 part 2（ef_search=128 / QPS 1830）作背景。

## 关键差异与判定

1. **gold 判定**：Q1 gold = tracelens-deployment-notes.md；Q2 gold = vector-index-tuning-guide (part 1 of 2).md 第 5 节。两题的 gold 都在"AI 基础设施"库——**B/C 六格全中，A 五中一缺（Q2 未召回）**。
2. **A 的 Q2 缺口根因**：`balance_kbs=True` 把 top-10 摊到 11 个库 + 经验文档（0.748）在同库竞争名额；无阈值时 gold 排 #2（0.726）。属 search skill 已设计的"Phase 1 失败 → Phase 2 升级"场景，不是索引缺失（A6-V 已验证可召回）。
3. **B/C 的代价**：耗时长 10-20 倍（peek 全库头部 + Laya CPU 判决 300+ 段）；证据包 12K 截断下 gold 头部可能被饱和带挤出——已修 pack 排序（agreement 文档优先）+ survivor 补读契约兜底。
4. **本轮新修**：C 通道 `run_hybrid` 补接 description-agreement（此前只在 harness B 通道生效），C Q2 gold 由 kept=False → True。

## 结论

- **简单事实题、已知领域**：A 最优（35-70s、证据精、事实全在包内）。
- **A 未召回或跨库/多文档**：B/C 是决定性兜底（Q2 实证）；B 单通道足够，C 的额外价值在双通道去重与并行的召回互补。
- **延迟敏感**：A → B 级联（search skill 的 Phase 1→2 设计）；**召回优先/不确信**：直接 C。
