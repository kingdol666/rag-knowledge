# 全功能验收报告（ACCEPTANCE-REPORT-20261113）

> 验收方式：杀净栈（含 spawn 孤儿句柄持有者）→ subagent 经 skill Step 0 死栈自启 → 全功能 API + 实机作业。
> 主席独立复核所有关键数字与金标。PRD：`.omc/prd.json`（AC-1..AC-4）。

## 总判定：**ACCEPT**（4/4 AC PASS；发现 6 项产品缺陷/观察，全部记录且不阻断）

---

## AC-1 测试文献与环境准备 — PASS
- TinyBERT PDF（1909.10351，12 页/50,523 字符）金标派发前独立提取："more than 96.8% the performance of its teacher BERTBASE on GLUE benchmark, while being 7.5x smaller and 9.4x faster"
- Wikipedia QA 条目 MD（16,206 字符）金标：closed-domain/open-domain 分类（实测命中）
- 语料查重通过；三端口全灭（8771/6789/8000 全 000），击杀 2 个 multiprocessing spawn 孤儿（继承 8771 句柄形态第三次实锤）

## AC-2 Step 0 自启 + 管理 + 入库 + 检索 — PASS

**Step 0（被测核心）**：`ensure_stack.py --json` 在死栈上 → `[check] backend=False web=False mcp_kblist=False catalog=0` → actions=[start_backend, start_web, start_kbmcp] 自动拉起 → `mcp_kblist: true, catalog_n: 50, e2e_vector_search: true, ready: true`，退出码 0。**零人工干预。**

| 块 | 结果 | 关键证据 |
|---|---|---|
| F1 管理 | PASS | kb_list 50 库；两验收库创建（中文名无损）；改名→探针→改回闭环；get_documents 确认空库 |
| F2 入库 | PASS | TinyBERT：MinerU 解析 57,173 字符、U+FFFD=0 → **121 chunks**（<60K 单卷）→ 回查 0.654；wiki_qa.md：→ **37 chunks** → 0.651（3 标签全应用） |
| F3 检索 | PASS | scoped 向量 5/5 命中（0.692）；two_stage stage1 0.920（504 排空后自愈）；跨库全局经 reindex 修复后 wiki_qa.md **rank #1 进 top-10** |

## AC-3 整理全链 + agent harness — PASS

**F4 整理 6/6**：子库创建 → 移动（子库 0.691 + 父库递归命中同 doc_path）→ 改名卫生（显式带 description 规避 D1）→ tags 平台级读回 → reindex(force) +30s 探针 → 三源一致性（catalog=磁盘树=yml id）。

**F5 omp harness 两题（四维判定全 PASS）**：
- Q1 跨库事实题（task kbt_mwdu8jpy，290.4s completed）：TinyBERT = Transformer 蒸馏两阶段 + 三类 loss；**96.8% GLUE / 7.5x smaller / 9.4x faster**（金标逐字命中，主席独立复核 ✓）；QA 分类 closed/open-domain（金标 ✓）；引用跨两库且含 F4 移动后的子库新路径（跨库+递归端到端贯通）
- Q2 OOD 拒答题（task kbt_mwdu8lbf，360.3s completed）：**NOT_FOUND**——2 轮全库宽网+字面扫描+元数据检索三层全空、degraded=false 排除故障、未编造得主、仅实引无关示例句并标注不可作答

## AC-4 独立复核 — PASS（本报告）
金标对齐 ✓（96.8/7.5/9.4、closed/open、NOT_FOUND、零编造）· 工件 10/10 在位 · D3 波及面独立实锤（backend 日志可见历史库 "Nothing found on disk"；两验收库 scoped 健康 0.654/0.651）· 栈收尾健康（53 库 catalog）。

---

## 发现清单（产品缺陷与观察，按价值排序）

| # | 级别 | 发现 | 处置建议 |
|---|---|---|---|
| D3 | 高 | **全局向量通道对 HNSW 段损坏集合静默跳过**（per-collection 循环吞错，响应仍 success=true/degraded=false）；波及 1 新库+7 历史库（backend 日志实锤）；scoped（get_collection 句柄）正常、global（list_collections 句柄）失败 | kb_reindex(force) 可愈（WikiQA 已实证）；建议加段可读探针 + degraded_reasons 聚合上报 + 存量 7 库批量重建 |
| D5 | 中 | two_stage 504 后后台继续运行、同通道排队堆叠、显式 budget 未生效，~20s 自愈 | 超时可取消后台任务 |
| D1 | 中 | kb_update name-only 清空 description（语义=未提供即清除） | 改 patch 语义 |
| E1 | 中 | 父库 reindex 不下钻子库（total_docs=0） | 递归子库或显式声明 |
| E2 | 低 | 改名不重写向量 chunk 的 doc_path 字符串 | 改名同步刷新索引元数据 |
| E3 | 中 | kb_laya_judge criterion=evidence 无主题相关性过滤（Q2 55 段假阳性 survivor，agent 靠复核兜住）——已知宽判现象的再确认 | 增加 topic-relevance 判据 |
| D2 | 低 | kb_index_document doc_path 被叠加库根前缀（404） | 路径归一化 |
| D4 | 低 | score_threshold 过滤发生在 short_content 降权前 | 降权后二次过阈 |
| O1 | 观察 | 控制台中文乱码=GBK 显示伪影（API 层无损） | — |

## 结论

1. **"skill 自动检查启动"机制在死栈上再次实测成功**（第三次独立验证），且本轮从 Step 0 开始的全功能链（管理→入库→检索→整理→agent harness）全部通过同一死栈自启入口完成；
2. **全功能可用**：管理 API、MinerU 解析入库（PDF+MD）、三模式检索（scoped/关键词/跨库全局）、整理六步、omp agent 车道（跨库事实+诚实拒答）全绿；
3. **回答质量**：F5 两题四维全 PASS，数字与派发前隔离金标逐字一致，OOD 零编造；
4. **最有价值的验收产出 = D3**：全局检索通道对损坏集合静默跳过的机制实锤——解释了 floor 平台组成指纹现象的底层机制，已入产品修复清单。

## 证据清单（acceptance/ 目录）
ensure_stack_output.txt · trace.jsonl(45 行) · trace_b.jsonl(13 行) · F1F2F3_REPORT.md · F4F5_REPORT.md · f5_q1.json · f5_q2.json · tinybert.pdf · wiki_qa.md · 本报告
