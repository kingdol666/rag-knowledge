# System source audit for the CIKM Demo revision

Date: 2026-09-19. Scope: current local implementation versus `sec2_system.tex` and `sec3_demo.tex`. This is a read-only implementation audit, not an independent benchmark reproduction or an acceptance test. Only this report was written.

## 1. Executive verdict / submission blockers

1. **The shared-protocol architecture is overstated.** Web retrieval does not pass through MCP. MCP exposes primitives; the vector-first rewrite → rubric gate → librarian fallback → five-section answer procedure is principally an agent-executed skill, not a compulsory FastAPI/MCP state machine. Show a separate orchestration layer in the architecture figure.
2. **The live upload story is not implemented as described.** The file-system upload flow takes a selected parent; parsing/saving is a separate path; no universal content-classifier, automatic category recommendation, or all-part tag propagation is established for that UI. Present agent-assisted ingestion, not an automatic rule-free upload wizard.
3. **Demo numbers mix executions.** The current answer artifact gives NISQ 8/8, not the paper's 7/8; the tumor answer currently has a 7/8 fast-exit label while its prose mentions supplementary Phase 2. Freeze a coherent run and its UI evidence before presenting precise gate trajectories.
4. **Auditability is narrower than claimed.** Mutable JSON/YAML metadata is not an append-only per-query audit log. Benchmark artifacts persist evidence and agent judgments, but the ordinary retrieval endpoints do not require a query trace, a gate judgment, or a final failure artifact. Most classification assignments have no individual rationale.
5. **A correctness bug undermines the universal all-part story.** The create endpoint can return multiple documents, but the MCP wrapper tags and schedules indexing only for `result.document` (the first part). Benchmark tagging was applied separately across parts. Also, `graph_stats.tag_count=165` counts Tag nodes, not tagged documents.
6. **Deployment wording needs conditions.** `ragctl` is primarily a setup/service-management CLI, not the same retrieval protocol as MCP. Local parsing/embeddings are supported, but the approximately 20-second cold start is not substantiated by the inspected artifacts and depends on what is cold.

The strongest supportable contribution is **an agent-native knowledge-management platform with deterministic storage/search primitives and a packaged, inspectable content-verification workflow, demonstrated on a curated five-base corpus**. Do not equate instructed behavior with server-enforced guarantees.

## 2. Evidence scope and deployed checkout

Main repository HEAD: `439bf3c6e0d705fcbb5868dea00d4bb90e3edcc9`. Existing unrelated working-tree changes were present and left untouched. Sibling repository HEADs: backend `0294626`, frontend `c59ca56`.

Read-only process inspection found:
- PID 20504: `D:\codes\ClaudeGPT\rag_project\rag-knowledge\backend\.venv\Scripts\python.exe main.py`.
- PID 26384 and Nuxt workers: the monorepo's `web/node_modules/nuxt/...`, port 6789.
- No matching active sibling-backend/frontend process was found in that snapshot.

This supports auditing **monorepo backend/web as the locally running implementation**, rather than substituting the sibling copies. It does not establish that every changed source line has been reloaded by an already-running process. No service was restarted and no upload, retrieval, indexing, or destructive benchmark script was executed.

Configuration evidence: `D:/codes/ClaudeGPT/rag_project/rag-knowledge/config.yml:19-28` selects development backend 8770 and frontend 6789; `D:/codes/ClaudeGPT/rag_project/dev.ps1:13-14,124-145,161-192` instead targets the sibling projects on 8000/3000. These are different launch paths. `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/config.py:53-60,78-85,120-136` documents/implements merged private/shared configuration with environment overrides. A launcher or README alone cannot identify the live deployment.

## 3. Actual call paths and tool accounting

### 3.1 Web search is HTTP, not MCP

`knowledge-search.vue` → `useKbAdvancedSearch.ts` → Nuxt `/api/search/vector` or `/api/search/two-stage` → FastAPI `/api/v1/search/vector` or `/api/v1/search/two-stage` → vector/two-stage services.

Evidence:
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/composables/useKbAdvancedSearch.ts:131-159,181-217` sends HTTP requests and maps scores/snippets.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/api/search/vector.post.ts:4-11` and `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/api/search/two-stage.post.ts:4-11` proxy bodies to FastAPI.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/api/routes/search.py:101-163` handles retrieval requests; it does not perform the skill's 0–8 adjudication, librarian traversal, or five-section answer composition.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/pages/knowledge-search.vue:258-282` displays snippets and combined/vector/BM25/raw scores. These are not rubric gate scores.

### 3.2 MCP splits between Nuxt CRUD and direct FastAPI search

