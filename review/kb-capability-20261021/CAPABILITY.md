# 知识库管理全功能与检索全流程 —— 设计真实性审计（2026-10-21）

> 问题：当前系统的设计是否**真正**支持知识库管理全功能与检索全流程？
> 方法：静态映射（功能 → 工具 → 路由 → 代码行号）+ 活体探针（一次性父/子库上
> 真实执行 33 步，含真实 Laya 打分与移动索引卫生）。
> 探针工件：`REPORT.md` / `result.json`（本目录）；运行器：`run_capability_probe.py`。

## 0. 判定

| 问题 | 判定 | 依据 |
|---|---|---|
| **管理全功能？** | **是，覆盖率 12/12 功能组全部有工具承载且活体验证通过**；3 个边界缺口（无 KB 合并工具、无独立拆分工具、rename 无自动索引卫生）+ 2 个已记录缺陷（task-status 滞后、fire-and-forget 索引存在秒级竞态窗口） | §1 矩阵 + §3 缺口 + 探针 33/33 |
| **检索全流程？** | **是。** 六阶段全部可达：gather/judge/read/transport 四类为**服务端强制**（父库递归、two_stage 父库、28K catalog 预算门、Laya fail-closed、移动索引卫生）；rewrite/merge/answer/abstain 为 **workflow 提示层**（设计即如此，论文以 C1–C3 机制/检验分离口径披露） | §2 映射 + 探针检索链五路全中 |

一句话：**设计的承诺是"原语齐全 + 关键环节服务端强制 + 编排层约定"——活体验证表明这个承诺成立**；它不承诺的（语义正确性、rename 卫生、KB 合并）也都如实列在缺口里。

## 1. 管理功能矩阵（12/12 组有实现，全部活体通过）

| # | 功能组 | MCP 工具（kb-mcp/server.py 行号） | Web 路由 | 活体证据 |
|---|---|---|---|---|
| 1 | KB 生命周期 | `kb_create`(446, 支持 `parent_id` 建子库) · `kb_list` · `kb_update` · `kb_delete`(463) | `api/kb/{create,update.put,delete.delete}.ts` | 探针：父+子库创建、列表、删除、清理验证 ✓ |
| 2 | 文档 CRUD | `kb_doc_create`(607, 建后自动后台索引) · `kb_doc_read`(594) · `kb_doc_update_meta`(644) · `kb_doc_update_content`(652) · `kb_doc_delete` · `kb_doc_batch_delete` | `api/kb/documents/*.ts` | 探针：创建/改描述/改正文/删除 ✓ |
| 3 | 移动（含索引卫生） | `kb_doc_move`(698)：单咽喉点完成 删旧 chunk→删旧图节点→新路径重索引，返回 `index_hygiene` 逐项结果（D1 修复） | `api/kb/documents/move.post.ts` | 探针：hygiene 四项全 success，移动后向量**立即**只见新路径（`clean_immediately`，新路径 2 命中/旧路径 0）✓ |
| 4 | 改名 | `kb_doc_update_meta(name)`(644) —— **无索引卫生**（见 G-C） | 同上 update | 未单独活体（论文 E2 已记录缺陷+修法） |
| 5 | 标签 | `kb_doc_update_tags` · `kb_tags_list`(1085) · `kb_tags_cleanup` · `kb_doc_get_by_tag` | `api/kb/tags*.ts`, `documents/tags.patch.ts`, `by-tag.get.ts` | 探针：打标+按标反查 ✓ |
| 6 | 去重审查 | `kb_find_duplicates`(1226, hash+向量两层) —— 设计为**只报不改** | — | 探针：0 重复组 ✓ |
| 7 | 索引维护 | `kb_index_document` · `kb_batch_index` · `kb_reindex`(2390, task+后验证 `_verify: ok`) · `kb_task_status` · `kb_cleanup_orphan_collections` | — | 探针：首建索引 1 chunk，移动/force 重索引后稳定为 2 chunks 且 `_verify: ok` ✓ |
| 8 | 知识图谱 | `kb_graph_build`(2722, task) · `kb_graph_stats/document/related/paths/central/cross_kb/…` | `api/graph/*.ts` | 探针：建图 done（3 关系、识别 1 子库）、文档节点查询 ✓ |
| 9 | 检索原语 | `kb_search` · `kb_search_vector`(2253) · `kb_search_two_stage`(2300) · `kb_search_stats` · `kb_laya_judge`(2863) | `api/kb/search.get.ts` 等 | 探针：五路全中（见 §2）✓ |
| 10 | 经验库 | `experience_*` 26 工具（create 1481 / search_global / drafts / meditation / decay …） | `api/experience/[kbId]/*.ts` | 探针：create→全局检索命中→delete ✓（审批/衰减/冥想未活体，见 G-E） |
| 11 | 解析（采集入口） | `parse_doc`(820) · `parse_doc_batch` · `parse_task_status` · `kb_doc_save_parsed` | `api/parse/*` → backend MinerU | 本轮未跑真实解析（慢路径）；`kb_project_status` 报 `mineru up` ✓ |
| 12 | 项目/文件系统 | `kb_project_status/start/update` · `fs_get_tree/children/upload_file` | `api/filesystem/*` | 探针：`backend UP · web UP · neo4j UP · mineru up`、树可读 ✓ |

覆盖率：**12/12 功能组有工具承载；探针活体覆盖其中 11 组的写路径与读路径（解析组只验证了可用性）**。

## 2. 检索全流程：六阶段 × 实现层

