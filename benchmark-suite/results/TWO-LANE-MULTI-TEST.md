# 多问题 · 双车道对照测试（描述修复后）

车道 A = 向量+内容（chat API + 完整 kb 工具）· 车道 B = 逐级穷尽召回 + Jev 门（122 管线，mode `union`，阈值 0.4）

## 监控总表

| QID | 类型 | A 时延 | A 工具 | A 成本 | B 时延 | B 候选 | B 窗口 | B 保留 part | B 判据 | B 后端 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Q1 | early scene | 55.0s | 7 | 0.646592 | 41.5s | 19 | 55 | [3] | evidence | llm |
| Q2 | mid turning point | 53.5s | 12 | 0.6489739999999998 | 43.3s | 20 | 58 | [14] | evidence | llm |
| Q3 | late reveal | 42.5s | 10 | 0.7362839999999999 | 50.4s | 20 | 58 | [21, 24, 25] | evidence | llm |
| Q4 | confusable detail | 29.2s | 6 | 0.5395420000000001 | 28.6s | 11 | 33 | [] | evidence | llm |
| Q5 | character arc | 42.2s | 10 | 0.69255 | 40.5s | 21 | 61 | [3, 5, 16, 18] | evidence | llm |
| Q6 | enumeration / completeness | 69.0s | 16 | 1.0285900000000001 | 37.3s | 22 | 64 | [5, 13, 17, 18, 24, 25] | instance | llm |

## 车道 A 向量工具使用情况（确认 A 是向量车道）

- Q1: mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector、mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector、mcp__plugin_rag-knowledge_kb-mcp__kb_search_two_stage、mcp__plugin_rag-knowledge_kb-mcp__kb_search_two_stage
- Q2: mcp__plugin_rag-knowledge_kb-mcp__kb_search_two_stage、mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector、mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector
- Q3: mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector、mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector、mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector
- Q4: mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_two_stage、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector
- Q5: mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_two_stage、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector
- Q6: mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector、mcp__kb-mcp__kb_search_vector

## Q1 — early scene

**Q**：At the Meryton assembly, what does Mr. Darcy say about Elizabeth when Bingley suggests he dance with her, and how does Elizabeth react to it?

### 车道 A（向量 + 内容）

Retrieved from **Novel-PridePrejudice / pride_and_prejudice (part 2 of 26).md** (chapters covering the Meryton assembly), with corroborating hits in part 3 and part 5.

At the Meryton assembly, when Bingley urged Darcy to dance and proposed that he ask Elizabeth, Darcy looked at her briefly, withdrew his eyes, and said coldly: "She is tolerable: but not handsome enough to tempt *me*; and I am in no humour at present to give consequence to young ladies who are slighted by other men." He then told Bingley to return to his own partner rather than waste his time. Elizabeth, seated nearby for want of partners, overheard the whole exchange. She did not show that she had heard it, but she remained with "no very cordial feelings" toward him. Being of a lively, playful disposition, she "told the story with great spirit among her friends," making Darcy's slight into an amusing anecdote. She liked him too little to care for his good opinion, so the remark bred in her a lasting prejudice rather than any wound. This is the source of Elizabeth's pique that Austen later names as the origin of both her prejudice and Darcy's pride.

### 车道 B（逐级穷尽 + Jev 门）

The evidence does not contain the actual exchange in which Bingley suggests Darcy dance with Elizabeth, nor Darcy's remark itself — it only reports the remark second-hand, when Charlotte says, "Poor Eliza! to be only just _tolerable_." Elizabeth's reaction is expressed later in the same chapter: "I could easily forgive _his_ pride, if he had not mortified _mine_," and she promises her mother she may "safely promise you _never_ to dance with him."

Source used: pride_and_prejudice (part 3 of 26), Chapter V (chunk includes Chapters V–VI).

## Q2 — mid turning point

**Q**：Why does Elizabeth refuse Mr. Darcy's proposal at Hunsford, and what does his letter the next morning reveal about Mr. Wickham's past?

### 车道 A（向量 + 内容）

I have complete evidence from the KB.

