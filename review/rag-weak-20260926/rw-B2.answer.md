五份材料齐备（284 段全文、4 个非幸存段、2 处 kb_doc_read 续读、L0 目录 16 KB）。以下为 L6 交付。

## Search Paths

- **L0 目录**：`kb_list(lightweight=true)` → 共 16 个 KB。逐条读描述后标注：**relevant ×1** = `Novel-PridePrejudice`（b4c48237…，28 docs，"《Pride and Prejudice》(Gutenberg #1342) 英文全文，按 30000 字符窗口拆 26 part"）；其余 15 个（计算机与人工智能 131 docs、自然科学与地球科学 75、生命科学与医学 53、工程与能源 39、经济与社会 24、AI 基础设施、aw-industrial、e2e/soul 测试库、ZZ 复现库等）描述具体且无文学/小说维度 → **out_of_scope**，不进入 L2。
- **L1**：complete-recall 模式保留全部 relevant/possible → 1 个架位（无固定 top-2/3 截断；该 KB `parent_id=null`，无子 KB，无限深度遍历不适用）。
- **L2**：该架位 28 个文档全部列入（26 个 part + 2 个二次拆分片 `part 1 of 26 (2 of 2)` / `part 22 of 26 (2 of 2)`；拆分兄弟按逻辑 doc 分组、保留各自 doc_id/path）。
- **L3 描述可信度**：KB 描述具体、与实存 part 数吻合，无样板/空泛/范围倒置症状 → 描述可信；且本轮未依赖描述筛选——候选清单由 `make_candidates.py` **整文件读入**后用 skill 参考分段器分段生成（即内容直接见证，绕开描述风险）。
- **L4 全段召回**：`tmp/candidates-ragweak.json` 288 个结构化段，覆盖 28 个文档的**每一行**（全 30000 字符窗口逐段切分，`max_segment_chars=3000`）。
- **L5 真实引擎门**：`jev_filter.py --engine laya --require-real`；backend=`laya_sdk`，本地模型 `model/laya`，criterion=auto→**instance**（枚举题），threshold=0.5；**288/288 打分（0 缺失、0 错误）→ 284 幸存**（0.5126–0.9489，均值 0.8242；27 个文档有幸存段）。
- **本轮 L5.5/L6**：不重打分、不裁剪——直接读取全部 284 条幸存段的完整文本（校验：**无一条段文本短于其字符跨度**，即 JSON 内文本无截断）逐段扫描定位场景；`evidence_pack` 渲染被 20k 字符截断（included_count=8/284），故从 `survivors` 全量数组重建证据；唯一续读缺口用 `kb_doc_read` 补齐（part22(2of2) 全文 5 行、part23 开头 L1-49 确认衔接，无叙事缺失）。
- 4 条非幸存段（fail-closed 拒收）：part1(2of2) L1-3 **0.3918**（Gutenberg 前页）、part6 L509-557 **0.2225**、part17 L1-60 **0.4941**、part22(1of2) L516-567 **0.4696** —— 逐条目检，**均不含求婚场景**。

## Answer

全书按故事顺序共 **5 场求婚**（2 场柯林斯 + 2 场达西 + 1 场宾利），其余"婚姻级"事件（韦翰-丽迪雅、玛丽·金、达西-德·包尔表亲的"婚约"）非求爱场景，单列于后：

1. **柯林斯 → 伊丽莎白**（Longbourn 早餐室；part8，约第 19 章）——**被拒**。
   柯林斯先向班纳特太太"求见许可"（"May I hope, madam, for your interest with your fair daughter Elizabeth…"），继而陈述三条结婚理由、自陈"the violence of my affection"。伊丽莎白当场拒绝（"it is impossible for me to do otherwise than decline them"）；柯林斯以"女性惯常假意拒绝"为由拒不接受，她被迫升级措辞："to accept them is absolutely impossible. My feelings in every respect forbid it. Can I speak plainer? … as a rational creature speaking the truth from her heart."，随后默然离场。后续：班纳特先生"unhappy alternative"谈话、班纳特太太持续施压。

