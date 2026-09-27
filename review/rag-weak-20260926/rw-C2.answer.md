All evidence is gathered — every one of the five proposal scenes was re-read from source, and the lane/judge statistics are computed. Final answer follows.

## Search Paths（双道统计 + Laya 判决数）

**Run**: `status=ok` · engine=`laya` (real_engine=**true**, backend `laya_sdk`) · wall 841.7s · `--lane-agreement` on, `--require-real` satisfied.

| Lane | Stats |
|---|---|
| **A · vector** (own MCP conn) | `kb_search_vector` top_k=10, threshold=0.35 → **10 raw hits → 7 dedup docs**, 6.4s, no error |
| **B · catalog** (own MCP conn) | **14 shelves scanned** (2 excluded) → **371 descriptions** → 30 desc-overlap docs → **20 full reads** + **100 zero-overlap heads peeked** (0 empty, 31.4s) → 341 zero-overlap unread (budget, declared); 21.7s |

**Merge** on (kb_id, path): **125 docs** — both=2, vector-only=5, catalog-only=118. Unified reread: 3/5 vector-only done, 2 → `unscanned` (`empty_content`, declared — a Corpus chunk + an experience doc). Sibling completion + post-judge stem expansion: 11 docs expanded, **46 upgraded** (17.5s) — this pulled the *entire* 26-part novel into the kept set.

**Laya 判决数**: **607/607 segments scored = 607 verdicts** across **134 documents** → 131 docs ≥ absolute 0.50 → 68 docs ≥ relative cut 0.864 (global_best 0.964 = P&P part 9, margin 0.10) → top-K floor applied → **final result_list = 53 docs, 其中 27 篇为《傲慢与偏见》分片（parts 1–26 全部在列，含 1 个嵌套拆分条目）**.

## Answer

《傲慢与偏见》（该 KB 为 Gutenberg #1342 全本，26 个分片）中共有 **5 个当面求婚场景**，按故事顺序：

**1. 柯林斯先生 → 伊丽莎白·班纳特**（第 XIX 章 · part 8，浪搏恩）
柯林斯为"牧师应作婚姻表率 + 凯瑟琳夫人的建议"登门正式求婚，伊丽莎白明确拒绝（"It is impossible for me to do otherwise than decline them"）；柯林斯却视拒绝为"优雅女性的矜持"，拒绝接受拒绝。**结果：拒绝**（女方坚拒，男方自欺，事后转怨）。

**2. 柯林斯先生 → 夏洛特·卢卡斯**（第 XXII 章 · part 9，卢卡斯府）
被拒后仅数日，柯林斯溜出浪搏恩直奔卢卡斯府求婚，"as short a time as Mr. Collins's long speeches would allow, everything was settled"；夏洛特出于"只求一个舒适的家"（"I ask only a comfortable home"）接受，卢卡斯爵士夫妇欣然同意。**结果：接受**（即刻订婚）。

**3. 达西先生 → 伊丽莎白·班纳特（第一次）**（第 XXXIV 章 · part 13，汉斯福牧师住宅）
达西以 "In vain have I struggled… how ardently I admire and love you" 表白，但通篇强调门第差距与"降格屈就"，自信必获应允；伊丽莎白怒斥其拆散彬格莱与吉英、毁掉韦翰，并回以 "you were the last man in the world whom I could ever be prevailed on to marry"。次日（第 XXXV 章 · part 13 末 → part 14）达西递长信自辩，成为全书转折。**结果：拒绝**。

**4. 彬格莱先生 → 吉英·班纳特**（第 LV 章 · part 23，浪搏恩）
彬格莱重返尼日斐花园后来访，与吉英在壁炉前定情；吉英"the happiest creature in the world"，班纳特先生祝福 "Jane, I congratulate you. You will be a very happy woman."。**结果：接受**（订婚）。

**5. 达西先生 → 伊丽莎白·班纳特（第二次）**（第 LVIII 章 · part 24，浪搏恩外散步途中）
伊丽莎白先致谢其对丽迪雅之恩；达西重申 "My affections and wishes are unchanged"，并给出一句否决权；伊丽莎白答 "her sentiments had undergone so material a change"，应允。第 LX 章（part 25）回溯：凯瑟琳夫人的阻挠之行反成促成之因。**结果：接受**（订婚）。

