# A/B/C 模式设计符合性验收报告（2026-09-27 晚）

## 一、三种模式的作业流程（现状）

```
A 向量优先   kb_search_vector 宽网 top_k=30 → 硬阈值+文档去重 → 批量重读 → 结构分段
             → 真实 Laya 逐段判决(fail-closed) → yes 全收 → result_list
             脚本: .claude/skills/knowledgebase-search/scripts/vector_jev_search.py

B 图书管理员 kb_list → 书架标签(L1) → 全量描述(L2) → 元数据信任(L3) → 预算读取(L4:
             重叠全文/不可信头读/分篇补全) → complete_recall 真实 Laya 判决 → 引擎裁决即终审
             脚本: .claude/skills/knowledgebase-librarian/scripts/complete_recall.py (+jev_filter.py)

C 并行重定义 A ∥ B 两个独立子进程同时启动(先完成者 join 等待) → 按 doc_path 去重合并
             (共识优先) → 合并文档 kb_doc_read 完整正文(truncated 自动续读) → 知识增强包
             脚本: scripts/124_mode_c_parallel.py (旧 vector∥catalog 实现以
                   RAG_MODE_C_IMPL=hybrid 可回退 → hybrid_search.py)
```

## 二、验收标准与逐条证据

| # | 验收标准 | 证据 | 结论 |
|---|---|---|---|
| AC1 | A 按契约执行: 宽网+逐段真判+fail-closed | arm_A: real_engine=true, q1 95 段全判, 金标 part1+2 在结果集 | ✅ |
| AC2 | B 按契约执行: 逐级目录道+引擎裁决终审 | arm_B: real_engine=true, L2=131 docs→幸存 23 docs, 金标命中 | ✅ |
| AC3 | **C 真并行**: 两 worker 同时启动、区间相交 | 并行窗口 A[0, 24.3s] / B[0, 20.0s]，`workers_overlapped=true`；merge_s 24.3 ≈ max(A,B) 而非 A+B 之和 | ✅ |
| AC4 | C 去重合并: 无重复 + 共识优先 | 合并 12 篇无重复路径；金标分篇在共识集且排序靠前 | ✅ |
| AC5 | C 完整读取+知识增强包 | 最终 JSON 含 12 篇全文 161,189 字符(truncated 续读到完整)；主对话只接收该产物(ANSWER-q1.md 即基于此) | ✅ |
| AC6 | 全链路使用 MinerU .venv | 124 两 worker interpreter=backend/.venv/Scripts/python.exe（写进产物）；判决引擎 device=cuda；140 RUN.json 记录 laya_env{torch 2.12.1+cu130, cuda:true} | ✅ |
| AC7 | init 自动初始化覆盖 | init SKILL.md 新增 **Phase 5b**(laya 包+模型+GPU 判决冒烟+解释器 fail-closed 规则)、Fast-Path 判据、Phase 11 验证行、完成报告模板 | ✅ |
| AC8 | 回归无退化 | 118: 0 FAIL/0 WARN · validate PASS · 单元 46/46 · 三模式门 6/6 · 并行 C 双题金标+无重复 | ✅ |

实测数字（本轮验收）：C q1 41.9s / q2 29.9s（含 12 篇全文读取 16-18 万字符）；worker 窗口
q1 A[0,31.3]/B[0,32.8]，q2 A[0,24.3]/B[0,20.0]——均真并行。

## 三、本轮修正项

1. init skill 补 Phase 5b（此前 Laya 引擎完全不在初始化覆盖内）
2. `124` 脚本补 worker 起止时间戳与 parallelism 字段；修 `0.0 or 1e9` 假值陷阱（起点 0 被吞导致 overlap 误判 False）
3. `141`/`PIPELINE.md` 的 C 描述同步为并行语义

## 四、复验命令

```bash
python scripts/124_mode_c_parallel.py --query "..." --shelves "计算机与人工智能" --out out.json
python benchmark-suite/scripts/140_retrieval_modes_exp.py --mode A --mode B --mode C
python benchmark-suite/scripts/141_retrieval_modes_report.py <run_dir>
python scripts/118_skill_audit.py && node scripts/validate_skills.cjs
```