2. **柯林斯 → 夏洛特·卢卡斯**（Lucas Lodge；part9，约第 22 章）——**成功**，全书第一桩完成的婚事。
   被拒仅约三日，柯林斯"hasten to Lucas Lodge to throw himself at her feet"，夏洛特主动创造"偶遇"（"instantly set out to meet him accidentally in the lane"），"so much love and eloquence awaited her there"；"In as short a time as Mr. Collins's long speeches would allow, everything was settled"——她接受他"solely from the pure and disinterested desire of an establishment"，卢卡斯夫妇即刻同意。叙述者点题：**"Mr. Collins's making two offers of marriage within three days"**。伊丽莎白震惊（"Engaged to Mr. Collins! my dear Charlotte, impossible!"）；婚礼举行（part10："The wedding took place"）。

3. **达西 → 伊丽莎白（第一次）**（Hunsford 牧师宅；part13，第 34 章）——**被拒**。
   达西突然到访、踯躅数分钟后开口："In vain have I struggled. It will not do. My feelings will not be repressed. You must allow me to tell you how ardently I admire and love you." 求爱中夹带对她家世的贬抑（"a sense of her inferiority, of its being a degradation"），并自信必获应允。伊丽莎白历数其傲慢与拆散简-宾利之事，以名句收束：**"you were the last man in the world whom I could ever be prevailed on to marry."** 达西："You have said quite enough, madam… accept my best wishes for your health and happiness."，随即离去。次日达西留下解释信（part14）。

4. **宾利 → 简**（Longbourn 客厅；part22(2of2)–part23，第 55 章）——**成功**。（注意：**故事顺序上早于达西第二次求婚**）
   求婚一幕以侧写呈现：班纳特太太设局让出客厅，伊丽莎白折返时看到"her sister and Bingley standing together over the hearth"，宾利对她耳语几句便跑出房间；随后简向伊丽莎白"instantly embracing her, acknowledged… that she was the happiest creature in the world"。宾利正式以"a sister's good wishes"身份见伊丽莎白（part23 L99）。此后（第 58 章散步中）达西证实"Darcy was delighted with their engagement; his friend had given him the earliest information of it."

5. **达西 → 伊丽莎白（第二次）**（Longbourn 近郊散步；part24，第 58 章）——**成功**。
   触发者是咖苔琳夫人：她上门逼伊丽莎白"承诺不嫁达西"遭强硬回绝（part23 L285-531），转告达西后**适得其反**（"its effect had been exactly contrariwise"）。散步中伊丽莎白先谢他对丽迪雅之恩，达西接道：**"You are too generous to trifle with me. If your feelings are still what they were last April, tell me so at once. My affections and wishes are unchanged; but one word from you will silence me on this subject for ever."** 伊丽莎白应允——"her sentiments had undergone so material a change… as to make her receive with gratitude and pleasure his present assurances"，随之"dearest, loveliest Elizabeth!"、双方互剖心迹。后续：达西向班纳特先生求娶（"I have given him my consent"），双婚礼同日在第 61 章收束。

**相近但非求婚的场景（幸存段可证）**：韦翰-丽迪雅的婚姻是"patched-up business"式的金钱交涉（part20 L450-498，Jev 0.9074；part25），韦翰一度接近娶玛丽·金而未成（part15 L251-291，0.781）；简 15 岁时有位先生"would make her an offer… but he did not"（part4 L379-425，0.772）；咖苔琳夫人声称达西与德·包尔小姐有"tacit engagement"，并无实际求婚（part23 L353-414，0.8768）。

## Sources（文档 + 行号 + Jev 分）

KB：`Novel-PridePrejudice`（b4c48237-6937-440a-9696-cc1e66bed5c1）。路径前缀均省略为 `pride_and_prejudice`：