Agent → `kb-mcp/server.py` → `KbClient`:
- Catalog/document CRUD/read/tag operations use Nuxt APIs backed by tree/KB services.
- Vector/two-stage search calls FastAPI directly, not necessarily through Nuxt.

Evidence: `D:/codes/ClaudeGPT/rag_project/rag-knowledge/kb-mcp/kb_client/client.py:97-108,212-297,480-484,534-574`; `D:/codes/ClaudeGPT/rag_project/rag-knowledge/kb-mcp/server.py:370-380,2005-2073`. The MCP server is a tool adapter, not itself the QDCVR execution controller.

### 3.3 Web agent chat is a distinct, conditional surface

The console also has agent chat. `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/api/claude/chat.post.ts:161-231,323-359,470-487` builds KB instructions when KB-enhancement is enabled and calls a configured harness. Full-library mode explicitly requests `/knowledgebase-search`; its inline step description still describes an older vector-plus-two-stage sequence. More seriously, both the selected-KB prompt at lines 178-179 and the full-library prompt at lines 214-216 permit answers from content-verification scores >=4, whereas the packaged skill discards scores <=4 and fast-exits at >=6. This conflicting instruction further prevents claiming that web chat reliably executes one identical protocol. `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/engines/claude-engine.ts:27-61` uses the agent SDK with user/project settings. Project MCP configuration is in `D:/codes/ClaudeGPT/rag_project/rag-knowledge/.mcp.json:1-14`.

Thus the console can host an agent running the skill, but **ordinary search, optional enhanced chat, and arbitrary MCP clients are not behaviorally equivalent**. Test the selected harness and demonstrate the skill explicitly. Do not promise “any MCP-capable harness” will discover and obey project skills automatically.

### 3.4 CLI and count

AST inspection of top-level `@mcp.tool()` definitions in `D:/codes/ClaudeGPT/rag_project/rag-knowledge/kb-mcp/server.py` finds **94 tools, of which 41 names start with `kb_`**. The count in §2 is correct for this source snapshot. It is not a count of 41 complete workflows, nor an observed live MCP registration response.

Important non-`kb_` operations include `fs_upload_file` (569), `parse_doc` (590), `parse_doc_batch` (630), `parse_task_status` (665), and experience tools (1233-1894). Saying that all scenarios use “the same 41 tools” excludes tools needed for parsing and lifecycle operations.

`D:/codes/ClaudeGPT/rag_project/rag-knowledge/command/ragctl.js:4154-4184` dispatches setup, dependencies/models, lifecycle/service management, backups, meditation, SOUL, and harness operations; there is no general `search` or `ingest` command here. Its specialized SOUL/meditation commands also use HTTP APIs, not a compulsory MCP retrieval workflow.

**Safe wording:** “The web console and MCP clients share storage and retrieval services. The MCP adapter exposes 94 tools, including 41 `kb_*` tools. A packaged agent skill composes these primitives into the demonstrated verification workflow; `ragctl` manages installation and services.”

## 4. Ingestion: separate agent judgment from deterministic execution

### 4.1 Classification and five bases

`D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts/61_ingest_phase2_classify.py:22-30,48-64,69-95` loads `classification.json`, creates the declared bases, and applies supplied assignments/tags. It does **not** run a standalone document classifier. `D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/data/papers/classification.json:2-9` defines five benchmark categories and identifies the executing agent as classifier.

The product skill supports existing sub-bases, parent bases, or new bases, not a fixed five-class taxonomy: `D:/codes/ClaudeGPT/rag_project/rag-knowledge/.claude/skills/knowledgebase-ingest/SKILL.md:204-222`. That decision tree is explicitly a routing policy. The skill's content-analysis, tag-quality, description, and attribution requirements are instructions for the executor; they are not universally applied by CRUD endpoints.

Only **3 of 50** classification entries have a `note` field (lines 258, 331, 356); assignment fields otherwise contain base and tags. The top-level `classified_by` statement is not 50 individual rationales. The ingest report's routed rows contain slug, field, arxiv_id, KB, tags, chars, tag_ok, verify_ok—not a per-document reasoning trace.

**Safe wording:** “For the demonstration corpus, an executing agent read parsed excerpts and recorded assignments to five category bases. Deterministic scripts applied those assignments. Three filename/content discrepancies have explicit notes; the other assignments were not independently adjudicated.” Avoid “every rationale is inspectable” and “bases are induced, not declared” without a recorded induction procedure.

### 4.2 Splitting is real, but path-dependent

- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/api/kb/documents/create.post.ts:48-92`: content over the configured ceiling is submitted for splitting unless disabled; parts are stored separately. Failure falls back to a single document.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/api/parse/save-parsed-files.post.ts:147-208`: parsed-file splitting requires explicit `split: true` and enabled configuration; failure also falls back.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/composables/usePDFParser.ts:76-99`: the UI's parsed-save helper supplies a required parent ID and `split: true`.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/utils/large-doc-split.ts:55-70`: calls FastAPI `/api/v1/documents/split`.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/services/document_splitter.py:84-155,175-219`: deterministic heading/paragraph/window splitting and synthesized context headers; no LLM classifier.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/config.yml:94-99`: 30,000-character part target and 400-character overlap. Separate vector chunks are 500 characters with 50-character overlap at lines 34-43. Do not conflate document parts and vector chunks.

The ingest skill additionally mandates its scripted A2.5 split gate and per-part storage (`D:/codes/ClaudeGPT/rag_project/rag-knowledge/.claude/skills/knowledgebase-ingest/SKILL.md:232-249,360-374`). This is another execution path, not proof that every upload follows the skill. The search skill still mentions 10k/12k historical part sizes at lines 152-153, inconsistent with current 30k configuration.

### 4.3 All-part tags/indexing are not universal

`D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/api/kb/documents/create.post.ts:64-79` returns `documents` plus `document: documents[0]`. But `D:/codes/ClaudeGPT/rag_project/rag-knowledge/kb-mcp/server.py:395-416` reads only `result.document`, tags that path, and schedules indexing for it. It does not iterate `documents`. The parsed-save API explicitly does not index (`D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/api/parse/save-parsed-files.post.ts:86-87`), and the MCP parsed-save documentation requests subsequent indexing/tagging (`D:/codes/ClaudeGPT/rag_project/rag-knowledge/kb-mcp/server.py:763-767`).

The benchmark has a separate all-part tag application loop: `D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts/62_apply_tags.py:31-64`.

Read-only inspection of the current five `.knowledge-base.yml` files under `D:/codes/ClaudeGPT/rag_project/rag-knowledge/storage/tree-file-system/` confirmed **72+43+32+6+12=165 document entries, all with nonempty tags**. This supports the current metadata snapshot, not a universal ingestion guarantee or an independent live-index completeness check.

Crucially, `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/services/graph_service.py:972` computes `tag_count` using `MATCH (t:Tag) RETURN count(t)`. The 165 in `D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/graph_stats.json:1` counts tag nodes. Replace the paper's tag-coverage attribution with actual per-document metadata/loop verification. The 730+130 typed-relation snapshot is distinct from the 1,671 total edges, as the paper already notes.

**Safe wording:** “The benchmark preparation applied tags to all 165 stored parts/whole documents and verified their metadata. The platform supplies deterministic splitting and tagging primitives; the ingest workflow coordinates per-part operations.”

## 5. Retrieval, verification, and trace guarantees

