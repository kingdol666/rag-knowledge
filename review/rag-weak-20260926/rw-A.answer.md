三路检索（全库网 ×2 + 小说库内完整召回）与分页深读已全部完成。以下为最终报告。

---

## Search Paths

**Pre-Flight**：`backend_status` → healthy，vector ready（一句带过）。

**Phase 1 —— 向量宽网 + Laya/Jev 核验门（三路，脚本 `vector_jev_search.py`，引擎 `laya_sdk` 真实加载，fail-closed，阈值 0.5）**：

| 检索路 | 范围 | 参数 | recall | Laya 判决 | 存活 |
|---|---|---|---|---|---|
| 路A（初始宽网） | 全库 | top_k=30 | 23 hits → 14 去重 → 10 读取 | 53 段全评，global_best 0.925，criterion=instance | 10 篇（小说类：part 8、part 9） |
| 路B（达西线定向扩网） | 全库 | top_k=80 | 61 hits → 42 去重 → 34 读取 | 189 段全评，global_best 0.8277，criterion=evidence | 26 篇（小说类新增：part 13、5、22-1、14） |
| 路C（小说库内枚举完整召回） | `kb-id b4c48237-…`（Novel-PridePrejudice） | top_k=60 | 60 hits → 19 去重 → 19 读取 | 80 段全评，global_best **0.9366**，criterion=instance | **19/19 全存活** |

- 手工具 `kb_search_vector`（含 `balance_kbs` 语义）先于一切；路C 锁定单库后信噪比大幅提升——**part 23（彬格莱求婚）经路C 升至 0.9366 首位**，正是全库网两次漏掉的分片。
- **Jev 核验门**：`kb_doc_read` 按 doc_id 分批读取候选全文 → 结构分段 → 真实 Laya 逐段计分（脚本内嵌 jev_filter 同等门控，未手工降级为 LLM rubric）。跨域误召回（经济学/LLM/量子物理论文）在小说库内路C 被整体排除。
- **分页补读**：命中分片普遍 `truncated=true`，对 part 8/9/13/23/24/25 用 offset 续读窗口（如 part 13 读 offset=280 窗口取得 Ch.34 求婚开场原文），所有引用均来自正文实读。
- **覆盖统计**：28 个分片中 20 片经 Laya 计分；**5 个求婚章节所在分片（part 8/9/13/23/24）5/5 全部过门存活**（分数 0.734–0.937）。

## Answer

《傲慢与偏见》全书中**共 5 处求婚场景**，按故事顺序：

| # | 谁 → 谁 | 章节/地点 | 结果 | 引擎分 |
|---|---|---|---|---|
| 1 | **柯林斯 → 伊丽莎白** | 第19章 · Longbourn | **被拒** | part 8：0.9211 |
| 2 | **柯林斯 → 夏绿蒂·卢卡斯** | 第22章（求婚在幕后，正文呈现宣布与自述） | **成功** | part 9：0.9023 |
| 3 | **达西 → 伊丽莎白（第一次）** | 第34章 · Hunsford 牧师住宅 | **被拒**（次日交信 Ch.35） | part 13：0.7343 |
| 4 | **彬格莱 → 吉英** | 第55章 · Longbourn | **成功** | part 23：0.9366 |
| 5 | **达西 → 伊丽莎白（第二次）** | 第58章 · Longbourn 散步途中 | **成功** | part 24：0.9114 |

**场景细节（正文实读核验）**：

1. **柯林斯→伊丽莎白（Ch.19，part 8）**：Collins 正式宣告——"May I hope, madam, for your interest with your fair daughter Elizabeth…"；Elizabeth 拒绝——"it is impossible for me to do otherwise than decline them"；她向父亲确认拒绝（"and this offer of marriage you have refused?" — "I have, sir."）。Collins 随即把殷勤转向 Charlotte。
2. **柯林斯→夏绿蒂（Ch.22，part 9）**：求婚本身发生在章节间隙（奥斯汀未戏剧化），正文为 Sir William 宣布订婚（"he unfolded the matter"），Mrs. Bennet 不信、Lydia 喊 "Do not you know that Mr. Collins wants to marry Lizzy?"；Charlotte 自述——"I am not romantic… I ask only a comfortable home"。**成功**。
3. **达西→伊丽莎白 第一次（Ch.34，part 13）**："In vain have I struggled. It will not do. My feelings will not be repressed. You must allow me to tell you how ardently I admire and love you."；Elizabeth 严词拒绝——"you were the last man in the world whom I could ever be prevailed on to marry."；达西 "You have said quite enough, madam…" 愤然离去，次日（Ch.35）递信。**被拒**。
4. **彬格莱→吉英（Ch.55，part 23）**：Elizabeth 撞见二人立于壁炉前的"earnest conversation"，Jane 拥抱妹妹自陈 "the happiest creature in the world"；Bingley 已向 Mr. Bennet 求允，Mr. Bennet 当晚对 Jane 说 "Jane, I congratulate you. You will be a very happy woman."（达西暗中促成并默许）。**成功**。
5. **达西→伊丽莎白 第二次（Ch.58，part 24）**："You are too generous to trifle with me. If your feelings are still what they were last April, tell me so at once. My affections and wishes are unchanged…"；Elizabeth 应允——"her sentiments had undergone so material a change… as to make her receive with gratitude and pleasure his present assurances."。Ch.60（part 25）回顾动因："My aunt's intelligence had given me hope, and I was determined at once to know everything."（凯瑟琳夫人逼退反成助攻）。**成功**。

## Sources

