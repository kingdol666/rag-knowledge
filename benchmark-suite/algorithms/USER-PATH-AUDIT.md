# 用户文件路径审计 — baseline 复现项目的可用性核查

> 审计日期: 2026-09-16 · 方式: 读原始论文 §4.2 + 逐行读复现代码 + 在线 API 实测 +
> A/B 对照实验 · 可执行回归脚本: [`audit_user_path.py`](audit_user_path.py)(退出码 1 = 检出缺陷)

审计对象: `benchmark-suite/algorithms` — 复现 **DeepRead: Document Structure-Aware
Reasoning to Enhance Agentic Search** (arXiv:2602.05014) Table 1 的对比算法矩阵,
并提供 HTTP API 按算法检索问答。

## 0. 结论摘要

| 问题 | 结论 |
|---|---|
| 算法实现是否与论文一致? | **大体一致, 2 处偏差未登记**(其中 1 处对 baseline 不利) |
| 能否通过 API 选算法检索回答? | ✅ **能** — `/ask` `/compare` 实测通过, 指标/作答/判分/匿名排名齐全 |
| 能否让用户**自己传入文件**? | ❌ **HTTP API 不能**(无上传路由, 语料冻结); 仅库函数可(见 §4) |
| 能否拿到 top-k? | ⚠️ **仅文档级**(`doc_rank`), 无 chunk 级文本与分数 |
| 能否依据检索内容回答? | ⚠️ **能返回答案, 但长文档答案被证据通道缺陷污染**(P0, 见 §2) |

**一句话**: 该复现对**冻结 SciFact 语料**是可靠的(360/360 字段与快照一致),
但**对用户自带文件不成立** — 不是因为没有接口, 而是因为证据通道在长文档上
系统性丢失真正命中的内容。

---

## 1. 与原始论文的设置核对

论文 §4.2 原文(逐条)与实现对照:

| 论文明确要求 | 实现 | 判定 |
|---|---|---|
| single-pass/ITRG: chunk size **800 / overlap 400** | `corpus.chunk_fixed(800,400)` 预切 item | ⚠️ 见 §3.2 |
| single-pass 单轮返 **top-10** | `dense()` k=10 | ✅ |
| rerank 开启时一阶段 **30 候选** → 重排 → 截断至 token 预算 | 30 → LLM listwise → top-10 | ✅ (偏差②已登记) |
| **RAPTOR** Collapsed Tree, node ≤800 tok, **5 层**, cluster top-**5**, 检索 top-**10** 节点 | 同参数; 聚类用 union-find 替代 GMM | ✅ (偏差③已登记) |
| **ITRG** 4 轮 × top-**6** | 4 轮 × top-6, refresh/refine 两版 | ✅ |
| Search-o1/DeepRead: structure chunking **overlap 0**, 每次返 **2 chunks** | `chunk_structure` o0 + top_k=2 | ✅ |
| context expansion 窗口 **(1,1)** | `deepread` 的 Retrieve ω=(1,1) | ✅ |
| **Search-o1 注入文档结构 schema**(原文: *"we additionally inject the document structural schema into the system prompt (matching DeepRead's access to structure)"*) | ❌ 反向: prompt 明写 *"The corpus is a FLAT collection of text chunks (no structure exposed)."* | ❌ **未登记偏差** |
| 策略模型 **DeepSeek v3.2, temperature 0** | omp (实测 provider=ustc/deepseek-flash), **未设 temperature** | ⚠️ 部分登记 |
| Search-o1/DeepRead **最大 50 轮** | cap **8** | ✅ (偏差⑤已登记) |
| dense retriever **Qwen3-embedding-8b** | `BAAI/bge-m3` | ✅ (偏差①已登记) |
| reranker **Qwen3-reranker-8b** | omp Agent listwise 代理 | ✅ (偏差②已登记) |
| 判分 **DeepSeek V3.2** + 2 独立 judge 稳健性 | 单一 omp judge | ✅ (偏差⑨已登记) |

