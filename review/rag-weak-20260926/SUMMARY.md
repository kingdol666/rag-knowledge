# RAG-Weak Three-Mode Test — 2026-09-26

## 任务设计（专打向量 RAG 软肋）
**Q**: 列出《傲慢与偏见》小说中所有求婚情节（谁向谁、结果、按序）。
RAG-hostile 要素：①枚举题（top-k 结构性无解）②中文问句 vs 英文原文 ③金标场景之一位于单次读取截断窗口之外（part 13 深部 L234+，向量分仅 0.51-0.57）④part 22 主路径空正文（嵌套拆分）⑤向量分区间与 300+ 篇学术文档重叠。

**金标（语料实证，含两处边缘）**：G1 柯林斯→伊丽莎白（ch19/part8，拒）；G2 达西第一次（ch34/part13 深部，"In vain have I struggled"，拒）；G3 达西第二次（ch58/part24，成）；G4 彬格莱→吉英（ch55/part23，成，侧写）；G5 柯林斯→夏洛特（ch22/part9，成，幕间）。

## 执行（全部经 POST /api/claude/chat，engine=claude，bypassPermissions）

| 轮 | 模式 | 耗时 | 执行方式（artifact 实证） | 场景命中 |
|---|---|---|---|---|
| rw-A | A 向量宽网+Jev门 | 677.6s | `vector_jev_search.py` 真跑 ×3（tmp/vector-jev-ragweak.json：laya_sdk、53/53 段；另两路 top_k=80/库内 top_k=60 共 269 段）+ part13 offset 深读 | **5/5** |
| rw-B (+B2 续答) | B 图书管理员 | 511.9+386.5s | L0-L4 全走（325 次 kb_doc_read 提及）→ `jev_filter.py` 真跑（**288/288 段真 Laya，284 幸存**，instance 判据） | **5/5** |
| rw-C (+C2 续答) | C 并行混合 | 1020.4(超时)→脚本 841.7s+231.5s | `hybrid_search.py` 真跑（607/607 判决，53 保留，**小说 27/28 part 全收**） | **5/5** |

**执行过程观察**：
- 三模式全部真实调用 Laya 引擎（产物 JSON `real_engine=true` 实证），无 LLM rubric 代判。
- A 主动三路扩网：全库网两次漏掉 part 23（彬格莱场），库内定向网捞回——向量提议+引擎判决+agent 补位的协同。
- B 的 agent 在 jev_filter 后台运行时提前结束回合并"预约自动继续"（chat 回合不会自动续）→ 用 chat API follow-up 取回最终答案（B2）；C 同理（900s turn 墙钟截断在 agent 读大 JSON 阶段，C2 续答）。两处 follow-up 均为新的 chat 调用（自包含提示词指向磁盘产物）。
- 跨语言：三模式都靠 extra-terms 双语关键词桥接；库内定向检索（A 路C）信噪比最高。

## 回答质量对比（金标 5 场景）
| 维度 | A | B | C |
|---|---|---|---|
| 场景命中 | 5/5（自证 5 幕 2拒3成） | 5/5 + 非场景干扰项单列（韦翰-丽迪雅协议婚事等 4 项） | 5/5 + 韦翰-丽迪雅边界说明 |
| 顺序 | ✅ 19→22→34→55→58 | ✅（行序+章节标题双重锚定，显式论证彬格莱早于达西#2） | ✅ |
| 溯源 | 文档+引擎分 | **行号+Jev 分逐场 ≥6 段互证（最全）** | 文档+lane+引擎分 |
| 盲区诚实度 | 覆盖统计明确 | **0.4941 距阈值 0.006 的 fail-closed 近失都披露**；evidence_pack 8/284 截断→从 survivors 全量重建 | 26 篇跨库干扰"按内容排除非按分数"；JSON 记账瑕疵自曝 |
| 陷阱处理 | part13 深部=offset 深读命中 | part22 空正文→嵌套子文件全读（5 行文件+part23 衔接核验） | sibling completion 拉全 26 part，"枚举完整性由结构保证" |

## 结论：逐级检索在这个 RAG 弱势任务上是否优秀？
**是，且是三者中最完整的证据链**——但更准确的结论是：三层协同（向量提议、目录保底、引擎裁决）都到达了 5/5，差异在**证据完备度与诚实度**：
- B 的幸存集（284 段全文在案）让每个论断都有行号级多段互证，连"差 0.006 被拒"的边界都如实交代——这是"查库存"式检索独有的可审计性；
- C 用 sibling-completion 把 26 个 part 结构性全拉入（枚举完整性的机制保证），代价是 17 分钟与跨库噪声清理；
- A 证明优化后的向量+引擎门已能靠"三路扩网+深读补位"追平枚举题，速度最快（11 分钟）——但 part 23 差一点漏掉，靠 agent 第二次定向扩网才救回（单路 top-k 的老风险仍在该模式的基因里）。

工件：`review/rag-weak-20260926/`（rw-{A,B,B2,C,C2}.answer.md/.transcript/.status、flow_check.py、run_ragweak.py）+ `tmp/{vector-jev,candidates,judged,hybrid}-ragweak.json`。
