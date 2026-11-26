# F1/F2/F3 全功能验收报告 — subagent A

- 日期：2026-11-13（作业窗口 01:04–01:40 本地）
- 验收目录：`D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/experiment-redesign-20261101/artifacts/demo-20261113/acceptance/`
- 前置状态：平台栈三端口（MCP 8000 / backend 8771 / web 6789）实探全部 HTTP:000（死栈实锤，被测前置成立）
- 产物：`ensure_stack_output.txt`（Step 0 原文）、`trace.jsonl`（45 条，含 n=0 Step 0 记录 + n=1..44 MCP 调用全记录）

---

## ① Step 0 死栈自启观察记录（被测功能 AC-2.1）

| 项目 | 实测 |
|---|---|
| 死栈确认 | curl 三端口 8000/8771/6789 全部 HTTP:000 |
| 命令 | `python -X utf8 scripts/ensure_stack.py --json`（仓库根执行） |
| 初始检测 | `[check] backend=False web=False mcp_kblist=False catalog=0` —— **三 False 如预期** |
| 自动拉起 | `actions: ["start_backend", "start_web", "start_kbmcp"]`（SOP 顺序 backend→web→kb-mcp） |
| 终态 | `{"checks": {..., "mcp_kblist": true, "catalog_n": 50, "e2e_vector_search": true}, "ready": true}`，退出码 0 |
| 判定 | **PASS** —— 三 False 检测 → 自动拉起三服务 → 端到端真实向量检索验证（非端口探活）→ ready=true，与 AC-2.1 契约逐项吻合 |

## ② F1 管理功能 API 冒烟

| # | 调用 | 参数要点 | 结果 | 判定 |
|---|---|---|---|---|
| n=1 | kb_list | lightweight=true | success=true, **count=50** | PASS |
| n=2 | kb_create | 「验收-TinyBERT-1113」 | kb_id=`d77085f1-4e31-4da9-812e-504ac3835b72`，中文名/描述回显无损 | PASS |
| n=3 | kb_create | 「验收-WikiQA-1113」 | kb_id=`5053aaf4-a044-4e4f-9388-25052ee28696` | PASS |
| n=4 | kb_update | TinyBERT 库改名 →「验收-TinyBERT-1113-v2」 | success=true | PASS（但见缺陷 D1） |
| n=5/6 | kb_search_vector 探针 | scoped + 全局 | scoped success=true 空结果（无文档属预期，status=completed）；全局正常 | PASS |
| kb_list 复核 | 目录层可见新名 `验收-TinyBERT-1113-v2` | — | PASS |
| n=7 | kb_update | 改回「验收-TinyBERT-1113」 | success=true | PASS |
| n=8 | kb_update | 修复 D1（重设 description） | success=true，kb_list 复核描述恢复 | PASS |
| n=9/10 | kb_get_documents | 两库 | 均 `count=0, total=0` | PASS（documentCount=0 达标） |

**F1 总判定：PASS（8/8 步），发现并处置缺陷 D1。**

### 缺陷 D1（F1）：kb_update 仅传 name 时清空 description
- 现象：创建时设置的描述「TinyBERT: distilling BERT for NLP, arXiv 1909.10351 全文」在两次 name-only kb_update 后变为 `""`（kb_list 证实）。
- 语义：`description` 未提供 = 清除，而非"保持不变"。
- 处置：n=8 显式重传 description 修复，kb_list 复核恢复。**建议**：后端将未提供字段语义改为 patch（保持原值）。

## ③ F2 双文献入库

### TinyBERT PDF（parse_doc → kb_doc_save_parsed → kb_index_document）
| 步骤 | 结果 |
|---|---|
| n=11 parse_doc（use_ocr=true） | 异步 task `2cceb364d58f` |
| n=12 parse_task_status（6 次轮询，56s） | done；`markdown_chars=57173`，20 图，输出 `backend/output/30ead82904bc/tinybert.md` |
| 乱码检查 | 标题/摘要正确，U+FFFD 计数 **0**，无乱码 |
| n=13 kb_doc_save_parsed | savedCount=1，doc_id=`2d26598a-5369-4d5d-800f-7787cdbb2387`，57211 字节，tree+yaml 持久化双 true，自动索引 task `b1cae3d2746f` |
| n=15 kb_index_document | **total_chunks=121**（≥1 达标；57K<60K 单文档未拆卷），bge-m3，collection `kb_d77085f1-...` |
| n=18 回查 `TinyBERT distillation GLUE` | top1 **0.654**（chunk 15，"96.8% performance / 9.4x faster"），3/3 相关 | 

