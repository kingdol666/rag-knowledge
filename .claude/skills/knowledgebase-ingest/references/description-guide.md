# Description Writing Guide — Description Quality Gate

> **Core principle**: a description must be a **precise summary of content you have actually read** — not the filename, not a guess, not generic filler.
> The description is retrieval's "first filter" — `kb_list(lightweight=true)` / `kb_get_documents(lightweight=true)` / `kb_search` (metadata) all depend on it. A bad description = retrieval blindness.

## Golden Rule

**Read first, then describe. Writing a description without reading the body is forbidden.**

```
Parse path:  parse → poll until complete → read ≥3000 chars → write description → content readback verification
Direct path: read the full text (or the first 3000 chars) → write description → content readback verification
```

---

## D1 — The "Four Elements" Every Description Must Contain

A qualified document description must let the reader know, **from that single sentence alone, what the document is about and what problem it solves**:

| Element | What it is | If missing |
|---|---|---|
| **① Subject** | What the research object/material/system is | Domain cannot be judged |
| **② Method/Technology** | Which specific method/model/process was used | Similar documents cannot be distinguished |
| **③ Scenario/Problem** | What problem it solves, what scenario it applies to | Relevance cannot be judged |
| **④ Key data/Conclusion** | Key metrics, experiment scale, core findings | No credibility anchor |

**At least 2 concrete nouns among ③** (method names/equipment names/material names/dataset names); otherwise it is judged a "generic description" and rewritten.

## D2 — Document-Level Template

```
[Subject] + [Method/Technology] + [Problem solved/Scenario] + [Key data/Conclusion] + [Language]
```

### ✅ Good (every one has concrete words + is verifiable)
- "CNN-LSTM-based early-warning method for coal mill blockage in thermal power plants. Trains a multi-input single-step prediction model on DCS historical data; real-time residual analysis enables early identification of gradual faults. Field-tested on a 660 MW unit with a 315 min advance warning and zero false alarms. Chinese." (original: "基于 CNN-LSTM 的火电厂磨煤机堵管故障预警方法。利用 DCS 历史数据训练多输入单步预测模型，通过实时残差分析实现渐变故障早期识别。在 660 MW 机组实测，提前 315 min 预警且零误报。中文。")
- "Raman spectroscopy study of the effect of KI concentration (1%–3%) in PVA polarizing film on the iodine complex (I₃⁻/I₅⁻) equilibrium. Reveals that as KI concentration rises, I₅⁻ converts to I₃⁻, affecting the polarizing film's optical performance. 2022 Polymers. Mixed Chinese-English." (original: "PVA 偏光膜中 KI 浓度（1%–3%）对碘络合物（I₃⁻/I₅⁻）平衡影响的拉曼光谱研究。揭示 KI 浓度升高时 I₅⁻ 向 I₃⁻ 转化，影响偏光膜光学性能。2022 Polymers。中英混合。")
- "Self-RAG: through reflection tokens, a single LM learns when to retrieve, how to critique retrieval results, and how to use reflections to improve generation, improving factuality and controllability. Chinese organizing notes + English original abstract." (original: "Self-RAG：通过反思 token 让单一 LM 学会何时检索、如何评判检索结果、如何利用反思改进生成，提升事实性与可控性。中文整理 + 英文原文摘要。")

### ❌ Bad (must be rejected)
| Bad description | What's wrong |
|---|---|
| "a paper about coal mills" (一篇关于磨煤机的论文) | No method, no data, no scenario |
| "Parsed from XXX.pdf" | Filename/parse status used as the description |
| "test" / "Renamed" / "document" (文档) | Hollow |
| "introduces content related to deep learning" (介绍了深度学习的相关内容) | Generic, no concrete method |
| "polymer materials research" (高分子材料研究) | Domain only; no subject/method/scenario |
| "RAG survey" (RAG 综述) | Title restatement; no incremental information |

## D3 — KB-Level Templates (Layered)

### Parent KB
```
[Industry/Major category] + [List of covered sub-domains] + [Method lineage] + [Content types] + [Language]
```
✅ "Literature library on polymer biaxial stretching (Biaxial Stretching) technology, covering the biaxial stretching processes, crystallization mechanisms, characterization methods (WAXD/SAXS/DSC), and processing equipment of PET/PVA/PP/PLA/PA films. Mixed Chinese-English literature." (original: "高分子双向拉伸（Biaxial Stretching）技术文献库，涵盖 PET/PVA/PP/PLA/PA 等薄膜的双向拉伸工艺、结晶机理、表征方法（WAXD/SAXS/DSC）与加工设备。中英文献混合。")

### Sub-KB
```
[Specific material/sub-domain] + [Core method/process] + [Scenario] + [Document count] + [Language]
```
✅ "PET (polyester) biaxial stretching sub-library: thermo-mechanical constitutive modeling, strain-induced crystallization, birefringence, piezoelectric properties. Contains 6 TUe/arXiv/Polymers papers. Mixed Chinese-English." (original: "PET（聚酯）双向拉伸子库：热机械本构建模、应变诱导结晶、双折射、压电性能。含 6 篇 TUe/arXiv/Polymers 文献。中英混合。")

## D4 — Content Readback Verification (Mandatory, Cannot Be Skipped)

After writing the description, you **must** read the body back and verify **every key claim** in the description:

```
kb_doc_read(kb_id, doc_path, max_chars=800)
```

