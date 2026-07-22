# Smart Search & Auto-Cleanup Details

> Referenced by knowledgebase-experience E4d (smart search) and E12 (auto-cleanup).

## E4d — Smart Search Enhancement

### Recommended entry: `experience_search_smart`

```
experience_search_smart(query, top_k=8)
  → intent recognition → adaptive threshold → multi-path recall → multi-round degradation → transparency
```

### Intent-based adaptive thresholds

| Intent type | Threshold | Strategy |
|-------------|-----------|----------|
| troubleshooting (故障排查) | 0.55 | Quality-first, only high-confidence |
| best_practice (最佳实践) | 0.45 | Medium bar |
| learning (学习参考) | 0.35 | Weak relevance acceptable |
| decision (决策支持) | 0.50 | Strong evidence needed |

### Multi-round degradation

```
Round 1: original query + adaptive threshold → 0 results
  → Round 2: lower threshold 30% → 0 results
    → Round 3: lower another 40% + skip content verify → results marked "degraded"
    → Still 0 → honest declaration "无相关经验"
```

### Transparency fields (per returned experience)

- `retrieval_paths`: recall path list (vector, keyword)
- `match_details`: {domain_match, problem_match, coverages}
- `ranking_reason`: human-readable ranking rationale

### Counter-example detection

`_content_verify` extracts domain terms from query and experience, detects mismatch. If `domain_diff > 50%` and `overlap < 30%` → score penalty (multiplier 0.5) → prevents false positives.

Example: "battery thermal management" vs "data center thermal management" — shares generic "thermal management" but differs in domain nouns → penalized.

### Smart rerank

```
experience_rerank(query, experiences_json)
  → multi-dimension scoring: tag_match(0.45) + problem_match(0.3) + solution_match(0.2) + credibility(0.25)
  → output sorted results + per-item ranking reason
```

### Relationship to E4a

- E4a Step 1底层 calls `experience_search_global` (compatibility preserved)
- E4d's `experience_search_smart` is recommended entry — adds intent recognition + multi-round degradation + transparency on top of `_global`
- Agent should prefer `experience_search_smart`; use `_global` only when manual threshold control needed

---

## E12 — Auto Health Check & Cleanup

### Trigger时机

- Every `knowledgebase-verify` V8 step (see [knowledgebase-verify](../../knowledgebase-verify/SKILL.md))
- Monthly periodic maintenance
- Auto-linked after document deletion

### Detection flow

```
# Step 1: global stale/orphan detection
experience_check_stale()   # empty kb_id = global
  → stale=0, orphan=0 → healthy
  → stale>0 → Step 2
  → orphan>0 → Step 3

# Step 2: handle stale experiences
for each stale_exp:
    experience_sync_kb(kb_id)   # re-extract from related doc (if still exists)
    # unrecoverable → mark needs_cleanup

# Step 3: handle orphan experiences
for each orphan_exp:
    detail = experience_read(kb_id, exp_id)
    if applied_count == 0 and rating == 0:
        experience_delete(kb_id, exp_id)    # unused orphan → delete
    elif applied_count > 0:
        experience_update(kb_id, exp_id, related_docs=[])  # valuable but link broken
    # else: keep, mark needs_sync

# Step 4: test pollution detection
for each kb with experiences:
    exp_list = experience_list(kb_id)   # ⚠️ use list not summary (summary returns top 5 only)
    for exp where rating==0 and applied==0:
        detail = experience_read(kb_id, exp.id)
        age_days = (now - detail.created_at).days
        if age_days > 7:
            experience_delete(kb_id, exp.id)
```

### Cleanup decision matrix

| Condition | Action |
|-----------|--------|
| orphan + applied=0 + rating=0 | Delete directly |
| orphan + applied>0 | Clear `related_docs`, keep experience content |
| stale + doc still exists | `experience_sync_kb` → re-extract |
| stale + doc deleted | → becomes orphan, handle per above |
| test pollution (rating=0, applied=0, age>7d) | Delete directly |
| disputed (review≥3, rating<2) | Mark downgrade, suggest manual review |
