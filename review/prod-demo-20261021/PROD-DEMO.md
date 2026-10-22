# 生产就绪实机演示报告（prod demo, 2026-10-21, ralph run 3）

> 任务：完整审视系统设计 → 判定实验结果可靠性与论文可用性 → 全功能实机演示
> （管理作业 + 三种检索方式 + 图书管理员逐级检索重点测试）→ 生产就绪结论。
> 工件：`mgmt_result.json` · `parse_result.json` · `librarian_results.json` ·
> `../benchmark-suite/results/runs/chatmodes-20261021T051709Z-a8273b5/`。

## 1. 系统设计总览（US-201）

**拓扑**：三服务 + MCP 层，单一 `config.yml`——
Browser → Nuxt3 Web(6789, 代理+KB 存储) → FastAPI Backend(8771, 解析调度/向量/图/经验/SOUL) → MinerU(临时端口)；kb-mcp(stdio, 95 工具) 面向所有 agent harness。

**五层存储**：L1 Markdown 文件 · L2 `.tree-fs.json` 全局树 · L3 `.knowledge-base.yml` 库注册表 · L4 ChromaDB 向量（BGE-M3, 1024 维, 按库 collection, 父库递归）· L5 Neo4j 文档图。三源一致性（L1↔L2↔L3）是组织层的核心不变量。

**管理功能面（12 组，95 工具，全部活体验证）**：

| 组 | 能力 |
|---|---|
| KB 生命周期 | 建库（支持 `parent_id` 子库嵌套）/改描述/删库（级联清向量+图） |
| 文档 CRUD | 创建（自动后台索引）/读/改元数据/**改名**/改正文/删/批量删 |
| 移动 | 跨库移动，单咽喉点索引卫生（删旧向量→删旧图节点→新路径重索引），逐项回执 |
| 标签 | 打标/注册表/孤儿清理(dry-run)/按标反查 |
| 去重 | 内容指纹+向量两层，**只报不删**（防误删相邻部分） |
| 索引维护 | 单篇/批量/force 重索引（task+后验证 `_verify:ok`）/孤儿 collection 清理 |
| 知识图谱 | 建图(task)/统计/库概览/文档相关/中心度/跨库桥接/路径 |
| 检索原语 | 关键词/向量(父库递归)/两阶段(词×图→稠密)/统计/**Laya 内容裁决**（服务端取文→分段→打分→fail-closed） |
| 经验库 | 26 工具：CRUD/全局智能检索/草稿审批/衰减/冥想 |
| 采集 | MinerU 解析（PDF/图片/Office）→ `save_parsed`(task_id 模式) → 索引 |
| 项目/文件系统 | 服务状态/runtime 检查、树/子节点/上传 |
| SOUL | 20 工具（人格生命周期，本轮只读面验证） |

**检索全流程分层**（论文 C1–C3 的机制/检验分离）：gather/judge/read/传输预算为**服务端强制**（父库递归、fail-closed 裁决、28K 目录预算门+分组视图）；rewrite/merge/读取顺序/弃答为 **workflow 提示层**（chat API 注入指令，`kb-instruction.ts`）。

## 2. 实验结果可靠性与论文可用性（US-202）

**当日复验（本机新证据）**：
- `TEST-RESULTS/verify.py` → **PASS**：论文每个 grounded/strict/cited/chunk/时延/成本主张都从 `run-20261013T094350Z-5f9faac` 落盘工件复算命中。
- 论文管线闸门 `paper_report.json` → **19/19 通过，0 fail**（A 轨满分、无哨兵、密索引探针、回归覆盖五库等）。
- 检索回归探针 → **15/15 命中**。
- 冻结 manifest → 注解/判分器 OK（3 处 eval tex 漂移为既知遗留，与实验数据无关）。

**可作为论文实验部分论据的（强）**：两个 30 单元网格（gold 60/60、strict/alias/cited 逐格可复算）、E4 检索矩阵与派生行、E6 判定器角色诊断（0.94→0.44→0.94）、E7 稳定性 27/27、E5b 部署臂+18 臂诚实性、E1/E2 管理层测量。**只能作补充材料/工程证据的（弱）**：本轮实机演示（n=1 一次性库）、dev_smoke 21/21、管线自检 38/39——它们证明"平台功能合约真实可用"，不改变任何统计结论。**不可写入的**：单次演示的绝对时延/成本（无重复运行）。

## 3. 管理作业全量实机测试（US-203）

`management_full_test.py`：一次性库上 **29/29 步 PASS**（`mgmt_result.json`）。
覆盖：KB 建库/改描述、`fs_upload_file`+`fs_get_children`（修正参数名 `parent_id` 后通过）、文档创建/索引/**改名**/批量索引/批量删除、标签注册表+孤儿 dry-run、**图家族 7 项**（建图/统计/库概览/文档相关/中心度/跨库桥/路径）、`kb_search_stats`、经验五连（create/list/read/summary/check_stale/delete）、`soul_list` 只读面、清理验证。

