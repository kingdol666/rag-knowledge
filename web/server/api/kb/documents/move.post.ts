import { defineEventHandler, readBody, createError } from 'h3'
import { readFileSync, existsSync } from 'node:fs'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { coerceKbPayload } from '~/server/utils/kb-payload'
import { getDynamicBackendUrl, getDynamicAuthConfig, resolveMonorepoPath } from '~/server/utils/dynamic-config'

/**
 * Candidate service tokens, most-likely-first.
 *
 * The `.env` `MCP_AUTH_TOKEN` can be stale (the backend rotates the loop token),
 * and `server.auth.enabled` gating means the backend-auth Nitro plugin may not
 * inject anything at all — so we resolve the token ourselves and try each
 * candidate on 401. `storage/loop-auth.json` holds the live loop token.
 */
function candidateTokens(): string[] {
  const out: string[] = []
  try {
    const t = getDynamicAuthConfig().token
    if (t) out.push(t)
  } catch { /* ignore */ }
  try {
    const p = resolveMonorepoPath('storage/loop-auth.json')
    if (existsSync(p)) {
      const j = JSON.parse(readFileSync(p, 'utf-8'))
      if (j?.token) out.push(String(j.token))
    }
  } catch { /* ignore */ }
  return [...new Set(out.filter(Boolean))]
}

/**
 * POST /api/kb/documents/move
 * Move a document to a different knowledge base (or folder).
 *
 * Body: { docPath, targetKbId }
 *
 * docPath accepts full relative paths (e.g. "kb_name/doc.md") or bare
 * filenames (e.g. "doc.md").  Bare names are tried via the service's
 * getFileByPath against every folder path as prefix.
 *
 * ── Index hygiene (D1 fix, 2026-09-24) ─────────────────────────────────────
 * Moving the file is NOT enough. Left alone, the document's old-path vector
 * chunks survive in the source collection and keep matching: measured symptoms
 * were a doubled chunk_count (18 for a 9-chunk doc), every chunk returned twice
 * (old + new path, identical scores) and a false self-duplicate reported by
 * kb_find_duplicates. So after the move we (1) delete the old-path vectors from
 * the source KB, (2) delete the old graph node, (3) re-index at the new path.
 * Each step is best-effort and reported under `index_hygiene` — a hygiene
 * failure never fails the move itself, but it is never silently swallowed.
 */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}
  coerceKbPayload(body)

  if (!body.docPath?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'docPath is required' })
  }
  if (!body.targetKbId?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'targetKbId is required' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  // Try docPath directly; if that fails and it's a bare filename,
  // scan KB folders as prefixes.
  let file = await treeService.getFileByPath(body.docPath)
  if (!file && !body.docPath.includes('\\') && !body.docPath.includes('/')) {
    const folderNodes = (treeService as any)['metadata']?.folders || []
    for (const fld of folderNodes) {
      if (!fld?.isKnowledgeBase) continue
      const candidate = fld.path.replace(/\\/g, '/') + '/' + body.docPath
      file = await treeService.getFileByPath(candidate)
      if (file) break
    }
  }

  if (!file) {
    throw createError({ statusCode: 404, statusMessage: 'Document not found' })
  }

  const targetKb = await treeService.getKnowledgeBaseById(body.targetKbId)
  if (!targetKb) {
    throw createError({ statusCode: 404, statusMessage: 'Target knowledge base not found' })
  }

  // Capture BEFORE the move — moveFile mutates the file record's path.
  const oldPath = file.path
  const sourceKbUuid =
    (treeService as any).getKnowledgeBaseUuid?.(oldPath) || ''

  const moved = await treeService.moveFile(file.id, targetKb.id)

  // ── index hygiene: clean old-path vectors + graph node, re-index new path ──
  const backend = getDynamicBackendUrl()
  const hygiene: Record<string, unknown> = { sourceKb: sourceKbUuid, oldPath }

  // Attach the service token explicitly (the backend-auth Nitro plugin only
  // injects when `server.auth.enabled` is true, and the .env token may be stale)
  // — try each candidate token on 401.
  const tokens = candidateTokens()

  async function backendCall(url: string, opts: Record<string, any>) {
    let lastErr: any
    const list = tokens.length ? tokens : ['']
    for (const t of list) {
      try {
        return await $fetch(url, {
          ...opts,
          headers: { ...(opts.headers || {}), ...(t ? { Authorization: `Bearer ${t}` } : {}) },
        })
      } catch (e: any) {
        lastErr = e
        if (e?.status !== 401 && e?.statusCode !== 401) throw e
      }
    }
    throw lastErr
  }

  try {
    if (sourceKbUuid) {
      hygiene.vectors = await backendCall(`${backend}/api/v1/search/document`, {
        method: 'DELETE',
        params: { kb_id: sourceKbUuid, doc_path: oldPath },
        timeout: 30000,
      })
    } else {
      hygiene.vectorsSkipped = 'source KB uuid unresolved'
    }
    hygiene.graph = await backendCall(`${backend}/api/v1/graph/document`, {
      method: 'DELETE',
      params: { doc_path: oldPath },
      timeout: 30000,
    })
  } catch (e: any) {
    hygiene.cleanupError = String(e?.message || e).slice(0, 200)
  }

  const newPath = (moved as any)?.path
  if (newPath) {
    hygiene.newPath = newPath
    try {
      hygiene.reindexed = await backendCall(`${backend}/api/v1/search/index-document`, {
        method: 'POST',
        body: {
          kb_id: targetKb.id,
          doc_path: newPath,
          doc_name: (moved as any)?.name || '',
        },
        timeout: 60000,
      })
    } catch (e: any) {
      hygiene.reindexError = String(e?.message || e).slice(0, 200)
    }
  } else {
    hygiene.reindexSkipped = 'new path not returned by move'
  }

  return { success: true, document: moved, index_hygiene: hygiene }
})
