# KBQA PIPELINE — 文献入库·复刻入库·出题·三轨对照·分析（可复用全流程）

> **一句话**：从下载真实文献到三轨对照回答再到分析评价的**完整可复现测试流水线**。
> 执行者 = 一个 Agent（读本文档后按 Stage 0→9 顺序执行）；判断性步骤由 Agent
> 亲自完成并落盘为**判断工件**，脚本只消费工件——**全程真实执行，严禁编造结果
> 或用固定脚本生成假数据（这是本 PIPELINE 的第一红线）**。
>
> 产物目录约定：语料 `data/papers/`、导出 md `data/corpus_md/`、
> 全部结果 `results/`（只增不改）。所有命令在 `benchmark-suite/` 下执行。

## Stage 总览（预计总耗时 ~2 小时，其中脚本约 100 分钟）

| Stage | 内容 | 执行体 | 脚本/工件 | 预计 |
|---|---|---|---|---|
| 0 | 服务预检 | Agent | `ragctl status` + `/health` | 1 min |
| 1 | 清空知识库 | 脚本 | `scripts/90_reset.py` | 3 min |
| 2 | 下载 50 篇跨领域论文 | 脚本 | `scripts/91_fetch_papers.py`（幂等） | 1-20 min |
| 3a | 解析 50 篇入中转库 + 导出摘要 | 脚本 | `scripts/60_ingest_phase1_parse.py` | 15-20 min |
| 3b | **A1/A3d 内容分类（Agent 判断件）** | **Agent** | 读 `results/ingest_survey.json` → 写 `data/papers/classification.json` | 15-30 min |
| 3c | 按分类路由建 5 门类库 + 索引 + A6-V | 脚本 | `scripts/61_ingest_phase2_classify.py` | 15-20 min |
| 4 | 全部 part 打内容标签（A3b） | 脚本 | `scripts/62_apply_tags.py` | 7 min |
| 5 | 复现项目：导出 md → 清库 → 三套分块建库 | 脚本 | `scripts/70_repro_ingest.py` + `71_repro_smoke.py` | 45-50 min |
| 5b | **重启后端**（BM25 陈旧索引处置） | Agent | `ragctl restart backend` | 1 min |
| 6 | 10 题检索回归验证 | 脚本 | `scripts/72_bench10_verify.py` | 2 min |
| 7a | **Track A：QDCVR v2 skill 流程（Agent 判断件）** | 脚本+**Agent** | `75_skill_track_phase1.py` → Agent 门控/兜底/五段式回答（写 `skill_track_answers.json`）→ `76_skill_track_phase2.py` | 10-20 min |
| 7b | Track B/C：裸 Agent + dense 复刻 | 脚本 | `scripts/77_tracks_bc.py` | 20-30 min |
| 8 | 报告生成（分轨汇整 MD） | 脚本 | `scripts/74_threeway_report.py` / `78_replication_report.py` | 1 min |
| 9 | **结果分析评价（Agent 判断件）** | **Agent** | 读全部 MD/JSON → 写 `results/ANALYSIS.md` | 15 min |

```bash
# 脚本段一键串行参考（Agent 判断段见各 Stage 说明, 不可跳过）
python scripts/90_reset.py && python scripts/91_fetch_papers.py && \
python scripts/60_ingest_phase1_parse.py &&   # → Agent 写 classification.json
python scripts/61_ingest_phase2_classify.py && python scripts/62_apply_tags.py && \
python scripts/70_repro_ingest.py && python scripts/71_repro_smoke.py && \
# → Agent: ragctl restart backend
python scripts/72_bench10_verify.py && \
python scripts/75_skill_track_phase1.py       # → Agent 写 skill_track_answers.json
python scripts/76_skill_track_phase2.py       # 仅有门控<6 的题目时执行
python scripts/77_tracks_bc.py && \
python scripts/74_threeway_report.py && python scripts/78_replication_report.py
# → Agent 写 results/ANALYSIS.md
```

---

## Stage 0 — 服务预检

```bash
cd <repo-root> && ragctl status        # Backend:8771 / Web:6789 / Neo4j / MinerU 全部 healthy
curl -s http://localhost:8771/health   # {"status":"healthy"}
```
不健康 → `ragctl up --mode dev`（冷启动 ~20s）后再查。依赖：Python 3.11+、curl、
uv、omp（Stage 7）。

## Stage 1 — 清空知识库

```bash
python scripts/90_reset.py
```
通过判据：输出 `ok: true`（catalog=0，幽灵目录兜底清理）。

## Stage 2 — 下载真实文献（幂等）

```bash
python scripts/91_fetch_papers.py
```
- `scripts/91` 内 `SPECS` 定义领域×数量（当前 26 领域 50 篇；8 领域×3、4 领域×2、
  14 领域×1）。Agent 可按需修改 SPECS，但必须重算总数与 TARGET 一致。
