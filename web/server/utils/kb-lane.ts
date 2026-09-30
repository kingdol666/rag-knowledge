/**
 * Shared KB retrieval-lane configuration — the ONE definition used by both
 * the chat SSE/JSON route (/api/claude/chat, kbEnhanced) and the external
 * ingestion surface (/api/kb/agent/chat, AgentWorkShop rag-bridge) runs
 * full-native WITHOUT this file's restrictions by design.
 *
 * Measured constraints (2026-09-28/29 sessions, see review/chat-api-stream-20260928):
 *  - Only `disallowedTools` gates harness-internal tools; `allowedTools` does
 *    not. Every internal tool left visible drew an opening-turn detour
 *    (ToolSearch +14-21s, Skill +23-40s, Agent/Task delegation +170s,
 *    PowerShell +34s, SendMessage +10s, TaskStop/ReadMcpResource +~10s,
 *    TaskCreate/Workflow/EndConversation turn noise).
 *  - KB turns mount MCP via the PERSISTENT HTTP instance (127.0.0.1:8000/sse)
 *    under strictMcpConfig — stdio cold start (~5s, worse under load)
 *    intermittently missed the mount window and left the model with zero kb
 *    tools (measured hallucination session f8fbe814).
 *  - Loopback must bypass ambient proxies (HTTPS_PROXY=127.0.0.1:7890 was
 *    inherited by the engine child and broke the MCP mount) — NO_PROXY is set
 *    in claude-engine env, not here.
 */

/** Only kb-mcp loads; user-scope MCP (fetch/memory/context7/…) excluded. */
export const KB_MCP_SERVERS = {
  'kb-mcp': { type: 'sse' as const, url: 'http://127.0.0.1:8000/sse' },
}

/** MCP read tools sufficient for both kb lanes (no repo tools, no Skill). */
export const KB_MCP_TOOLS = [
  'mcp__kb-mcp__kb_list',
  'mcp__kb-mcp__kb_search',
  'mcp__kb-mcp__kb_search_vector',
  'mcp__kb-mcp__kb_search_two_stage',
  'mcp__kb-mcp__kb_search_stats',
  'mcp__kb-mcp__kb_get_documents',
  'mcp__kb-mcp__kb_doc_read',
  'mcp__kb-mcp__kb_doc_get_by_tag',
  'mcp__kb-mcp__kb_tags_list',
  'mcp__kb-mcp__kb_laya_judge',
  'mcp__kb-mcp__kb_project_status',
  'mcp__kb-mcp__backend_status',
  'mcp__kb-mcp__kb_graph_search',
  'mcp__kb-mcp__kb_graph_stats',
  'mcp__kb-mcp__kb_graph_document',
  'mcp__kb-mcp__kb_graph_document_related',
  'mcp__kb-mcp__kb_graph_kb_overview',
  'mcp__kb-mcp__kb_graph_cross_kb_documents',
  'mcp__kb-mcp__kb_graph_document_paths',
  'mcp__kb-mcp__kb_graph_central_documents',
]

/** Harness-internal tools banned on every kb retrieval turn. */
export const KB_DISALLOWED_TOOLS = [
  'ToolSearch', 'Task', 'Agent', 'Skill', 'PowerShell',
  'SendMessage', 'SendMessageToAgent', 'AgentMessage',
  'TaskOutput', 'TaskUpdate', 'TaskGet', 'TaskList', 'TaskStop',
  'TaskCreate', 'Workflow', 'EndConversation',
  'ReadMcpResourceTool', 'ReadMcpResourceDirTool', 'ListMcpResourcesTool',
  'EnterWorktree', 'Bash', 'Edit', 'Write', 'NotebookEdit',
  'Read', 'Glob', 'Grep',
  'WebSearch', 'WebFetch', 'WebFetchDomain',
  'AskUserQuestion', 'EnterPlanMode', 'ExitPlanMode',
  'TodoWrite', 'TodoRead', 'CronCreate', 'CronDelete',
  'CronList', 'CronUpdate', 'DesignSync',
]

/**
 * SOUL persona read-path tools (soulEnhanced chat turns). Measured 2026-09-30:
 * without pre-allowlisting, every soul_* call hit the permission callback and
 * was auto-denied on non-stream calls ("无人工审批通道") — the persona answer
 * could never form. Write/admin soul tools (init/learn/delete/eval/…) stay
 * permission-gated on purpose.
 */
export const SOUL_READ_TOOLS = [
  'mcp__kb-mcp__soul_ask',
  'mcp__kb-mcp__soul_qdcvr_ask',
  'mcp__kb-mcp__soul_list',
  'mcp__kb-mcp__soul_router',
  'mcp__kb-mcp__soul_status',
  'mcp__kb-mcp__kb_task_status',
]
