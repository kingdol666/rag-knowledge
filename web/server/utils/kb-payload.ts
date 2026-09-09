/**
 * P2-1 (2026-09-09): accept snake_case aliases alongside the canonical
 * camelCase request fields.
 *
 * The MCP tool layer (kb-mcp) uses snake_case (`kb_id`, `doc_path`, ...) while
 * the web HTTP layer historically only accepted camelCase (`kbId`, `docPath`).
 * External HTTP integrators kept hitting `400 kbId is required` when passing
 * the snake_case spelling documented by the MCP tools. This helper copies the
 * snake_case aliases onto the camelCase fields in place; camelCase always wins
 * if both are provided.
 */
const KB_FIELD_ALIASES: Record<string, string> = {
  kb_id: 'kbId',
  doc_path: 'docPath',
  doc_paths: 'docPaths',
  doc_id: 'docId',
  target_kb_id: 'targetKbId',
  parent_id: 'parentId',
  source_path: 'sourcePath',
}

export function coerceKbPayload<T extends Record<string, any>>(body: T): T {
  if (!body || typeof body !== 'object') return body
  for (const [snake, camel] of Object.entries(KB_FIELD_ALIASES)) {
    if (body[snake] !== undefined && body[camel] === undefined) {
      ;(body as any)[camel] = body[snake]
    }
  }
  return body
}
