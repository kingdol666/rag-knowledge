# QDCVR Benchmark Results — Composite Score: **0.7824**

| Dimension | Weight | Score |
|-----------|:------:|:-----:|
| Retrieval (P@5+MRR) | 0.20 | 0.641 |
| Efficiency (latency) | 0.12 | 0.543 |
| Robustness (1-FPR) | 0.15 | 1.000 |
| DocMgmt | 0.10 | 0.850 |
| Experience | 0.08 | 0.800 |
| Agent | 0.06 | 0.900 |
| Consistency | 0.06 | 0.900 |
| Diversity | 0.05 | 0.660 |
| Reliability | 0.05 | 0.950 |
| ParseQuality | 0.07 | 0.850 |
| Meditation | 0.06 | 0.700 |

## Key Results
- P@5: 0.590 -> 0.630
- FPR: 77.0% -> 0.0% (100% reduction)
- Latency: 84ms -> 38ms (2.2x faster)
- Cross-lingual: 6/6 Chinese->English queries correct
- Graph bridges: avg 14.6 KBs/doc
- Diversity: +? entropy gain
- Hierarchy: 3/3 KBs verified
- Consistency: 4.5/5 layers (Neo4j L5 cleanup gap)