**未登记偏差 A(重要)**: 论文为了让 Search-o1 与 DeepRead 公平对比,**专门把文档
结构 schema 注入 Search-o1 的 system prompt**。复现的 `SEARCH_O1_BOOT`
([`methods.py:270`](methods.py)) 却明确告诉模型"语料是扁平 chunk 集合,不暴露结构"。
这削弱了 baseline,方向对本系统有利,且 `REPRODUCTION-NOTES.md` 未登记。

**未登记偏差 B**: README/VERIFICATION 称复现"Table 1 的**全部**对比算法"。Table 1
实为 9 行(含 `Search-o1 w/ expand`、`DeepRead w/ expand`)。复现 8 个方法覆盖 7 个
方法族 + 本系统 qdcvr;`deepread` 恒开 ω=(1,1)(即 expand 版),非 expand 版与
`search_o1_expand` 未单独实现。建议把措辞改为"Table 1 的 7 个基线方法族"。

---

## 2. 【P0】证据通道缺陷 — 检索对了, 证据丢了

### 2.1 缺陷

后端 `kb_search_vector` **一直返回真实命中的 chunk 文本**:

```json
{"content": "## The Energetic Cost Constraint\n\nA central finding ...",
 "score": 0.6928, "doc_path": "VerifyDemo-Chunks800/orbital-debris-removal__k00.md",
 "kb_id": "e3183a01-...", "chunk_index": 6, "collection": "kb_e3183a01-..."}
```

但复现层 [`methods.py:75-84`](methods.py) 的 `Ctx.vector` **丢弃 `content`**,
改用 `cache/texts_<KB>.json[doc_path]` 里的**整条 item 文本**代替:

```python
out.append({"path": dp, "score": float(h.get("score", 0)),
            "text": self.texts.get(kb, {}).get(dp, {}).get("text", "")})
#           ^^^ 丢掉了 h["content"], 换成整条 item
```

随后各方法再对这条"整条 item 文本"做**头部截断**:
`dense` `[:1400]` (L189) · `itrg` `[:1400]` (L254) · `raptor` `[:1500]` (L215)
· `search_o1` `[:1200]` (L305)。

净效果: **检索命中正确的 chunk, 但交给作答 Agent 的是 item 的前 1400 字符** —
真正命中的那段内容根本没进证据。

### 2.2 实测(3029 字符用户文档)

```
=== 检测 1: 真实命中 chunk vs 复现层实际证据 ===
  后端 top-1: chunk_index=6 score=0.6928 len=494
  'delta-v'                  真实chunk=True   实际证据=False   <== 证据丢失
  '180 metres per second'    真实chunk=True   实际证据=False   <== 证据丢失
  'ion-beam shepherd'        真实chunk=True   实际证据=False   <== 证据丢失
```

后端 top-1 就是答案所在段落(含 `delta-v` / `180 metres per second`)。
`dense_rag` 拿到的是文档前 1400 字符,**不含答案**,于是回答:

> "The provided excerpts do not contain the requested information ... No ion-beam
> shepherd method and no delta-v figure for a spent rocket upper stage appear in
> the evidence, so the question cannot be answered from these excerpts."

同一问题、同一模型、同一 prompt,**只把证据换成后端真实 `content`**:

> "The ion-beam shepherd, proposed by Bombardelli and Pelaez in 2011, removes
> debris without contact ... the required delta-v for a 300 km perigee lowering is
> approximately **180 m/s**, with the transfer taking between **90 and 180 days**."

⇒ 缺陷与修复均已由 A/B 对照证实。复跑: `python audit_user_path.py`。

### 2.3 影响范围

| 文档长度 | `[:1400]` 证据覆盖率 |
|---|---|
| 1278 字符(SciFact 中位摘要) | **100%** ← 缺陷在此不可见 |
| 3029 字符(本次测试文档) | 46.2% |
| 15300 字符(E19 的 ARCHITECTURE.md) | **9.2%** |

- **冻结 SciFact 矩阵也受影响, 不只是用户文档**: `DR-Chunks800` 148 条 item 中
  **61 条(41.2%)超过 1400 字符**被截断, 平均覆盖率 91.6%, 最低 46.5%。
  受影响方法: `dense_rag` `dense_rag_rerank` `itrg_refresh` `itrg_refine`
  `raptor` `search_o1`(6/8)。
