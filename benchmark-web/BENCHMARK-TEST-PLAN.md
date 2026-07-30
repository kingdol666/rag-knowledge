# QDCVR+MoE Benchmark — System-Unique Test Plan v2.0
# Target: Measure KB Management Automation + MoE-style Activation + Content Verification
# Date: 2026-07-30

## 0. What Makes This System Different

Standard RAG benchmarks measure "given a query and N documents, can you find the right one?"
This system does something fundamentally different:

  ┌─────────────────────────────────────────────────────┐
  │              MoE-style QDCVR Architecture            │
  │                                                      │
  │  User Query                                          │
  │     │                                                │
  │     ▼                                                │
  │  ┌──────────────────────┐                            │
  │  │ Step 0: Query Analyze │  Intent classification    │
  │  │ → 改写为检索友好形态   │  Entity extraction        │
  │  └──────┬───────────────┘                            │
  │         │                                            │
  │         ▼                                            │
  │  ┌──────────────────────┐                            │
  │  │ Step 1: MoE Router    │  ← THE CORE INNOVATION    │
  │  │ kb_list(lightweight)  │  Read KB descriptions     │
  │  │ → Select top 1-3 KBs  │  Activate ONLY these KBs  │
  │  │ → IGNORE others       │  ← 像 MoE gate 一样       │
  │  └──────┬───────────────┘                            │
  │         │                                            │
  │         ▼                                            │
  │  ┌──────────────────────┐                            │
  │  │ Step 2: Activated     │  Vector search ONLY on     │
  │  │ Search (仅选中KB)     │  activated KBs            │
  │  │ kb_search_vector/      │  NOT full scan            │
  │  │ kb_search_two_stage    │                            │
  │  └──────┬───────────────┘                            │
  │         │                                            │
  │         ▼                                            │
  │  ┌──────────────────────┐                            │
  │  │ Step 3: Content       │  kb_doc_read 3000 chars   │
  │  │ Verification          │  0-8 rubric scoring       │
  │  │ → 独立裁决,不盲信向量  │  Content > Vector         │
  │  └──────┬───────────────┘                            │
  │         │                                            │
  │         ▼                                            │
  │  ┌──────────────────────┐                            │
  │  │ Step 6: Answer +      │  P0/P1/P2 置信度          │
  │  │ Blind-spot声明        │  + 来源 + 盲区             │
  │  └──────────────────────┘                            │
  └─────────────────────────────────────────────────────┘

The key metrics for THIS system are NOT P@1/P@5 — they are:

  A. KB ROUTING ACCURACY: Does Step 1 select the correct KB(s)?
  B. SEARCH SPACE REDUCTION: How many chunks are filtered out?
  C. CONTENT VERIFICATION ACCURACY: Does Step 3 correctly judge relevance?
  D. END-TO-END ANSWER QUALITY: Does the final answer contain verified evidence?
  E. INGEST AUTOMATION QUALITY: Auto-tag + auto-subKB routing accuracy


## I. BENCHMARK DESIGN PRINCIPLES

### Principle 1: Use REAL documents from the actual 14 KBs
No synthetic docs. Use existing documents from 高分子双向拉伸文献库 (77 docs,
13 sub-KBs), AI-ML-Research (20 docs), etc. This tests the system as-deployed.

### Principle 2: Measure KB ROUTING, not just retrieval
The unique value is the MoE gate — selecting which KB to activate. Compare:
- QDCVR-MoE: Step 1 selects KBs → search only those
- QDCVR-Flat: Skip Step 1 → search all KBs (ablation)
- The difference = MoE routing contribution

### Principle 3: Measure CONTENT VERIFICATION, not just vector similarity
Vector score is a HINT. Content score is the VERDICT.
Compare answer quality with and without Step 3 content verification.

### Principle 4: Measure SEARCH SPACE REDUCTION
A 77-doc KB with 7612 chunks: how many chunks does each query actually scan?
The MoE architecture should scan << 7612 on average.

### Principle 5: Measure INGEST AUTOMATION
How well does the system auto-tag and auto-route new documents into sub-KBs?


## II. TEST PHASES

### Phase A: KB Routing Accuracy (MoE Gate Test)
────────────────────────────────────────────────
What: Given 20 queries spanning 6+ domains, does Step 1 select the correct KB?

Method:
  1. For each query, run the FULL QDCVR pipeline
  2. Record which KB(s) Step 1 selected
  3. Compare against ground-truth "correct KB" annotation
  4. Also run as ablation: skip Step 1, search ALL KBs

Metrics:
  - KB Selection Precision: % of queries where correct KB is in selected set
  - KB Selection Recall: % of all correct KBs that were selected
  - Over-selection Rate: avg # of KBs selected (lower = more efficient)
  - Routing Latency: time spent in Step 1

