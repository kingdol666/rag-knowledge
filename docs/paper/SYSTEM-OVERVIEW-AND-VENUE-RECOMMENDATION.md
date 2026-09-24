# QDCVR / rag-knowledge 平台：系统功能全景、设计逻辑、创新点与投稿建议

> 生成：2026-09-24 · 分支 `feat/soul-persona-system` · 全部数字回源码核对（非引用文档）
> 核对对象：`kb-mcp/server.py`（工具面）、`backend/app/`（服务面）、`web/pages/`（页面面）、
> `benchmark-suite/PIPELINE.md` + `results/R2-EXP-3TRACK-REPORT.md`（实验面）、
> `docs/paper/{SYSTEM-DESIGN-PHILOSOPHY,PAPER-FRAMEWORK,SUBMISSION-MASTER-PLAN,EDITORIAL-DECISION,REVIEW-TODO}.md`（论文面）

---

## 0 · 一句话定位

**一个把"一堆 PDF/Office/扫描件"变成"一个 AI Agent 可以负责任地据以作答的知识库"的自托管平台**——
按**文档说了什么**组织（而不是按它躺在哪个文件夹），并以**可解释的内容裁决**而非向量相似度作为检索的最终判据。

> Vectors are fast. Content is accurate.
> 余弦相似度 0.95 但内容分 ≤4 的文档被**丢弃**，不是降权，是丢弃。

---

## 1 · 系统功能全景（五层能力）

| 层 | 功能 | 代码证据 |
|---|---|---|
| **① 接入与解析** | PDF/Word/Excel/PPT/图片 → Markdown（MinerU OCR，双模式：远程 mineru-api 或本地子进程自动选空闲端口） | `backend/app/services/mineru_service.py`、`mineru_manager.py`（Windows Job Object / Linux `PR_SET_PDEATHSIG` / macOS 进程组） |
| **② 内容驱动组织** | A0–A9 入库管线：去重 → 解析 → 质量门 → 结构化分析 → **A3d 内容归属决策** → 打标 → 四要素描述 → 归档 → 向量+图索引 → 索引终检 | `kb-mcp` 工具链 + `.claude/skills/knowledgebase-*` |
| **③ QDCVR 检索** | 查询改写 → KB 路由 → 两阶段召回（BM25→向量 + balance_kbs）→ **0–8 内容裁决** → 馆员兜底 → not-found 契约 → 五段式回答 | `backend/app/services/two_stage_search_service.py`、`vector_service.py`、`keyword_index_service.py` |
| **④ 知识对象** | 文档（分层/父子 KB）· 标签 · 知识图谱（Neo4j）· **经验（E0–E12 生命周期）** · **SOUL 人格** | `experience_service.py`、`graph_service.py`、`soul_*.py`（20 个 soul 服务模块） |
| **⑤ 治理与工程** | 94 MCP 工具 · 令牌鉴权 · 限流 600/60s · 审计 · hash-pinned 数据快照 · 溯源门禁 | `backend/app/api/routes/auth.py`、`middleware/`、`docs/paper/cikm/provenance_audit.py` |

### 四种使用入口

| 入口 | 形态 | 说明 |
|---|---|---|
| Web UI（:6789） | 11 个页面：`index / file-system / knowledge-base / knowledge-search / knowledge-graph / soul / claude-chat / harnesses / settings / tokens / login` | `web/pages/` 实测 11 个 .vue |
| HTTP API（:8770） | Bearer token 鉴权，OpenAPI 在 `/docs` | 除 `/api/v1/health` 与 `/api/v1/auth/*` 外全需 token |
| CLI | `ragctl`（生命周期/资产/界面/知识/运维 5 组命令） | 单一入口 |
| **MCP** | **94 个工具**（stdio，`.mcp.json` 挂载） | 见下表 |

### 94 个 MCP 工具的真实分布（回 `kb-mcp/server.py` 逐函数核对）

| 族 | 数量 | 覆盖 |
|---|:--:|---|
| `kb_*` 知识库域 | **41** | 图谱 11 · 文档 CRUD 9 · 向量/索引 6 · KB CRUD 4 · 检索 4 · 标签 4 · 通用任务轮询 1 · 项目生命周期 3（含 kb_project_*） |
| `experience_*` 经验 | **26** | E0–E12 全生命周期 + search_global/search_smart/rerank + 草稿池审批 + 陈旧检测 + 衰减 + 冥想（Agent 自动归纳） |
| `soul_*` 人格 | **20** | 蒸馏/初始化 · 学习 · RL 训练 · 四维评估 · 认知草稿 · 反思 · 检查点回滚 · 人格问答 · QDCVR 集成 · LoRA 导出 |
| `fs_*` / `parse_*` / `backend_status` | 7 | 文件树、上传、解析（**非阻塞**，返回 task_id）、健康探针 |