- **这正是 360/360 快照核验无法发现它的原因**: 该核验只比 `retrieval` 指标,
  而 `doc_rank` 由 `doc_path` 去重得来, 与证据文本无关 — 检索层指标恒正确。
- **这是 E19"真实场景泛化"结论失效的根因**: `REALSCENARIO-BENCHMARK.md` 里
  "suite 侧 dense_rag(整文档 3200 字符块)"的描述与实际不符 — 实际送作答的是
  该 3200 字符块的**前 1400 字符**。
- **偏差方向**: 削弱 baseline ⇒ 相对有利于本系统。但 E16 实测 **qdcvr 的
  judge 均分 7.70 为全场最低**(其余 8.13–8.93),`hit@1`=0.70 也仅高于 deepread 的
  0.5667;`dense_rag_rerank` hit@1=0.90 / judge 8.67 全场领先。即该缺陷并未被用来
  制造对本系统有利的结论 — 修好后 baseline 只会更强。结论方向仍稳健, 但绝对数值需重跑。

---

## 3. 其他缺陷

### 3.1 【P1】分块保真度未真正落地

论文规定 800/400 **token** 分块;复现用 `chunk_fixed` 预切成 3200 字符的 item,
但每个 item 再经 `kb_index_document(content=...)`
([`index_kb.py:106-110`](index_kb.py)) 交给后端,而后端按
**`vector.chunk_size=500` / `chunk_overlap=50`**(`config.yml`) 重新切块建向量索引。

实测证据: 3029 字符文档的命中 `chunk_index` 最大为 6, `len(content)=494~500`
⇒ 检索实际运行在 **500 字符粒度**,而非论文的 3200 字符粒度。
"chunk 800/400" 只决定了文档如何被预切,并未决定检索粒度。`REPRODUCTION-NOTES.md`
未登记此项(仅提到 "token≈4 chars 近似")。

### 3.2 【P1】HTTP API 不支持用户文件

`api_server.py` 的完整路由面(源码 + 实测 404 双重确认):

```
GET  /health  /methods  /questions
POST /ask     /compare
```

实测 `/upload` `/ingest` `/corpus` `/documents` `/index` 全部 `404 unknown path`。
`/ask` 的语料**恒为冻结 KB-SciFact**;`question` 字段只能换问题,不能换语料。
`connect` 到用户文件的路径只存在于库函数 `user_scenario.py`,且
`scripts/29_real_scenario_test.py` 把文档**写死在源码里**
(`DOCS = [docs/ARCHITECTURE.md, docs/paper/SUBMISSION-MASTER-PLAN.md]`),
没有 `--docs` 参数。E19 的"用户上传"实为"改源码后跑脚本"。

### 3.3 【P2】`/ask` 返回的 top-k 是文档级, 无 chunk 级信息

```json
"retrieval": {"doc_rank": ["32587939", ...], "n_chunks": 10}
```

`doc_rank` 是去重后的文档 id 序列;**没有** chunk 文本、chunk 分数、chunk 坐标。
要"得到 top-k 检索结果"的调用方拿不到证据本体。

### 3.4 【P2】自由文本问题绕过缓存 ⇒ 不可复现

`api_server.py:66` `cache_key = f"{method}_{qid}" if qid else None` —
不带 `qid` 的调用(`question=` 形式,即用户提问形式)**完全不落缓存**。
README 声称"任何通过 API 取得的结果与离线矩阵逐字一致",该性质**只对 `qid` 调用成立**;
用户提问每次都会真实重跑 LLM(实测一次 `/ask` 165s),且结果不可复现/不可审计。

### 3.5 【P3】temperature 未固定

论文明确 *"with a decoding temperature of 0"*。`omp_client.py` 的 `OmpRpc`/`OmpOneshot`
命令行均**未传 temperature**(`omp --mode=rpc --no-session --no-tools --no-lsp` /
`omp -p --mode=json ...`)。因此 README 的"确定性重放"实为**LLM 磁盘缓存回放**,
而非采样确定性;清缓存(`DR_NO_LLM_CACHE=1`)后不可复现。

---

## 4. 实测记录(本次)

