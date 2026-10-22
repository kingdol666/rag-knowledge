# 平台验收报告（acceptance run 2026-10-21）

> 执行方式：ralph PRD 驱动（`.omc/prd.json` US-001…US-006），每条标准都以
> 当日新证据执行，命令与输出可复跑。范围 = 系统设计层 + skill 层 + 业务/对外
> API export + 测试工件清理 + benchmark pipeline 合理性。

## 0. 结论速览

| 验收域 | 判定 | 一句话 |
|---|---|---|
| US-001 设计层 | **PASS（3 项发现）** | 架构与文档/实现一致；文档端口与工具数漂移（P1/P2）；无 P0 设计缺陷 |
| US-002 Skill 层 | **PASS** | 21 skill 同步 PASS + 15 skill 一致性 8 项检查 0 issue |
| US-003 业务/API export | **PASS（修复后）** | dev_smoke 21/21；MCP 95 工具；132 路由全有 default export；修复 2 处过时测试 + 1 处引擎缺陷 |
| US-004 测试工件清理 | **PASS（1 项遗留）** | 未跟踪文件 59 → 5；31/31 论文工件完好；冻结 manifest 存在清理前已发生的 3 处漂移（根因=冻结后的论文修订未重新冻结，待作者决定） |
| US-005 benchmark pipeline | **PASS（5 项缺口）** | 三检索模式/对照臂/汇整保存可视化齐备且自检 0 fail；全功能中经验/SOUL/生命周期不在套件内；2×2 析因开关仍缺 |
| US-006 验收定义与执行 | **PASS** | 本文档即验收定义 + 证据；独立 reviewer 复核结论见 §6 |

## 1. US-001 设计层检查

### 验证通过的设计点（抽样证据）

- 服务拓扑 = 3 长驻服务 + MCP 层，全部由单一 `config.yml` 驱动；后端
  `/api/v1/health` 返回 `healthy` 且 `vector.ready=true`（dev_smoke #1）。
- 写走 HTTP、读走直读文件、MCP-first 的分层原则与实现一致
  （`web/server/services/kb-search-service.ts` 直读 `.tree-fs.json`；
  `kb-mcp/server.py` 无 HTTP 代码）。
- 后端反僵尸启动守卫存在：`backend/main.py:33-80`（bare `socket.bind` 探测，
  端口被占即拒启并提示 `BACKEND_PORT`）。
- 五层存储 + 三源一致性契约在 `docs/ARCHITECTURE.md` §3 与 verify skill 对应。
- 工具面非阻塞任务模式（parse/graph/reindex 返回 `task_id`）与文档一致。

### 发现清单

| 级别 | 发现 | 证据 | 建议 |
|---|---|---|---|
| **P1（文档）** | `CLAUDE.md` 后端端口全部写 8765（L22/233/336/338/368），与 `config.yml`（dev 8770）、README（8770 + 8771 第二实例说明）、运行实例（8771）三方不一致；按 CLAUDE.md 操作的 agent 会探错端口 | `CLAUDE.md:22,233,336-338,368` vs `config.yml:21` vs `README.md:236,243` | 把 CLAUDE.md 端口统一改为"以 config.yml/.env 为准，当前 dev=8770（多实例时可见 8771）" |
| **P2（文档）** | 工具数漂移：实际 `@mcp.tool`=95、`kb_*`=42；README.md L335 写 "94/41"（同文件 L57/L496 已是 95/42，自相矛盾）；README-zh L57/331/491 全部停在 94/41；ARCHITECTURE.md 通篇 94 | 本日 tools/list=95；`grep -c "@mcp.tool" kb-mcp/server.py`=95 | 三处文档统一为 95/42，并保留 ARCHITECTURE.md 已有的"随版本复核"提示 |
| **P2（代码，已修）** | mock 引擎 result 帧缺 `subtype:'success'`，导致非流式 mock 回复恒报 `success:false`（真引擎均带 subtype；benchmark runner/外部调用方按 success 判单元会误判 mock 失败） | `web/server/engines/mock-engine.ts:81`；修复后实测 `success=True, subtype=success` | 已修复并经运行实例热加载验证 |
| **P2（测试，已修）** | `scripts/dev_smoke.py` 两处过时：① chat SSE 检查未传 `stream:true`（2026-09-28 起 API 默认非流式，必然失败）；② `/meditation/harnesses` 用默认 30s 超时，冷缓存实测 >30s（warm 9s） | 修复前 19/21；修复后 21/21 | 已修复（`stream:True` + timeout=90）；建议 CI/pre-commit 跑 dev_smoke 防再漂移 |
| **P2（运维，已知）** | meditation 冷缓存首击 >30s；kb-mcp :8000 SSE 事件循环历史性僵死（3 次复发）；chat 路径已默认 stdio 挂载构造性消除，SSE 仅剩集成面 | dev_smoke 修复记录；chat_tracks.py `mcpMount` 注释 | 维持现状 + 看门狗自动化；若再复发考虑给 SSE 通道加健康探针自愈 |
| **P2（能力边界，论文已披露）** | 服务端无"关闭内容裁决"开关（`grep enable_judge` 为空）→ 2×2 析因（F1/F2）无法原生运行，E8 只能重建 frozen-pool 协议 | `kb-mcp/server.py` 无该开关；论文 §E8 deviation_from_plan | 若下轮评审要求因果证据，先加开关再跑析因 |