- 护栏：https + arXiv host 白名单 + DNS 解析逐 IP 公网校验 + XML 拒绝
  DOCTYPE/ENTITY；传输层 curl（urllib TLS 指纹在本机网络会间歇 406）。
- 通过判据：`data/papers/manifest.json` papers 数 = 50，全部含 sha256。

## Stage 3a — 解析入库到中转库（官方链路）

```bash
python scripts/60_ingest_phase1_parse.py
```
每篇 PDF：`parse_doc`(MinerU) → `kb_doc_save_parsed` 入中转库 `Papers-Inbox`
（A0 同 arxiv_id 去重）。完成后导出 `results/ingest_survey.json`：每篇标题+
正文前 1400 字（**这是 Stage 3b 的唯一分类依据**）。
通过判据：50/50 parsed；全部探针可检索。

## Stage 3b — 内容驱动分类（Agent 判断件 ⭐ 严禁跳过或机械生成）

1. Agent 生成摘要清单并**逐篇研读**：
   ```bash
   python - <<'PY'
   import json, re
   d = json.load(open('results/ingest_survey.json', encoding='utf-8'))
   for i, p in enumerate(d['papers'], 1):
       ex = re.sub(r'\s+', ' ', p['excerpt'])
       print(f"[{i}] {p['field']} | {p['arxiv_id']} | {p['title'][:70]}")
       print(f"    {ex[:330]}")
   PY
   ```
2. 按论文**实际正文内容**把每篇分配到门类库并给 2-3 个内容标签，写入
   `data/papers/classification.json`（schema 见文件内 `classified_by` 说明）。
   - 门类集合由 Agent 依语料构成判定（当前 5 类）。
   - **禁止只看文件名/领域前缀分类**：必须读摘要；与文件名先验相反时以内容为准
     （历史实例：neuroscience 文件名的 SNN 算法论文 → 计算机；agriculture 文件名
     的人口遗传学论文 → 生命科学），并在该条目加 `note` 说明理由。
3. 通过判据：`assign` 键数 = 论文数，无遗漏。

## Stage 3c — 按分类路由入库

```bash
python scripts/61_ingest_phase2_classify.py
```
脚本消费 `classification.json`：建门类库 → 逐篇读 Inbox 全文 → `kb_doc_create`
路由入库 → 删中转库 → batch-index force → A6-V 逐篇在自己门类库内探针 → 门类图谱。
通过判据：`verified == total`（当前=50/50）；`graph` 全 true。

## Stage 4 — 内容标签（A3b）

```bash
python scripts/62_apply_tags.py
```
对每个文档 part 打所属论文的内容标签（大文档自动拆分为 `(part k of N)`）。
通过判据：`tagged ok=N fail=0`。

## Stage 5 — 复现项目入库（RAG 复刻算法的库）

```bash
python scripts/70_repro_ingest.py
python scripts/71_repro_smoke.py
```
- 70：从 5 门类库按篇读回 → `data/corpus_md/*.md`（50 篇）→ 清理
  `LitQA-*`/`Corpus-*` 旧库 → 复现项目自有分块方案建
  `Corpus-Chunks800/Struct/Paras`（Paras 约 11k chunks，最慢 ~35 min）。
- 71：dense 检索冒烟（**必须先 activate_profile 重绑 methods 模块 KB 常量**，
  否则静默检索不存在的库）。
- 通过判据：`exported=50`、三库 probe 全过、smoke `chunks>0`。

## Stage 5b — 重启后端（必做 ⭐）

```bash
cd <repo-root> && ragctl restart backend && curl -s http://localhost:8771/health
```
大批删建后端内存 BM25 索引会陈旧（实测两次：删库重建后检索答案错库），
不重启则 Stage 6/7 的 two_stage 结果不可信。

## Stage 6 — 10 题检索回归（向量优先 = skill Phase 1 同款工具）

```bash
python scripts/72_bench10_verify.py
```
检索通道为 `kb_search_vector` 逐门类合并（QDCVR v2 skill Phase 1 的规定工具）。
通过判据：pass_rate ≥ 90%。低于 90% → 先查 Stage 5b 是否执行，再查金标文档
是否入库（`kb_doc_get_by_tag`）。

## Stage 7a — Track A：QDCVR v2 skill 流程（Agent 判断件 ⭐）

1. 脚本采集（Phase 0/1 工具调用段，全程计时）：
   ```bash
   python scripts/75_skill_track_phase1.py
   ```
   Phase 0 改写表 `REWRITES` 由 Agent 按语料更新（旧语料复跑可沿用）。
   **注意**：检索范围是 5 门类库——整库 `kb_id=""` 会把复现项目的 Corpus-* 索引
   库也搜进来污染结果（实测）。