> 设计红线：**写走 HTTP API（原子、可审计），读直连 `.tree-fs.json` / `.knowledge-base.yml`（零后端负载）**。
> 这是"Agent 原生"能低延迟跑完整工作流的工程基础。

---

## 2 · 架构设计

```
接入层   Browser(:6789)  ·  CLI(ragctl)  ·  MCP Client(任何 Agent)  ·  外部 HTTP
            │                                   │
            ▼                                   ▼
代理层   Nuxt 3 服务端代理（浏览器永不直连后端，无 CORS 面）
            │                                   │
            ▼                                   ▼
服务层   FastAPI(:8770)  ←→  MinerU(临时端口)          kb-mcp(94 工具)
         解析调度/向量/图谱/经验/SOUL                     写 HTTP · 读文件
            │
存储层   L1 .tree-fs.json（权威树）
         L2 .knowledge-base.yml（库级索引，检索直读）
         L3 .md 正文（磁盘）
         L4 ChromaDB（BGE-M3，一库一 collection）
         L5 Neo4j（文档/标签/库节点 + 类型化关系）
```

**关键设计取舍（每一条都可写成论文的一节）**

| 取舍 | 选择 | 代价/收益 |
|---|---|---|
| 组织 vs 检索 | **先组织再检索**（内容归属决策树 A3d） | 搜索空间从 N 压到 N_k；跨域假阳性被结构隔离；内容裁决只需验证 ~5 个候选而非 ~60 个 |
| 召回 vs 裁决 | **解耦**：向量+BM25+图负责召回，读正文的 0–8 rubric 独立裁决 | 引入 2–5 s/查询的裁决开销，换来可解释的决策边界 |
| 写 vs 读 | **非对称**：写 HTTP、读文件 | 实测 117 ms（限定库）vs 1411 ms（全库） |
| 找不到时 | **显式 not-found 报告**，永不猜 | 牺牲覆盖率，换取零编造（3/3 域外探针全部正确拒答） |
| 长任务 | 一律返回 `task_id`，不阻塞 Agent 回合 | 解析/重建索引/建图/冥想均可轮询 |

---

## 3 · 五个创新点（以及与最接近工作的差异）

### 创新 1 · 内容驱动组织作为检索原语（Organize-then-Retrieve）
现有 RAG 系统把语料当**扁平池**，靠向量在 O(N) 里找语义近邻。本平台在检索**之前**把文档按内容路由进领域库。
主张：**检索质量的上界不是嵌入精度，而是语料组织结构**。

### 创新 2 · QDCVR 内容裁决（Content-overrides-Vector）⭐核心
`c(d) ≤ 4 ⇒ discard(d)`，**与向量分 s(d) 独立**。0–8 = 主题(0–3) + 场景(0–3) + 证据(0–2)。
`=5` 保留为后备并触发**馆员兜底**（定向再检索 + 续读），全部不过 → **not-found 契约**。

### 创新 3 · 经验生命周期 E0–E12 + P0/P1/P2 可信度（**最干净的创新，无等价系统**）
把"经验"（故障排查/最佳实践/调参心得）提升为与文档并列的**一等知识对象**：
提取 → 质量门 → 草稿池 HITL → 分级 → 索引 → 陈旧检测 → 评审打分 → 看板 → 重排 → 跨库检索 → **时效衰减** → 自动体检。
修正项：disputed（≥3 评且 <2.0 分）硬封顶 P2；unvetted（0 评 0 应用）封顶 P1；**反例检测**（领域名词不匹配则降分）。

### 创新 4 · Agent 原生的完整生命周期接口（94 MCP 工具 + 技能层 + 统一 HITL）
内置 chat 可对接 14 个 agent harness，逐 harness 的模型/推理强度/权限模式，审批请求统一成一个对话框。

### 创新 5 · 可审计的工程可信性
hash-pinned 数据快照 + 溯源门禁（`provenance_audit.py`，摘要不符即中止）+ 三源一致性校验 + 诚实失败探针 + 负面结果照实发表。

### 差异化对照表