**Answer (from KB: Novel-PridePrejudice):**

Elizabeth refuses Darcy at Hunsford for two explicit reasons she states in the proposal scene: he has ruined "the happiness of a most beloved sister" by separating Bingley from Jane, and he has, in her belief, reduced Mr. Wickham to poverty by withholding the living designed for him — all delivered with an arrogant, unapologetic manner that insults her. She tells him he was "the last man in the world" she could ever be prevailed on to marry, citing his conceit and selfish disdain for others' feelings. His letter the next morning (in **part 14 of 26**, carrying Chapters 35–36) answers both charges, and its Wickham section reveals that George Wickham was the son of the Pemberley estate steward raised at old Mr. Darcy's expense through Cambridge, who resigned his claim to the promised living in exchange for £3,000, then lived a life of idleness and dissipation. When the living fell vacant he demanded it again and, refused, sought revenge: the previous summer he followed Georgiana Darcy to Ramsgate, using the complicit Mrs. Younge, and persuaded the fifteen-year-old — then worth £30,000 — to consent to an elopement. Darcy arrived a day or two before the intended flight, and Georgiana confessed everything herself; the affair was hushed up for her sake. The letter adds that Colonel Fitzwilliam, as executor and near relation, can corroborate every particular. Reading it, Elizabeth is "absolutely ashamed" of her own blindness, partiality and prejudice, recognizing that Wickham had told her only what suited him.

**Part files used:** `pride_and_prejudice (part 13 of 26).md` (Ch. 33–34, the Hunsford proposal and refusal) and `pride_and_prejudice (part 14 of 26).md` (the full Darcy letter, Ch. 35–36, including the Wickham/Georgiana revelation).

### 车道 B（逐级穷尽 + Jev 门）

The evidence is insufficient to answer this question.

The retrieved chunk (pride_and_prejudice, part 14 of 26) contains only Darcy's letter — his explanation of separating Bingley from Jane Bennet and the beginnings of his account regarding Wickham. It does not include the Hunsford proposal scene or Elizabeth's stated reasons for refusing him, and it is truncated mid-sentence ("condescended to adopt the measures of art s") before the letter's revelations about Wickham's past are given.

Source used: `pride_and_prejudice` (part 14 of 26).

## Q3 — late reveal

**Q**：How does Elizabeth learn the truth about Mr. Darcy's role in Lydia's marriage, and what exactly did he do and pay?

### 车道 A（向量 + 内容）

I have the evidence I need.

**Answer (from `pride_and_prejudice (part 21 of 26).md`, with `part 20`, `part 24`, and `part 25` as corroborating parts):**

Elizabeth first learns of Darcy's involvement at Longbourn in Chapter 49, where she accidentally discovers it while reading Mr. Gardiner's letter (part 20) — she assumes her uncle paid everything, and the narrator notes her surprise that Darcy was "in the affair." The full truth arrives in Chapter 52 through Mrs. Gardiner's long letter from Gracechurch Street (part 21): Darcy left Derbyshire a day after the Gardiners, came to town resolved to hunt down Wickham, bribed Mrs. Younge (formerly Georgiana's governess, now keeping lodgings in Edward Street) for their address, saw Wickham repeatedly and Lydia once, tried first to persuade Lydia to leave, and — finding marriage was never Wickham's design — negotiated and expedited the wedding, professing it his duty since his own mistaken pride had concealed Wickham's worthlessness. Mrs. Gardiner reports the exact terms: Wickham's debts paid ("considerably more than a thousand pounds"), another thousand added to Lydia's own settlement, and his commission purchased — a sum the family later estimates near ten thousand pounds (part 25, Ch. 60), all insisted on by Darcy himself despite the Gardiners' wish to share the cost. Finally, Elizabeth confirms the truth with Darcy when he admits it directly, and she then tells her father "what Mr. Darcy had voluntarily done for Lydia" (part 24). So Elizabeth learns it by letter-borne revelation from her aunt, and Darcy's actual actions were finding the couple, compelling marriage, and paying off the debts plus a settlement and army commission — roughly ten thousand pounds.

### 车道 B（逐级穷尽 + Jev 门）

