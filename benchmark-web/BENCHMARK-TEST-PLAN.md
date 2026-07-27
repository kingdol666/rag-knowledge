# QDCVR Benchmark — Complete Retrieval Test Plan v1.0
# Target: CIKM 2027 Experimental Evaluation
# Date: 2026-07-27

## 0. Pre-flight Checklist

- [x] Benchmark backend running on port 8800
- [x] Project API running on port 8765
- [ ] Documents loaded (target: 30+ across 6 domains)
- [ ] Query set defined (target: 30+ queries with ground truth)
- [ ] All 8 baselines verified functional

## 1. Document Loading (Phase A)

Load documents representing diverse domains into the benchmark backend.
Each document MUST have: id, content, title, domain.

### Domain Distribution (target: 5 docs × 6 domains = 30 docs)

| Domain | Documents | Example Topics |
|--------|:---------:|---------------|
| AI-ML-Research | 5 | DQN, Transformer, RAG, SHAP, Adam optimizer |
| Energy-Batteries | 5 | Li-ion thermal, solid-state, Na-ion, supercapacitor, SOC estimation |
| Materials-Science | 5 | MXene, graphene, 2D materials, ML potentials, metamaterials |
| Biomedical-Engineering | 5 | Medical imaging, wearables, EEG, tissue engineering, drug delivery |
| Embodied-AI | 5 | VLA models, humanoid robots, world models, Sim-to-Real |
| Chemistry-Catalysis | 5 | Electrocatalysis, photocatalysis, heterogeneous catalysis |

### Loading method:
```
POST /api/docs/batch  with array of {id, content, title, domain}
```

## 2. Query Design (Phase B)

Design queries that test specific retrieval capabilities.
Each query MUST have: query text, correct_domain, correct_doc_id.

### Query Categories:

**Category 1: Domain-Specific (18 queries, 3 per domain)**
- Q-AI-1: "deep Q-network reinforcement learning Atari games experience replay" → AI-ML-Research/dqn
- Q-AI-2: "multi-head self-attention scaled dot-product transformer architecture" → AI-ML-Research/transformer
- Q-AI-3: "SHAP value explainable AI feature importance model interpretation" → AI-ML-Research
- Q-EN-1: "battery thermal management phase change material liquid cooling PCM" → Energy-Batteries/battery
- Q-EN-2: "solid-state electrolyte lithium ion conductivity sulfide NASICON" → Energy-Batteries
- Q-EN-3: "sodium ion battery cathode anode comparison LFP NMC" → Energy-Batteries
- Q-MA-1: "MXene Ti3C2Tx supercapacitor specific capacitance interlayer" → Materials-Science/mxene
- Q-MA-2: "machine learning interatomic potential DFT replacement materials" → Materials-Science
- Q-MA-3: "2D materials graphene transition metal dichalcogenide roadmap" → Materials-Science
- Q-BI-1: "convolutional neural network medical imaging chest X-ray pneumonia" → Biomedical-Engineering/medical
- Q-BI-2: "wearable multimodal sensor motion detection accelerometer deep learning" → Biomedical-Engineering
- Q-BI-3: "intracranial EEG brain-computer interface neural recording implantable" → Biomedical-Engineering
- Q-EM-1: "humanoid robot loco-manipulation vision-language-action model" → Embodied-AI/robot
- Q-EM-2: "Sim-to-Real transfer domain randomization legged locomotion policy" → Embodied-AI
- Q-EM-3: "world model embodied AI Dreamer reinforcement learning planning" → Embodied-AI
- Q-CH-1: "electrocatalysis hydrogen evolution reaction oxygen evolution overpotential" → Chemistry-Catalysis
- Q-CH-2: "heterogeneous catalysis machine learning potential surface reaction barrier" → Chemistry-Catalysis
- Q-CH-3: "photocatalysis TiO2 fluoroalkylation ligand metal charge transfer" → Chemistry-Catalysis

**Category 2: Cross-Domain Adversarial (8 queries)**
Queries whose vocabulary overlaps multiple domains — testing FPR.
- Q-AD-1: "reinforcement learning optimization policy gradient materials design" → ambiguity: AI-ML vs Materials-ML
- Q-AD-2: "deep learning CNN lightweight efficient model edge deployment" → ambiguity: AI-ML vs Biomedical vs Industrial
- Q-AD-3: "graph neural network state estimation prediction time series" → ambiguity: AI-ML vs Energy vs Materials
- Q-AD-4: "thermal management cooling heat transfer computational fluid dynamics" → ambiguity: Energy vs Materials-Science
- Q-AD-5: "machine learning healthcare diagnosis classification detection" → ambiguity: AI-ML vs Biomedical
- Q-AD-6: "neural network membrane design polymer electrolyte inverse optimization" → ambiguity: AI-ML vs Materials vs Energy
- Q-AD-7: "attention mechanism robot control manipulation planning vision" → ambiguity: AI-ML vs Embodied-AI
- Q-AD-8: "catalyst design screening high-throughput computational prediction" → ambiguity: Chemistry vs Materials-Science

