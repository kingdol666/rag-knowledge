# 实验 PIPELINE — 终版复现与验收指导（2026-11-10）

> **一句话**：知识文档管理 + 基于内容的可信检索系统的实验 = 内容认知基线对比（外部） +
> 逐级检索机制消融（内部）。本指导自足：只读本文 + 仓库内脚本即可从零复现全部实验。
> 生成：2026-11-01 · 位置：`review/experiment-redesign-20261101/` · 脚本：`scripts/` · 语料：`corpus/multi-domain-docs-20261101/`

---

## 0. 研究定位与假设

系统 = 知识文档管理（层级库/书架/描述）+ 内容验证可信检索（引用式判卷 fail-closed、行级溯源、诚实拒答）。

| 假设 | 内容 | 检验手段 |
|---|---|---|
| H1 | 逐级检索在多库真实语料上 gold 定位率 ≥ 扁平/通读，且读入字节不随库容增长 | 消融 A0 vs A1/A1b |
| H2 | 内容证据门提升证据精度与拒答正确性，代价≈10s/题判卷延迟 | 消融 A0 vs A2 |
| H3 | 描述层提升跨域路由与定位 | 消融 A0 vs A3 |
| H4 | 可溯源准确性+拒答正确性优于内容认知基线，recall 不劣 | Stage 5；当前内容认知主表因缺 LLM endpoint 未执行，不能宣称已验证 |

## 1. Baseline 设计（外部对照 —— 禁传统 RAG 进主表）

### 1.1 对照分类学

| 类别 | 项目 | 内容认知机制 | 论文 | 优先级 |
|---|---|---|---|---|
| 传统 RAG | BM25/dense/RRF/naive-chunk | 无（纯相似度） | — | 仅附表 sanity 下限 |
| 内容评估类 | **CRAG** | 检索质量评估器（T5）判 Correct/Incorrect/Ambiguous→纠正动作 | arXiv 2401.15884 | **P0** |
| | **Self-RAG** | 反思 token（ISREL/ISSUP/ISUSE）逐条评审检索内容 | ICLR 2024 oral | **P0** |
| 内容结构化类 | **RAPTOR** | 递归聚类+摘要建树，跨层检索 | ICLR 2024 | P1 |
| | **HippoRAG** | LLM OpenIE 内容衍生 KG + Personalized PageRank | NeurIPS 2024 | P1 |
| | **LightRAG** | 实体/关系图 + 双层（细/宏观）检索 | arXiv 2410.05779 | P1 |
| | GraphRAG（Microsoft） | 社区摘要层级全局检索 | arXiv 2404.16130 | P2 可选 |

**裁定**（用户 2026-11-01）：baseline 必须是内容认知检索项目；传统 RAG 不进主表。
**为什么这样比**：这些系统在检索决策中"读取并理解/评估/结构化内容"，与本系统"判卷引擎逐段验证"同族——对比才有信息量。

### 1.2 已克隆仓库（`baselines/`，depth-1 pin）

| 仓库 | commit | 备注 |
|---|---|---|
| CRAG | de7c296 (2024-10-08) | HuskyInSalt/CRAG |
| self-rag | 1fcdc42 (2024-03-19) | AkariAsai/self-rag |
| raptor | 7da1d48 (2024-09-03) | parthsarthi03/raptor |
| HippoRAG | d5c8329 (2026-10-06 活跃) | OSU-NLP-Group/HippoRAG |
| LightRAG | aaebfe1 (2026-10-14 活跃) | HKUDS/LightRAG |

### 1.3 复现纪律（三级）与公平性契约

- **L1 原码复用**：官方代码 + OpenAI 兼容端点（可切本地 vLLM/Ollama，配置集中管理）；跑不通官方模型时如实记录偏差。
- **L2 适配**：语料转换器（本语料 → 各项目输入格式）+ 统一评测 hook。
- **L3 等效复刻**：仅当官方代码不可运行（如 Self-RAG 需专用 reflection-token 模型）——报告显著标注。
- **公平性契约**：同一题集、同一语料、同一判卷双轨（平台 Laya judge + 统一 LLM judge 各记一列，防"裁判即选手"）、同一 embedding/LLM 后端可配置；**旧实验教训**（`benchmark-suite/` 的 6 个基线全是脚本仿写且 PIPELINE 自认"非原论文代码"）——本轮一律真实项目源码。
- **成本闸门**：每基线先跑 20 题子集估成本（LLM 调用数/费用），超预算则降子集并如实报告。

