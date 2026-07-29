# RAG Knowledge Platform — System Process Logic

## Overall Data Flow

```
Upload PDF → MinerU OCR Parse → Save Markdown → Index Vectors → Build Graph → Searchable Knowledge
                                                                                        │
User Query ──→ KB Selection ──→ Multi-Recall ──→ Content Verify ──→ Confidence Rate ──→ Answer
                    │                │                │                    │
               balance_kbs      BM25+Vector      0-8 Rubric           P0/P1/P2
               diversity        +Graph+Tag        <6=expand            +Blind Spot
                                                        │
                                                   <4=HARD DISCARD
```

## Layer 1 — Ingestion Pipeline (A0-A9)

```
raw file (PDF/Word/Excel/Image)
    │
    ▼
[A0] fs_upload → registered in .tree-fs.json
    │
    ▼
[A1] parse_doc → MinerU OCR → Markdown
    │
    ▼
[A2] kb_doc_save_parsed → .knowledge-base.yml
    │
    ▼
[A3-A9] Quality Gates:
  dedup (content fingerprint)
  tag normalization + blacklist
  description quality check (4 elements)
  KB attribution decision tree
  vector indexing (BGE-M3 1024-dim)
  graph building (Neo4j nodes + edges)
  post-index verification
```

## Layer 2 — Retrieval Pipeline

```
                  User Query
                      │
                      ▼
         ┌─────────────────────┐
         │  KB Selection       │
         │  (smart dispatch)   │  ← balance_kbs diversity guard
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  Stage 1: Broad     │
         │  Recall (4 paths)   │
         │                     │
         │  BM25 Keyword ──────│── jieba tokenizer
         │  Vector Semantic ───│── BGE-M3 cos similarity
         │  Tag-Based ────────│── exact tag match
         │  Graph Expansion ──│── Neo4j RELATED_TO
         └──────────┬──────────┘
                    │ candidate docs
         ┌──────────▼──────────┐
         │  Stage 2: Fine      │
         │  Vector Rerank      │  ← only within candidate docs
         └──────────┬──────────┘
                    │ ranked chunks
         ┌──────────▼──────────┐
         │  Content Verify     │  ⭐ Core Innovation
         │  0-8 Scoring Rubric │
         │                     │
         │  7-8: Direct hit    │── P0 (returned)
         │  5-6: Partial       │── P1 (expand + return)
         │  3-4: Tangential    │── P2 (expand, reconsider)
         │  0-2: Off-topic     │── HARD DISCARD
         └──────────┬──────────┘
                    │ verified results
         ┌──────────▼──────────┐
         │  Confidence Rating  │
         │  + Blind-Spot Dec.  │  ← honest "I don't know"
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  Synthesized Answer │
         │  + Source Citations │  ← every claim links to doc
         └─────────────────────┘
```

## Layer 3 — Experience Lifecycle (E0-E12)

```
E0:  Document Ingestion Hook → signals "potential experience"
E1:  Heuristic Extraction     → parse docs for problem→solution patterns
E2:  Quality Gate             → LLM-refine, validate structure
E3:  Draft Pool               → pending review (list/read/approve/reject)
E4:  Experience-First Retrieval → P0/P1/P2 credibility tiers
E5:  User Feedback Loop       → rating, comment, apply
E6:  Stale Detection          → check if linked docs still exist
E7:  Re-index on Update       → sync when doc content changes
E8:  Dashboard & Analytics    → KB-level summary, top experiences
E9:  Search & Rerank          → semantic + keyword + multi-path
E10: Global Cross-KB Search   → enterprise-wide experience discovery
E11: Decay Cycles             → periodic credibility degradation
E12: Auto Health Check        → cleanup stale/orphan experiences
```

## Layer 4 — Data Consistency Model

```
┌──────────┐  L1: Raw files on disk
│  *.md    │  storage/tree-file-system/{KB}/{doc}.md
└──────────┘
     │
     ▼
┌──────────┐  L2: Global file tree index
│.tree-fs  │  .tree-fs.json (all folders + files + metadata)
│  .json   │
└──────────┘
     │
     ▼
┌──────────┐  L3: Per-KB document registry
│.knowledge│  .knowledge-base.yml (name/path/tags/vector_index)
│ -base.yml│
└──────────┘
     │
     ▼
┌──────────┐  L4: Vector embeddings
│ ChromaDB │  BGE-M3 1024-dim chunks
└──────────┘
     │
     ▼
┌──────────┐  L5: Knowledge graph
│  Neo4j   │  Document/Tag/KB nodes + RELATED_TO edges
└──────────┘
```

**Write Consistency Rule**: All 5 layers are updated in a single request.
**Read Consistency Rule**: Direct file reads for L1-L3, APIs for L4-L5.
**Delete Consistency**: `kb_doc_delete` now cleans L1-L5 atomically.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Writes via HTTP API | Guarantees 5-layer consistency |
| Reads via direct file I/O | Zero backend load, faster |
| MinerU as subprocess | Isolated lifecycle, crash-safe |
| ChromaDB for vectors | Lightweight, embedded, no separate server |
| Neo4j for graph | Rich relationship queries, path discovery |
| QDCVR over pure vector | Content verification prevents hallucination |
| MCP-first architecture | Any agent can interface with the system |