The strongest evidence is the packaged skill itself:
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/.claude/skills/knowledgebase-search/SKILL.md:28-39,65-75`: vector-first workflow and mandatory agent instructions.
- Same file, `125-163`: top 3–5 surviving candidates, body reads, 0–8 rubric, limited continuation reads, ≥6 fast exit, score 5 retained as a P1 backstop while fallback runs, ≤4 discarded.
- Same file, `167-179,230-272,308`: shelf traversal, structured answer/not-found instructions, five-section contract.

These are prompt-level obligations. Calling `kb_search_vector`, calling FastAPI directly, or displaying ordinary web search results does not enforce them. Even the skill verifies selected evidence windows, not every retrieved item or an entire corpus. It allows the retrieved chunk itself as admissible evidence and at most two additional continuation windows.

**Safe wording:** “In the demonstrated skill-guided workflow, the executing LLM reads selected candidate evidence and assigns an explicit relevance/evidence rubric score before composing an answer. Failed vector evidence triggers a librarian-style fallback. The underlying retrieval APIs return candidates without this adjudication.” Replace “every retrieval verified” with this scoped statement. A gate score is not proof of factual truth, exhaustive recall, or an independent judge's confidence.

A similarly named server path is not an exception: `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/services/soul_service.py:284-374` implements `soul_qdcvr_ask` as two-stage search, score≥0.35 filtering, deduplication, short-content filtering, top-k context injection, and SOUL synthesis. It does **not** implement the new 0–8 gate + shelf fallback workflow. The MCP wrapper describes the narrower implementation at `D:/codes/ClaudeGPT/rag_project/rag-knowledge/kb-mcp/server.py:2711-2737`. Do not infer protocol equivalence from “QDCVR” in its name.

### Trace and experiment boundaries

`D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts/75_skill_track_phase1.py:2-9,23-43,92-94` explicitly separates scripted evidence collection from executing-agent adjudication/composition; query rewrites are recorded in a predefined table. `D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts/76_skill_track_phase2.py:17-32,37-73` has question-specific BQ06/BQ10 fallback parameters and appends collected evidence. These are inspectable benchmark execution artifacts, not a generic runtime controller that automatically detects a gate failure for arbitrary attendees' questions.

`D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/services/knowledge-base-yaml-service.ts:64-85` loads and saves metadata; the search/read endpoints above do not require an append-only trace. No mandatory common trace schema/ID or trace sink spanning all these surfaces was found. Agent transcripts, task registries, SOUL logs, and benchmark JSON can exist without establishing that stronger claim.

**Safe wording:** “For the reported runs we retain query rewrites, retrieved evidence, and executing-agent judgments as benchmark artifacts. The metadata tree records document organization and indexing state.” Remove “every stage appends to one per-query trace” and universal replayability until a tested trace contract and exporter are identified.

## 6. Offset reads and provenance: useful but not exact source mapping

`D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/api/kb/document.get.ts:25-27,58-61` forwards read parameters. `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/server/services/kb-search-service.ts:179-207` uses **zero-based line offsets**, line limits, then a character cap; it returns content, totalLines, truncated. It does not return a source-PDF page/character anchor, exact next offset, or section identifier. A character cap can cut a line, so naive line-count advancement is not necessarily a lossless continuation cursor.

`D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/services/document_splitter.py:188-218` stores the initial heading path for grouped sections and synthesizes a source-title/part header. A group containing several headings is not a precise section address for every passage; missing Markdown headings cannot produce a meaningful section hierarchy. Synthetic headers are added after body budgeting, so the returned content need not fit a strict 30,000-character hard cap including headers.

The splitter's `start_char`/`end_char` are not robust provenance coordinates: `content.find(body)` can fall back to zero; each window of an oversized section reuses the same section start (lines 188-194), and later grouped sections retain the initial path. Do not describe these as exact original-source spans.

**Safe wording:** “Parts retain synthesized title/part labels and available Markdown heading context. Agents can read stored Markdown using line-offset pagination and cite the document, part, and visible section heading.” Avoid promising PDF-page resolution or validated ‘§4.1’ addresses without checking the actual cited document.

## 7. Lifecycle, dependencies, cold start

Experience extraction/curation exists but is not an obligatory final stage of every retrieval. `D:/codes/ClaudeGPT/rag_project/rag-knowledge/config.yml:101-104` disables `experience_auto`; `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/services/kb_meditation_config.py:21-35` defaults per-KB meditation to disabled and auto-publication to false. The ingest skill describes optional preparation followed by agent LLM refinement at `D:/codes/ClaudeGPT/rag_project/rag-knowledge/.claude/skills/knowledgebase-ingest/SKILL.md:328-331`.

**Safe wording:** “Optional experience-management and meditation workflows can distil selected material into reusable entries, with draft/review controls.” Render lifecycle as a dashed optional branch, not a compulsory online stage.

Deployment dependencies are substantive:
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/pyproject.toml:5-45`: Python 3.12, FastAPI, PyTorch, transformers, sentence-transformers, ChromaDB, Neo4j client, MinerU, etc.; platform-specific PyTorch sources follow.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/kb-mcp/pyproject.toml:6-12`: Python≥3.11, MCP/httpx/YAML.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/command/ragctl.js:1-14,649-706,4154-4168`: Node-based setup/management, dependency/model preparation, then service startup.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/services/embedding_service.py:64-114`: lazy model loading, cached local-first load with network fallback.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/config.yml:5-15`: current MinerU local mode with `start_on_boot: false`; `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/main.py:74-91` also supports remote mode and local fallback.
- `D:/codes/ClaudeGPT/rag_project/rag-knowledge/config.yml:54-70`: enabled local Neo4j deployment; graph dependency failures are handled separately in `D:/codes/ClaudeGPT/rag_project/rag-knowledge/backend/app/api/routes/search.py:32-39`.

Local embedding/parsing is supported, but “any configured LLM” should become “a supported, configured agent harness/model.” A fresh machine must obtain runtimes, packages and model weights; an existing installation can be started via `ragctl up`. No supporting 20-second cold-start measurement was found in the inspected benchmark/paper text artifacts beyond the paper assertion. Report startup versus first embedding versus first parse versus answer latency separately, with hardware/cache state, or remove the number.

