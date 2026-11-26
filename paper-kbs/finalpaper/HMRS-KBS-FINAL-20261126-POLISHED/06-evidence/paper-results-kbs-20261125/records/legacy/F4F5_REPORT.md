# F4/F5 全功能验收报告 — subagent B（2026-11-13）

栈：subagent A Step 0 拉起（backend http://127.0.0.1:6789 + MCP，token 取自 .env `MCP_AUTH_TOKEN`）。
MCP 调用：`python -X utf8 scripts/mcp_call.py <tool> '<json>' --raw`（仓库根）。trace 全量：`trace_b.jsonl`（phase=F4，13 行）。

已知库（Step 0 kb_list 确认全 id）：

| 库 | id | 文档 |
|---|---|---|
| 验收-TinyBERT-1113 | `d77085f1-4e31-4da9-812e-504ac3835b72` | tinybert.md（121 chunks） |
| 验收-WikiQA-1113 | `5053aaf4-a044-4e4f-9388-25052ee28696` | wiki_qa.md（37 chunks） |

---

## F4 整理功能全链（在 验收-WikiQA-1113 上操作）

| # | 步骤 | 工具 | 结果 | 证据 |
|---|---|---|---|---|
| 1 | 创建子库「扩展阅读」 | kb_create(name=扩展阅读, parent_id=5053aaf4…) | **PASS** (0.5s) | 返回 id=`f719c826-e065-4632-9312-c41ad3f9533f`，path=`验收-WikiQA-1113\扩展阅读`，parentId=5053aaf4…，childCount=0 |
| 2 | 移动 wiki_qa.md 到子库 | kb_doc_move(doc_path=验收-WikiQA-1113\\wiki_qa.md, target_kb_id=f719c826…) | **PASS** (1.4s) | 新 path=`验收-WikiQA-1113\扩展阅读\wiki_qa.md`；index_hygiene：旧路径向量清理 cleaned=1、graph 节点删除 nodes_deleted=1、新路径重索引 37 chunks 进 collection `kb_f719c826…`。**探针①子库检索**：kb_search_vector('question answering', kb_id=f719c826…) 命中 3 条，doc_path=`验收-WikiQA-1113/扩展阅读/wiki_qa.md`，top1 score=0.691。**探针②父库递归**：kb_search_vector('question answering', kb_id=5053aaf4…) 命中 3 条同一 doc_path（kb_id=f719c826…，递归下钻生效） |
| 3 | KB 改名卫生 | kb_update(name=验收-WikiQA-1113-rn, **显式带原 description**) → 探针 → 改回 | **PASS** (0.5+0.8+0.5s) | 改名后 id 不变（5053aaf4…）、description 完整保留（规避 name-only 清空陷阱）、path 变为 `验收-WikiQA-1113-rn`、childCount=1；改名后探针仍命中（score=0.691 不变）；改回原名同样显式带 description，path=`验收-WikiQA-1113` |
| 4 | tags 平台级读回 | kb_tags_list | **PASS** (0.5s) | 平台 tags 全表含 `question-answering`（同时含 wiki 文档的 `nlp`、`retrieval`） |
| 5 | 强制重建索引 | kb_reindex(kb_id=5053aaf4…, force=true) → kb_task_status → **+30s 探针** | **PASS** (task 1s + 30s 等待) | task_id=`bff0b8b6acbd`，status=done，success=true（⚠️ 见异常①）；+30s 后探针 kb_search_vector('question answering', kb_id=5053aaf4…) 仍命中 top1 score=0.691 |
| 6 | 三源一致性 | kb_list(lightweight) vs storage/tree-file-system 目录 vs .knowledge-base.yml | **PASS** | ①catalog：parent `5053aaf4…`(path 验收-WikiQA-1113, parent_id=null, doc_count=1) + 子库 `f719c826…`(path 验收-WikiQA-1113\扩展阅读, parent_id=5053aaf4…, doc_count=1)；②磁盘：`验收-WikiQA-1113/{.knowledge-base.yml, 扩展阅读/{.knowledge-base.yml, wiki_qa.md}}`（16238 bytes）；③yml id 正则：父 yml `id: 5053aaf4-a044-4e4f-9388-25052ee28696` = catalog id；子 yml `id: f719c826-e065-4632-9312-c41ad3f9533f` + 文档 `695407b5-…` 与移动响应一致。三源完全一致 |

**F4 结论：6/6 PASS。** 整理链（建子库→移动→索引卫生→改名→tags→reindex→三源一致）全绿。

### F4 异常与观察（均不影响本次验收结论）

1. **父库 reindex 不下钻子库文档**：kb_reindex(kb_id=父库, force=true) 返回 `total_docs=0, total_chunks=0`——文档已在子库 f719c826，父库 reindex 只统计直属文档、未重建子库 collection。+30s 探针仍命中是因为递归查询直接读子库 collection（`kb_f719c826…`）。验收步骤按规格执行、探针通过；建议平台将「kb_id 为父库时 reindex 递归子库（或在返回中显式声明跳过 N 个子库）」列为改进项。
2. **改名不重写向量 chunk 的 doc_path 字符串**：改名 `-rn` 后探针命中的 doc_path 仍显示改名前的 `验收-WikiQA-1113/扩展阅读/wiki_qa.md`（chunk_id_prefix 同）。因本验收随即改回原名，三源一致性未受影响；若改名后不回改，向量层 doc_path 与磁盘路径会暂时不一致，需 reindex 刷新。已在异常①同一改进方向（改名时同步刷新索引元数据）。
3. kb_get_documents(lightweight) 一次返回中出现 `doc_id: null` 的 sub_kb 条目（扩展阅读作为子库目录项混入文档列表，entry_type=sub_kb 可区分）——非缺陷，属设计。