| 系统 | 稠密检索 | 内容验证 | KB 管理 | 经验生命周期 | Agent 原生 | 开源 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| DPR / 经典 RAG | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| GraphRAG | ✓ | ✗ | 部分 | ✗ | ✗ | ✓ |
| **CRAG** (NAACL'24) | ✓ | 训练评估器（黑箱三分类） | ✗ | ✗ | ✗ | ✓ |
| **Self-RAG** (ICLR'24) | ✓ | reflection token（**需训练**） | ✗ | ✗ | ✗ | ✓ |
| **MCP-Pyserini** (SIGIR'26) | ✓ | ✗ | ✗（仅 ~10 个 IR 工具） | ✗ | ✓（工具包） | ✓ |
| RAGFlow / Dify | ✓ | ✗ | 手动 | ✗ | 部分 | ✓ |
| **本平台 (QDCVR)** | ✓ | **✓ 0–8 三维可解释 rubric** | **✓ 自动归档** | **✓ E0–E12** | **✓ 94 工具全生命周期** | ✓ |

---

## 4 · 证据盘点（实测，可追溯）

| 项 | 数字 | 来源 |
|---|---|---|
| MCP 工具 | 94 = 41 kb\_ + 26 experience\_ + 20 soul\_ + 7 其它 | `kb-mcp/server.py` 逐函数核对 |
| Web 页面 | 11 | `web/pages/` |
| 后端测试 | 139 单测 · kb-mcp 57 E2E · 鉴权 e2e 26/26 · 全功能冒烟 60/60 | `SUBMISSION-MASTER-PLAN.md` |
| 语料 | 100 篇 arXiv 论文 / 26 领域 → 5 个内容类别库，322 docs | `benchmark-suite/PIPELINE.md`（R2） |
| 解析 | 50/50（首轮）→ 3.8M 字符 | `BENCHMARK.md` |
| 三轨对照（100 篇语料，run `experiment_chat_20260922-211000`） | A 平台 9/10 · B 裸 Agent 6/10 · C 稠密 RAG 5/10（pass = 金标可追溯 ∧ ≥60% 关键词） | `results/R2-EXP-3TRACK-REPORT.md` |
| 部件/章节级引用 | 平台 7/10 vs 裸 Agent 4/10 vs 稠密 1/10 | `paper_demo/tex/sec0_abstract.tex` |
| 诚实失败 | 3 个域外探针 → 3 份 not-found 报告，零编造 | 同上 |

> ⚠️ **口径不一致（投稿前必须统一）**：README 的"Live three-track answering A 10/10"来自 **50 篇**语料的老轮次；
> 最新 **100 篇** R2 轮次是 **A 9/10**。论文口径已用 9/10，README 尚未同步。

---

## 5 · 现存硬缺口（诚实清单，决定能投哪个 track）

来自 `docs/paper/cikm/REVIEW-TODO.md` 与 `EDITORIAL-DECISION.md`（五席位评审合成，Major Revision，66 findings）：

| 级别 | 缺口 | 影响 |
|---|---|---|
| 🔴 | **无人工标注 κ**：0–8 rubric 是 LLM 判定，无 3 标注者一致性、无 LLM-vs-human 一致率 | 裁决器是"未校准的仪器"，Full Research 必被打 |
| 🔴 | **无公开多域评测**：所有多域结果都是自建数据，公开集（SciFact/SQuAD）全是单域 | 核心机制（跨域干扰下裁决有效）**未被任何可复现实验证明** |
| 🔴 | **消融与主表协议不一致**：主表 P@5 0.117–0.200，消融 0.723–0.875，差 4–7× | 两个表不能对读，结论不可引用 |
| 🔴 | **无显著性检验**：修订版已全删 p 值/CI | CIKM 审稿人期望有 |
| 🔴 | **无匿名 artifact**：无 qrels、无逐查询分、无 judge prompt | 不可验证 = 不可信 |
| 🟠 | 经验模块无 baseline（对比"直接总结文档"）、五路召回无 leave-one-out、30 天衰减未做敏感性扫描 | 经验生命周期目前是**设计文档**而非已验证贡献 |

**结论：这决定了 track 选择，而不是决定能不能发。**

---

## 6 · 投稿推荐

### 🏆 首选：CIKM 2027 — **Applied Research Papers** track

| 属性 | 事实（据 CIKM 2026 官方，2027 按同模式推算） |
|---|---|
| 会议 | 36th ACM CIKM，2027-10-25~29，**Sydney** |
| 截稿 | Abstract **~2027-05-16** / Paper **~2027-05-23 AoE**（2026 模式） |
| 页数 | **≤7 页含附录与致谢**，GenAI Usage Disclosure 与参考文献**不限页** |
| 评审 | **单盲**（须署姓名单位）；ACM `sigconf` 双栏 |
| ⚠️ Desk-reject 陷阱 | **必须在 EasyChair 提名至少一位作者为审稿人，未提名直接拒稿** |

**为什么是它（四条硬理由）**

1. **官方明文放宽新颖性定义**：Applied Research track 写明"novelty 一般不必来自新的研究贡献，可来自**应用域选择、工程设计、可用性方法或业务用例**"——这正是本平台的最强项，且**绕开第 5 节里最致命的评测严谨性短板**。
2. **主题一级匹配**：CIKM = IR + KM + DB + DM；2026 CFP 新增 **"Agentic AI for Information and Knowledge Tasks"** 为一等主题，本平台的 agent-native 94 工具面正中靶心。
3. **资产已齐**：开源仓库 + 真实截图 + 3 分钟演示视频 + 可复现 benchmark 流水线 + 100 篇语料实例——Applied/Resource/Demo 三个 track 的准入条件你已经满足。
4. **声誉够**：ACM 主办 35 年，h5-index 48，CORE A* / CCF-B。

**同一份工作的备选 track（不可同时投，concurrent submission ban）**

| Track | 页数 | 适合时机 |
|---|:--:|---|
| **Applied Research**（推荐） | ≤7 | 想讲完整系统 + 部署证据 |
| Resource | ≤4 | 强调开源框架/工具可被他人采用（须公开可访问的代码与文档） |
| Demo | ≤4 + **3 分钟视频** | 你有视频，已有 paper_demo 稿，改动最小 |
| Full Research | ≤10 + 2 页参考文献 | **现在不建议**：第 5 节 5 个 🔴 未闭环前冲 Full Research 概率低 |

### 🥇 期刊第一选择：**Knowledge-Based Systems (KBS)** — Elsevier

| 属性 | 数值 |
|---|---|
| 影响因子 | **7.6–8.0（2025）** |
| 分区 | **中科院 1 区 Top** · JCR **Q1**（计算机：人工智能） |
| 投稿 | Editorial Manager（`KNOSYS`），Hybrid，可自选非 OA |
| 收稿范围 | 明文欢迎"基于知识的**方法、系统、软件工具的新开发与实现**"——系统论文友好度在同类里最高 |

**选它的理由**：KBS 是本平台"**知识库管理 + 经验生命周期 + Agent 系统**"叙事的最自然落点；
它不像 TOIS/TKDE 那样要求你先在公开 IR 基准上证明算法增益，
但对"完整系统 + 真实部署 + 可复现评测"的容忍度明显更高。
风险：1 区 Top 同样卷，且审稿周期波动大（网友反馈从 2–3 个月到 7.8 个月都有），**建议先投会议再扩写期刊版**。

### 期刊梯队（按"质量 × 命中率"排序）

| 排序 | 期刊 | IF(2025) | 级别 | 适配度 | 判断 |
|:--:|---|---|---|---|---|
| 🥇 | **Knowledge-Based Systems** | 7.6–8.0 | 中科院1区Top / JCR Q1 | ★★★★★ | **命中率最高的高质量期刊**，系统论文友好 |
| 🥈 | **Information Processing & Management** | 6.9–8.1 | 中科院1区Top / JCR Q1 / SCI+SSCI / 图情A类 | ★★★★☆ | 方向极对口，但**录取率 <10%**，且要求公开集 + qrels + 显著性；TODO-11/12/20 闭环后再投 |
| 🥉 | **IEEE TKDE** | **11.6** | **CCF-A** / 中科院1区Top | ★★★★☆ | 冲顶用。须按期刊版扩写（正文 12–14 页双栏 + 完整实验 + CRAG/Self-RAG 复现对比），前提是补完 M3/M10/M12 |
| 4 | **ACM TOIS** | 11.2 | CCF-A / JCR Q1 / 中科院2区 | ★★★☆☆ | IR 顶刊，但你的 IR 增量偏薄（自身评审也承认负面结果），需先把多域公开实验做出来 |
| 5 | ACM TiiS | ~2–3 | ACM（无 CCF 等级） | ★★★☆☆ | 若把"Agent 交互 + 统一 HITL"作主干可选；IF 偏低，质量够但不是"高 IF" |
| 6 | SoftwareX / Software Impacts | 低 | — | ★★☆☆☆ | 纯软件论文兜底，能保证见刊但不满足"期刊质量较好" |

### 会议梯队

| 排序 | 会议 | 级别 | 判断 |
|:--:|---|---|---|
| 🥇 | **CIKM 2027（Applied/Resource/Demo）** | CORE A* / CCF-B | **最推荐**，见上 |
| 🥈 | SIGIR 2027 Resource/Demo | **CCF-A** | 截稿更早（约 2027-01），声誉更高；但 IR 内容偏薄是自身评审的共识，适合作为"加速备选" |
| 🥉 | ECML-PKDD 2027 ADS Track | CORE A / CCF-B | Applied Data Science track 专收部署系统，截稿约 2027-03，是 CIKM 之外的好缓冲 |
| — | WWW / KDD / VLDB | CCF-A | 与核心贡献错配（无 Web/挖掘/存储引擎贡献），不建议 |

---

## 7 · CIKM 投稿流程（Applied Research 轨道，按 2026 官方流程还原）

| 阶段 | 时间（2027 推算） | 动作 | 易踩的坑 |
|---|---|---|---|
| **T-8 月 · 定题定人** | 现在 ~ 2027-01 | 锁定作者名单（**Abstract 截止后冻结**）、确定贡献声明、补第 5 节 🔴 缺口 | 作者名单在 abstract 后就改不了 |
| **T-4 月 · 做实验** | 2027-01~04 | ≥5 次重复运行 + SD；显著性检验；人工 κ；公开多域拆分（HotpotQA 支持文档聚成 8–12 个主题库） | 别再"跑一次挑好结果" |
| **T-2 月 · 写稿** | 2027-03~05 | ACM `sigconf` 双栏，**≤7 页含附录**；GenAI Usage Disclosure 与参考文献**不计页数** | 单盲 → **必须带姓名和单位** |
| **T-1 周 · 交 Abstract** | ~2027-05-16 AoE | EasyChair 提交标题+摘要 | Abstract 比全文早一周，别漏 |
| **D-day · 交全文** | ~2027-05-23 AoE | EasyChair 选 **"CIKM 2027 Applied Research"** track，上传 PDF | ⚠️ **必须提名 ≥1 位作者为审稿人，否则 desk reject** |
| **附件/artifact** | 同步 | 匿名 artifact 链接（Zenodo / anonymous.4open.science）；GitHub 代码与文档可引用 | 仓库需去除署名或提供匿名副本 |
| **评审** | ~2027-08-07 | 通知；若有 rebuttal 期则按期提交 | |
| **Camera-ready** | ~2027-08-23 | 终稿 + ACM 版权 + ORCID + 上传 ACM DL | |
| **参会** | 2027-10-25~29 Sydney | **至少一位作者注册并到场报告** | Demo/Resource/Applied 同样要求到场 |

**投稿前自查清单**
- [ ] 单盲格式：作者姓名、单位齐全
- [ ] 页数 ≤7（含附录与致谢），参考文献与 GenAI Disclosure 不计
- [ ] EasyChair 已提名作者审稿人
- [ ] GenAI Usage Disclosure 单独成节，**分别**说明写作 / 代码 / 数据 / 评测工具的使用
- [ ] 匿名 artifact 可访问（含 qrels、逐查询分、judge prompt、模型版本与解码参数）
- [ ] 正文零红色 `[TODO-n]` 标记
- [ ] 所有数字可回溯到带时间戳的运行目录（`results/experiment_chat_<ts>/`）
- [ ] 与 CRAG / Self-RAG / MCP-Pyserini 的边界在 Related Work 里**显式**划清

---

## 8 · 八个月补强路线（决定最终能上哪个 track）

| 阶段 | 时间 | 交付 | 解锁 |
|---|---|---|---|
| P1 校准仪器 | 2026-10~11 | 3 标注者 × 40–60 条 0–8 rubric，报 κ；judge 模型/版本/prompt 固定；阈值敏感性扫描 | 解锁 Full Research 的一半质疑 |
| P2 公开多域 | 2026-11~2027-01 | HotpotQA 支持文档聚成 8–12 主题库，跑 **2×2 析因**（scoping × adjudication）含交互项 | 解锁核心机制声明 |
| P3 协议统一 | 2027-01~02 | 消融与主表同一 query set / qrels / 指标；≥5 次运行 + SD + 显著性 | 解锁主表结论 |
| P4 经验模块 | 2027-02~03 | 无合成 baseline + 一次性 LLM 摘要 baseline（同 judge prompt）；五路召回 leave-one-out | 把 C3 从"设计"变成"贡献" |
| P5 写稿 + 内审 | 2027-03~05 | Applied Research 7 页稿 + 匿名 artifact | 投稿 |

> **兜底**：若 P2/P3 未按期完成，走 Applied Research 并把声明**限定在自建语料**（在摘要和 C1 里明说），
> 而不是在 Full Research 上过度声明——这是评审团给出的两条可接受分支中的第二条。
