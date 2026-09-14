# algorithms — DeepRead 论文检索算法复现与对比矩阵

复现 **DeepRead: Document Structure-Aware Reasoning to Enhance Agentic Search**
(arXiv:2602.05014) Table 1 的全部对比算法, 在本套件冻结语料 (BEIR SciFact 148
篇, KB-SciFact) 与冻结查询 (30 条 claim, 官方 qrels) 上与 **QDCVR**(本系统
knowledgebase-search skill 真链路)对比:

- 检索层: Hit@k / Recall@k / nDCG@10 / P@5 / MRR(qrels 金标)
- 回答层: 全部方法统一经 **omp RPC Agent** 作答(同一 4000 字符证据预算、
  同一冻结 prompt), 再由**第三方 omp Agent**(独立 fresh 进程, 注入金标文档)
  按 0-10 rubric 打分; 全部提问/证据/回答/判分逐条落盘。

## 方法(8)

| 方法 | 论文对应 | 通道 |
|---|---|---|
| `qdcvr` | 本系统 skill(two-stage + 0.35 阈值 + 内容验证重排) | kb-mcp MCP |
| `dense_rag` | Dense RAG(chunk 800/400, top-10) | chunk KB + 后端嵌入 |
| `dense_rag_rerank` | Dense RAG w/ Reranker(30→重排→10) | + omp listwise 重排 |
| `raptor` | RAPTOR Collapsed Tree(≤800 tok/节点, 5 层, cluster top-5, top-10) | 树 KB + omp 摘要 |
| `itrg_refresh` | ITRG refresh(4 轮 × top-6, 证据仅留本轮) | + omp 假设句 |
| `itrg_refine` | ITRG refine(4 轮 × top-6, 证据累积) | + omp 假设句 |
| `search_o1` | Search-o1(平铺分块, 每次 2 chunks, ≤8 轮) | omp RPC 多回合 |
| `deepread` | DeepRead(TOC + Retrieve ω=(1,1) + ReadSection, ≤8 轮) | omp RPC 多回合 |

忠实度与全部偏差(嵌入模型、重排器代理、轮数上限、语料形态退化等)逐条见
[REPRODUCTION-NOTES.md](REPRODUCTION-NOTES.md)。

## 运行(其他用户/Agent 可照此全自动复现)

前置: 后端 8771 与 web 6789 已启动; 仓库 `.env` 含 `MCP_AUTH_TOKEN`;
`KB-SciFact` 已入库(无则先跑 `scripts/21_std2_ingest.py`)。

```bash
cd benchmark-suite/algorithms

# 0) 端到端冒烟(2 条查询, ~10 分钟): 验证 8 方法 + 作答 + 判分全链路
BENCH_LIMIT=2 python run_matrix.py --stage ingest
BENCH_LIMIT=2 python run_matrix.py --stage raptor      # 首次建树 ~15 分钟
BENCH_LIMIT=2 python run_matrix.py --stage retrieve --stage answer \
                                     --stage judge --stage report

# 1) 全量(30 查询 × 8 方法): 检索层即时完成, LLM 阶段按缓存断点续跑
python run_matrix.py --stage retrieve
python run_matrix.py --stage answer
python run_matrix.py --stage judge
python run_matrix.py --stage report          # → results/run-*/deepread_matrix.json
```

- 并发: `DR_WORKERS=3`(默认 3)。
- 断点续跑: 每次omp 调用与每 (方法, 查询) 的证据/作答/判分都以内容哈希落盘
  `cache/`; 重跑只补缺口。`DR_NO_LLM_CACHE=1` 强制真实重新调用。
- 重建索引/树: `DR_REBUILD_KB=1`。
- LLM 通道: **omp RPC 协议**(`omp --mode=rpc` 常驻会话, agentic 方法多回合
  复用; 独立调用走 `omp -p --mode=json`, 与平台 harness 同款)。模型以本机
  omp 配置为准(实测 provider=ustc, deepseek-flash)。

## API 模式 — 通过 HTTP 选择检索算法问答(127.0.0.1:8790)

```bash
cd benchmark-suite/algorithms
python api_server.py &           # 仅绑定 127.0.0.1; 启动时加载 148 篇金标全文
curl -s http://127.0.0.1:8790/health
curl -s -X POST http://127.0.0.1:8790/ask \
     -H "Content-Type: application/json" \
     -d '{"method":"qdcvr","qid":"sf-003","judge":true}'
curl -s -X POST http://127.0.0.1:8790/compare \
     -H "Content-Type: application/json" \
     -d '{"qid":"sf-003","rank":true}'   # 8 方法同题并答 + 中间 Agent 匿名排名
# 全流程测试(同问题×8方法, 指标+判分+中间Agent排名, 并与 E16 缓存逐字核对):
cd .. && python scripts/27_api_flow_test.py      # BENCH_LIMIT=2 冒烟
```

| 路由 | 作用 |
|---|---|
| `GET /health` | 存活 + 方法清单 + 语料/查询规模 |
| `GET /methods` | 8 算法注册表与论文对应 |
| `GET /questions` | 30 条冻结查询 |
| `POST /ask` | `{method, qid|question, judge}` → 指标 + 回答 + 判分 |
| `POST /compare` | `{qid, methods?, rank}` → 同题多算法并答 + 中间 Agent 排名 |

`/ask`、`/compare` 与 run_matrix 共用同一缓存与同一冻结 prompt ⇒ 任何通过 API
取得的结果与离线矩阵逐字一致(由 27 号脚本的 consistency 断言验证)。

## E17 平台整理功能评价(去重/标签/图谱)

`../scripts/26_platform_ops_eval.py`: 一次性 KB 植入 9 篇文档与 2 组重复
真值 → 度量 kb_find_duplicates 检出、标签内容精确率、cleanup dry-run 完整性、
图谱构建与探针、catalog 无幽灵条目。输出 `results/run-*/platform_ops_eval.json`。

## 产物

| 文件 | 内容 |
|---|---|
| `results/run-*/deepread_matrix.json` | 检索层指标 + 作答 + 判分汇总与逐查询行 |
| `results/run-*/deepread_qa_transcripts.md` | 每条查询 × 每方法的完整问答记录(判分/理由/证据来源) |
| `results/run-*/platform_ops_eval.json` | E17 整理功能指标 |
| `cache/llm_*.json`, `cache/ev_*,ans_*,judge_*.json` | 全部 LLM 调用与阶段产物(可审计/续跑) |
