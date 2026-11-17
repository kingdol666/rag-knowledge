/**
 * Normalize tool names emitted by the two supported MCP adapters.
 *
 * Claude's SDK keeps the server/tool separator explicit:
 *   mcp__kb-mcp__kb_list
 * OMP flattens server ids into underscore-delimited namespaces. The managed
 * plugin's directory and server are both kb-mcp, so its names look like:
 *   mcp__kb_mcp_kb_mcp_kb_list
 * Older direct-server names also remain supported:
 *   mcp__kb_mcp_kb_list
 *
 * Match the complete kb-mcp server namespace, not a loose `kb` substring, so
 * unrelated MCP servers (for example `mcp__other__kb_list`) never count as KB
 * retrieval. The returned name is canonical for telemetry and guard logic;
 * callers that dispatch tools must retain the original emitted name.
 */
export function normalizeKbMcpToolName(name: unknown): string | null {
  if (typeof name !== 'string') return null

  const claudePrefix = 'mcp__kb-mcp__'
  // OMP 18.12.2's installed source namespaces a plugin MCP server as
  // `${plugin}:${server}` before createMCPToolName sanitizes it and joins the
  // parts with one underscore. With plugin dir `kb-mcp` and server `kb-mcp`,
  // the real server namespace is `kb_mcp_kb_mcp`.
  const ompPluginPrefix = 'mcp__kb_mcp_kb_mcp_'
  const ompLegacyPrefix = 'mcp__kb_mcp_'
  if (name.startsWith(claudePrefix)) {
    return name.length > claudePrefix.length ? name : null
  }

  // Check the plugin namespace first. Its `kb_mcp_` segment is server
  // identity, not part of the real MCP tool name. A legacy tool beginning
  // `kb_mcp_` is inherently ambiguous with the plugin spelling; no current
  // kb-mcp tool has that prefix, so prefer the managed plugin namespace.
  const ompPrefix = name.startsWith(ompPluginPrefix)
    ? ompPluginPrefix
    : name.startsWith(ompLegacyPrefix)
      ? ompLegacyPrefix
      : null
  if (!ompPrefix) return null

  const toolName = name.slice(ompPrefix.length)
  // The family check is deliberately anchored after the exact server
  // namespace. It rejects names from unrelated MCP servers that merely contain
  // `kb`, while allowing the distinct kb/soul/experience tool names exposed by
  // the kb-mcp server.
  if (!/^(?:(?:kb|soul|experience|fs|parse)_[a-z0-9_]+|backend_status)$/.test(toolName)) return null
  return `${claudePrefix}${toolName}`
}

export function isKbMcpTool(name: unknown): boolean {
  return normalizeKbMcpToolName(name) !== null
}

/**
 * OMP 18.12.2 mounts MCP tools as `xd://` virtual devices: the model invokes
 * the native read/write tools with `path: "xd://mcp__kb_mcp_<tool>"` (observed
 * verbatim in rpc toolcall frames), so the frame's tool name is `read`/`write`
 * while the real MCP tool lives in the arguments. Map such calls back to the
 * canonical kb-mcp tool name for tool cards and telemetry; returns null for
 * every other call shape.
 */
export function resolveOmpXdMcpToolName(name: unknown, args: unknown): string | null {
  if (typeof args !== 'object' || args === null) return null
  const path = (args as { path?: unknown }).path
  if (typeof path !== 'string') return null
  const match = /^xd:\/\/(mcp__[A-Za-z0-9_-]+)/.exec(path)
  if (!match) return null
  return normalizeKbMcpToolName(match[1])
}

export function filterKbMcpTools(names: readonly string[]): string[] {
  return names.flatMap((name) => {
    const normalized = normalizeKbMcpToolName(name)
    return normalized ? [normalized] : []
  })
}

/** Apply the chat endpoint's retrieval-success guard and telemetry contract. */
export function evaluateKbRetrieval(
  names: readonly string[],
  answer: string,
  success: boolean,
  retrievalRequired: boolean,
): { success: boolean; code?: 'KB_TOOLS_NOT_READY' | 'KB_NO_RETRIEVAL'; toolCalls: string[]; toolCallCount: number } {
  const toolCalls = filterKbMcpTools(names)
  if (retrievalRequired && !toolCalls.length && success) {
    return {
      success: false,
      code: answer.includes('KB_TOOLS_NOT_READY') ? 'KB_TOOLS_NOT_READY' : 'KB_NO_RETRIEVAL',
      toolCalls,
      toolCallCount: 0,
    }
  }
  return { success, toolCalls, toolCallCount: toolCalls.length }
}

/** Whether a caller's allowlist explicitly asks for a kb-mcp tool. */
export function requestsKbMcp(names: readonly string[]): boolean {
  return names.some(isKbMcpTool)
}