## 2. US-002 Skill 层

- `python scripts/sync_skills.py --check` → **PASS**（21 skill · 13 目标目录，
  事实源 `.claude/skills` 与各镜像一致，AGENTS.md 索引同步）。
- `node scripts/validate_skills.cjs` → **PASS**（载入 15 个 knowledgebase skill，
  8 类检查 0 issue 0 warning：触发词无路由冲突、共享阈值引用权威源、相对引用
  可解析、frontmatter 合法、阶段编号一致）。
- 21 个 skill 的 SKILL.md 全部存在（sync --check 即证）。

## 3. US-003 业务与对外 API export

- `python scripts/dev_smoke.py` → **21/21 PASS**（backend 健康/meditation×3/
  models/config/graph/search×3/experience/soul、web 3 页面、/api/harnesses=15、
  claude/models、mock/codex/dsh diagnostics、mock chat SSE events+result）。
- MCP `tools/list` → **95 个工具**，`kb_laya_judge` 在位；与论文 §7 "95 registered
  tools" 一致。
- `web/server/api` 静态检查 → **132 个路由文件全部含 default export**，无孤儿路由。
- 本会话早前的 harness API 实测（`/api/kb/agent/chat` ingest→retrieve→abstain）：
  claude 12/12、omp 功能全对（工具名遥测为通用 read/write，属适配器映射限制）。

## 4. US-004 测试工件清理（只保留论文引用结果）

### 删除（全部为未跟踪文件；tracked 一律未动）

| 类别 | 路径 |
|---|---|
| 本会话/上会话 harness 测试 | `review/harness-agent-api-20261020/` · `review/harness-ingest-retrieval-20261018/` |
| 未被论文引用的重跑轮 | `benchmark-suite/results/exp_rerun_grade.json`（run_dir 指向 rerun-20261017）· `runs/rerun-20261017/` · `runs/rerun-pilot/` · `runs/rerun5-pilot/`（论文引用的是 **tracked** 的 `runs/rerun5-20261017/` 与 `runs/run-20261013T094350Z-5f9faac/`，二者保留） |
| 临时脚本/中转 | `_spot.py` `_v1.py` `_v2.py` `_v3.py` `.review_tmp_b2-b6.txt` `native_found_tmp.json` `.librarian_out_transformer/` `.librarian_run/` `tmp_librarian_transformer/` |
| 调试残留 | `web/bisect_debug.txt` `web/bisect_out.json` `web/bisect_out2.json` `web/scripts/_mcp-probe-stdio.json` |
| LaTeX 中间产物 | `paper-kbs/{submission,tex,tex/journal,tex/review,tex20}` 下 `main2*.out`/`main_20p.out`/`chk.out`/`_pathtest.out`；`journal_20p/qdcvr_kbs.{bbl,out,pdf}` |
| 过期页面渲染 | `journal_20p/render/final-20261017{,-v2,-v3,-v4}/`（可由当前 PDF 重新生成） |

未跟踪文件数：**59 → 5**（余：`.omc/prd.json`、`.omc/progress.txt`＝本次 ralph
状态；`skills-archive/`＝非测试产物保留；`review/archive-superseded/` 下新增归档
包 2 件，见下）。

### 归档（不可低价再生、论文未引用的评审工作区）

`review/{PROJECT-AUDIT-2026-10-15.md, paper-audit-20261017/, paper-audit-20261018/,
paper-audit-final-20261017/}` → `review/archive-superseded/review-audits-20261015-18.tar.gz`
（附 MANIFEST，注明 20261018 那次为退化自动审计：1 issue、quote_verified=false，
不应作为实质评审结论）。恢复：`tar -xzf` 即可。

### 清理后完整性验证