| 项 | 命令/请求 | 结果 |
|---|---|---|
| 后端 | `GET :8771/api/v1/health` | `{"status":"healthy","vector":{"ready":true,"embedding_available":true}}` |
| 算法 API | `GET :8790/health` | `8 methods / 30 queries / KB-SciFact 148 docs` |
| 算法注册表 | `GET :8790/methods` | 8 方法 + 论文对应 ✅ |
| 冻结查询 | `GET :8790/questions` | 30 条 ✅ |
| 选算法问答 | `POST /ask {method:dense_rag, question:<自由文本>}` | ✅ 165s, 返回 doc_rank + 作答 |
| 多算法并答 | `POST /compare {qid:sf-003, methods:[qdcvr,dense_rag,deepread], rank:true}` | ✅ 3 方法指标 + 判分(9/10/9)+ 中间 Agent 匿名排名 |
| 用户文件上传 | `POST /upload` 等 5 个路由 | ❌ 全部 404 |
| 用户文件全链路 | `python ask_user_docs.py --docs <新文档> --question ...` | ⚠️ 上传/索引/检索/作答**均跑通**, 但答案被 §2 缺陷污染 |
| 缺陷回归 | `python audit_user_path.py` | ❌ 退出码 1(检出 3 项证据丢失) |

新增可复跑入口:
- [`ask_user_docs.py`](ask_user_docs.py) — 用户自由传文件 + 自由提问 + 选算法(CLI)
- [`audit_user_path.py`](audit_user_path.py) — 证据通道缺陷回归检测(含 A/B 对照)

---

## 5. 建议修复(按优先级)

1. **P0 · `methods.Ctx.vector` 改用后端真实 chunk**
   ```python
   out.append({"path": dp, "score": float(h.get("score", 0)),
               "text": str(h.get("content") or ""),        # ← 用真实命中 chunk
               "chunk_index": h.get("chunk_index")})
   ```
   同时把 `dense`/`itrg`/`raptor`/`search_o1` 的 `[:1400]`/`[:1200]` 头部截断
   改为"按分数装箱至预算",而非"取文本头部"。
   ⚠️ 修完后 E16 矩阵数值会变 ⇒ 需重跑 `run_matrix.py` 全量并重冻
   `docs/paper/cikm/data-snapshot/deepread_matrix.json`(会连带影响论文表格)。
2. **P1 · 给 `search_o1` 补上论文要求的结构 schema 注入**,并在
   `REPRODUCTION-NOTES.md` 登记"Table 1 为 9 行 / 复现 7 个方法族"。
3. **P1 · 登记分块粒度差异**: 检索实际运行在后端 500/50 chunk 上;
   若要与论文 800/400 token 严格对齐,需让索引侧按同一粒度入库。
4. **P2 · API 增加 `POST /index`(收文件)+ `POST /ask` 支持 `corpus` 选择**,
   让用户文件路径与冻结语料路径统一走同一入口。
5. **P2 · `/ask` 返回 chunk 级 top-k**(文本 + 分数 + 坐标),并对自由文本问题
   按 `sha256(question)` 落缓存,恢复可复现性。
6. **P3 · `omp` 调用加 temperature=0**,与论文一致。

---

## 6. 复现命令

```bash
# 前置: 后端 8771 健康; web 6789; omp 可用; .env 含 MCP_AUTH_TOKEN
cd benchmark-suite/algorithms

# 算法 API(若未启动)
python api_server.py &

# 1) 选算法问答(冻结语料, 可复现)
curl -s -X POST http://127.0.0.1:8790/ask \
     -H "Content-Type: application/json" \
     -d '{"method":"deepread","qid":"sf-003","judge":true}'

# 2) 多算法并排 + 匿名排名
curl -s -X POST http://127.0.0.1:8790/compare \
     -H "Content-Type: application/json" \
     -d '{"qid":"sf-003","rank":true}'

# 3) 用户自带文件 → 检索 top-k → 依据检索内容作答(CLI)
python ask_user_docs.py \
    --docs _verify_userdoc/orbital-debris-removal.md \
    --question "How does the ion-beam shepherd remove orbital debris?" \
    --methods qdcvr,dense_rag --prefix VerifyDemo

# 4) 证据通道缺陷回归(退出码 1 = 检出)
python audit_user_path.py --skip-ab
```