Check item by item:
- [ ] Do the **method/model names** in the description appear in the body? ("CNN-LSTM" → search the body, confirm it exists)
- [ ] Do the **materials/equipment** appear in the body? ("660 MW unit" → confirm)
- [ ] Are the **data/conclusions** in the description consistent with the body? ("315 min advance warning" → the body really has this figure)
- [ ] Is the **language label** accurate? (the body is Chinese/English/mixed)

**Any mismatch → rewrite the description**, never modify the body to fit the description.
> Field case: a description once claimed "Transformer attention mechanism" while the body was actually CNN image classification → this must be rewritten.

## D5 — Quality Contract for Sub-Agent Delegation

For ≥3 documents or a single document >50KB, when delegating analysis to sub-agents, the **hard output contract** is:

```json
{
  "title": "specific title (not the filename)",
  "domain": "main domain",
  "sub_domain": "sub-domain",
  "methods": ["method 1", "method 2"],
  "materials": ["material 1"],
  "scenario": "scenario/problem solved",
  "key_results": ["key data/conclusion 1"],
  "language": "zh|en|mixed",
  "suggested_tags": ["2-5 normalized tags"],
  "suggested_description": "complete description with ≥ the four elements",
  "content_evidence": "where each keyword in the description appears in the body / the sentence"
}
```

**Acceptance**: the parent Agent must check that `content_evidence` is non-empty and that `methods` and `materials` are locatable in the body; otherwise reject and redo.

## D6 — Self-Check Mantra

> "If someone runs into [the scenario I described], reading only this one description, can they be **100% certain** this is the document they need?"

- Answer "yes" → pass
- Answer "maybe/probably" → add concrete words
- Answer "not sure" → re-read the content and rewrite

## D7 — Multilingual Handling

- Chinese documents: description in Chinese, proprietary technical terms kept in English (`Transformer` `GraphRAG`)
- English documents: description as a Chinese summary + tagged "English original"
- Mixed: description in Chinese + "mixed Chinese-English" tag at the end
- **Never** use an English abstract as the description directly — it must be distilled into a structured Chinese summary

## D8 — Multi-Dimension Description + Query Orientation (Core of Retrieval Positioning) ⭐

> A description's mission is not just "summarizing the document" but **making future queries hit**. Users phrase questions in endlessly varied ways,
> so the description must lay in the **keywords of multiple query paths**.

### The Five Mandatory Dimensions (check one by one; fill in any missing dimension)

| Dimension | What to write | Typical query phrasing |
|---|---|---|
| **Domain dimension (领域维)** | Canonical terms of the domain/sub-domain | "literature in the XX field" (XX领域的文献) |
| **Method dimension (方法维)** | Proper names of methods/models/algorithms | "material that uses CNN-LSTM / Transformer / RAG" (用了 CNN-LSTM / Transformer / RAG 的资料) |
| **Object dimension (对象维)** | Proper names of materials/equipment/systems/datasets | "content about PET film / 660MW units" (关于 PET 薄膜 / 660MW 机组的内容) |
| **Problem dimension (问题维)** | The question this document can answer, **written in the questioner's voice** | a search for "how to early-warn coal mill blockage" (磨煤机堵管怎么预警) hits |
| **Conclusion dimension (结论维)** | Key quantitative conclusions (numbers preferred) | "the case with a 315 min advance warning" (提前 315 min 预警的案例) |

### Bilingual Anchors
Keep English method/model/dataset names verbatim (`Transformer` `GraphRAG` `BERT`) inside Chinese descriptions,
so both Chinese and English queries can hit metadata search.

### Three-Window Sampling for Long Documents (mandatory for >20000 chars)
Reading only the first 3000 chars misses the real meaning of the mid/tail sections. Before writing the description you must:
```
Head window 0-3000 + middle window (total/2)±1500 + tail window (total-2000)-total
```
Distill 1-2 points from each of the three windows into the description; a long-document description written from the head window alone is disqualified.

### Two-Layer Description Pattern for Split Parts
After a large document is split, each part's description must be **two-layered**, so both "find by paper" and "find by section" hit:
```
【第 i/N 部分 · <本章章节范围>】<论文级主体+方法> —— <本 part 特有内容/关键点>
# i.e. 【Part i/N · <this part's section range>】<paper-level subject + method> —— <this part's specific content/key points>
```
The paper-level elements (subject/method/conclusion) are kept in every part; this part's specific section content goes after the em dash.

### Length Cap
A single description is **≤ 220 chars** (so the `kb_list` view stays scannable). When overlong, first compress secondary numbers in the conclusion dimension; **never delete** the method dimension or the problem dimension.

## D9 — Retrieval Self-Test (Mandatory Closed Loop After Writing the Description) ⭐

> "Finished writing" is not done — **use your own description as the query and verify retrieval can recall it**.

Run after ingestion completes (after A6 indexing):

```
# 1. Metadata search: query with the problem-dimension wording from the description
kb_search(query="<the problem-dimension sentence>", top_k=5)
→ the target document must appear in the results (metadata search mainly matches description/tags)

# 2. Vector search: query with a paraphrase (do not copy the original sentence)
kb_search_vector(query="<paraphrased question>", top_k=5, score_threshold=0.3)
→ the target document in the top-5 (proves the vector index works)
```

**Miss → the description lacks a query path**: merge the query's keywords (problem/method dimensions) into the description,
then retest after updating the description. A3c passes the gate only when both channels hit.
