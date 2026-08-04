# Error Analysis — QDCVR Benchmark

**Date:** 2026-07-27 | **System:** QDCVR Knowledge Platform v1.0 | **Queries:** 8 benchmark + 20 operational

---

## 1. Retrieval Errors (EXP-1, EXP-2)

### 1.1 Cross-Domain False Positives (Flat Search)

| Query | Flat P@5 | FPR | Cross-Domain Hits | Root Cause |
|-------|----------|-----|--------------------|------------|
| thermal management cooling optimization | 0.60 | 0.40 | Materials-ML (spacecraft thermal), 高分子 (thermal analysis) | Keyword overlap "thermal management" across domains |
| reinforcement learning policy optimization | 0.20 | 0.80 | Economics-DataScience (financial RL), Materials-ML (×2), AI-ML/RAG | "RL" spans finance, materials, and AI; no domain anchor |
| deep learning neural network attention transformer | 0.80 | 0.20 | Economics-DataScience (transformer for finance) | "Transformer" overloaded: NLP architecture vs financial models |
| behavioral economics cognitive bias decision making | 0.80 | 0.20 | Energy-Batteries (battery economics) | "Economics" keyword triggers battery cost-analysis docs |
| graph neural network materials property prediction | 0.80 | 0.20 | 高分子 (GNN for polymer) | GNN methods shared across materials subfields |

**Pattern:** All FPR>0 queries involve **multi-domain terminology** — terms that exist in multiple KBs with different meanings. Flat vector search cannot distinguish "transformer" (NLP) from "transformer" (finance) or "RL" (AI) from "RL" (finance).

**QDCVR Fix:** Domain scoping (Step 1) + content verification (Step 3) eliminates 91% of these false positives.

### 1.2 Domain Selection Errors

| Query | Expected KB | Selected KB | Impact |
|-------|-------------|-------------|--------|
| graph neural network materials property prediction inverse design | Materials-ML-InverseDesign | Materials-Science | P@5 still 1.0 (both KBs relevant), but suboptimal for future queries |

**Rate:** 1/8 = 12.5% domain selection error. Low impact in this case because Materials-Science and Materials-ML-InverseDesign share relevant documents. Higher impact expected for more divergent domains.

---

## 2. Archiving Errors (EXP-6)

### 2.1 Intra-Domain Confusion (12% of errors)

| Actual KB | Predicted KB | Count | Shared Vocabulary |
|-----------|--------------|-------|-------------------|
| Materials-ML-InverseDesign | Materials-Science | 1 | "materials," "property prediction" |
| Materials-Science | Materials-ML-InverseDesign | 1 | "materials," "ML methods" |
| 高分子双向拉伸文献库 | Materials-Science | 2 | "polymer," "mechanical properties" |
| AI-ML-Research | Materials-ML-InverseDesign | 1 | "neural network," "prediction" |

**Pattern:** Related subdomains share significant vocabulary. The A3d decision tree correctly identifies the parent domain but confuses sibling sub-KBs.

**Mitigation:** Content-based verification (Step A6) catches most of these by reading the document body, not just the title.

### 2.2 Cross-Domain Errors (4% of errors)

| Title | Expected | Predicted | Cause |
|-------|----------|-----------|-------|
| Economic Analysis of Battery Storage | Energy-Batteries | Economics-DataScience | Title leads with "Economic" |
| ML for Polymer Property Prediction | 高分子 | Materials-ML-InverseDesign | "ML" in title dominates |

**Pattern:** Adversarial titles that lead with the wrong domain keyword. Top-1 accuracy drops from 84% to 65% on adversarial titles.

**Mitigation:** A3d decision tree reads full content, not just title. Content-based archiving (A6) corrects most title-induced errors.

---

## 3. Content Verification Errors (EXP-4)

### 3.1 False Negatives (Missed Rescues)

| Doc | Vector Score | Content Score | Issue |
|-----|-------------|---------------|-------|
| "Solid electrolyte interface in Li-metal batteries" | 0.48 | 6 | Abbreviation "SEI" not in query; vector fails to match |
| "Policy gradient methods for continuous control" | 0.44 | 6 | Mathematical notation differs from query phrasing |

**Rate:** 8% of candidates are low-vector but content-relevant. 69% of these are rescued by content verification; 31% are lost because they don't pass the vector pre-filter (score < 0.35).

**Impact:** Minor — these are edge cases where terminology differs significantly between query and document.

### 3.2 False Positive Leakage (Missed Catches)

| Doc | Vector Score | Content Score | Issue |
|-----|-------------|---------------|-------|
| "Thermal analysis of polymer films" | 0.72 | 5 | Borderline: relevant to materials but query asks about energy |
| "Transformer models for time series" | 0.68 | 5 | Ambiguous: could be energy load forecasting or NLP |

**Rate:** 28% of high-vector false positives (vector > 0.6) are not caught by content verification (content score 5, just below threshold 6).

**Mitigation:** Lowering content threshold to 5 would catch these but would also filter more borderline-relevant docs. Threshold 6 is the optimal trade-off (see EXP-8 sensitivity analysis).

---

## 4. Experience Pipeline Gaps (EXP-5)

### 4.1 Coverage Gap

- **14 experiences exist, all in AI-ML-Research sub-KB**
- **10 KBs have zero experiences**
- Experience hit rate for AI-ML queries: 95%
- Experience hit rate for other domains: 0%

**Impact:** Experience acceleration (62% doc reduction, 60% time reduction) only benefits AI-ML queries. Other domains see no experience benefit.

**Recommendation:** Priority experience extraction for 高分子 (largest KB) and Materials-ML-InverseDesign (most cross-domain queries).

### 4.2 Experience Quality

- Auto-extraction accuracy: 82% (18% of extracted experiences need manual correction)
- Average quality score: 3.8/5
- 2/14 experiences rated below 3.0 (low quality, need E1 heuristic refinement)

---

## 5. Latency Bottlenecks (EXP-7)

| Stage | Latency | % Total | Optimization Opportunity |
|-------|---------|---------|--------------------------|
| Content Verification | 1,050ms | 56.8% | **Primary target:** fast-exit, parallel scoring, smaller candidate set |
| Two-Stage Recall | 250ms | 13.5% | Minor: index optimization |
| Answer Synthesis | 200ms | 10.8% | Minor: template-based for P0 |
| Confidence Tiering | 150ms | 8.1% | Minor: cached rules |
| Query Understanding | 120ms | 6.5% | Minimal: already fast |
| KB Selection | 80ms | 4.3% | Minimal: metadata lookup |

**Fast-Exit Impact:** When content score ≥ 6 on first evaluation, remaining 19 candidates are skipped. Fast-exit rate: 17.5%, reducing latency from 1,850ms to ~680ms (63% reduction) with only 0.005 P@5 loss.

---

## 6. Summary of Error Sources

| Error Source | Frequency | Impact | Mitigation |
|--------------|-----------|--------|------------|
| Multi-domain terminology | 5/8 queries | High (FPR +27.5%) | Domain scoping + content verification |
| Sub-KB confusion | 12% of docs | Medium (wrong KB) | Content-based archiving |
| Adversarial titles | 35% of adversarial | Medium (wrong KB) | Full-content reading (A6) |
| Low-vector relevant docs | 8% of candidates | Low (missed rescue) | BM25 fusion helps |
| Experience coverage gap | 10/12 KBs | Medium (no exp benefit) | Priority extraction |
| Content verification latency | Every query | High (56.8% latency) | Fast-exit + parallel scoring |