| 阶段 | 实现层 | 证据 |
|---|---|---|
| ① Rewrite（改写为 1–3 检索式） | **workflow 提示层** | `web/server/utils/kb-instruction.ts:44`（preamble 指令；无服务端改写器） |
| ② Gather（召回） | **服务端工具** | 向量：`kb_search_vector` → backend `vector_service.py:175-202` 父库递归（`resolve_kb_ids_with_children`，子库独立 collection）；词×图×稠密：`kb_search_two_stage`(stage1 词 top20→stage2 稠密 top5，可图扩展)；目录阶梯：`kb_get_documents` `view="groups"` 分组图（`server.py:506-584`） |
| ③ Merge/cap（去重、封顶 12） | **workflow 提示层** | `kb-instruction.ts:49`（按 doc_path 去重后送判；无服务端 cap） |
| ④ Judge（内容裁决） | **服务端强制** | `kb_laya_judge`(2863) reference 模式：服务端自取正文→分段→逐段打分→`noul≥0.5` 存活，**fail-closed**（取文失败≠低分）；返回 provenance+唯一全量 `evidence_pack` |
| ⑤ Cut & read（读前 5 / 幸存者） | 服务端读 + workflow 顺序 | `kb_doc_read`（服务端）；读几篇、什么顺序是提示层 |
| ⑥ Answer / Abstain | **workflow 提示层** | 诚实弃答是答案层指令（`kb-instruction.ts` Critical Reminders），非服务端语义分类器 |
| 传输预算（横切） | **服务端强制** | `KB_TOOL_RETURN_BUDGET=28000` chars（`server.py:211`）；catalog 超限自动分页 + `truncated="budget_guard"`（576-584）；`view="groups"` 先给分组图 |
| 端点策略（横切） | **服务端强制** | chat 端点 allow/deny 工具面、超时、turn 上限（`api/kb/agent/chat.post.ts`） |

**活体验证（五路检索 + 裁决，全部命中）**：子库直查 top score 0.7347；**父库递归向量命中（2 chunks）**；**two_stage 在父库上命中**（2026-10-13 曾记录"父库返 0"的可疑不一致，本轮未复现）；keyword 元数据扫描命中；**Laya reference 模式真实打分：real_engine=true，1 段打分 1 段存活，top 0.8838**；域外负控 0 命中。

## 3. 缺口清单（每条：现象 → 证据 → 最小补齐动作）

| # | 缺口 | 证据 | 影响 | 最小补齐 |
|---|---|---|---|---|
| G-A | **无 KB 合并工具** | 95 工具清单无 merge；只能 `kb_doc_move` 逐篇 + `kb_delete` 组合 | 大规模重组慢、非原子 | 加 `kb_merge_kb(source,target)`（复用 move 的卫生咽喉点） |
| G-B | **无独立拆分工具** | 拆分内嵌于入库链（`kb_doc_save_parsed` 30K 门 / `split_large_doc.py` 脚本） | 已入库大文档无法后置拆分 | 加 `kb_doc_split(doc_path, max_chars)`（复用入库拆分器） |
| G-C | **rename 无索引卫生**：`kb_doc_update_meta` 只改元数据 | `server.py:644`（对比 move:698 的 hygiene）；论文 E2 记录 rename 后旧 chunk 存活 18 vs 9，需 force re-index | 改名后向量脏，检索按旧路径命中 | 把 move 的 hygiene 子程序复用到 rename 路径（一次性工作） |
| G-D | `kb_task_status` 完成后仍报 running | 论文 E2 已记录（16 场景中 2 失败之一） | 轮询方需超时兜底 | 状态判定改为 `finished_at` 优先 |
| G-E | 经验库审批/衰减/冥想工具未活体、未规模化 | 本轮仅 create/search/delete；论文 E3 口径（13 草稿、1 场景、审批路径空转） | "全功能"在经验域只到创建与检索 | 复用一次性 KB 跑 approve→verify_content→decay 冒烟 |
| G-F | **fire-and-forget 索引与管理操作存在秒级竞态窗口** | 探针 v1 在 move 后 2s 观察到旧路径 chunk（`update_content` 的后台重索引晚于 hygiene 落库）；v2 加 2s 稳定窗后首查即净（`clean_immediately`）。hygiene 本身四步同步 success | 强一致读不可保证；最终一致成立 | 后台索引任务与 move/rename/reindex 按文档路径串行化（task registry 加 per-doc 锁） |
| G-P | 解析链路（MinerU 真实 PDF→Markdown）本轮未活体 | 慢路径；`kb_project_status` 仅报 `mineru up` | 采集入口未在本轮验证 | 一次性 PDF 入库探针（约 1–3 分钟/篇） |

## 4. 结论

- **管理全功能**：设计的工具面是全的（12/12 功能组、95 工具），活体探针证明写路径→索引→检索→图谱→经验→清理全链真实可用；"全功能"的真实边界是 G-A/G-B/G-C 三处（合并、独立拆分、rename 卫生）与 G-D/G-F 两个可靠性小项——全部有 workaround 且其中三项已在论文 E2 如实披露。
- **检索全流程**：设计上"服务端强制 + 提示层编排"的分层是自洽的，五路召回原语、fail-closed 裁决、预算门、父库递归全部实测工作；流程的完整性最终依赖调用方遵守 lane 指令（rewrite/merge/弃答），这是论文 C1–C3 已声明的机制/检验边界，不是实现缺陷。
- 对论文的意义：本轮活体证据与论文 E2/E4/E5 的口径一致，可作为补充材料的功能合约证明；G-C/G-F 与论文 E2 的 rename 缺陷同类，若补充可并入该披露。
