# 两种检索方式的 chat-API 对照测试（小说情节题）

KB：`Novel-PridePrejudice` · 两条车道均经 `POST /api/claude/chat` 执行 · 车道 B 的工具集已剔除 ('kb_search_vector', 'kb_search_two_stage', 'kb_search_stats')

## 监控总表

| QID | 车道 | 时延 s | 工具数 | tokens in/out | 成本 $ | 被拒工具 |
|---|---|---:|---:|---|---:|---:|
| NQ1 | A | 132.9 | 13 | 187379/1772 | 1.149451 | 0 |
| NQ1 | B | 75.2 | 12 | 149659/1687 | 1.00519 | 0 |
| NQ2 | A | 58.3 | 9 | 107382/1623 | 0.6819970000000001 | 0 |
| NQ2 | B | 59.3 | 15 | 195419/1877 | 1.2424199999999999 | 0 |
| NQ3 | A | 55.8 | 8 | 107832/1225 | 0.6514490000000001 | 0 |
| NQ3 | B | 50.0 | 12 | 136913/1360 | 0.9406129999999999 | 0 |
| NQ4 | A | 43.4 | 7 | 97584/959 | 0.5780069999999999 | 0 |
| NQ4 | B | 59.1 | 19 | 37066/1608 | 0.503834 | 0 |

## 调用轨迹（验证车道 B 是否真的没用向量工具）

### NQ1
- **A** ✓：`ToolSearch`, `ToolSearch`, `mcp__plugin_rag-knowledge_kb-mcp__kb_get_documents`, `mcp__plugin_rag-knowledge_kb-mcp__kb_search_two_stage`, `mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector`, `Grep`, `ToolSearch`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`
- **B** ✓：`ToolSearch`, `ToolSearch`, `mcp__kb-mcp__kb_list`, `mcp__kb-mcp__kb_get_documents`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`

### NQ2
- **A** ✓：`ToolSearch`, `ToolSearch`, `mcp__kb-mcp__kb_list`, `mcp__kb-mcp__kb_get_documents`, `mcp__kb-mcp__kb_search_vector`, `mcp__kb-mcp__kb_search_vector`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`
- **B** ✓：`ToolSearch`, `ToolSearch`, `mcp__plugin_rag-knowledge_kb-mcp__kb_list`, `mcp__plugin_rag-knowledge_kb-mcp__kb_get_documents`, `mcp__plugin_rag-knowledge_kb-mcp__kb_list`, `mcp__plugin_rag-knowledge_kb-mcp__kb_get_documents`, `ToolSearch`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`