- 论文引用工件 **31/31 在位**（run-20261013T094350Z、rerun5-20261017、
  exp1/exp5/exp6/exp7/exp8/exp9/exp10/exp11/exp12、两个 grade JSON、
  e5_corrected 题集、107 判分器、e5_numbers.json、冻结 manifest、补充材料 PDF、
  20p/69p 两个 PDF、TEST-RESULTS、stability-20261013、替代语料配方、归档 tarball）。
- `sha256sum -c .frozen-experiment-sha256.txt`：注解/判分器全 OK；**3 处 FAILED
  （n8a/n8b/n8c_eval.tex）为清理前已存在**，清理未引入新漂移（见下）。
- dev_smoke 与 MCP 面不受影响（21/21、95 工具复验）。

### ⚠️ 遗留项（需作者决定，非本次清理造成）

冻结 manifest 钉的是 2026-10-17 20:53 的三个 eval 章节；此后 **23:14 的
a8273b5（final audit）提交与 10-18 的未提交编辑**都改动了这三个文件且未重新冻结
（HEAD 哈希 ≠ manifest ≠ 工作区，三方互异）。论文 Data availability 里"frozen
for this submission … cannot drift"的声明当前对这三节不成立。**二选一**：
(a) 确认当前文本即投稿文本 → 重跑冻结命令并提交（注解部分未变，无需改论文）；
(b) 认为冻结版才是终稿 → 回退 10-17 23:14 之后的改动。在做出决定前，建议**不要
投稿**，否则该声明可被审稿人复算证伪。

## 5. US-005 benchmark pipeline 合理性

### 四个问题的结论（证据 = PIPELINE.md 全文 + 脚本实存 + 117 自检实跑）

**(a) 能否覆盖系统全功能？** 部分能。回答侧 8 项功能（检索召回/路由/裁决/拒答/
引用/长文窗口/同域干扰/跨库）由 V2-Quick10 十题显式覆盖（QK01–QK10 分层表）；
工程侧由 Stage 0–9（下载→解析→分类路由→打标→复刻建库→三轨→报告→分析）覆盖
采集与组织。**缺口**：经验库 26 工具、SOUL 20 工具、生命周期 16 场景、图证据
不在本套件内（它们靠 skill 专项 campaign 与论文 E1–E3 覆盖）；若要求"一条管线
测全功能"，需新增一个功能冒烟 Stage（可复用本次 harness API lifecycle 测试的
形态）。

**(b) 检索多种模式有无独立入口与对照臂？** 有，且分了层：纯检索矩阵
`exp.py --retmodes --ret-baselines bm25,vector,rrf`（`140_retrieval_modes_exp.py`
A/B/C 臂 + 金标验证门）；系统车道本体 `exp.py --chatmodes`（A 钉库向量/B 全库
逐级/C 混合，经 chat API 真跑）；跨系统对照 `runner --tracks a,a2,b,c`（文件
工具证伪臂 = a−a2）。Laya 判卷环境由 `resolve_laya_python()` fail-closed 解析。

**(c) 对照实验是否成立？** 成立且比一般系统论文严格：答案键隔离（import 即断言，
V1）；baseline 与被测同走一个 chat API 作答通道（113）；轨序逐题随机化 + seed +
统一 max-turns（runner）；provenance manifest（git/config/prompt_version/seed）；
L2 外部 judge 与被测系统解耦（110 硬约束拒绝自评）；≥5 次重复 + Wilcoxon/Holm +
bootstrap CI + power（115）；6 项一致性自检（compare_report）+ 39 项管线自检
（117，本日实跑 **38 通过/0 失败/1 警告**，警告=80 题集未建，含端到端 dry-run 链
真实产出 COMPARE.html 与 REPORT.md）。**缺口**：平台无"关裁决"开关 → F1/F2 的
2×2 析因仍跑不了（与论文口径一致，属已披露边界）。

**(d) 结果能否汇整、保存、可视化？** 能：规范 run 目录 `results/runs/run-<utc>-<sha>/`
不可原地覆盖；`track_*.json`/`baselines.json`/`monitor.json`/`judge.json`/
`qrels_scores.json`/`stats.json`/`report.json` 全链机读落盘；人读层有 `SUMMARY.md`、
`COMPARE.md`、离线单文件 `COMPARE.html`（KPI 卡/可排序资源表/功能验证条/逐题并列/
自检区）、`VISUAL_REPORT.html`、论文级 `160_run_paper_pipeline.py` →
`paper_report.json` + `PAPER-REPORT.html` + 19 条 fail-closed 闸门、`116` 的
`REPORT.md`（主表+分层+显著性+未测量项），以及仓库根 `TEST-RESULTS/` 入口与
`verify.py` 独立复算。