---

## F5 agent/chat harness omp（真实 Agent 车道）

入口：POST `http://127.0.0.1:6789/api/kb/agent/chat`，Authorization: Bearer `.env` 的 MCP_AUTH_TOKEN，body `{"prompt":…,"harness":"omp","permission":"bypassPermissions","mode":"async","timeout_ms":1100000}`；轮询 GET `/api/kb/agent/tasks/<task_id>`（10s 间隔）。完整返回存 `f5_q1.json` / `f5_q2.json`。

### Q1（跨库事实题，两问）— PASS（四维全过）

- task_id：`kbt_mwdu8jpy_a24a66e4`；status：**completed**；耗时：**290.4s**（约 29 轮 10s 轮询）
- 执行：QDCVR 全链（3 次宽网 top_k=30 + 3 次 kb_laya_judge 引用模式 real_engine=true + 2 次 kb_doc_read 逐字核验）
- 回答要点（与原文 ground truth 逐条比对）：
  1. **训练方法**：Transformer 蒸馏 + 两阶段学习框架（预训练阶段 general distillation + 微调阶段 task-specific distillation + 数据增强），三类 loss（embedding / hidden states+attention / prediction logits）✔ 与 tinybert.md 一致
  2. **GLUE 对比**：TinyBERT₄ 保留 **>96.8%** BERTBASE 性能、**7.5x 更小、9.4x 更快**（参数 ~13.3%、推理时间 ~10.6%）；TinyBERT₆ 与 BERT_BASE 持平 ✔ 全部数字与原文一致
  3. **问答系统按领域两类**：**closed-domain / open-domain**（并正确区分了"技术路线"维度的 rule-based/statistical/hybrid/knowledge-graph-based，未混淆）✔ 与 wiki_qa.md 一致
- 引用 doc_path：`验收-TinyBERT-1113/tinybert.md`（库 d77085f1…）＋ `验收-WikiQA-1113/扩展阅读/wiki_qa.md`（库 f719c826…，即 F4 移动后的新子库路径——跨库事实 + 递归定位同时得到端到端证明）
- 判定：
  - 正确性 **PASS**（3 个子答全部与原文一致，数字精确）
  - 溯源 **PASS**（两份文档均给出 doc_path + 库 id，可信度分级 P0）
  - 逐字引用 **PASS**（对原始文件逐字校验：two-stage 框架句、96.8%/7.5x/9.4x 句、13.3%/10.6% 句、三类 loss 句、closed/open-domain 定义句全部精确命中；唯一微瑕：技术路线清单在原文为 markdown 列表多行，回复中拍平为一行，内容逐字相同、非编造）
  - 零编造 **PASS**（主动声明"未检索到第二份独立佐证文档，不做多源交叉声明"，将仅提供背景的 DistilBERT/bert_pretraining 文档排除在数字佐证外）

### Q2（OOD 域外拒答题）— PASS（四维全过）

- task_id：`kbt_mwdu8lbf_47d63dae`；status：**completed**；耗时：**360.3s**
- 执行：改写（含字面变体）→ 2 轮全库宽网（top_k=30，最高分仅 0.5448/0.4944 且均为噪声）→ 2 个文学库定向检索 → kb_laya_judge 13 篇/93 段（engine-yes 55 段，调用方 qrel 复核主题相关 = 0）→ 全库字面扫描 `Nobel|诺贝尔|諾貝爾|文学奖|文學獎`（仅 4 行/3 文件，全为物理奖示例/经济学引文/化学奖引文）→ kb_search 元数据检索 0 命中 → librarian 书架盘点（无新闻/奖项类库）
- 回答要点：**如实报告 NOT_FOUND**——知识库无 2026 年诺贝尔文学奖得主记录，不存在"获奖作品的知识库文档路径"；明确建议接外部权威来源（nobelprize.org）
- 引用 doc_path：正确地**未给出**获奖作品 doc_path；仅引用真实存在的字面命中行（wiki_qa.md 的 Einstein 物理奖示例句，标 P2 不可作答案）
- 判定：
  - 正确性 **PASS**（2026 诺奖内容确实不在库内，拒答是唯一正确行为）
  - 溯源 **PASS**（"未找到"有三层实证：语义/元数据/字面全空集，retrieval.degraded=false 排除检索故障）
  - 逐字引用 **PASS**（Einstein Nobel 例句为原文实引）
  - 零编造 **PASS**（未编造得主姓名、未虚构文档路径、未从高分噪声段推断）

### F5 异常与观察

1. **kb_laya_judge criterion=evidence 无主题相关性过滤**（Q2 实测）：93 段中 55 段 engine-yes，但全是"有证据形态文本"（word2vec/TinyBERT/《罪与罚》等），真正答题的存活数 = 0。omp agent 靠自身 qrel 复核兜住并如实上报；建议平台给 laya_judge 增加 topic-relevance 判据或对 OOD 查询在文档层提示假阳性风险。
2. Q2 期间 1 条 fetch_error（`Corpus-Chunks800/…__k24.md` 取文失败，13 篇候选中 1 篇），agent 已在 fetch_errors[] 中如实披露，不影响 NOT_FOUND 结论（该文档与本问题无关）。
3. 两个任务并行提交、各自 ~5-6 分钟完成，无串扰；async + 轮询机制稳定。

---

## 总结

- **F4：6/6 PASS**（trace_b.jsonl 13 行全记录）。
- **F5：Q1 正确性/溯源/逐字/零编造 四维 PASS；Q2 拒答 四维 PASS**。omp 真实 Agent 车道与 F4 整理后的新状态（文档在子库、跨库）端到端贯通。
- 需平台跟进（非阻断）：父库 reindex 子库下钻、改名后索引 doc_path 同步、laya_judge 主题相关性判据。
