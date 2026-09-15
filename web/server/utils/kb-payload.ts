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
  parent_kb_id: 'parentKbId',
  source_path: 'sourcePath',
  top_k: 'topK',
  max_chars: 'maxChars',
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

/**
 * Same alias contract as `coerceKbPayload`, but for **query strings**, and
 * bidirectional.
 *
 * The read endpoints historically read only the snake_case spellings
 * (`?kb_id=`), while every other layer documents camelCase as canonical — and
 * `meditation.get.ts` read only camelCase. An external integrator following the
 * documented contract therefore got a bare
 * `400 doc_id, path, or kb_id+doc_path is required` from `GET /api/kb/document`.
 *
 * Normalising here makes both spellings work on every read endpoint, so the
 * documented contract and the MCP layer's snake_case names both hold.
 */
export function coerceKbQuery<T extends Record<string, any>>(query: T): T {
  if (!query || typeof query !== 'object') return query
  for (const [snake, camel] of Object.entries(KB_FIELD_ALIASES)) {
    const snakeVal = (query as any)[snake]
    const camelVal = (query as any)[camel]
    if (camelVal !== undefined && snakeVal === undefined) (query as any)[snake] = camelVal
    if (snakeVal !== undefined && camelVal === undefined) (query as any)[camel] = snakeVal
  }
  return query
}
