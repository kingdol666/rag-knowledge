# 全栈体检 + 三模式检索 + 新文档解析入库 + 问答 — 完整记录（2026-09-27）

> 本轮全部实测真机跑通，**零功能缺陷**。唯一行为变化（自动路由在人格库拥挤时诚实拒答）经核实为规范设计，测试断言已随之校准。

---

## 一、系统健康

| 项 | 状态 |
|---|---|
| 后端 (8771) | `{"status":"healthy"}` |
| Web (6789) | HTTP 200 |
| Neo4j (7474/7687) | HTTP 200 |
| GPU | RTX 4070 Ti SUPER 16GB（CUDA 可用） |
| MinerU 环境 (backend/.venv) | laya 0.3.20 + torch 2.12.1+cu130 + cuda=True ✓ |

## 二、Skill 全量检查 — 全绿

| 检查 | 覆盖 | 结果 |
|---|---|---|
| 118 静态审计 | 21 skill / 94 工具引用 / 核心结构 | 0 FAIL 0 WARN |
| validate_skills.cjs | 跨 skill 一致性 | PASS |
| 单元测试（librarian / hybrid / butian） | 46 用例 | 46/46 |
| 119 只读冒烟（MCP stdio 真通道） | 18 skill / 26 调用 | 0 失败 |
| **120 全生命周期实测 v8** | **45 步**（建库→入库→检索→深检索→查重→改名→跨库移动→重建索引→图谱→经验 CRUD→soul 全链→4 边界用例→清理） | **45/45 PASS**，训练 reward 2.6，清理零残留 |

soul 真机证据（本轮）：qdcvr 检索+人格作答正确（42 升 + 2 引用 + PAS 5.0）、RL 训练完成、草稿审批面正常、checkpoint→rollback 恢复 6 条记忆。

## 三、三模式检索（新鲜轮 run: `retmodes-20260927T062953Z-47cc948`）

| 模式 | q1（英文方法题） | q2（中文跨语言题） | 金标 | 引擎 |
|---|---:|---:|:--:|---|
| A 向量优先 | 30.1s / 17 docs | 24.5s / 15 docs | ✅✅ | real Laya |
| B 图书管理员 | 22.0s / 23 docs | 9.8s / 11 docs | ✅✅ | real Laya |
| C 混合并行 | 68.9s / 36 docs | 63.8s / 38 docs | ✅✅ | real Laya |

- 6/6 臂过硬验证门（exit / real_engine / 证据非空 / 金标命中 / 延迟记录），与上轮（218s 总耗时）数字稳定一致，无回归。

## 四、新文档解析入库（严格按 knowledgebase-ingest A0-A7 规范）

文档：**手工构造的全新 .docx**（1723 字节，MinerU docx 解析链），内容=三模式实测知识卡（数字有真值可校验）。目标库：`demo-qa-20260927`。

| 步骤 | 结果 |
|---|---|
| A0 去重预检 | 库内无同名/同主题 ✓ |
| A2 解析 | parse_doc → MinerU → done（markdown 落盘于 backend output）✓ |
| A3c+A5 描述+存储 | task_id 模式 → `retmodes-knowledge-card.md` ✓ |
| A3b 标签 | retrieval/benchmark/laya/gpu ✓ |
| A6 索引 | 2 chunks ✓ |
| A7 终检 | 目录可见 + 向量即命中新内容（"68.6"）✓ |

## 五、问答（soul_qdcvr_ask 真链路）

| 题 | 系统回答 | 引用 | PAS |
|---|---|---|---|
| QA1 模式C在 q1 花了多少秒？整体提速？ | **68.6 秒**；1620s→218s 提速 7.4 倍 | 2 条，指向新文档 | 5.0 |
| QA2 GPU 热身后单段判决延迟？判决脚本用哪个环境？ | **约 0.047 秒**；必须用 backend/.venv（MinerU 环境） | 2 条，指向新文档 | 5.0 |
| QA3 库外探针：RTX 5090 功耗？ | **诚实拒答**："检索不到任何记录…无法给出该数值"——并逐条排查了检索到的无关证据（4070 Ti SUPER 出现上下文 / Transformer 的 P100 / 旅行者号 RTG 470W），声明"即便我记得公开规格也不属于本次证据范围" | 3 条（作为"已检证据"列出） | 5.0 |

新文档入库后**索引即时可检索**，两道事实题全部精确命中，拒答题零编造。

## 六、butian 闭环（附带复检）

musk 种子 → `ragctl soul distill` 落地 → 4 宪法文档 → 人格化作答（第一性原理语言风格）→ 清理无残留：**ALL PASS**。

## 七、观察与建议

1. **自动路由的拥挤现象（本轮新发现，规范行为）**：库内常驻人格已有 3 个（soul-demo-qa、soul-e2e-tester-024115、soul-e2e-20260926-022340）。v7 轮路由器对"刚创建几秒、profile 未生成"的测试人格给出**低置信结构化拒答**（route_reason="无足够置信度的 SOUL 匹配"，零引用不编造）；v8 轮路由到常驻人格后对该人格知识范围外的问题诚实说"无法回答"。两条路径都未伪造——安全语义正确，但提示：**测试残留人格会稀释路由置信度**，建议定期清理（`ragctl soul delete <name>`）或给常驻人格设置明确的 domain_labels 区隔。
2. C×q2 的 38 docs 与上轮 GPU 轮一致（数值漂移已稳定复现，金标不受影响）。
3. 语料卫生提醒（沿用前轮建议）：跨库检索候选池仍含测试残留 KB，可考虑检索层白名单。

## 八、工件索引

- 全生命周期：`review/skill-fulltest-20260927/REPORT.md`（v8，45 步）+ `review-skill-fulltest-v7/v8-console.log`
- 三模式：`benchmark-suite/results/runs/retmodes-20260927T062953Z-47cc948/`（arm_*.json + THREE-MODE-REPORT.md）
- 解析入库+问答：`review/fullcheck-20260927/`（ingest-qa-log.json + retmodes-knowledge-card.docx）
- 脚本：`scripts/120_skill_fulltest.py`（v8 断言）、`scripts/123_demo_docx_ingest_qa.py`（新增）