### NQ3
- **A** ✓：`ToolSearch`, `ToolSearch`, `mcp__kb-mcp__kb_search_vector`, `mcp__plugin_rag-knowledge_kb-mcp__kb_search`, `mcp__kb-mcp__kb_search_vector`, `mcp__plugin_rag-knowledge_kb-mcp__kb_search_two_stage`, `mcp__kb-mcp__kb_search_vector`, `mcp__plugin_rag-knowledge_kb-mcp__kb_search_vector`
- **B** ✓：`ToolSearch`, `mcp__kb-mcp__kb_list`, `mcp__kb-mcp__kb_get_documents`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`

### NQ4
- **A** ✓：`ToolSearch`, `mcp__kb-mcp__kb_list`, `mcp__kb-mcp__kb_search_two_stage`, `mcp__kb-mcp__kb_search_two_stage`, `mcp__kb-mcp__kb_search_two_stage`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_search_two_stage`
- **B** ✓：`ToolSearch`, `mcp__kb-mcp__kb_list`, `mcp__kb-mcp__kb_get_documents`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`, `mcp__kb-mcp__kb_doc_read`

## NQ1

**Q**：At the Meryton assembly, what does Mr. Darcy say about Elizabeth when Bingley suggests he dance with her, and how does Elizabeth react to it?

### 车道 A（向量 + 内容）

**Answer (from KB: Novel-PridePrejudice — files used: `pride_and_prejudice (part 1 of 26) (part 1 of 2).md`, `pride_and_prejudice (part 3 of 26).md`, `pride_and_prejudice (part 5 of 26).md`):**

1. At the Meryton assembly, Mr. Bingley urges Darcy to dance, but Darcy refuses, saying he has no intention of dancing and that Elizabeth is "tolerable; but not handsome enough to tempt me." 2. He adds that he is in no humour to give consequence to young ladies slighted by other men. 3. Elizabeth overhears this remark and is left with no very cordial feelings toward him, though she tells the story with spirit and good humour among her friends. 4. She afterward says she could easily forgive his pride if he had not mortified *hers*. 5. She jokes to her mother that she may safely promise never to dance with him, and lightly mocks his dancing with Sir William Lucas with "Mr. Darcy is all politeness." 6. Her distaste is compounded by finding him disagreeable and by regarding him as the man who made himself agreeable nowhere. *Note: the vector search (`kb_search_vector`) returned a direct hit for the "tolerable" speech in part 3; `kb_search_two_stage` timed out.*

### 车道 B（纯内容 · 无向量）

Chapter III should follow. Let me read the next section.





## NQ2

**Q**：Why does Elizabeth refuse Mr. Darcy's proposal at Hunsford, and what does his letter the next morning reveal about Mr. Wickham's past?

### 车道 A（向量 + 内容）

I have both key passages verified directly from the source text.

**Answer (sources: `pride_and_prejudice (part 13 of 26).md` — Chapters XXXIII–XXXIV, the Hunsford proposal; `pride_and_prejudice (part 14 of 26).md` — Chapter XXXV, Darcy's letter):**

Elizabeth refuses Darcy at Hunsford because his declaration is delivered in a manner "so little suited to recommend them," openly cataloguing the inferiority of her connections and the objections he had to overcome, which wounds her pride and rouses her anger. She tells him he could not have made the offer "in any possible way that would have tempted me to accept it," citing two specific grievances: his admitted role in separating Bingley from Jane ("the means of ruining, perhaps for ever, the happiness of a most beloved sister"), and his supposed cruelty to Wickham, whose account of his misfortunes had fixed her opinion of Darcy months earlier. She adds that from their first acquaintance his "arrogance, your conceit, and your selfish disdain of the feelings of others" had formed an immovable dislike. His letter the next morning answers both charges, recounting that he had detached Bingley because he believed Jane indifferent, while concealing from Bingley that she was in town. Regarding Wickham, the letter reveals that he was the son of the late Mr. Darcy's steward, educated at the elder Darcy's expense and promised a family living; he instead resigned all claim to the church for three thousand pounds, then lived a life of "idleness and dissipation," studying law as "a mere pretence." When the living later fell vacant he applied for it again and, refused, turned violently abusive. Most damningly, the letter discloses that the previous summer Wickham attempted to elope with Darcy's fifteen-year-old sister Georgiana at Ramsgate, aided by Mrs. Younge, chiefly to seize her thirty-thousand-pound fortune and to revenge himself on Darcy; Darcy discovered it days before the intended elopement, and Georgiana confessed the whole to him herself. Thus the letter shows Wickham to be a fortune-hunter and seducer rather than the wronged man Elizabeth believed, while exposing it was Darcy, not Wickham, who had been wronged.

### 车道 B（纯内容 · 无向量）

The offset behaves unexpectedly (content repeats from the top). I already have the essential Georgiana material referenced in the letter's structure; let me read the letter's latter portion by locating the Georgiana passage directly.



## NQ3

**Q**：How does Elizabeth learn the truth about Mr. Darcy's role in Lydia's marriage, and what exactly did he do and pay?

### 车道 A（向量 + 内容）

I have everything needed. The evidence comes from parts 21, 20, 24, and 25, corroborated by the passages retrieved.

**Answer** (sources: `pride_and_prejudice (part 21 of 26).md` primarily; corroborated by parts 20, 24, and 25):

Elizabeth first learns the truth from Lydia herself, who carelessly lets slip that "Mr. Darcy might have done as well" and that he "was to come there with Wickham" at the wedding — at which Elizabeth "repeated in utter amazement" (part 21). The full account arrives in Mrs. Gardiner's long letter, which explains that Darcy left Derbyshire a day after the Gardiners, came to town resolved to hunt down Wickham, and called on Mr. Gardiner, shut up with him for several hours, to tell him he had found the couple (parts 21). Mrs. Gardiner reports that Darcy "found out where your sister and Mr. Wickham were" and saw and talked with Wickham repeatedly and Lydia once, first trying to persuade Lydia to leave her disgraceful situation and return to her friends (part 21). Because Lydia refused to leave Wickham, Darcy arranged the marriage, and what he did for the young people was: Wickham's debts paid, "amounting, I believe, to considerably more than a thousand pounds," another thousand pounds settled on Lydia in addition to her own, and Wickham's commission purchased (part 21). Darcy alone insisted on doing all this, offering it as owing to his own reserve having allowed Wickham's character to be so misunderstood; Mrs. Gardiner begs that this go no further than Elizabeth and Jane (part 21). Elizabeth, who had been crediting her uncle and aunt for everything, is stunned by the discovery, and later tells Darcy directly that she has been informed of his "unexampled kindness to my poor sister" (part 24).

### 车道 B（纯内容 · 无向量）

I'll navigate the knowledge base to find the answer.



## NQ4

**Q**：Mr. Wickham was involved in two elopements. For each, state who the girl was, how old she was, where it happened, and whether it was carried out.

### 车道 A（向量 + 内容）

I have what I need from the retrieval.

**Answer:** Wickham's first elopement involved Miss Georgiana Darcy, Mr. Darcy's sister, who was "then but fifteen," and it was planned at Ramsgate, where she had gone for the summer with her companion Mrs. Younge (who connived with Wickham, her prior acquaintance); Darcy arrived unexpectedly a day or two before the intended elopement and it was **never carried out** — Darcy's account of it appears in *pride_and_prejudice (part 14 of 26).md*. His second elopement involved Lydia Bennet, the youngest Bennet daughter, who was sixteen (her mother exclaims "She will be married at sixteen!"); she went from Brighton with the regiment's encampment and ran off with Wickham, and it **was** carried out, though Wickham never intended to marry her — he was found with her in London (traced by Darcy in town) and only married her after Darcy's intervention and financial settlement. Lydia's own aunt and father stress that Wickham's intent was dishonourable and that he had never intended marriage, and Elizabeth reflects on "a dishonourable elopement" — all in *pride_and_prejudice (part 18, part 19, part 20, part 21 of 26).md*. So: Georgiana Darcy, 15, Ramsgate — not carried out; Lydia Bennet, 16, from Brighton to London — carried out (ultimately as a marriage).

### 车道 B（纯内容 · 无向量）

I'll verify by reading content, since descriptions are boilerplate.