**result_list（Novel-PridePrejudice 库，`kb_id=b4c48237-…`，按引擎判决分排序；★=求婚场景所在分片）**：

| 分片 | Laya 判决分 | 向量分 | 内容定位 |
|---|---|---|---|
| ★ part 23 | **0.9366** | 0.5834 | Ch.55 彬格莱→吉英 求婚成功 |
| part 12 | 0.9364 | 0.5879 | Ch.30–32 Hunsford 邻近期（达西频繁造访，铺垫） |
| part 3 | 0.9317 | 0.5642 | Ch.5–6 Lucas Lodge 舞会（早期婚配市场语境） |
| ★ part 25 | 0.9299 | 0.5955 | Ch.60–61 达西求婚回顾 + 终章 |
| ★ part 8 | **0.9211** | 0.6397 | Ch.18 舞会 + Ch.19 柯林斯→伊丽莎白（拒绝） |
| part 18 | 0.9176 | 0.5906 | Ch.45 Pemberley 再访（情势逆转） |
| ★ part 14 | 0.9131 | 0.5658 | Ch.35 达西解释信（第一次求婚余波） |
| part 11 | 0.9128 | 0.5705 | Ch.27 吉英来信 + 韦翰转向金小姐 |
| ★ part 24 | **0.9114** | 0.5804 | Ch.57–58 达西第二次求婚（应允） |
| part 7 | 0.9104 | 0.6111 | Ch.17–18 尼日斐舞会 |
| part 20 | 0.9101 | 0.5983 | Ch.49 柯林斯慰问信（莉迪亚婚事） |
| part 5 | 0.9066 | 0.5894 | Ch.11 达西情愫渐生 |
| part 4 | 0.9029 | 0.5742 | Ch.8 Netherfield 沙龙 |
| ★ part 9 | **0.9023** | 0.6025 | Ch.21 柯林斯撤回 + Ch.22→夏绿蒂（成功） |
| part 10 | 0.8961 | 0.5925 | Ch.24 吉英错失彬格莱（离间余波） |
| part 22 (1/2) | 0.8938 | 0.5896 | Ch.53 彬格莱与达西重返（复合契机） |
| part 1 (1/2) | 0.8878 | 0.5797 | 版权/序言（编者言及婚配主线） |
| part 17 | 0.8867 | 0.5766 | Ch.42–43 彭伯里初访 |
| part 2 | 0.8580 | 0.6075 | Ch.15–16 柯林斯择偶 + 韦翰之词 |
| ★ part 13 | **0.7343**（路B） | 0.6347 | Ch.33–34 **达西第一次求婚（拒绝）** + 信始 |

跨库两路（路A/B）的 result_list 另含大量非小说存活项（经济学 2011.14424、LLM 2005.14165、量子物理 2311.00487 等 0.71–0.93 分）——均为向量宽网在 0.35 阈值下的跨域误召回，对本题无引用价值，已由小说库内路C 排除。

## Confidence

**High —— after Jev verification**：5/5 求婚章节所在分片全部通过 Laya 门（判决分 0.734–0.937，阈值 0.5，criterion=instance，fail-closed 无错误段），三路检索对 part 8/9 相互印证；全部关键场景均以分页 `kb_doc_read` 实读原文、逐句引用核验（含 truncated 窗口续读）；来源为单一 KB 内 28 分片完整切分的同一部小说，20/28 分片经引擎计分且覆盖全部 5 个求婚章节。

## Blind Spots (Cross-Library Perspective)

- **文本本身未戏剧化的部分**：Ch.22 柯林斯向夏绿蒂求婚的"原话"、Ch.55 彬格莱求婚的"原话"在小说中不存在直接引语（分别以宣布/叙述转述呈现）——任何知识库都无法提供不存在的台词；本回答如实标注此性质。
- **未被 Laya 计分的分片（未扫描盲区）**：part 6、15、16、19、21、26、part 1(2/2)、part 22(2/2)。按章节映射均不含求婚场景（part 6 = Ch.15 柯林斯择偶铺垫最接近），但未经引擎验证；若求 100% 穷尽，建议对 part 6 做一次补充 `kb_doc_read`。
- **近似但非求婚的情节（未列入清单）**：韦翰追求伊丽莎白（从未求婚）、韦翰转向金小姐（£10,000 财势考量）、莉迪亚–韦翰婚姻（由达西出资安排，无求婚场景）、韦翰诱拐乔治安娜未遂（Ch.35 信中提及）、凯瑟琳夫人"逼退"伊丽莎白（反向要求放弃婚约）。若采用宽口径"婚配事件"定义，需另行纳入。
- **跨库信噪比提示（Cross-Library 视角）**：全库网对本文学枚举问题在向量 0.35 阈值下产生大量跨域块，部分甚至获 Laya 高分（"proposal/marriage" 通用语义所致）——说明跨库宽网对文类问题精度有限，最终结论以小说库内定向完整召回为准；其他 KB（经济/计算机/生命科学等）对本问无实质覆盖。
- **元数据可信度**：part 2 的 KB 描述声称 "Chapters XV–XLIX" 且提及 "Collins's proposal to Charlotte"，与正文实际映射（Ch.15–16）不符，属不可信描述（本次裁决基于正文+引擎，未受影响）；建议后续用 List/Verify 流程回修该描述。
- **需用户确认点**：章节号按 Project Gutenberg #1342 标准章序给出；若用户以其他版本/卷次编号，请以分片路径 `Novel-PridePrejudice/pride_and_prejudice (part N of 26).md` 为准。