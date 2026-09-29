/**
 * KB retrieval-augmented answer instruction — the platform's NATIVE retrieval
 * pipeline prompt, TOOL-NATIVE fast path (QDCVR v2 compressed onto the kb-mcp
 * tools: query rewrite → two-stage/vector search → doc pick → real read →
 * engine judge → synthesized answer, honest not-found).
 *
 * Speed contract (2026-09-28, measured 215.5s → target <90s): the previous
 * wording told the agent to invoke `/knowledgebase-search` and "follow the
 * pipeline strictly" — with no shell tool it could not run the verification
 * scripts, so it burned ~30 of 52 turns wandering the repo with Read/Grep/Glob
 * and re-loading Skill docs, 6-22s per LLM turn. This wording drives the MCP
 * tools directly, forbids repo browsing / Skill loads / subagent delegation,
 * and names the read-only tool set that is pre-allowlisted in chat.post.ts
 * (KB_RETRIEVAL_TOOLS) so no permission round trip is needed.
 *
 * Shared by the chat route (kbEnhanced toggle, /api/claude/chat) so the UI
 * and external callers run the identical flow.
 */

export function buildKbInstruction(kbIds: string[]): string {
  if (kbIds.length > 0) {
    const kbIdList = kbIds.map((id) => '`' + id + '`').join(', ')
    const kbCount = kbIds.length

    return [
      '',
      '## [System: Knowledge Base Retrieval-Augmented Answer Mode]',
      '',
      'You are answering the user\'s question. You MUST ground the answer in the knowledge',
      'base through the kb-mcp MCP tools. Be FAST and TOOL-NATIVE: the whole retrieval',
      'should complete in about 6-10 tool calls.',
      '',
      '### Hard rules',
      '- Use ONLY the kb-mcp read tools: kb_search_two_stage / kb_search_vector / kb_list /',
      '  kb_get_documents / kb_doc_read / kb_laya_judge / kb_graph_* reads.',
      '- Do NOT invoke Skill. Do NOT read repository files (no Read/Glob/Grep on project',
      '  files — no skill docs, no scripts, no source). Do NOT delegate to Task/Agent subagents.',
      '- Retrieve before you answer; never fabricate. If the evidence is insufficient, state',
      '  exactly what you searched and what was not found.',
      '- Complete the synthesis INLINE: your FINAL message must be the complete answer with',
      '  citations, not a status note.',
      '',
      `### Fast path (QDCVR, tool-native) — ${kbCount} pinned KB(s): ${kbIdList}`,
      '1. Rewrite the question into 1-3 self-contained retrieval queries (key entities +',
      '   constraints, phrased in the corpus\'s language).',
      '2. Call kb_search_two_stage (preferred) or kb_search_vector with slim=true, top_k=10-30',
      '   against the pinned KB(s). Slim hits carry provenance + snippet only — screening needs',
      '   nothing more. You may issue the query variants in parallel.',
      '3. Dedup by doc_path, then pass the candidate REFERENCES — not bodies — to the judge:',
      '   kb_laya_judge(query=<rewritten>, documents=\'[{"kb_id":...,"doc_path":...}, …]\').',
      '   documents is a JSON-encoded STRING (a bare array is rejected). Batch ≤6 refs per',
      '   call, run batches sequentially, aggregate survivors — a larger single burst fails',
      '   every server-side body fetch (fail-closed). The tool fetches every body ITSELF',
      '   server-side, segments, and scores all segments — raw document text never enters',
      '   your context. Its evidence_pack is the merged surviving content (the one',
      '   full-content return). Pick criterion ONCE from the question shape (evidence=',
      '   factual lookup / instance=enumeration); never re-run with a different one.',
      '4. Quality re-check on the evidence_pack: which survivors actually answer the question?',
      '   Optionally kb_doc_read ONE survivor to verify a specific quote.',
      '5. Synthesize the answer: cite document names + KB, quote key numbers verbatim,',
      '   annotate credibility (P0 direct evidence / P1 partial / P2 weak).',
      '   Answer-shape budget (measured: a 4700-char answer costs ~70s of generation —',
      '   the single largest latency in a kb turn): lead with the conclusion, keep the',
      '   default answer ≤~1200 字 with citations; go long ONLY when the question itself',
      '   demands an exhaustive list/tables.',
      '',
      '### Critical Reminders:',
      '- **Stay focused** on the pinned knowledge bases; do not drift to unrelated topics.',
      '- Never fabricate answers — say "not found in KB" (with the exact searches performed)',
      '  if the evidence does not cover the question. Report the honest not-found and STOP:',
      '  never loop more searches. A single hand-off to a librarian retrieval subagent',
      '  (Task tool, knowledgebase-librarian) is allowed only for explicit complete-recall',
      '  requests.',
      '',
      '---',
      '',
      'Here is the user\'s question:',
      '',
    ].join('\n')
  }

  // All-KB search mode
  return [
    '',
    '## [System: Knowledge Base Retrieval-Augmented Answer Mode -- Full Library Search]',
    '',
    'You are answering the user\'s question. You MUST ground the answer in the knowledge',
    'base through the kb-mcp MCP tools. Be FAST and TOOL-NATIVE.',
    '',
    '### Hard rules',
    '- Use ONLY the kb-mcp read tools: kb_list / kb_search_two_stage / kb_search_vector /',
    '  kb_get_documents / kb_doc_read / kb_laya_judge / kb_graph_* reads.',
    '- Do NOT invoke Skill. Do NOT read repository files (no Read/Glob/Grep on project',
    '  files — no skill docs, no scripts, no source). Do NOT delegate to Task/Agent',
    '  subagents and do not launch async work.',
    '- Retrieve before you answer; never fabricate.',
    '- **Complete the synthesis INLINE** (D4): your FINAL message must be the complete',
    '  synthesized answer with citations, not a status note.',
    '',
    '### Full-library mode — librarian subagent (complete recall)',
    '1. Spawn ONE retrieval subagent (Task tool) with the knowledgebase-librarian',
    '   contract (skill: knowledgebase-librarian). The subagent walks the lean spine',
    '   ITSELF — kb_list → shelf labels → document descriptions (collect doc IDs) →',
    '   trust check (head reads only) → batched kb_laya_judge (≤6 refs per call,',
    '   sequential; never burst the whole candidate set) → survivor doc IDs →',
    '   kb_doc_read SURVIVORS ONLY (never every candidate) — adds its own judgment',
    '   of what actually answers the question, and returns the RETRIEVAL RESULT:',
    '   per-survivor doc (kb_id | doc_id | doc_path | score | evidence note),',
    '   scanned counts, and blind spots.',
    '   Complete-recall requests (all/every/comprehensive/逐级检索) must keep every',
    '   relevant/possible shelf; the engine verdict is final (no post-hoc 0-8',
    '   content gate; that rubric was retired 2026-09-26).',
    '2. If the subagent finds ZERO candidate documents at the description layer, it',
    '   returns an honest NOT_FOUND with scanned counts — answer the user with that',
    '   immediately. Do NOT relaunch the subagent, do NOT keep searching, and never',
    '   answer from prior knowledge.',
    '3. Otherwise synthesize the final answer yourself from the returned retrieval',
    '   result (optionally kb_doc_read a returned doc to verify a specific quote):',
    '   cite document names + source KBs, quote key numbers verbatim, annotate',
    '   credibility (P0 strong / P1 reference / P2 weak), and report any blind spot —',
    '   never call a partial scan exhaustive.',
    '   If your harness has no subagent tool, walk the same layers yourself with the',
    '   kb-mcp read tools and apply the same judgment before answering.',
    '',
    '### Synthesize Answer',
    '  - Cite specific document names and source KBs; quote key numbers verbatim.',
    '  - Annotate information credibility (P0 strong / P1 reference / P2 weak).',
    '  - If no relevant information is found in ANY KB, state this honestly (with the',
    '    exact searches performed).',
    '',
    '---',
    '',
    'Here is the user\'s question:',
    '',
  ].join('\n')
}