## 2. 消融设计（内部机制隔离 —— 终版口径）

> **执行口径修正（2026-11-02 晚，重测轮）**：readall 臂两处口径缺陷已修复——
> ① 目录**分页取全**（`kb_get_documents` 默认只回 page1/40 条且 oversized 自动截断，旧跑仅枚举 229/879 卷就误称"全库通读"；
> 现按 `page=1,2,…` 直到 `has_more=false`，879 卷全枚举）；② `kb_doc_read` 默认 `limit=200` **行**会把短行文档截掉一半以上
> （实测 12,077/28,314 bytes），现 `limit=100000` 读全卷（与磁盘字节 1:1 对账）。修复后 readall 真实口径
> = **24.3MB/题、897 次调用**（旧报告 3.2MB/题 是截断产物，已作废）。
> A3 臂路由卡随描述层同步剥离（name-only），否则 H3 消融不成立；A0 与 A3 禁止同次调用。
> A0/A3 路由目录卡的就绪门加固：reindex done + 单点探针有命中 ≠ 全部卡向量化完成（实测曾致路由 37.5%，
> 误路由全部吸向最后入库的两张卡）——现轮询至 top_k=20 检出 ≥10 张卡再开跑。
> **终版范围纪律（2026-11-10）**：A1b/A2 必须对十个评测库逐库调用 `kb_search_vector(kb_id=<eval_kb_id>)`，
> 合并后按 score 截 top_k=30；禁止 `kb_id=""` 全平台搜索（旧口径会召回 A3 孪生/生产/Corpus-Chunks800）。
> 终局污染审计必须满足：survivors/top1 不含 `路由目录卡`、A1b/A2 候选路径属于十个 `MD语料-*` 库、qid 每臂唯一。
> floor 终版权威值（卫生平台复跑）：BM25 24/40、dense 19/40、RRF 26/40。

| 臂 | 逐级导航 | 向量 | 证据门 | 定义 | 主指标 |
|---|---|---|---|---|---|
| **A0 完整** | ✅ | ✅ | ✅ | 逐级检索机制全开 | 时间+证据 |
| **A1 逐篇通读**（用户裁定主消融臂） | ❌ | ❌ | ❌ | **不启动逐级检索：按固定顺序一篇一篇读完全部文档再作答**（879 卷 24.3MB/题忠实口径） | **时间+证据** |
| A1b **十库 scoped union 向量** | ❌ | ✅ | ✅ | 隔离“导航”贡献；逐库定向搜索后合并，禁止全平台 `kb_id=""` | 同 |
| A2 无证据门 | ✅ | ✅ | ❌ | 隔离内容验证贡献；与 A0 的终版 qid-paired p=.0227 | 证据精度/幻觉率 |
| A3 无描述层 | ✅（描述剥离重建，路由卡同步 name-only） | ✅ | ✅ | 隔离描述层贡献 | 路由正确率 |

**计量口径（防不公平比较）**：
- **时间双轨**：① `tool_seconds`（MCP 墙钟）② `llm_digest_seconds` = 读入字节 ÷ 消化速率
  （默认 4000 chars/s，出处：librarian 量化事实 735k tokens≈10min；`--digest-rate` 可调）。
  **红线教训**（试点实测）：通读工具时间可以最快（1.6s/题），但每题灌全库字节——试点 107KB/题，
  正式语料 4-5MB/题≈百万 token 级必爆；ladder 字节随候选预算恒定。
- **证据三口径**：gold_hit（金标句进入证据集）、**evidence_focus**（证据字节/全库字节，通读=1.0 无聚焦）、
  first_hit_read_index（通读读到第几篇才命中）。
- 拒答探针（域外题）双轨：机械臂测语料级拒答；**A1-readall 全量版须真实 agent 执行**才测"消化后承认没有"。

## 3. 语料与题集