| 场景 | 文档 | 行号 | Jev |
|---|---|---|---|
| ① 柯林斯→伊丽莎白 | part 8 | L186-240 / L241-282 / L283-335 / L336-389 | 0.8455 / 0.8357 / 0.8907 / 0.9362 |
| ① 证据链旁证 | part 8 | L390-460 / L461-508 / L509-540；part 9 L1-51；part 10 L284-335 | 0.8747 / 0.8575 / 0.8802 / 0.8773 / 0.8667 |
| ② 柯林斯→夏洛特 | part 9 | L223-266 / L267-290 / L291-340 / L341-392 / L393-445 / L446-489 / L490-538 | 0.6861 / 0.7567 / 0.8478 / 0.6485 / 0.8823 / 0.8762 / 0.9192 |
| ② 婚礼 | part 10 | L501-554 | 0.8712 |
| ③ 达西#1 | part 13 | L270-317 / L374-432 / L433-487 | 0.8608 / 0.9157 / 0.9253 |
| ③ 后续（信/重温） | part 14 L94-204；part 15 L191-250 | — | 0.8881 / 0.8160 |
| ④ 宾利→简 | part 22(2of2) L1-5；part 23 L1-49 / L50-98 / L99-155 / L156-216；part 22(1of2) L568-639 | — | 0.6106 / 0.8089 / 0.8231 / 0.8401 / 0.7520 / 0.8186 |
| ④ 达西证实 | part 24 | L316-374 | 0.9078 |
| ⑤ 夫人干预（触发） | part 23 | L285-352 / L353-414 / L415-477 / L478-531 / L532-585 / L586-623 | 0.8722 / 0.8768 / 0.7988 / 0.8174 / 0.6319 / 0.8983 |
| ⑤ 达西#2 | part 24 | L120-170 / L171-216 / L217-266 / L267-315 | 0.8736 / 0.8615 / 0.7670 / 0.8428 |
| ⑤ 允婚后续 | part 24 L441-505 / L506-558 / L559-590；part 25 L52-111 | — | 0.9207 / 0.8318 / 0.5673 / 0.9396 |
| 非场景注记 | part 4 L379-425；part 15 L251-291；part 20 L450-498；part 22 L239-288 | — | 0.772 / 0.781 / 0.9074 / 0.8170 |

## Confidence

- **引擎级可信**：288/288 由真实本地 Laya SDK 打分（`real_engine=true`，errors=[]，0 缺失分），阈值 0.5，284 幸存（留存率 98.6%）——拒收的 4 段已逐条目检，无一含求婚内容。
- **覆盖度**：全集 28 文档整本分段（每行皆入 manifest），27 文档产出幸存段，74 万字符幸存文本；5 场求婚每场均有 **≥6 条**互相印证的幸存段（直接引语全部在幸存原文中逐字核对），场景顺序由文档内行序与章节标题（XX→XXII→XXXV→LV→LXI 等）双重锚定；宾利场（第 55 章）先于达西#2（第 58 章）由 part23/24 行序及"Darcy was delighted with their engagement"处直接见证。
- **续读无缺口**：evidence_pack 渲染截断（8/284）不影响作答——全部证据取自 survivors 全量数组；kb_doc_read 补读处确认 part22(2of2) 文件本身仅 5 行，其叙事衔接在 part23 开头且已被幸存段覆盖。
- 最弱环：宾利求婚**现场为侧写**（原文本就如此，非检索缺失），"结果"由简亲口宣告补强。

## Blind Spots (Cross-Library Perspective)

1. **跨库范围**：其余 15 个 KB 仅凭描述判为 out_of_scope，**未做文档级读取**——于本题（英国文学）无合理架位，但此边界为声明项；若问题涉及工程/自然科学语料中的"求婚"语义，本报告不覆盖。
2. **未扫描范围**：本 KB 无子 KB（parent_id=null），无限深度遍历不适用；无子级未被读取。
3. **引擎面**：`real_jev=false`——按设计只用本地 Laya，未与远程 Jev 交叉复核；无第二引擎一致性校验。
4. **幸存噪声已披露**：instance 门较宽，许可/前页文本也通过了闸门（如 part25 L512-565 = 0.5633、part26 L111-162 = 0.7815 的 Gutenberg 协议段），且全书最高分段之一 part2 L442-495（0.9489）实为达西初登场（非求婚）。答案仅取材于场景段，噪声幸存段如实列出、未参与论断。
5. **阈值边界近失**：part17 L1-60 得 **0.4941**，距 0.5 仅差 0.006 被 fail-closed 拒收（内容为彭伯里管家婆赞达西，属第二次求婚的语境材料而非求婚场景）；已记录，未人工复活。
6. **语言层**：库内仅有英文原作，无中译本；中文引文为我的对译，非源文本。
7. **证据包渲染**：`evidence_pack` 因 20k 字符上限仅含 8/284 段（`truncated_candidate_ids` 记录 1 条）——本报告改由 survivors 全量恢复，属契约允许路径；如有需要可对任一幸存段用 `kb_doc_read` 按 offset 重取。