**边界说明**：韦翰与丽迪雅（第 LI–LII 章 · part 20–21）是私奔后由达西出钱促成的**协议婚事**——书中没有韦翰当面向丽迪雅求婚的场面；若把"为结婚达成的婚约"也算作求婚，则另有此第 6 个特殊条目（非当面求婚场景，建议单列）。

即：**柯林斯求婚 2 次（对两位女性，1 拒 1 成）、达西求婚 2 次（对同一人，1 拒 1 成）、彬格莱求婚 1 次（成）——共 5 幕，2 拒 3 成。**

## Sources（文档 + lane + 分数）

| # | 场景 | 文档 | lane | vector | Laya | 核对 |
|---|---|---|---|---|---|---|
| 1 | 柯林斯→伊丽莎白 | part 8 of 26 (Ch.19) | **both** | 0.5110 | **0.8920** | kb_doc_read 全文 ✅ |
| 2 | 柯林斯→夏洛特 | part 9 of 26 (Ch.20–22) | catalog | — | **0.9638** | 全文 ✅（本场全局最高分）|
| 3 | 达西→伊丽莎白① | part 13 of 26 (Ch.33–35) | catalog | — | **0.8928** | 首读+`offset=330` 续读 ✅ |
| — | 达西长信 | part 14 of 26 (Ch.35–36) | catalog | — | **0.9374** | 全文 ✅ |
| 4 | 彬格莱→吉英 | part 23 of 26 (Ch.55–56) | catalog | — | **0.9062** | 全文 ✅ |
| 5 | 达西→伊丽莎白② | part 24 of 26 (Ch.58–59) | catalog | — | **0.8996** | 全文 ✅ |
| — | 回溯印证 | part 25 of 26 (Ch.60) | catalog | — | **0.9203** | 全文 ✅ |

KB: `b4c48237-6937-440a-9696-cc1e66bed5c1` (Novel-PridePrejudice)。27 篇幸存分片覆盖全书 parts 1–26 → 枚举完整性由 sibling completion 保证（任一场景所在章节都不可能缺席）。

## Confidence

**高（P0，内容核验 8/8）**。五幕均逐字读原文核实（proposer→proposee→结果→章序 19→22→34→55→58 全部有原文支撑），并与 Ch.60 回溯、分片描述互证；证据来自 53 篇幸存文档中的 P&P 全本分片，未依赖未读内容。唯一解释依赖项是韦翰–丽迪雅的"协议婚事"边界（已在答案中显式标注，不计入 5 幕）。

## Blind Spots (Cross-Library Perspective)

- **跨库干扰项未被分数剔除**：53 篇幸存中有 26 篇来自另外 4 个 KB（AI/数据库/统计/地球科学/经济），它们通过了全局相对切（Laya 分布偏顶重），但经描述+evidence_pack 头部核验后确认零 P&P 内容，被**按内容排除**而非按分数排除——这是本语料"高分≠相关"的典型表现。
- **目录道预算缺口**：341 条零重叠描述未读 + 2 个 shelf 被排除——对"库内是否另有 P&P 副本/评论"的问法是理论盲区；peek-head 网（100 篇）补扫后未发现第二处 P&P 材料。
- **KB 单副本**：Novel-PridePrejudice 仅存 Gutenberg #1342 一个版本（无译本/改编本），若他处另有版本不影响本枚举。
- **2 篇 vector 道 unscanned**（`empty_content`，Corpus 分块 + 经验文档），已声明，与本题无关；part 1 的 front-matter 后半（0.2536）被正确丢弃（版权页，无正文）。
- **JSON 记账小瑕疵（不影响答案）**：`judge.kept_total=73` 与 `kept_doc_indices`/`result_list`=53 不一致；`kept_doc_indices` 与 `result_list` 路径集有 19 条出入；result_list 内 1 条 vector-lane 条目 `kb_id=null`。答案以 result_list（53 条，P&P 全 26 部）＋原文直读为准。