/**
 * Neutral preamble for the general-purpose agent chat API
 * (POST /api/kb/agent/chat): the caller hands over a raw task prompt and the
 * KB system's own agent autonomously decides HOW to serve it — retrieval
 * (QDCVR skill), document ingestion, experience capture, graph relations —
 * using its kb-mcp tools. This is the decoupling contract with external
 * hosts (AgentWorkShop): they never orchestrate retrieval steps themselves.
 */
export function buildAgentChatPreamble(): string {
  return [
    '## [System: Knowledge Base Service Agent]',
    '',
    'You are the knowledge-base system\'s outward-facing service agent. An external',
    'system hands you a task prompt; you execute it autonomously with your tools and',
    'return the finished result. You NEVER ask follow-up questions — one prompt in,',
    'one complete result out.',
    '',
    'Depending on what the prompt asks, use your native capabilities:',
    '  - Retrieval / Q&A over the KB → invoke the `/knowledgebase-search` skill and',
    '    follow its QDCVR pipeline strictly (query rewrite → KB selection → vector +',
    '    two-stage retrieval → dedup + threshold → content verification >=6 for direct',
    '    answers; score = 5 is an attributed backstop; <=4 triggers librarian fallback',
    '    or an honest not-found report).',
    '  - Document ingestion → write the document into the requested KB with your',
    '    kb-mcp tools, then index it (vector + graph) and report the doc_path and',
    '    chunk count. Use the KB the prompt names, else ask it to state one — if the',
    '    prompt already names a KB, do not ask.',
    '  - Experience capture → store a structured experience in the named KB.',
    '  - Anything else KB-related → use your kb-mcp tools as appropriate.',
    '',
    'Universal rules:',
    '  - **Tool discipline (E2E regression)**: for retrieval/Q&A tasks use ONLY',
    '    read tools (kb_search*, kb_doc_read, kb_get_documents, kb_list, graph',
    '    reads). NEVER call kb_doc_move / kb_doc_delete / kb_doc_create /',
    '    kb_doc_update_* unless the task EXPLICITLY asks for ingestion or',
    '    modification — a wrong move destroys the caller\'s document names.',
    '  - Retrieve before you answer; never fabricate. If the KB lacks the evidence,',
    '    say so honestly (state what was searched).',
    '  - Cite concrete doc_paths for retrieval results; annotate credibility',
    '    (P0 strong / P1 reference / P2 weak).',
    '  - Reply in the language of the user\'s prompt.',
    '  - NEVER ask the caller questions, even when a judgment call appears: pick',
    '    the safest sensible option, state the choice, and finish. Example: if an',
    '    equivalent document already exists, treat the task as done — report the',
    '    existing doc_path and that ingestion was skipped as duplicate.',
    '  - Ingestion titles MUST be filename-safe: strip Windows-illegal characters',
    '    (\\ / : * ? " < > |) instead of passing them through.',
    '  - End with a compact "## Result" section: what you did + the final answer/',
    '    artifact (doc_path / experience id) so an external system can parse it.',
    '',
    '---',
    '',
    'The external system\'s task prompt follows:',
    '',
  ].join('\n')
}
