# E2E 全链条验收测试报告（2026-09-25）

范围：入库 → 三模式检索 → 经验写入/检索 → 经验归纳 → 一致性校验/查重。
环境：真实后端（8771，重启加载修复）、真实 kb-mcp（stdio）、真实本地 Laya 判决。
产物目录：`review/e2e-chain-20260925/`（文档、转录、日志、后端日志）。

## 一、全链条执行记录

| 阶段 | 执行内容 | 结果 |
|---|---|---|
| A0 去重探针 | 两文档特征句 kb_search_vector，最高 0.637 < 0.85 | ✅ 无重复 |
| A2 质量门 | 原生 markdown、结构完整 | ✅ |
| A2.5 拆分门 | doc2 13258 字符 > --max-chars 8000，`split_large_doc.py` 真实拆分 | ✅ 2 parts（8108/5393），源删除，sha256 记录 |
| A3/A3b/A3c | 四要素描述（≤220 字、【k/N·】前缀 + ——锚点）+ 归一标签 | ✅（人工按规范产出） |
| A3d/A4 建库 | `AI 基础设施` 已存在（409 去重保护生效）→ 走"匹配现有库"分支 | ✅ |
| A5 入库 | kb_doc_create × 3（doc1 + 2 parts） | ✅ |
| A6-V 索引验证 | 向量可召回（0.652-0.8）、kb_list doc_count=3 | ✅ |
| 检索-A | Q1 向量+内容门（mode_a + Laya） | ✅ gold kept 0.8885 |
| 检索-B | Q1 逐级（peek + 扩展词 + agreement） | ✅ gold kept（经修复，见 F2/F3） |
| 检索-C | Q1 并行混合 CLI（--lane-agreement --peek-heads） | ✅ gold kept + 进证据包，real=True |
| E0/E5 经验提取与创建 | experience_extract(prepare) 任务包 → 2 条结构化经验入库 | ✅ exp-104b… / exp-c2a2… |
| E4 经验优先检索 | 2 条 incident 查询 | ✅（经修复，见 F1）命中 P2 |
| E8 看板 | experience_dashboard | ✅ total=3 |
| 经验归纳（summarize） | 两条具体经验 → 1 条可迁移方法论（CREATE 模式） | ✅ exp-7b41… |
| V1 三方一致性 | kb_list ↔ kb_get_documents ↔ fs tree（doc_count=3=3） | ✅ |
| V4 索引覆盖 | 3/3 文档向量可召回（注意：doc_path 分隔符 \ / 需归一化比较） | ✅ |
| O2 查重 | kb_find_duplicates = 0 pairs | ✅ |

## 二、发现并修复的问题（3 个真 bug + 2 个测试基建问题）

### F1 🔴 E4 经验检索误杀高相关经验（后端 bug，已修）
- 现象：两条 incident 查询，向量召回 2 条经验但内容验证全部丢弃（"无确认经验，不编造"）。
- 根因（`backend/app/services/experience_service.py`）：
  1. `_extract_domain_terms` 对整段文本去掉空格后做 CJK bigram，产生跨词垃圾项
     （"从跳"/"到怎"/"么排"）；
  2. `_semantic_verify_delta` 用 title/scenario/tags 的域项集与查询域项集比对，
     中文口语查询 vs 英文术语型元数据 → 结构性 overlap 13%、diff 93% → 0.5 重罚
     → 内容分 4→2 < 3 → 丢弃。经"采样率跳变"这类完全相关的经验被误杀。
- 修复：① bigram 只在连续 CJK run 内生成；② 跨语言（脚本构成差 >0.6）不罚；
  ③ exp 项集 >15（长文本）时弃权，交回主内容维度裁决。
- 验证：离线复现 3 例全对（相关保留/无关拒绝），后端重启后 E4 实测 2/2 命中。

### F2 🔴 饱和分布下相对切点失效（保留策略增强，已修）
- 现象：B 通道 Q1，Laya 对 96/329 篇头部给分 ≥0.9（best=1.0，模型自带未校准警告），
  gold 0.8885 被切点 0.9 切掉（排名 97+）。
- 修复：把 lane-agreement 原则接入 librarian 通道——描述命中（候选信号）+ Laya 过绝对
  阈值（内容信号）= 双信号保底（`retain_docs(agreed_keys=...)`）。
### F3 🟠 max_kept 截断击败 agreement 保底（交互 bug，已修）
- 现象：96 篇饱和带被 cap 到 30 后，agreement 文档被按分数挤出——保底形同虚设。
- 修复：截断后强制并回 agreed_keys（cap 只裁"可弃带"，不裁双信号契约）。
- 验证：新增单测 `test_retain_docs_agreement_survives_max_kept_cap`；B Q1 复测 gold kept=true（kept_n=31=30+1）。

### F4 🟡 测试基建（非产品 bug）
- `run_retrieval.py` REPO 用 parents[3] 越界 → A 模块找不到、C 脚本路径不存在
  （Windows python "can't open file" 退出码 2）；已修 parents[2]。
- V4 探针首跑把 `\`/`/` 路径差异判为未覆盖；改归一化比较后 3/3 ✓。

### F5 🟡 A 通道已知特性（设计内，记录不改码）
- Q2（part 1 事实题）A 单独未命中：`balance_kbs=True` 在 11 库摊薄 top-10，
  且经验文档（0.748）与源文档竞争同库名额。无阈值时 gold 排名 #2（0.726）。
- search skill 的设计答复：Phase 1 失败 → Phase 2 librarian 升级（B/C 通道均命中）。
  E4 场景下经验文档排第一也正是"经验优先"的预期行为。

## 三、环境运维记录
- 后端重启 2 次：第一次杀主进程 53452 后端口仍被孤儿 uvicorn worker（PID 56000，
  主进程 +2s 启动）持有——记忆中 reload 陷阱的又一实例；杀孤儿后从 `backend/`
  目录用 `python main.py` 正确重启。token 未轮换（check_token ok）。
- 仓库根没有 main.py（在 backend/ 下）；`uvicorn reload 失效` 意味着改后端代码必须
  手动重启。

## 四、结论
全链条（入库 A0-A6 → 检索 A/B/C → 经验 E0/E4/E8 → 归纳 → V1/V4/O2 校验）打通。
修复 3 个真 bug（E4 误杀、饱和切点、cap-击败-agreement），41→43 项离线测试全绿，
skill-creator 校验通过。已知残留：Laya 分数饱和（96 篇 ≥0.9）是模型校准问题，
流程层已用双信号 agreement 兜底。
