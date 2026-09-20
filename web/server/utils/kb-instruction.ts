/**
 * KB retrieval-augmented answer instruction — the platform's NATIVE retrieval
 * pipeline prompt (QDCVR v2: query rewrite → KB selection → vector+two-stage →
 * dedup+threshold → content verification → synthesized answer, librarian deep
 * retrieval fallback, honest not-found).
 *
 * Shared by the chat SSE route (kbEnhanced toggle) and the one-shot native
 * search API (POST /api/kb/native-search) so both run the identical flow.
 */

export function buildKbInstruction(kbIds: string[]): string {  if (kbIds.length > 0) {
    const kbIdList = kbIds.map((id) => '`' + id + '`').join(', ')
    const kbCount = kbIds.length

    return [
      '',
      '## [System: Knowledge Base Retrieval-Augmented Answer Mode]',
      '',
      'You are answering the user\'s question. You MUST use the knowledge base retrieval system to enhance your answer quality.',
      'Follow these steps strictly:',
      '',
      '### Step 1: Analyze the Question',
      'Carefully read the user\'s question. Extract key entities, attributes, and constraints.',
      '',
      `### Step 2: Search Knowledge Bases`,
      `Invoke \`/knowledgebase-search\` skill to search the following ${kbCount} knowledge base(s): ${kbIdList}.`,
      '  - Follow the knowledgebase-search skill QDCVR pipeline strictly (Step 0 Query Rewrite -> Step 1 KB Selection -> Step 2 Vector + Two-Stage Retrieval -> Step 2.5 Dedup + Threshold -> Step 3 Content Verification -> Step 6 Synthesized Answer)',
      '  - Only use results with content verification score >= 4 for your answer',
      '  - Focus on the specified KBs, do not drift to unrelated topics',
      '',
      '### Step 3: Synthesize Answer',
      'Based on the reliably retrieved knowledge, synthesize a clear, structured answer.',
      '  - Cite specific document names and sources',
      '  - Annotate information credibility (P0 strong / P1 reference / P2 weak)',
      '  - If no relevant information is found, state this honestly',
      '',
      '### Critical Reminders:',
      '- **Retrieve first, then answer** -- never guess from memory',
      '- **Stay focused** on the specified knowledge bases',
      '- Use Step 0 query rewriting for vague queries to optimize retrieval',
      '- Never fabricate answers -- say "not found in KB" if needed',
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
    'You are answering the user\'s question. You MUST use the knowledge base retrieval system to enhance your answer quality.',
    'Follow these steps strictly:',
    '',
    '### Step 1: Analyze the Question',
    'Carefully read the user\'s question. Extract key entities, attributes, and constraints.',
    '',
    '### Step 2: Full Library Search',
    'Invoke `/knowledgebase-search` skill to search ALL available knowledge bases.',
    '  - Follow the knowledgebase-search skill QDCVR pipeline strictly (Step 0 Query Rewrite -> Step 1 KB Selection -> Step 2 Vector + Two-Stage Retrieval -> Step 2.5 Dedup + Threshold -> Step 3 Content Verification -> Step 6 Synthesized Answer)',
    '  - If results concentrate in <2 KBs, auto-upgrade to enterprise multi-strategy search',
    '  - Only use results with content verification score >= 4 for your answer',
    '',
    '### Step 3: Synthesize Answer',
    'Based on the reliably retrieved knowledge, synthesize a clear, structured answer.',
    '  - Cite specific document names and source KBs',
    '  - Annotate information credibility (P0 strong / P1 reference / P2 weak)',
    '  - If no relevant information is found in ANY KB, state this honestly',
    '',
    '### Critical Reminders:',
    '- **Retrieve first, then answer** -- never guess from memory',
    '- **Search across ALL KBs** comprehensively -- don\'t miss any relevant source',
    '- Use Step 0 query rewriting for vague queries to optimize retrieval',
    '- Never fabricate answers -- say "not found in KB" if needed',
    '',
    '---',
    '',
    'Here is the user\'s question:',
    '',
  ].join('\n')
}

/**
 * One-shot native retrieval prompt: shared instruction + the caller's
 * question + an answer-shape budget. Used by POST /api/kb/native-search so
 * external systems (AgentWorkShop rag-bridge) run the identical native flow
 * as the chat UI without orchestrating any retrieval steps themselves.
 */
export function buildNativeSearchPrompt(kbIds: string[], question: string, topK: number): string {
  const budget = `[Retrieval budget: return at most ${topK} cited sources; keep the answer concise and structured.]`
  return [buildKbInstruction(kbIds), question, budget].join('')
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
    '    two-stage retrieval → dedup + threshold → content verification ≥4 →',
    '    synthesized answer; librarian deep-retrieval fallback).',
    '  - Document ingestion → write the document into the requested KB with your',
    '    kb-mcp tools, then index it (vector + graph) and report the doc_path and',
    '    chunk count. Use the KB the prompt names, else ask it to state one — if the',
    '    prompt already names a KB, do not ask.',
    '  - Experience capture → store a structured experience in the named KB.',
    '  - Anything else KB-related → use your kb-mcp tools as appropriate.',
    '',
    'Universal rules:',
    '  - Retrieve before you answer; never fabricate. If the KB lacks the evidence,',
    '    say so honestly (state what was searched).',
    '  - Cite concrete doc_paths for retrieval results; annotate credibility',
    '    (P0 strong / P1 reference / P2 weak).',
    '  - Reply in the language of the user\'s prompt.',
    '  - End with a compact "## Result" section: what you did + the final answer/',
    '    artifact (doc_path / experience id) so an external system can parse it.',
    '',
    '---',
    '',
    'The external system\'s task prompt follows:',
    '',
  ].join('\n')
}