### 差距清单（按影响排序）

| # | 缺口 | 影响的验收维度 | 最小补齐动作 |
|---|---|---|---|
| G1 | `qa_v2.json` 80 题六层题集未建（117 唯一警告） | 统计功效路径（V5–V7 全链） | 跑 `112 --skeleton` + 出题 + `--validate --strict-quota` |
| G2 | L2 judge 环境（JUDGE_ENDPOINT/MODEL/KEY）未确认配置 | 主因变量仍是 L1 词法层 | 下轮 campaign 前跑 110 --judge 冒烟 1 题验证 |
| G3 | 无服务端关裁决开关 | F1/F2 因果证据（2×2 析因） | kb-mcp 加 `enable_judge` 参数（默认开，行为不变）后跑 V4 析因 |
| G4 | 经验/SOUL/生命周期/图不在套件内 | "一条管线测全功能" | 新增功能冒烟 Stage（lifecycle+experience+SOUL ask 各 1–2 题，复用 harness API 形态） |
| G5 | qrels 池化标注 + 人工 κ 未做 | IR 指标（P@5/nDCG）与 rubric 校准声明 | 人力步骤；跑 114 --build 后 3 人标注 |
| G6 | 文档口径漂移（见 US-001 P1/P2） | 新人/agent 按文档操作会踩错端口、引错工具数 | 三处文档统一（CLAUDE.md 端口、README L335、README-zh、ARCHITECTURE.md 94→95/42） |

## 6. US-006 验收定义与执行状态

本节即验收定义；每条标准的状态：

| # | 标准 | 状态 | 证据 |
|---|---|---|---|
| A1 | 三服务健康 + 向量就绪 | PASS | dev_smoke #1（healthy, vector.ready） |
| A2 | skill 同步与一致性 0 issue | PASS | sync --check PASS；validate 8/8 |
| A3 | MCP 面与论文一致（95） | PASS | tools/list=95；`@mcp.tool`=95 |
| A4 | 全部 web 路由可加载（default export） | PASS | 132/132 |
| A5 | dev_smoke 全绿 | PASS（修复后） | 19/21 → 21/21 |
| A6 | mock 非流式 success 语义正确 | PASS（修复后） | success=True, subtype=success |
| A7 | 工作区仅存论文相关结果 | PASS | 未跟踪 59→5；删除/归档清单见 §4 |
| A8 | 论文工件完整（31 项抽查） | PASS | 31/31 |
| A9 | 冻结 manifest 可复算 | **FAIL（遗留，非本次造成）** | 3 处 eval tex 漂移，根因 §4；待作者二选一 |
| A10 | 管线自检 0 fail | PASS | 117：38 通过/1 警告/0 失败 |
| A11 | 检索三模式入口齐备 | PASS | retmodes/chatmodes/140/runner 四入口实存 |
| A12 | 对照实验要件齐备 | PASS（G3 开关除外） | 隔离/同通道/随机化/provenance/judge 解耦/统计 |
| A13 | 汇整保存可视化链路 | PASS | 117 dry-run 链真实产出 COMPARE.html+REPORT.md |
| A14 | reviewer 复核 | PASS | general-purpose agent 对照 A1–A13 复核，APPROVE（报告见同目录 `REVIEW.md`） |
| A15 | deslop + 回归 | PASS | ai-slop-cleaner 仅触及本次改动文件；回归 = dev_smoke 21/21 + validate PASS + manifest 结果不变 |

复跑方式：`python scripts/dev_smoke.py`；`python scripts/sync_skills.py --check`；
`node scripts/validate_skills.cjs`；`cd benchmark-suite && python scripts/117_pipeline_selfcheck.py`；
`cd paper-kbs/tex/journal_20p && sha256sum -c .frozen-experiment-sha256.txt`；
`python - <<PY`（MCP tools/list 计数）。

## 7. 投稿前剩余动作（按优先级）

1. **P0**：解决冻结 manifest 三处漂移（§4 遗留项二选一），否则投稿后该声明可被证伪。
2. **P0**：作者占位符（姓名/单位/邮箱/CRediT）——用户已知，投稿前必填。
3. **P1**：页数口径决策（20 页双栏 vs 69 页双倍行距），压缩预案在
   `paper-kbs/notes/page-budget-2026-10-16.md`。
4. **P1**：E5 marker 一致性措辞（"agree … in 18" 应为 "both carry a marker in 18
   cells (3 in neither)"，raw agreement 21/30），连同 manifest 注释里的 "18/30"。
5. **P2**：文档口径统一（G6）；skill 层与本验收无需改动。