Queries (20 total):
  ┌──────┬──────────────────────────────────────────────────┬──────────────────────┐
  │ ID   │ Query                                             │ Correct KB(s)         │
  ├──────┼──────────────────────────────────────────────────┼──────────────────────┤
  │ R-01 │ BOPET薄膜拉伸过程中的应变诱导结晶行为              │ 高分子双向拉伸/03_PET │
  │ R-02 │ PVA偏光片薄膜的双向拉伸工艺与光学性能              │ 高分子双向拉伸/04_PVA │
  │ R-03 │ BOPP电容膜击穿强度与拉伸比的关系                  │ 高分子双向拉伸/05_PP  │
  │ R-04 │ PLA可降解薄膜的热定型松弛行为                      │ 高分子双向拉伸/06_PLA │
  │ R-05 │ 尼龙6双向拉伸过程中的晶型转变                      │ 高分子双向拉伸/07_PA  │
  │ R-06 │ Adam优化器的自适应学习率与偏差校正机制             │ AI-ML-Research        │
  │ R-07 │ Transformer多头自注意力与位置编码                  │ AI-ML-Research        │
  │ R-08 │ RAG检索增强生成的三种范式对比                      │ AI-ML-Research        │
  │ R-09 │ 锂离子电池相变材料热管理中的铜泡沫复合材料         │ Energy-Batteries      │
  │ R-10 │ 固态电解质LLZO离子电导率与界面稳定性               │ Energy-Batteries      │
  │ R-11 │ MXene Ti3C2Tx的层间距调控与赝电容机理              │ Materials-Science     │
  │ R-12 │ 机器学习原子间势函数替代DFT计算                    │ Materials-Science     │
  │ R-13 │ 脑机接口颅内EEG的PEDOT:PSS电极阻抗优化             │ Biomedical-Engineering│
  │ R-14 │ 细菌纤维素骨组织工程支架的羟基磷灰石矿化           │ Biomedical-Engineering│
  │ R-15 │ RT-2视觉语言动作模型的sim-to-real泛化             │ Embodied-AI           │
  │ R-16 │ DreamerV3世界模型的离散隐空间想象规划             │ Embodied-AI           │
  │ R-17 │ 单原子催化剂M-N4位点的CO2还原法拉第效率           │ Chemistry-Catalysis   │
  │ R-18 │ TiO2光催化氟烷基化的配体-金属电荷转移机理          │ Chemistry-Catalysis   │
  │ R-19 │ 2D材料范德华异质结的能带工程与twistronics         │ Materials-Science     │
  │     │   (adversarial: also matches 高分子库 physics)     │                       │
  │ R-20 │ 强化学习在材料逆设计中的应用                      │ Materials-ML-Inverse  │
  │     │   (cross-domain: AI-ML ∩ Materials)               │ Design                │
  └──────┴──────────────────────────────────────────────────┴──────────────────────┘


### Phase B: Search Space Reduction (Efficiency Test)
────────────────────────────────────────────────
What: How many chunks does the system actually scan per query?

Method:
  1. For each of the 20 queries above, record:
     a) Total chunks in full KB set: ~30,000 (all 14 KBs)
     b) Chunks in activated KBs (Step 1): typically 500-8000
     c) Chunks in Step 2 recall candidates (stage1_top_k): 20
     d) Chunks in Step 2.5 after dedup+threshold: typically 3-8
     e) Chunks actually read in Step 3 (kb_doc_read, max_chars=3000): typically 1-5
  2. Compare QDCVR-MoE vs QDCVR-Flat (skip Step 1)

Metrics:
  - Search Space Compression Ratio = (c) / (b)  — Step 2 compresses activated KB
  - MoE Reduction Ratio = (b) / (a)  — Step 1 compresses full KB set
  - Total Reduction Ratio = (e) / (a)  — end-to-end: read 5 docs out of 30K chunks
  - Avg chunks scanned per query

Expected: Total Reduction Ratio should be ~30K → 5 = 6000x


### Phase C: Content Verification Accuracy (Step 3 Test)
────────────────────────────────────────────────
What: Does Step 3 correctly separate relevant from irrelevant results?

Method:
  1. For the top 5 results from Step 2 (before Step 3), annotate ground-truth:
     - Score 0-2: Irrelevant — wrong domain or topic
     - Score 3-5: Partially relevant — adjacent domain, useful background
     - Score 6-8: Directly relevant — answers the query
  2. Run Step 3 content verification (kb_doc_read + 0-8 scoring)
  3. Compare system content score vs human annotation

Metrics:
  - Content Score Accuracy: correlation between system 0-8 and human 0-2/3-5/6-8
  - False Positive Rate: system scores ≥6 but human says ≤2
  - False Negative Rate: system scores ≤4 but human says ≥6
  - P0/P1/P2 tier accuracy: does tier assignment match human judgment?

Test set: Sample 30 result pairs (query, doc) from Phase A, annotate manually.


### Phase D: Ingest Automation Quality (Auto-Management Test)
────────────────────────────────────────────────
What: When new documents are ingested, does the system correctly:
  - Assign accurate tags?
  - Route to the correct KB/sub-KB?
  - Generate useful descriptions?