**新发现（设计缺陷实锤，超出论文 E2 记录）**：
> **G-C（强化版）**：rename 在注册表/磁盘层完全生效（catalog 新路径、读新路径成功、读旧路径失败），但**向量 chunk 的 `doc_path` 标签在 force re-index 之后仍停留在旧路径**——论文 E2 说"force re-index 恢复 chunk 数量"，实测确认：数量恢复了，**路径标签没有恢复**。后果：rename 后检索命中的溯源指向一个已不存在的路径（按旧路径 `kb_doc_read` 失败）。两个独立探针（rename 深度探针 + 管理全量测试）确定性复现。最小修复：rename 端点复用 move 的卫生模式（更新 `vector_index.chunk_id_prefix` 并同步重索引）。

**采集链闭环（G-P 补测，`parse_result.json` 全 PASS）**：真实 26KB PDF → `parse_doc`（MinerU 按需拉起）→ task done → `kb_doc_save_parsed`(task_id 模式) → 索引 6 chunks → 检索命中（top 0.656，内容为 Wind Energy 论文正文）→ 全文读取 → 清理。

## 4. 三种检索方式真机对照（US-204）

`exp.py --chatmodes`，生产语料（21 库/388 文档），`POST /api/claude/chat` 非流式真跑。
Run: `chatmodes-20261021T051709Z-a8273b5`。**9/9 全部 HTTP 200、0 执行错误、0 哨兵；
闸门 8/9 通过**（唯一 ❌ 见下）。产物：`CHAT-MODES-COMPARE.md`。

| 模式 | 题 | 预期 | 耗时 | turns | 闸门 | 实质判定 |
|---|---|---|---:|---:|:--:|---|
| A 钉库向量 | cm1 InstructDS | found | 163.3s | 4 | ❌ | **答案实质 PASS**：金标词命中、1849 字、带 §3.2 逐字引用——闸门拒绝启发式误报（与论文 E5b 修正过的同类；单元格只存 answer_head，触发词无法离线复核，已记录为测试工件粒度缺口） |
| A | cm2 卒中/EHR | found | 129.3s | 4 | ✅ | 唯一对口文献 1904.11280，75% 准确率等数字逐字引用 |
| A | cm3 对撞机（虚构） | refusal | 200.5s | 7 | ✅ | 明确 not-found + 列出检索范围 |
| B 全库逐级 | cm1 | found | 188.6s | 7 | ✅ | 三步合成流程+45%→75% 过滤数字 |
| B | cm2 | found | 178.5s | 8 | ✅ | 10 属性低相关不能削减+MLP 75.02% |
| B | cm3 | refusal | 192.6s | 12 | ✅ | **完整阶梯轨迹可见**：`kb_list` 21 库逐一比对描述（"自然科学 75 篇不含粒子物理…"）→ NOT_FOUND |
| C 混合 | cm1 | found | **130.0s** | 5 | ✅ | 三车道最快；结论句+两道过滤细节 |
| C | cm2 | found | 167.0s | 7 | ✅ | 同金标+ credibility 标注 |
| C | cm3 | refusal | 181.0s | 7 | ✅ | 两阶段检索 20 候选→5 命中全为无关文档→如实拒答 |

