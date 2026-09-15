# REALSCENARIO-TEST-PLAN — 真实场景诊断测试流程（Agent 可执行）

> 目标：把 **同一批用户上传文档 + 同一组问题** 交给 **本项目 QDCVR（生产链路）** 与
> **8 个论文复现检索算法**（E16 同一套实现），记录全部 top-k 命中与回答原文，
> 由独立评审 Agent 打分、中间 Agent 匿名排名，产出 MD + HTML 报告与一致性校验。
>
> 执行者：任何 Agent（逐步执行，每阶段有**命令 → 断言**门，不过即停）。
> 铁律：**不要编造**——所有数字必须来自命令的真实输出；失败如实记录再修。

对应产物：`REALSCENARIO-BENCHMARK.md` / `.html`、`REALSCENARIO-QA-LOG.md/.log`、
`REALSCENARIO-VERIFY.json`、`results/real-scenario-*/real_scenario*.json`。

---

## P0 环境与健康门

```bash
cd rag-knowledge
curl -s -m 5 http://127.0.0.1:8771/api/v1/health     # 断言: "status":"healthy" 且 vector.ready=true
omp --version                                        # 断言: omp/18.x
/usr/bin/grep -E "^HF_|^TRANSFORMERS_" .env          # 断言: HF_HUB_OFFLINE=1 与 TRANSFORMERS_OFFLINE=1 在场
```

- 后端不健康或不在线：`cmd //c "ragctl.bat restart backend"`，30s 后重探。
- `.env` 的 `MCP_AUTH_TOKEN` 是机密：**只检查存在，不打印值**。
- 嵌入模型已离线化（`HF_HUB_OFFLINE=1`）；若向量探针为 0，先查 embedding 日志再继续。

## P1 （可选）启动论文复现 API 在线面

```bash
cd benchmark-suite/algorithms
python api_server.py &        # 127.0.0.1:8790, 加载冻结 SciFact 矩阵(~1-2min)
curl -s http://127.0.0.1:8790/health   # 断言: methods=8, corpus=KB-SciFact
```

在线冒烟（全部命中缓存应秒回）：

```bash
curl -s -X POST http://127.0.0.1:8790/ask -H "Content-Type: application/json" \
  -d '{"method":"qdcvr","qid":"sf-001"}'   # 断言: answer 与 judge 字段非空
curl -s -X POST http://127.0.0.1:8790/compare -H "Content-Type: application/json" \
  -d '{"qid":"sf-003","methods":["qdcvr","dense_rag","deepread"],"rank":true}'
                                           # 断言: middle_agent_ranking 覆盖全部别名
```

## P2 上传文档 + 建索引 + 冒烟（真实用户路径）

被测文档在 `scripts/29_real_scenario_test.py` 的 `DOCS` 常量中声明（默认两份：
`docs/ARCHITECTURE.md` 英文 + `docs/paper/SUBMISSION-MASTER-PLAN.md` 中文，
**不属于任何评测语料**）。换文档 = 改这一处。

```bash
cd benchmark-suite
python scripts/29_real_scenario_test.py --smoke > smoke.log 2>&1   # 断言: exit=0
```

断言（读 smoke.log）：

- `production KB (user upload path)` 阶段打印 `probe_hits` 覆盖全部文档（后台索引可查）；
- 三个基线 KB（`UserDemo-Chunks800/Struct/Paras`）`probe=1`；
- RAPTOR 树打印 `levels` 且 `vector_probe_hits=1`；
- 每个冒烟问题 8 法中抽测的 `[qdcvr|dense_rag]` 行有 `judge=` 数值。

原理：`kb_doc_create` = 平台真实上传契约（tree-fs + fire-and-forget 向量/图索引），
大文档自动拆 `(part N of M)`；基线索引复用 E16 的 `index_kb.build_kb` / `raptor.build_tree`
参数化版本（对源文档按各论文方案分块）。**两侧语料同源**：同一批源文件 + 指纹
（`user_scenario.fingerprint`，SHA-256 前 16 位）。

## P3 全量矩阵（每文档 3 问 × 8 方法）

```bash
python scripts/29_real_scenario_test.py > full.log 2>&1   # 断言: exit=0
```

产物断言（三件套落盘）：

1. `results/real-scenario-<ts>/real_scenario.json`
2. `REALSCENARIO-QA-LOG.log`（控制台实录）与 `REALSCENARIO-QA-LOG.md`（6 问 × 8 法全问答）
3. `REALSCENARIO-BENCHMARK.md`

已知耗时：检索 agentic 方法（search_o1/deepread/itrg）为真实多回合 omp 调用，
3 并发全量约 30-60 分钟（provider 慢时 RAPTOR 建树摘要另需 10-15 分钟，之后有缓存）。

## P4 修复回路（仅当出现空回答行）

两类根因、两种修法（命令自动分流）：

```bash
python scripts/29_real_scenario_test.py --repair real-scenario-<ts>
# 断言: 打印 fallback=[...] 与 regenerated=[...] 并写出 real_scenario_repaired.json
```

- a) 中文回答含未转义 ASCII 引号 → 严格 JSON 解析失败但内容完好 → 字段级回退解析恢复；
- b) provider 截断（如 `{"answer": "本论文总`）→ 该 (问题, 方法) 单元整体重生成
  （检索→作答→评审），`DR_NO_LLM_CACHE=1` 绕开被污染缓存。
- 原 `real_scenario.json` 按不可变约定保留；报告优先读 repaired 副本。

## P5 报告与一致性校验

```bash
python scripts/32_real_scenario_report.py            # 默认取最新运行(优先 repaired)
                                                     # 断言: exit=0 且 7 项检查全 PASS
cat REALSCENARIO-VERIFY.json                          # 断言: all_fatal_pass=true
```

七项校验的含义：同文档（指纹复算一致）、同问题（唯一 qid 列表 × 8 方法行完整）、
回答完整、48/48 评审覆盖、QA log 记录数（6 头 / 48 法）、hit@1 可由 doc_rank 重算、
生产 KB 在目录中在线。

## P6 验收清单（Agent 逐项核对后交付）

- [ ] P0-P5 全部断言通过；
- [ ] `REALSCENARIO-BENCHMARK.md` 含：主表（hit@1/@3/@5、judge 均分/中位、
      judge 胜出、中间 Agent 第一、零编造、时延、LLM 调用）、金标位置矩阵、
      逐题胜出、**评价（基线 vs 本项目）**、一致性校验表；
- [ ] `REALSCENARIO-BENCHMARK.html` 浏览器可打开（Chart.js 双图 + 逐题九系统
      回答卡，含回答原文与评审意见）；
- [ ] `REALSCENARIO-QA-LOG.md` 每问含 QUESTION/EXPECTED/GOLD QUOTE 与 8 个
      `--- method=` 块（doc_rank、metrics、trace、evidence、ANSWER、JUDGE）。

## 已知陷阱速查（详见 algorithms/REPRODUCTION-NOTES.md）

- KB 限定两阶段检索对**新建库**曾静默 0 召回（BM25 增量索引 kb_id 名字 vs UUID，
  P1 已修复于 `backend/app/api/routes/search.py`）——若复现历史版本需带此补丁；
- `kb_reindex` 只重建向量+图，不建 BM25；其 task_id 只在发起的 MCP stdio 进程内有效；
- 评分解释：QDCVR 证据通道读 top-2 part（~1KB 粒度），检索命中但答案段被切分遗漏时
  按设计**弃答**（零编造），判分低是机制边界而非失效；
- omp 单回合 5-45s、provider 高峰更慢；全部调用按 (stage, prompt) 哈希缓存，重跑零成本。
