---
name: knowledge-search
description: >
  Knowledge base search. Dedicated keyword and tag-based search workflow.
  S1→S5: parse query intent, full-text search across all KBs, tag-based
  lookup, group results by KB, present with scores and snippets.
  Invoked by Archival when the user wants to find documents by content
  or topic. Triggered by: "search", "find documents about", "query KB",
  "搜索", "查找内容".
---

# Knowledge Search — Collection Search Engine

Invoked by Archival when the scenario is diagnosed as **Search**
(search, find, query, 搜索, 查找, 查内容).

**Read-only.** Never modify any KB, document, or tag.

## S1 — Parse Query Intent

What type of search is the user asking for?

| Query type | Signal words | Procedure |
|-----------|--------------|-----------|
| **Keyword search** | "find documents about [topic]", "search for [term]" | S2 |
| **Tag search** | "documents tagged with [tag]", "find by tag [tag]" | S3 |
| **Combined** | "search for [topic] in [KB]" | S2 + S4 filter |
| **Similar documents** | "find docs like this one" | S2 with doc content as query |

## S2 — Keyword Search

```
kb_search(query="<user's topic or keywords>", top_k=15)
```

Returns hits ranked by relevance score, each with:
- Document name, KB name, score
- Content snippet with matching context

Present results grouped by KB:

```
## Search Results: "[query]"
Found N hits across M KBs

### [KB-Name] (N hits)
1. **[doc-name]** — Score: 0.95
   Snippet: "...matching text..."
2. **[doc-name]** — Score: 0.72
   Snippet: "...matching text..."

### [KB-Name] (N hits)
...
```

## S3 — Tag-Based Search

```
kb_doc_get_by_tag(tag="<tag>", kb_id?)
```

Leave `kb_id` empty to search all KBs, or specify to limit.

Present as:
```
## Tag Search: "[tag]"
N documents across M KBs

| KB | Document | Description |
|----|----------|-------------|
| Name | doc | (description) |
```

## S4 — Combined Search (Keyword + Tag)

1. Run `kb_search(query, top_k=10)` for keyword hits.
2. Run `kb_doc_get_by_tag(tag)` for tag hits.
3. Merge results, remove duplicates.
4. If KB specified: filter results to that KB.

## S5 — Present Results with Recommendations

After showing results, offer to:
- Read any result (`kb_doc_read` or `preview_file`)
- Refine the search with different keywords
- Search within a specific KB
- Add a new tag to a result document

---

## CRITICAL RULES
1. **Read-only.** Never modify. No create/update/delete/move.
2. S2 requires `kb_search()` — the full-text engine. Not available for raw PDFs.
3. S3 requires `kb_tags_list()` as context — load before searching by tag.
4. Format for humans: grouped, scored, with snippets. Not raw JSON.