### wiki_qa.md（kb_doc_create → kb_index_document）
| 步骤 | 结果 |
|---|---|
| 读源文件 | 16228 字符，U+FFFD=0 |
| n=16 kb_doc_create（@file 载荷） | doc_id=`695407b5-5b85-41cf-8f40-fe2ff2c32df8`，tags=[question-answering, nlp, retrieval] 全部应用 `_tags_applied=true`，自动索引 task `4102297893a8` |
| n=17 kb_index_document | **total_chunks=37**，bge-m3 |
| n=19 回查 `open-domain question answering` | top1 **0.651**（chunk 21，open-domain 定义段），3/3 相关 |

**F2 总判定：PASS（双卷入库、分卷、回查全达标）。** 处置异常 D2（见下）。

### 缺陷 D2（F2）：kb_index_document 的 doc_path 拼接错误
- 现象：n=14 传 `doc_path="验收-TinyBERT-1113\tinybert.md"` 报 404：`Document content not found: 验收-TinyBERT-1113/验收-TinyBERT-1113\tinybert.md` —— 后端把 doc_path 又拼了一层库名前缀。
- 处置：改传库相对路径 `tinybert.md` 成功（n=15）。**建议**：修正 kb_index_document 的路径归一（doc_path 不应再叠加 kb 根）。

## ④ F3 三模式检索验证

| 模式 | 规格 | 实测 | 判定 |
|---|---|---|---|
| F3-1 scoped 向量 | kb_search_vector('knowledge distillation transformer', kb_id=TinyBERT, top_k=5, threshold=0.3) | n=20：**5/5 命中**，全来自 tinybert.md，top **0.692**，均过阈 | **PASS** |
| F3-2 关键词/两阶段 | kb_search_two_stage('TinyBERT GLUE benchmark', kb_id=TinyBERT) | n=21/22/23 三次 504（15s budget 耗尽）→ n=24 kb_search 关键词通道 top1 tinybert.md(score=5) → n=25 排空后重试 **成功**：stage1 keyword 命中 0.920，stage2 返回 5 条全 tinybert.md，bm25_status=ready | **PASS**（经处置） |
| F3-3 跨库全局 | kb_search_vector('question answering open domain', kb_id='', top_k=10, threshold=0.3, balance_kbs=true) 应含 wiki_qa.md | 首测（n=26）与 60s 后重测（n=32）top-10 **均无 wiki_qa.md**；换序/无阈值/direct API top-50 共 5 种探针全部缺席（n=27–33）；scoped 同文档 0.642–0.651 正常 → 定位全局向量通道静默跳过 kb_5053aaf4（后端日志实锤） → `kb_reindex(force=true)` 重建后 **n=43：wiki_qa.md 全局 rank #1（0.622）进入 top-10** | **FAIL→修复→PASS** |
| 内容验证（OVERRIDE 规则） | kb_doc_read 交叉核对 top 命中 | n=44：`验收-WikiQA-1113/wiki_qa.md` 正文与源文件一致、无乱码 | PASS |

### 缺陷 D3（F3，本验收最重要发现）：全局向量通道对"段不可读集合"静默跳过
- 现象：全局/平衡（balance_kbs=true）向量检索对 kb_5053aaf4（新建 WikiQA 库）等 **8 个集合** 的查询在 vector_service 循环内抛异常被 `except: logger.warning + continue` 吞掉，检索照常返回 `success=true, degraded=false`，**调用方无从感知覆盖不全**。
- 日志实锤（backend/logs/backend.log）：
  `Vector query failed in kb_5053aaf4-...: Error executing plan: Internal error: Error creating hnsw segment reader: Nothing found on disk`