Method:
  1. Select 10 real research paper abstracts (not yet in any KB)
  2. Run the full A0-A9 ingest pipeline:
     parse_doc → A2-Q parse quality → A3a structured analysis →
     A3b tag quality gate → A3c description quality gate →
     A4 KB attribution decision tree → A5 store → A6 index
  3. For each document, record:
     - Auto-assigned tags (predicted)
     - Auto-selected KB (predicted)
     - Auto-generated description (predicted)
  4. Compare against human annotations (ground truth)

Metrics:
  - Tag Precision: % of auto-tags that are correct (human-approved)
  - Tag Recall: % of human-expected tags that were auto-assigned
  - KB Routing Accuracy: % of docs routed to correct KB
  - Sub-KB Routing Accuracy: % of docs correctly routed to sub-KB (if applicable)
  - Description Quality Score: 0-4 rubric (domain identified + method named +
    problem stated + key finding mentioned)


### Phase E: End-to-End Answer Quality (Full Pipeline Test)
────────────────────────────────────────────────
What: Given a query, does the FULL QDCVR+MoE pipeline produce a correct,
evidence-backed answer?

Method:
  1. For 15 queries from Phase A, run the complete pipeline
  2. Evaluate the final answer on:
     a) Factual correctness (0-3): Does the answer contain verifiable facts?
     b) Evidence grounding (0-3): Are claims backed by specific document citations?
     c) Completeness (0-2): Does the answer address all parts of the query?
     d) Blind-spot honesty (0-2): Does the answer admit what it doesn't know?
  3. Compare: QDCVR-MoE vs QDCVR-Flat vs BM25-only

Metrics:
  - Answer Quality Score (0-10 composite)
  - Hallucination Rate: claims not supported by cited documents
  - Blind-spot Declaration Rate: % of answers that honestly declare gaps


### Phase F: Experience Extraction Quality (Meditation Test)
────────────────────────────────────────────────
What: After Q&A pairs are accumulated as "signals", does the meditation
system correctly extract actionable experiences?

Method:
  1. Collect 10 Q&A pairs as signals (use Phase E queries + answers)
  2. Trigger meditation: experience_meditation_run(kb_id)
  3. Evaluate extracted experiences:
     - Is the title actionable (not just the doc title)?
     - Does the problem statement correctly capture the Q&A intent?
     - Does the solution contain specific, actionable steps?
     - Are key_lessons independently useful?

Metrics:
  - Experience Actionability Score (0-5): Can someone act on this?
  - Signal-to-Experience Conversion Rate: useful experiences / total signals
  - Content Fidelity: does the experience accurately reflect the source doc?


## III. COMPARISON BASELINES (Simplified)

Not comparing against external RAG methods — comparing against ABLATIONS of our own system:

| ID  | Method                          | What it tests                              |
|-----|---------------------------------|--------------------------------------------|
| B1  | QDCVR-MoE (full)               | Complete pipeline — our system             |
| B2  | QDCVR-Flat (no Step 1)         | Ablation: skip KB routing — search all KBs |
| B3  | QDCVR-NoVerify (no Step 3)     | Ablation: skip content verification        |
| B4  | BM25-only (no QDCVR)           | Baseline: pure keyword retrieval           |

The comparisons tell us:
- B1 vs B2: Contribution of MoE KB routing
- B1 vs B3: Contribution of content verification
- B1 vs B4: Overall QDCVR improvement over BM25


## IV. METRICS SUMMARY TABLE

| Phase | Primary Metric | Target |
|-------|---------------|--------|
| A: KB Routing | KB Selection Precision | ≥ 90% |
| A: KB Routing | Over-selection Rate | ≤ 3 KBs avg |
| B: Space Reduction | Total Reduction Ratio (e/a) | ≥ 1000x |
| B: Space Reduction | MoE Reduction Ratio (b/a) | ≥ 10x |
| C: Content Verify | Content Score Accuracy | ≥ 85% agreement |
| C: Content Verify | False Positive Rate | ≤ 10% |
| D: Ingest Quality | KB Routing Accuracy | ≥ 90% |
| D: Ingest Quality | Tag Precision | ≥ 80% |
| E: Answer Quality | Answer Quality Score | ≥ 7/10 |
| E: Answer Quality | Hallucination Rate | ≤ 5% |
| F: Experience | Actionability Score | ≥ 3/5 |

## V. EXECUTION PLAN

1. [ ] Phase A: Run 20 KB routing queries, compare MoE vs Flat
2. [ ] Phase B: Record chunk counts at each pipeline stage
3. [ ] Phase C: Human-annotate 30 result pairs, compare Step 3 scores
4. [ ] Phase D: Ingest 10 new paper abstracts, evaluate auto-management
5. [ ] Phase E: Run full pipeline on 15 queries, evaluate answers
6. [ ] Phase F: Accumulate signals, trigger meditation, evaluate experiences
7. [ ] Generate HTML report with all metrics