**语料** `corpus/multi-domain-docs-20261101/`：8 域 18 文档（法律×3 全文 / 政务×2（工作报告 51KB、十四五 190KB）/ 红楼梦×5 回（繁体）/ P&P+MobyDick 整本（738KB/1.2MB）/ arXiv PDF×3 / 医学 OA 综述 XML×2 / K8s 章节×5 / 史记×2 卷）。来源合规（Gutenberg/wikisource/arXiv/EuropePMC OA/Apache-2.0）。
**金标**：manifest 20 题（**每题 evidence_substr 脚本实测命中，20/20**；构建时曾抓出 8 处繁简/版本错位——防编造机制工作正常）。
**外部金标源**：Qasper（`external-datasets/qasper/`，1585 篇完整论文+5049 问答+证据段标注），抽 20-40 题作附加评测。
**层级映射**：域=KB（8 库）→ 主题=书架分组 → 文档描述=入库时赋一句话描述。

---

# Stage 总览（执行顺序与耗时预估）

| Stage | 内容 | 命令入口 | 预计耗时 | 判断件 |
|---|---|---|---|---|
| S0 | 服务预检 | 下方命令 | 1 min | — |
| S1 | 语料校验 | `build_manifest.py` | 1 min | 脚本 |
| S2 | 全量入库 | `s2_ingest_corpus.py` | 15-30 min（PDF 解析链） | 脚本 |
| S3 | 题集构建与校验 | `s3_validate_questions.py` | 30-60 min（Agent 补占位题） | Agent+脚本 |
| S4 | 消融执行 | `s4_run_ablation.py` | 1-3 h（题数×臂） | 脚本+Agent |
| S5 | 基线复现执行 | `113_baselines` 模式重写→`baselines/adapters/` | 0.5-2 天/基线 | L1/L2 |
| S6 | 统计 | `s6_stats.py` | 1 min | 脚本 |
| S7 | 报告 | Agent 判断件 | 1-2 h | Agent |
| S8 | 审计 | 逐数字回溯 | 1 h | Agent |
| S9 | 清场 | kb_delete | 5 min | 脚本 |

---

## Stage 0 — 服务预检

```bash
curl -s -m 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:8771/api/v1/health   # 期望 200
curl -s -m 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:6789/                # 期望 200
curl -s -m 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/sse             # 期望 200
# kb-mcp 8000 挂了（历史 4 例）：
uv run --no-sync --directory kb-mcp python server.py --http    # 后台拉起，12s 内恢复
```

### ★ S0b 树注册表完整性（2026-11-02 新增，重测轮事故沉淀）

**症状**：kb_list 只剩生产库（34），10 个实验库"消失"；磁盘目录与 `.knowledge-base.yml` 完好。
**根因**：web 树服务内存快照跨在 S2 入库窗口中间，其全量回写把 `.tree-fs.json` 的 folder 条目抹掉
（file 条目走 read-modify-write 追加路径幸存——只有 folder 丢失是本事故指纹）。
**修复**：`python scripts/s0b_repair_tree_registry.py`（幂等：从每库 yml 重建 folder 条目，先写备份）。
**预防**：重启服务栈前先杀光全部实例（含 uv/bun 拉起的僵尸链），恢复顺序 backend → kb-mcp；
`Get-NetTCPConnection -LocalPort 8771` 核对监听属主是 venv python 而非 anaconda。
配套预检 `scripts/s0c_platform_probe.py`：①判卷修复活性（bad_request 分类）②10 库向量探针
③题集金标文档×库存交叉核验（72/72）——三者全绿才允许 S4 开跑。

## Stage 1 — 语料落盘校验（防编造红线）

```bash
python scripts/build_manifest.py
# 通过判据：evidence_failures=0；缺语料则先跑 scripts/download_corpus.py + scripts/fetch_wiki_round2.py
python scripts/s3_validate_questions.py --init-from-manifest   # 生成种子题集 questions.jsonl
```

## Stage 2 — 全量入库