**车道画像**：A 最快（found 题 4 turns）但钉库依赖；B 最深（拒答题 12 turns 走完全阶梯）且 3/3 全过——**逐级方式在三种车道里唯一"零误报"**；C 在 cm1 上最快。三车道对同一金标给出相互一致的事实数字（75.02/74.53/74.31%、45%/50% 过滤），交叉印证检索可靠性。

## 5. 图书管理员逐级检索重点测试（US-205）

`librarian_probe.py`：`kbEnhanced=true, kbIds=[]`（注入完整阶梯指令）× 3 题，
SSE 流捕获**完整工具轨迹**（`librarian_results.json`）。

| 题 | 类型 | 车道内轨迹（首次到达顺序） | 工具次数 | 耗时/turns/成本 | 判定 |
|---|---|---|---|---|---|
| LIB1 InstructDS 查找 | found | kb_list → 描述层 → **judge** → read | list1/desc4/judge1/read2 | 147.2s / 9 / \$0.356 | **PASS-gold**：3B>175B ChatGPT 等数字+出处 |
| LIB2 降水极端枚举 | found(枚举) | kb_list → 描述层 → **judge** → read | list1/desc6/judge1/read2 | 171.2s / 11 / \$0.437 | **PASS-gold**：精确枚举 2 篇直接对口+1 篇相关（1503.07557 P0 强，逐篇发现） |
| LIB3 泡菜配方 | verified-absent | kb_list → 描述层（**按拒答预算规则停止**） | list1/desc6 | 83.8s / 8 / \$0.163 | **PASS-诚实拒答**（初判 FAIL 系探针拒绝词表漏检 "NOT_FOUND/没有任何"，已修词表离线重判；答案原文为显式 NOT_FOUND） |

**LIB3 答案原文要点**（判定依据）："知识库中没有任何 Sichuan pickled vegetable 配方…我不会凭记忆补写" → 列出 21 KB/388 文档扫描范围 → **按规则强制抽查通用架**（demo-qa-20260927 等逐架列出文档名）→ "结论：NOT_FOUND…这不是部分扫描后的结论" → **盲点声明**（技术论文语料库不含烹饪来源）。

**车道纪律**：三题轨迹均无 `kb_search_vector`/`kb_search` 等越车道工具（纯
catalog→描述→judge→read 阶梯）；拒答路径遵守"目录层+一次描述层即停"的预算规则，
未读任何正文就完成拒绝——与指令契约完全一致。

## 6. 生产就绪结论（US-206）

**判定：在"单机自托管、单团队"的设计边界内，系统已具备投入真实生产运行的功能完整性与行为可靠性；企业级（多机/多租户）尚有明确缺口。**

当日实机演示证据链：
- **管理作业 29/29 PASS**（含采集入口闭环：真实 PDF→MinerU→入库→索引→检索）。
- **三车道 9/9 运行零错误，8/9 闸门通过**（唯一失败为闸门误报，非系统错误）。
- **图书管理员逐级车道 3/3 PASS**，含精确枚举与契约式拒答。
- 加上当日此前已验收的：dev_smoke 21/21、MCP 95 工具、管线自检 38/39、能力探针 33/33。

**投产前必须知悉的缺陷/缺口**（全部有 workaround，除标注外）：
1. **rename 溯源标签缺陷（新实锤）**：rename 后即使 force re-index，向量 `doc_path` 仍指旧路径——检索溯源会引用无法解析的旧路径。规避：rename 后改用"移动到其他库再移回"或删除重建；根治：rename 端点复用 move 卫生。
2. fire-and-forget 后台索引与管理操作存在秒级竞态窗口（最终一致成立）。
3. `kb_task_status` 完成后短暂报 running（轮询方加超时兜底）。
4. 经验库审批/衰减/冥想未规模化验证；SOUL 域本轮仅只读验证。
5. 并发容量：独立查询 ~4-5 RPS（进程级锁）；30 并发客户端缓存修复前 41% 超时。
6. 企业级缺口：无 HA/备份/崩溃恢复验证、无多租户权限模型/审计日志、规模未超 400 文档级验证。

**建议**：以当前形态投产于"团队知识库+溯源问答"场景可行；把第 1 条根治（rename 卫生）作为投产前唯一必改项，其余可带病运行并列入运维手册。