**Category 3: Ambiguous/Boundary (4 queries)**
- Q-AM-1: "transformer architecture natural language processing" → AI-ML-Research (but 'transformer' appears in many domains)
- Q-AM-2: "energy storage battery materials electrolyte electrode design" → Energy (but overlaps with Materials)
- Q-AM-3: "sensor detection monitoring real-time wearable biomedical" → Biomedical (but overlaps with Materials)
- Q-AM-4: "machine learning model training optimization gradient descent" → AI-ML (generic ML terms)

**Total: 30 queries**

## 3. Baseline Methods (Phase C)

8 methods to test per query:

| ID | Method | Realness | Implementation |
|----|--------|:--------:|---------------|
| M1 | BM25 | [REAL] | rank_bm25 library |
| M2 | Dense | [REAL] | FAISS + BGE-M3 |
| M3 | Hybrid | [REAL] | BM25 + FAISS fusion (α=0.5) |
| M4 | CE Rerank | [REAL] | FAISS top-20 → cross-encoder/ms-marco-MiniLM-L-6-v2 rerank |
| M5 | CRAG | [ALGO] | Dense top-20 → evaluator → Correct/Incorrect/Ambiguous → expand |
| M6 | Self-RAG | [ALGO] | Dense top-20 → ISREL/ISSUP/ISUSE reflection → filter |
| M7 | QDCVR Flat | [PROJECT] | Your system: kb_search_vector(kb_id="") |
| M8 | QDCVR Domain | [PROJECT] | Your system: kb_search_vector(kb_id=<domain>) |

## 4. Execution Protocol (Phase D)

For each of the 30 queries:
1. Call `POST /api/search` with query + all 8 methods + top_k=5
2. Record: results, latencies, scores per method
3. For adversarial queries (Cat 2+3), also call `POST /api/compare` for FPR analysis

Total API calls: 30 queries × 1 request = 30 requests (each tests all 8 methods)
Plus: 12 adversarial queries × 1 compare request = 12 requests
**Total: ~42 API calls**

## 5. Metrics (Phase E)

Per query per method:
- P@1, P@3, P@5 (ground-truth doc in top-k)
- nDCG@5 (normalized discounted cumulative gain)
- MRR (mean reciprocal rank of first correct result)
- FPR (false positive rate = fraction of top-5 from wrong domain)
- Latency (ms)
- Search space size (chunks scanned)

Aggregate:
- Mean ± std for all metrics
- Paired t-test: M8 vs M1-M7 (Bonferroni corrected)
- Cohen's d effect size
- Win/Tie/Loss counts

## 6. Results Storage (Phase F)

All results saved to:
```
benchmark-web/backend/results/
├── raw/
│   ├── query_001.json ... query_030.json    ← raw API responses
│   └── compare_001.json ... compare_012.json ← FPR comparison data
├── aggregate.json                            ← computed metrics
├── statistical_tests.json                    ← significance tests
└── summary.json                              ← paper-ready summary
```

Plus LaTeX-ready tables in:
```
benchmark/paper-tables/
├── table1-main-results.tex   ← 8 methods × 7 metrics
├── table2-crossdomain.tex    ← FPR comparison
└── table3-ablation.tex       ← if ablation done
```

## 7. Success Criteria

| Criterion | Threshold |
|-----------|:---------:|
| Documents loaded | ≥ 30 across ≥ 6 domains |
| Queries executed | 30 |
| All 8 baselines functional | 8/8 |
| QDCVR Domain P@5 ≥ best baseline | P@5 improvement |
| QDCVR Domain FPR ≤ 0.05 | Near-zero cross-domain pollution |
| Statistical significance | p < 0.05 after Bonferroni |
| Effect size | Cohen's d ≥ 0.8 |

## 8. Execution Order

1. [ ] Load all 30 documents via batch API
2. [ ] Verify document count: GET /api/docs
3. [ ] Execute all 30 queries via /api/search (saves raw results)
4. [ ] Execute 12 adversarial queries via /api/compare (FPR analysis)
5. [ ] Compute aggregate metrics
6. [ ] Run statistical tests
7. [ ] Generate tables and figures
8. [ ] Write summary report
