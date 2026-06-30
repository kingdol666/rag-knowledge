# Agentic Knowledge Base Management System


## Architecture and Development Guide

> Version 1.0 | 2026-06-29


## 1. Overview

This document defines the complete architecture, implementation roadmap, Agent design, MCP tool extensions, and development standards for evolving the RAG Knowledge Platform into a fully Agentic-driven knowledge base management system.


## 2. Current State

All 40 MCP tools are implemented and verified. Services run as:

- Backend (FastAPI) on port from config.yml
- Web (Nuxt 3) on port from config.yml
- MinerU OCR engine managed by backend
- kb-mcp server connected to Claude Code via stdio


## 3. Target Architecture

The target system has two distinct Agent roles:

### KB Admin Agent
- Creates and manages knowledge bases
- Uploads and parses documents into appropriate KBs
- Maintains folder structures and metadata
- Auto-summarizes and tags documents

### KB Retrieval Agent 
- Context-aware document retrieval
- Three-stage relevance judgment (title -> description -> content)
- Returns only truly relevant documents with judgment reasons
- Structured content extraction for Agent consumption


## 4. Implementation Phases


### Phase 2: Intelligent Enhancement (2-3 weeks)

New MCP tools:
- kb_doc_summarize: LLM-powered document summarization
- kb_doc_tag: Document tagging system
- kb_doc_classify: Automatic document classification
- kb_stats / kb_insights: Knowledge base analytics
- kb_doc_version_list / kb_doc_rollback: Version management

Schema changes:
- Extend .knowledge-base.yml with summary, tags, category fields
- Add kb_stats endpoint for per-KB analytics

### Phase 3: Agentic Core (4-6 weeks)

New MCP tools (killer features):
- kb_agentic_retrieve: Agent autonomously judges document relevance
- kb_search_hybrid: Keyword + vector hybrid search
- kb_merge: Merge two knowledge bases
- kb_graph: Document relationship graph
- kb_deduplicate: Intelligent deduplication

Infrastructure:
- ChromaDB integration for vector indexing
- LLM-based relevance judgment engine
- Hybrid search merging (keyword + vector)

### Phase 4: Skills and Multi-Modal (8-12 weeks)

- KB Admin Agent Skill (complete workflow automation)
- KB Retrieval Agent Skill (context-aware search)
- Multi-modal document support (PPT, video, audio)
- Knowledge base subscription/notification (Webhook)
- Cross-KB analytics (trends, hotspots, correlations)


## 5. Agent Decision Logic


### KB Admin Agent Decision Flow

1. Read document content (first 2000 chars)
2. Call kb_list to get all existing KBs
3. Compare document topic with each KB description
4. Decision:
   - High match: parse directly into existing KB
   - Medium match: confirm with user, then parse
   - No match: create new KB (name from document title)
   - Sub-topic: create nested KB with parent_id
5. After parsing, call kb_doc_summarize + kb_doc_tag

### KB Retrieval Agent Decision Flow

1. Extract 3-5 core concepts from task context
2. Scan KB landscape (kb_list + fs_get_tree)
3. For each relevant KB, get document list
4. For each candidate document, THREE-STAGE judgment:
   a) Title relevance - does name contain task keywords?
   b) Description match - does description hint at useful content?
   c) Content verification - read first 2000 chars, judge relevance
5. Score: pass 3/3 = high (0.85+), 2/3 = medium (0.5-0.85), 1/3 or 0/3 = skip
6. Return structured results with judgment reasons


## 6. MCP Tools Implementation Guide


### kb_doc_summarize

Flow:
1. kb_doc_read(doc_path, max_chars=8000) - get content
2. Call LLM API (DeepAgent or direct) with summarize prompt
3. kb_doc_update_meta(kb_id, doc_path, summary=result)
4. Update .knowledge-base.yml with summary field

### kb_agentic_retrieve (Core Killer Tool)

Flow:
1. Extract keywords from task_context (via LLM or keyword extraction)
2. kb_list() + fs_get_tree() - get KB structure
3. For each KB, kb_get_documents(kb_id) - get doc list
4. Initial filter: name or description contains any keyword
5. For each candidate (max 15):
   - kb_doc_read(path, max_chars=2000)
   - LLM judge: task_context vs document content
   - Return {score, reason} for each document
6. Sort by score, return top_k with reasons


## 7. .knowledge-base.yml Schema Extension


Current schema:
`yaml
knowledge_base:
  id: test
  name: test
  description: test
documents:
  - name: doc.md
    description: Parsed from doc.pdf
    path: test/doc.md
    file_type: md
    file_size: 12345
    metadata:
      sourcePdf: doc.pdf
      imageCount: 5
      parsedAt: ...
`

Extended schema (Phase 2):
`yaml
documents:
  - name: doc.md
    description: Parsed from doc.pdf
    path: test/doc.md
    file_type: md
    file_size: 12345
    summary: LLM-generated Chinese summary (Phase 2)
    tags: [tag1, tag2] (Phase 2)
    category: category-name (Phase 2)
    metadata:
      sourcePdf: doc.pdf
      imageCount: 5
      parsedAt: ...
      version_id: v1 (Phase 2)
      vector_indexed: true (Phase 3)
`


