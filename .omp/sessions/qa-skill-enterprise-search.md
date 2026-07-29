# QA Report: Search-Enterprise (跨库/平衡KBs)

| 工具 | PASS/FAIL | 观察 | 回归bug验证 |
|---|---|---|---|
| 1. backend_status | ✅ PASS | status: healthy, MinerU available |
| 2. kb_create ×2 | ✅ PASS | ML KB (id: c9015c54), BIO KB (id: f4c69f84) created |
| 3a. kb_doc_create ×6 | ✅ PASS | ML: Transformer-model, CNN-architecture, GAN-generative-model; BIO: protein-structure, gene-regulation, cell-biology |
| 3b. kb_index_document ×6 | ✅ PASS | All 6 indexed with 2 chunks each, bge-m3 | BUG5: auto-index + explicit index no conflict ✅ |
| 4. kb_search_vector(cross-KB) | ✅ PASS | Cross-KB vector search (kb_id="") returns results from both test KBs: ML GAN doc at score 0.683 (#1), BIO gene-regulation at 0.605; ML Transformer at 0.542 | BUG2: collection naming `kb_<UUID>` verified ✅ |
| 5. kb_search_two_stage(balance_kbs=True) | ✅ PASS | balance_kbs returns results from diverse KBs; cross-KB fallback triggered when BM25 returns only 1 KB; supplement adds balanced results |
| 6. kb_search(metadata) | ✅ PASS | "cell" → BIO cell-biology (score 10); "protein" → BIO protein-structure (score 10); "Transformer" → ML Transformer-model (score 10) |
| 7a. Boundary: unrelated vector search | ✅ PASS | "quantum chromodynamics" returns low scores (0.55→0.50), no test KB docs in results |
| 7b. Boundary: unrelated two_stage | ✅ PASS | "ancient greek philosophy" returns 1 keyword match, 5 stage2 results, no test KB docs |
| 8. kb_delete ×2 | ✅ PASS | Both KBs successfully deleted and no longer in kb_list |

| 回归验证 | 结果 | 备注 |
|---|---|---|
| BUG2: collection 命名统一 | ✅ PASS | Collection names use kb_<UUID> pattern |
| BUG5: 并发索引竞态 | ✅ PASS | Auto-index + explicit index both succeeded, no conflict |
| BUG6: stage2_top_k 严格 | ⚠️ NEEDS REVIEW | top_k=3 returns total_results=37, not 3. May need to verify if stage2_top_k is a separate parameter or top_k enforcement differs |
| BUG7: stage1=0 → source=vector | ⚠️ NEEDS REVIEW | stage1_top_k=0 still returns source:"keyword" with stage1_sources=[] — does not fall back to vector search |

## 关键发现

1. **Cross-KB vector search works** — both ML and BIO test KBs appear in results when searching across all KBs
2. **balance_kbs works** — when BM25 stage1 returns results from limited KBs, cross-KB fallback triggers balanced vector search supplement
3. **Metadata search finds test KBs** — by doc name across all collections
4. **Different content lengths affect cross-KB ranking** — short test docs (2 chunks) can be dominated by real KBs (hundreds of chunks) in broad queries; targeted queries work better
5. **ML KB needed explicit reindex** — after initial auto-index, vector search returned 0 results; re-solved after explicit kb_index_document

## 隔离性
- All operations scoped to QA-prefix KBs ✅
- Test KBs deleted after testing ✅
- No interaction with real 13 KBs ✅