- 波及集合（8）：kb_5053aaf4（新）、kb_5bc21b9b、kb_801c7549、kb_a0db9ea9、kb_3d5e65f7、kb_455137b4、kb_1cbebcfc、kb_2222261d（7 个历史库，其中红3d5e65f7 连 scoped 也 0 结果）。
- 特征：跨后端重启稳定（重启后 01:30:37 同 8 集合同错）；scoped（get_collection 句柄）正常、global（list_collections 句柄）失败；kb_search_stats 可见全部 chunk 计数；受影响集合的 HNSW 段文件为无 `index_metadata.pickle` 的 stub。
- 修复实证：`kb_reindex(kb_id=5053aaf4, force=true)` 重建（1 doc/37 chunks/errors=[]/verify ok）后 wiki_qa.md 立即以 rank #1 进入全局 top-10（n=43）。
- 处置建议：① 对新建/重建集合强制 flush 段落盘并在索引完成校验中加"段可读探针"；② 全局检索的 per-collection 异常应在响应中聚合为 degraded_reasons（如 `collection_query_failed: N`），禁止静默降级；③ 对存量 7 个坏段集合批量 kb_reindex。

### 缺陷 D4（F3）：score_threshold 对"短内容降权"结果不生效
- 现象：threshold=0.3 的请求仍返回 0.179/0.159/0.158/0.155 的 `short_content_warning` 结果（n=26/29/32/43 尾部）。降权发生在阈值过滤之后（vector_service.search 先 threshold 后 short-content 降权再排序，且平衡路径不过阈值）。
- 处置：记录；建议降权后二次过阈。

### 异常 D5（F3 过程性）：two_stage 超时排队堆叠
- 现象：n=21/22/23 连续 504（默认 15s budget；显式 response_budget_ms=40000 也 ~16s 返回，budget 未生效）。note 明示"synchronous backend work may still be running"——超时请求后台继续占锁，后续同通道请求继续超时。
- 处置：kb_search（关键词通道）先验证命中（n=24），约 20s 排空后 two_stage 恢复正常（n=25，0.78s 完成）。**建议**：超时应可取消后台同步任务；response_budget_ms 传参未生效需修。

### 观察项 O1：控制台管道中文显示乱码为显示层伪影
- mcp_call 输出经管道由 GBK 终端解码致乱码；kb_create 回显、kb_doc_read、kb_list API 直读均证实存储层编码无损。个别历史库（final-acceptance-standalone 等）的 `锟斤拷` 为历史存量数据问题，与本次作业无关。

## ⑤ 环境处置记录

- 验收中途为修复 D3 做过一次后端重启（kill uvicorn 子进程 45532 + ensure_stack 重拉，ready=true，catalog_n=52=50+2 新库账实相符）；重启后双库 scoped 分数与重启前逐位一致（数据无损，WAL 重放验证）。
- 遗留：除 WikiQA 外的 7 个历史坏段集合未处置（非本验收范围，已列入 D3 建议）；web/端口未做主动干预。

## ⑥ 总结

| 功能块 | 判定 |
|---|---|
| Step 0 死栈自启（AC-2.1） | **PASS** |
| F1 管理冒烟（list/create×2/update/rename/探针/documents×2） | **PASS**（8/8，含 D1 修复） |
| F2 双文献入库（PDF 解析 57173 字符→121 chunks；md 16228 字符→37 chunks；双回查 0.654/0.651） | **PASS** |
| F3 三模式检索（scoped 5/5；keyword/two_stage 命中 0.920；全局 wiki_qa rank#1 0.622） | **PASS**（F3-3 经 kb_reindex 修复后达标） |
| 新发现缺陷 | D1 kb_update 清描述、D2 index 路径拼接、D3 全局通道静默跳坏段集合（高优）、D4 阈值不拦截降权结果、D5 two_stage 超时堆叠 |

无 STACK-NOT-READY 情形；全部作业步骤完成，异常均如实记录于 trace.jsonl（45/45 行有效）与本报告。