The evidence does not contain the scene in which Elizabeth learns of Darcy's role — part 25 opens with Mr. Bennet already recounting it, and none of the retrieved parts (21, 24, 25) show her discovery. From Mr. Bennet's account, Darcy "did everything; made up the match, gave the money, paid the fellow's debts, and got him his commission" (part 25). Mrs. Bennet's reaction — "Ten thousand a year!" and her ecstatic chatter — follows Elizabeth's "important communication" to her mother that same evening (part 25). The letter in part 24 is from Mr. Collins, not the source of this revelation, and part 21 concerns Wickham's removal from the militia and the Gardiners' payment arrangements, not Darcy's role. So the exact payment amount and the earlier scene of Elizabeth's discovery are not in the retrieved evidence.

Sources used: `pride_and_prejudice` part 25 of 26; part 24 of 26; part 21 of 26.

## Q4 — confusable detail

**Q**：Mr. Wickham was involved in two elopements. For each, state who the girl was, how old she was, where it happened, and whether it was carried out.

### 车道 A（向量 + 内容）

I have the evidence from the KB. Here is the answer.

**Wickham's two elopements (source: Novel-PridePrejudice, part 14 of 26, part 16 of 26, part 18 of 26, part 20 of 26, and part 21 of 26):**

1. **Georgiana Darcy** — she was **fifteen** years old ("more than ten years my junior... she was taken from school"; Darcy's letter, *part 14 of 26*). It took place at **Ramsgate** the previous summer, where Wickham followed her by design with the connivance of her companion Mrs. Younge (*part 14 of 26*). It was **not carried out**: Georgiana confessed the whole plan to her brother two or three days before the intended elopement, and Darcy wrote to Wickham, who left the place immediately (*part 14 of 26*).

2. **Lydia Bennet** — she was **sixteen** (her mother exclaims "She will be married at sixteen!"; she is earlier described as "a stout, well-grown girl of fifteen," *parts 4 and 20 of 26*). It happened at **Brighton**, where she had gone with Mrs. Forster and from which she and Wickham "gone off together" (*part 18 of 26*). It **was effectively carried out** — she and Wickham lived together in London and were afterwards married, though only after Darcy intervened and settled money on them (*parts 20, 21, and 22 of 26*).

### 车道 B（逐级穷尽 + Jev 门）

The evidence is insufficient — no evidence was retrieved for this question, so I cannot answer it. I have no document paths, file names, or chunk IDs to cite, and I will not draw on prior knowledge.

## Q5 — character arc

**Q**：Trace how Elizabeth's opinion of Mr. Darcy changes from the beginning of the novel to the end, and name the scenes that turn it.

### 车道 A（向量 + 内容）

I have the full arc confirmed across the part files.

**Final answer.** Elizabeth's opinion of Darcy begins at the Meryton assembly, where his refusal to be introduced and his "tolerable" remark make him, in her eyes, "the proudest, most disagreeable man in the world" (`pride_and_prejudice (part 2 of 26).md`, corroborated in `part 3 of 26.md`). Her prejudice hardens through Netherfield and the Wickham episode, and she speaks of how he "improves on acquaintance" only ironically, insisting "in essentials... he is very much what he ever was" (`part 16 of 26.md`). The first turning point is Darcy's proposal at Hunsford and his letter the next morning, which she reads with "a contrariety of emotions" as Wickham's story collapses (`part 14 of 26.md`); afterward she is "most heartily sorry" and reproaches herself for having "spoken so warmly of Wickham" (`part 15 of 26.md`). The second turn is Pemberley, where Mrs. Reynolds' warm testimony and Darcy's altered manner begin to dissolve her judgment ("He is certainly a good brother," `part 17 of 26.md`). The decisive change comes with Darcy's rescue of Lydia, which she learns of after his second proposal, moving her to "heartily" acknowledge the worth her father confirms ("he deserves you," `part 24 of 26.md`). She humorously dates her love "from my first seeing his beautiful grounds at Pemberley," though she admits it "has been coming on so gradually" (`part 24 of 26.md`), and in Chapter LX she teases him about how he began to love her (`part 25 of 26.md`).

### 车道 B（逐级穷尽 + Jev 门）

The evidence is insufficient to answer this question.

The retrieved chunks are three disconnected slices of *Pride and Prejudice* (parts 3, 5, 16 and 18 of 26) and cover neither the beginning of the novel nor its end, so no continuous trace of Elizabeth's changing opinion is possible. Part 3 does contain an early stance — "I could easily forgive _his_ pride, if he had not mortified _mine_" and her pledge "never to dance with him" — and parts 5 and 18 show a later softening (respect, esteem, gratitude, and her reflection that "hatred had vanished long ago"), plus Mr. Darcy's housekeeper's testimony at Pemberley and Wickham's unpaid debts. But the pivotal scenes that would connect these states are absent: the first proposal and her rejection of it, Darcy's letter of explanation at Hunsford, the second proposal, and the closing chapters are all outside the retrieved passages. I also cannot name the turning scenes reliably, since only a fragment of the Pemberley visit (parts 18 and the opening of Chapter XLV) is present and no concluding text is available.

Sources used: pride_and_prejudice, part 3 of 26; part 5 of 26; part 16 of 26; part 18 of 26.

## Q6 — enumeration / completeness

**Q**：List every scene in the novel where Darcy and Elizabeth meet in person, in order, and say what changes in their relationship at each.

### 车道 A（向量 + 内容）

I have enough evidence across the part files.

**Answer (sources: `pride_and_prejudice (part 2 of 26).md`, `(part 3 of 26).md`, `(part 5 of 26).md`, `(part 7 of 26).md`, `(part 12 of 26).md`, `(part 13 of 26).md`, `(part 14 of 26).md`, `(part 17 of 26).md`, `(part 18 of 26).md`, `(part 22 of 26) (part 1 of 2).md`, `(part 22 of 26) (part 2 of 2).md`, `(part 23 of 26).md`, `(part 24 of 26).md`, `(part 25 of 26).md`)**

1. **Meryton assembly (part 2)** — Darcy refuses to dance and calls her "tolerable"; Elizabeth overhears and forms her prejudice, while Darcy begins to feel attraction.
2. **Lucas Lodge / Netherfield visits and the Netherfield ball (parts 3, 5, 7)** — teasing banter and the dance in which he asks "what have I done to offend you?"; interest deepens though both misread each other and the Wickham story hardens her dislike.
3. **Rosings/Hunsford encounters (parts 12–13)** — unexpected meetings in the park, her call at the parsonage and his first proposal, which she angrily refuses; the relationship reaches its lowest point, prompting his letter (part 14).
4. **Pemberley (parts 17–18)** — their surprise meeting in the grounds, his startling civility, the Georgiana introduction and dinner at Pemberley; her feelings reverse into admiration and regret.
5. **Longbourn after Lydia's elopement (parts 23–25)** — Darcy's renewed presence and the walk with Bingley and Kitty, followed by his second proposal and her acceptance; after Lady Catherine's confrontation they openly confess their changed feelings.
6. **Engagement conversations (part 25)** — they discuss how his first proposal was refused and her "impertinence," sealing their union.

### 车道 B（逐级穷尽 + Jev 门）

**Insufficient evidence.**

The evidence provided consists of four excerpts from *Pride and Prejudice* (parts 5, 13, 18, and 25 of 26) covering only a handful of scenes — the Netherfield music/dance exchange, Darcy's visits to the Parsonage and walks in Rosings park, the Pemberley visit and Elizabeth's reflections, and the post-engagement scenes at Longbourn. It does not contain the novel's other in-person meetings between Darcy and Elizabeth (for example, the Meryton assembly where they first meet, the Lucas Lodge gathering, the first proposal at Hunsford, or the Darcy–Elizabeth encounters in London), so a complete ordered list of every such scene with the relationship change at each cannot be assembled from this evidence.

Sources used: `pride_and_prejudice` (part 5 of 26); `pride_and_prejudice` (part 13 of 26); `pride_and_prejudice` (part 18 of 26); `pride_and_prejudice` (part 25 of 26).