## 8. Testing Standards


### Test Pyramid
- Lint / Type check: TypeScript check + Python mypy
- Unit tests (40+): Each MCP tool independently tested
- Integration tests (20+): MCP -> Web API -> Backend
- E2E tests (5-10): Full Agent workflow

### Per-Phase Test Checklist

Phase 2:
- kb_doc_summarize: summary not empty, max length honored
- kb_doc_tag: dedup works, merge correct
- kb_stats: count matches actual documents

Phase 3:
- kb_search_hybrid: hybrid > keyword-only accuracy
- kb_agentic_retrieve: known documents returned, irrelevant ones skipped
- Vector indexing: chunk count matches content length


## 9. Development Checklist Per Phase


### Phase 2 Deliverables
- [ ] kb_doc_summarize MCP tool + Web API + Backend LLM call
- [ ] kb_doc_tag MCP tool + Web API
- [ ] kb_stats / kb_insights MCP tools + Web API
- [ ] kb_doc_version_list / kb_doc_rollback tools
- [ ] .knowledge-base.yml schema extended
- [ ] Frontend: summary display, tag filter, stats panel
- [ ] Tests pass for all new tools
- [ ] MCP tool descriptions include Chinese parameter docs

### Phase 3 Deliverables
- [ ] ChromaDB integration (backend vector_service.py)
- [ ] kb_search_hybrid (keyword + vector merge)
- [ ] kb_agentic_retrieve (LLM relevance judgment)
- [ ] kb_merge / kb_deduplicate
- [ ] kb_graph (document relationship)
- [ ] Vector re-index on document update
- [ ] config.yml vector_db section added
- [ ] All tools tested via MCP

### Phase 4 Deliverables
- [ ] KB Admin Skill (.codex-plugin/skills/kb-admin/)
- [ ] KB Retrieval Skill (.codex-plugin/skills/kb-retriever/)
- [ ] Multi-modal parse support (PPT, video)
- [ ] Webhook notification system
- [ ] Cross-KB analytics dashboard


## 10. Quality Gates


Before committing any Phase:
- [ ] Zero hardcoded paths (all use __file__ / import.meta.url)
- [ ] All ports from config.yml
- [ ] .env.example updated for new env vars
- [ ] MCP tool docstrings include parameter descriptions
- [ ] git diff --stat shows only intended files
- [ ] Full MCP integration test passes


## 11. Vector DB Integration (Phase 3)

### ChromaDB Setup

```python
# backend/app/services/vector_service.py
import chromadb
from chromadb.utils import embedding_functions

class VectorService:
    def __init__(self, persist_dir = './chroma_db'):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        self.collections = {}

    def index_document(self, kb_id, doc_path, content, metadata):
        collection = self.get_collection(kb_id)
        chunks = [content[i:i+500] for i in range(0, len(content), 500)]
        ids = [doc_path + '_chunk_' + str(i) for i in range(len(chunks))]
        collection.add(documents=chunks, ids=ids, metadatas=metadata)

    def search(self, kb_id, query, top_k=5):
        return self.get_collection(kb_id).query(query_texts=[query], n_results=top_k)
```

### Auto-Index on Parse

When parse_pdf_to_kb succeeds, trigger index_document:

```python
async def after_parse(kb_id, doc_path, markdown_content):
    await vector_service.index_document(
        kb_id=kb_id, doc_path=doc_path,
        content=markdown_content,
        metadata={'parsed_at': datetime.now().isoformat()})
```


## 12. Files Affected Per Phase


### Phase 2 Files
- kb-mcp/server.py - add kb_doc_summarize, kb_doc_tag, kb_stats tools
- kb-mcp/kb_client/client.py - add summarize, tag, stats HTTP methods
- web/server/kb-search-service.ts - extend KnowledgeBaseDocument type
- web/server/knowledge-base-yaml-service.ts - handle new fields
- web/server/api/kb/documents/summarize.post.ts - new endpoint
- web/server/api/kb/stats.get.ts - new endpoint
- backend/app/services/llm_service.py - LLM client for summarization

### Phase 3 Files
- backend/app/services/vector_service.py - ChromaDB integration
- kb-mcp/server.py - add kb_agentic_retrieve, kb_search_hybrid
- kb-mcp/kb_client/client.py - add vector search methods
- web/server/services/agentic-service.ts - relevance judgment engine
- web/server/api/kb/agentic-retrieve.post.ts - new endpoint
- config.yml - add vector_db and agentic sections

### Phase 4 Files
- kb-mcp/skills/kb-admin-skill.md - KB Admin Agent skill
- kb-mcp/skills/kb-retriever-skill.md - KB Retrieval Agent skill
- web/server/api/parse/* - extend format support


## Appendix: Quality Rules


**CRITICAL - these must never be violated:**

1. **Zero hardcoded paths** - all paths from __file__ or import.meta.url
2. **config.yml is the single source of truth** - ports, URLs, feature flags
3. **MCP tools have descriptions** - every tool must document parameters
4. **Error responses** - always return {success: False, error: reason}
5. **No print()** - use logging.info / console.log
6. **Test before commit** - run MCP integration test
7. **Cross-platform** - path.join, not string slash concatenation
8. **Backward compatible** - new fields are optional