2. **Agent 研读证据并产出 `results/skill_track_answers.json`**：
   - 导出证据摘要（每题 top-3 的 chunk_text+head_excerpt）逐题研读；
   - 按 0-8 评分细则（主题 0-3 / 场景 0-3 / 证据 0-2）给最高分文档打分：
     **≥6 快速退出；=5 留后备并触发兜底；≤4 立即兜底**；
   - 长文条款：头窗不含答案时按 chunk 锚定 + 续读（`76` 号的定向再检索）；
   - 每题按 skill Phase 3 格式撰写五段式回答（Search Paths / Answer / Sources /
     Confidence / Blind Spots）——**回答只能引用读到的正文，读不到就如实写进
     Blind Spots**。
3. 若存在门控 <6 的题目：
   ```bash
   python scripts/76_skill_track_phase2.py   # PHASE2 表由 Agent 按题填写
   ```
通过判据：10/10 题在 `skill_track_answers.json` 有门控分数与五段式回答；
兜底题在 evidence JSON 里有 phase2 记录。

## Stage 7b — Track B/C

```bash
python scripts/77_tracks_bc.py
```
- B：裸 Agent（omp 保留文件工具，cwd=`data/corpus_md/`，每题独立会话）；
- C：`methods.dense`（Corpus-Chunks800）→ 4000 字符证据包 → 统一作答 prompt。
通过判据：20 条回答（10 题 × 2 轨）全部落盘 `results/track_bc.json`。

## Stage 8 — 报告

```bash
python scripts/74_threeway_report.py     # results/threeway_qa.md（如需与 dense 对照）
python scripts/78_replication_report.py  # results/skill_threeway_replication.md
```
报告只做汇整，**不做任何评价性改写**；回答一律原文引用。

## Stage 9 — 结果分析评价（Agent 判断件 ⭐）

Agent 通读 Stage 6/7/8 的全部 JSON 与 MD，写 `results/ANALYSIS.md`，必须包含：
1. **语料与入库统计**（真实数字取自 upload_parse/repro_ingest/ingest_report）；
2. **检索回归结果**（pass_rate 与失败题逐题归因）；
3. **三轨对照**（时延对比、金标词命中率、弃答/兜底行为）；
4. **诚实披露**（证据预算截断、分块窗口效应、单 LLM 判读的局限、不可复现项）；
5. **结论与改进方向**。
评价只允许引用落盘数字；没有的数字写"未测量"。

---

## 真实执行护栏（红线 ⭐）

1. **禁止编造**：任何 JSON/MD 里的数字与回答必须来自真实工具调用输出；
   Agent 判断件必须基于脚本导出的证据文件，禁止凭空撰写。
2. **判断工件可追溯**：classification.json / skill_track_answers.json 必须能在
   ingest_survey.json / skill_track_evidence.json 中找到对应证据。
3. **产物只增不改**：results/ 下本轮产物不覆盖上一轮（带时间戳的目录），
   脚本级 JSON 允许被新一轮覆盖但 git 可追溯。
4. **失败即停**：任一 Stage 退出码非 0 停止流水线并报告，禁止带病继续。
5. **不挑轮次**：LLM 通道结果有方差，报告完整运行史，禁止重跑挑好结果。

## 故障速查（实测沉淀）

| 症状 | 根因 | 处置 |
|---|---|---|
| two_stage/检索答案错库 | 大批删建后 BM25 内存索引陈旧 | Stage 5b 重启后端 |
| kb_doc_read 按篇名为空 | save_parsed 会再补 `.md`（实际名 `xxx.md.md`） | 用 kb_get_documents 返回的真实名 |
| 按篇名打标签 404 | 大文档 create 时拆 part，整篇名不存在 | 对每个 part 打标（62 号已处理） |
| kb_doc_update_tags 挂死 30s | kb_id 传了中文名（web 层只认 UUID） | kb_list 取 UUID 传入 |
| catalog 瞬时为空 | web 鉴权 60s 负缓存毒化；lightweight 分支上游缺 success 标志时 MCP 原样透传（无 catalog 键） | 等 60s 重试；脚本做双形状回退（catalog → knowledgeBases/kbId，62 号已内置） |
| curl rc=63 | PDF 超 --max-filesize | 已放宽 60MB |
| arXiv API 406 | 3s/请求限流 + urllib 指纹 | 退避重试 + curl 传输（91 已内置） |
| two_stage 按库限定结果错库/整库被 Corpus-* 挤占 | 多代删建后 BM25 内存索引脏化 + 同文重复分块挤占配额（实测 3-7/10） | 回归与 Track A 一律用 `kb_search_vector`（skill Phase 1 规定工具，实测 9-10/10）；two_stage 仅限未建 Corpus-* 时的整库查询 |