```bash
# ① dry-run：核对分卷/PDF 清单（配置阈值=60K，结构感知）
uv run --no-sync --directory kb-mcp python scripts/s2_ingest_corpus.py --dry-run
# ② 正式执行：>60K 文档按结构切分；PDF 走 MinerU 解析链
uv run --no-sync --directory kb-mcp python scripts/s2_ingest_corpus.py
# 产物 artifacts/provenance/s2_ingest_report_v2.json；通过判据：failures=0 且每个文档显式 index_document 后 chunks≥1
# ③ 三源核验：kb_list + .tree-fs.json + 每库 .knowledge-base.yml
```
```

## Stage 3 — 题集构建与校验

```bash
python scripts/s3_validate_questions.py --validate <绝对路径>/artifacts/provenance/questions.jsonl
```
- 终版状态：78 行（72 gold + 4 refusal + 2 cross 占位）；机械锚校验通过；2 道 cross 占位未入五臂主轮，必须在论文中披露。

## Stage 4 — 消融执行（终版入口）

> 终版 evidence 已落在 `artifacts/final_bench/`；重新执行时使用绝对路径。
> A1b/A2 必须是十库 scoped union（逐库定向→按 score 合并）；A3 目录卡库不得与 A1b/A2 全局搜索共存。

```bash
# 终版串行入口（stdio + skip-done + 监护）
bash scripts/supervise_final3.sh
# 单独执行一个臂；已完成 (qid,arm) 会跳过
uv run --no-sync --directory kb-mcp python scripts/s4_run_ablation.py \
  --questions <绝对路径>/artifacts/provenance/questions.jsonl --arms A1b,A2 --skip-done