## 8. Missing or unsubstantiated demo UI capabilities

### Scenario 1: upload to answerable

Evidence against a no-folder-dialog guarantee: `D:/codes/ClaudeGPT/rag_project/rag-knowledge/web/composables/useFileSystemUpload.ts:69-76,104-115` stores the selected parent's ID and passes it to upload. The parsed-save helper likewise requires a parent ID. No general upload-path content-classifier/recommendation stage was found in the traced handlers.

Not established for the standard upload console: automatic category recommendation from content; a visible classification-rationale/re-filing history; automatic tag generation and all-part propagation; a single readiness indicator confirming parsing, all-part indexing and retrieval probes. These operations may be orchestrated by an agent, but should be demonstrated through that surface and named accordingly.

**Demo-safe alternative:** upload to an explicitly selected inbox, invoke the ingestion skill in agent chat, show its proposed destination/tags and the resulting metadata. Say “no task-specific routing code written by the attendee,” not “no rules.”

### Scenarios 2–3: gate, rescue, not-found

The standard knowledge-search page provides score/snippet results, not a dedicated Phase 0–3 timeline or 0–8 dimension card. The chat surface can render agent messages and tool activity, but source inspection does not establish a structured rubric widget, a guaranteed fallback trace, a source-section deep link, or a per-query export/replay control for this protocol.

Use actual agent transcripts/saved artifacts for the gate demonstration, clearly separated from the ordinary search UI. An empty search result is not equivalent to the skill's reasoned not-found report. Shelf/catalog inspection supports “not found within the searched scope,” not a mathematical proof of corpus absence.

### Freeze the numerical demonstration

`D:/codes/ClaudeGPT/rag_project/rag-knowledge/paper_demo/tex/sec3_demo.tex:30-45` claims NISQ 7/8 and tumor 5/8→6/8. Current `D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/skill_track_answers.json:12-17,76-81` instead records NISQ 8/8 and tumor 7/8/fast-exit (with supplementary Phase 2 mentioned in prose). `D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/track_a_e2e_spot.json:2-11` is explicitly a separate four-question spot measurement and also records NISQ 8/8. The NISQ vector score approximately 0.71 is supported by `D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/skill_track_evidence.json:37-56`, but this does not validate the paper's associated gate score.

Select one dated immutable artifact bundle for the paper, figures, and demo playback; reconcile answer labels with fallback evidence. For arbitrary live queries, describe expected behavior rather than promising those exact values. Allowing attendee uploads changes the corpus and potentially ranks/graph statistics: run fixed-corpus examples first or scope them to a frozen benchmark subset, and keep attendee uploads in a separate inbox/base if “no reset” is retained.

## 9. Suggested replacement paragraph / figure contract

> The platform combines a Nuxt web console, an MCP adapter, and FastAPI services for parsing, indexing, and retrieval, backed by a file-based metadata tree, ChromaDB, and an optional Neo4j graph. Web and MCP clients share these services through different call paths. A packaged agent skill specifies query rewriting, vector-first candidate retrieval, rubric-based reading of selected evidence, and librarian-style fallback when that evidence is insufficient. The executing agent composes a cited answer or a scoped not-found report; these steps are not imposed on direct retrieval API calls. For the demonstration, an agent prepared assignments to five category bases, and deterministic ingestion scripts stored, split, tagged, and indexed the corpus. Recorded benchmark artifacts expose the evidence and agent judgments for the reported examples. The console's agent-chat surface and a configured MCP harness can be used to demonstrate this skill-guided workflow. Experience distillation is an optional extension.

Architecture figure requirements: show web HTTP and MCP adapter paths separately; put the skill/LLM controller above primitives; separate deterministic split/index/store from agent classification/tag selection; label five bases and 30k as demo configuration; replace “YAML audit log” with metadata/catalog; mark lifecycle optional; do not label raw vector results verified.

## 10. Audit verification and limits

Verification comprised a separate readback/evidence pass after source tracing: AST tool count; direct inspection of both sides of split-create/MCP handling; inspection of graph-stat Cypher semantics; JSON structure/score checks; read-only counting of tag-bearing documents in all five current metadata files; and local process-path inspection. No external documentation was needed to establish these local implementation facts. No source was modified and no service-side behavior was exercised.

No independent reviewer/subagent runtime was available in this task; this report does not claim independent approval. Remaining release evidence: choose/freeze a run bundle, demonstrate each promised scenario on the chosen UI/harness, verify all generated parts become searchable, and measure a defined cold-start condition. These are recommendations, not actions performed by this audit.