```
- 通过判据：每臂 n=76、qid 唯一、无 `路由目录卡` survivors/top1、A1b/A2 候选路径均属于十个评测库、A0 route_correct≥90%。
- 终版统计：`python scripts/s6_stats.py <绝对路径>/artifacts/final_bench/s4_traces_final.json --baseline-arm A0`。
- 终版图表：`python scripts/s7_charts.py <绝对路径>/artifacts/final_bench/s4_traces_final.json <绝对路径>/artifacts/final_bench/s5_floor.json`。

## Stage 5 — 基线复现执行（终版状态）

CRAG / Self-RAG / RAPTOR / HippoRAG / LightRAG 源码已 pin 于仓库 `baselines/`，但截至本终版没有 OpenAI-compatible LLM endpoint，**未生成可公平比较的内容认知主表**。因此：
- `artifacts/final_bench/s5_floor.json` 只作为传统检索 sanity floor（BM25 24/40、dense 19/40、RRF 26/40）；
- 不把 floor 冒充 CRAG/Self-RAG 等内容认知 baseline；
- 获得 endpoint 后，按本节原公平性契约跑成本闸（先 20 题），再写入 `results/baselines/<name>/run.json`。

## Stage 6 — 统计

```bash
python scripts/s6_stats.py <绝对路径>/artifacts/final_bench/s4_traces_final.json --baseline-arm A0
```
- 终版输出：`artifacts/final_bench/s6_stats.json`；gold 分母=72；McNemar=qid 配对精确双侧检验。
- 终版权威 p：readall <.0001、A1b=.6875、A2=.0227、A3=.4545。

## Stage 7 — 报告

终版报告：`RESULTS.md`。终版主表、floor 表、机制独立验证、已知限制与每个 Stage 的证据路径均在其中。唯一可引用 bench：`artifacts/final_bench/`。

## Stage 8 — 审计红线

- 每个数字 → `artifacts/final_bench/s4_traces_final.json`/`s6_stats.json` 行级可回溯；
- qid 每臂唯一；n=76/臂；A1b/A2 候选必须属于十个评测 KB；survivors/top1 不含 `路由目录卡`；
- 题目证据锚 → provenance questions/manifest 实测记录；
- 判卷真引擎标记（`real_engine=True`）必须在 trace/案例记录中；
- 复现差距、降级、成本超闸全部如实写入 RESULTS.md。

## Stage 9 — 清场与终态

终版交付目录已经完成清理：
- `artifacts/final_bench/`：唯一可引用的五臂 trace、统计、floor、审计、五图；
- `artifacts/e2e_validation/`：CoT、罪与罚自由入库、Agent、预检和零提示案例证据；
- `artifacts/provenance/`：语料、题集、入库报告、PDF 锚和路由归因；
- 旧 timestamped traces、污染 checkpoint、pilot、混沌期日志均已删除；
- 重新执行时禁止删除 final_bench，新的运行必须先落临时目录，经污染审计后才能替换终版。

---

## 附录 A — 脚本清单（`scripts/`，v3 终版）

| 脚本 | 用途 |
|---|---|
| `run_v4_serial.sh` + `supervise_final3.sh` | **终版入口**：stdio 串行 + 自愈监护（真实死亡判定：SSE curl exit 7 才杀、28=存活） |
| `s0b_repair_tree_registry.py` | 树注册表修复（folder 条目丢失事故，幂等+备份；修后必须重启 web） |
| `s0c_platform_probe.py` / `s0i_final_preflight.py` | 跑批预检：判卷活性 + 10 库题面级探针 + 题集×库存对账 |
| `s0j_final_rebuild.py` / `s0k_chroma_orphan_purge.py` | chroma 干净周期重建（逐卷索引，禁 reindex）+ 孤儿集合清剿 |
| `s2_ingest_corpus.py` / `s2b_ingest_spec.py` | 全量入库（spec 驱动，分卷+PDF 链） |
| `s3_validate_questions.py` | 题集 schema+防编造校验 |
| `s4_run_ablation.py` / `s4b_a3_readiness.py` | 五臂消融执行器（--skip-done 断点续跑；stdio 传输）+ A3 就绪探针 |
| `s5_floor.py` / `s6_stats.py` / `s6c_merge_traces.py` / `s7_charts.py` | floor 下限 / 统计（CI+McNemar）/ 终局合并 / 可视化 |
| `s8_route_v2.py` / `s8c_route_diag.py` | 路由归因实验 / 目录卡对照诊断 |
| `s_agent_sample.py` / `ingest_cot_paper.py` | 真实 Agent 采样（web agent/chat async）/ 单篇 E2E 验证入库 |
| `build_manifest_v2.py` / `reconcile_spec.py` / `merge_spec.py` / `expand_corpus.py` / `download_corpus.py` / `fetch_wiki*.py` / `s6b_increment_medicine.py` | 语料构建溯源链（构建期工具） |

## 附录 B — 已知风险与开放问题（终版）

1. 内容认知主表（CRAG/Self-RAG/RAPTOR/HippoRAG/LightRAG）需要 OpenAI-compatible LLM endpoint；当前只保留 pin 与适配契约，不把 floor 冒充主表 baseline。
2. 真实 Agent 通读拒答臂尚未执行；A1 脚本臂只测全库 bytes/containment。
3. 繁体语料 embedding 扰动：终版案例验证通过繁简双向改写，但主轮仍应按语言/域分层报告。
4. 单行长文档读取窗口会导致 Agent 保守漏读；默认 `limit=200` 行不是完整阅读，终版 readall 显式 `limit=100000`。
5. `kb_reindex` 异步提交可能触发 HNSW 段失配；终版重建使用停机独占 `delete_collection` + 逐卷 `kb_index_document`，禁用 reindex 重建。
6. 运行前必须过 `s0i_final_preflight.py`：10 库题面级探针、MCP 判卷活性、题集/库存对账；A1b/A2 必须 scoped union，禁止空 KB 全平台搜索。

## 附录 C — 终版工件目录约定

```
review/experiment-redesign-20261101/
├── EXPERIMENT-PIPELINE.md   ← 终版自足复现指导
├── RESULTS.md               ← 唯一可引用结果汇总
├── artifacts/
│   ├── artifacts/final_bench/         ← 唯一终局 bench：s4_traces_final/s5_floor/s6_stats/audit/viz
│   ├── artifacts/e2e_validation/      ← CoT/罪与罚/Agent/预检/零提示案例证据
│   └── artifacts/provenance/          ← manifest/questions/spec/入库/PDF锚/路由归因
├── scripts/                 ← 终版执行、预检、修复 SOP、统计和图表脚本
corpus/multi-domain-docs-20261101/   ← 语料（只读）
baselines/                            ← 5 个内容认知项目 pin；主表待 LLM endpoint
```

旧 timestamped traces、pilot、污染 checkpoint、混沌期日志不属于复现输入，已删除。
