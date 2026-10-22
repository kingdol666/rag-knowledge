import { defineEventHandler, readBody, createError } from 'h3'
import { readFileSync, existsSync } from 'node:fs'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { coerceKbPayload } from '~/server/utils/kb-payload'
import { getDynamicBackendUrl, getDynamicAuthConfig, resolveMonorepoPath } from '~/server/utils/dynamic-config'

/**
 * Candidate service tokens, most-likely-first (same contract as move.post.ts):
 * the `.env` token may be stale and the backend-auth Nitro plugin may not
 * inject anything, so resolve candidates ourselves and retry on 401.
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
 * PATCH /api/kb/documents/update
 * Update a document's metadata (name, description, metadata).
 *
 * Body: { kbId, docPath, name?, description?, metadata? }
 *
 * ── Rename index hygiene (run-4 fix, 2026-10-21) ───────────────────────────
 * A rename that changes the path is invisible to the vector store: the old
 * chunks keep their old doc_path labels, so retrieval provenance cites a path
 * that no longer resolves (measured live: rename_probe_before2 — after rename,
 * old-label hits 1, new-label hits 0, until the next force reindex). Mirror
 * the move endpoint's hygiene: delete old-path vectors + graph node, then
 * re-index at the new path. Gated on an actual path change so description /
 * metadata-only updates stay zero-cost. Best-effort and reported under
 * `index_hygiene`; a hygiene failure never fails the update itself.
 */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}
  coerceKbPayload(body)

  if (!body.kbId?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'kbId is required' })
  }
  if (!body.docPath?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'docPath is required' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()


  const resolvedPath = await treeService.resolveDocPath(body.kbId, body.docPath)
  if (!resolvedPath) {
    throw createError({ statusCode: 404, statusMessage: "Document not found" })
  }
  // reload-on-miss: another dev worker may have created/renamed this file
  // after our last index load (stale in-memory metadata would 404 here).
  const file = await treeService.getFileByPathWithReload(resolvedPath)
  if (!file) {
    throw createError({ statusCode: 404, statusMessage: 'Document not found' })
  }

  // Capture BEFORE the update — updateFile mutates the file record's path on rename.
  const oldPath = file.path
  const sourceKbUuid =
    (treeService as any).getKnowledgeBaseUuid?.(oldPath) || ''

  const updated = await treeService.updateFile(file.id, {
    name: body.name?.trim() || undefined,
    description: body.description?.trim() || undefined,
    metadata: body.metadata || undefined,
  })

  // ── rename hygiene: clean old-path vectors + graph node, re-index new path ──
  const newPath = (updated as any)?.path
  const hygiene: Record<string, unknown> = {}

  if (newPath && newPath !== oldPath) {
    hygiene.oldPath = oldPath
    hygiene.newPath = newPath

    const backend = getDynamicBackendUrl()
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
        hygiene.vectorsSkipped = 'KB uuid unresolved from old path'
      }
      hygiene.graph = await backendCall(`${backend}/api/v1/graph/document`, {
        method: 'DELETE',
        params: { doc_path: oldPath },
        timeout: 30000,
      })
    } catch (e: any) {
      hygiene.cleanupError = String(e?.message || e).slice(0, 200)
    }

    try {
      hygiene.reindexed = await backendCall(`${backend}/api/v1/search/index-document`, {
        method: 'POST',
        body: {
          kb_id: sourceKbUuid || body.kbId,
          doc_path: newPath,
          doc_name: (updated as any)?.name || '',
        },
        timeout: 60000,
      })
    } catch (e: any) {
      hygiene.reindexError = String(e?.message || e).slice(0, 200)
    }
  }

  const response: Record<string, unknown> = { success: true, document: updated }
  if (Object.keys(hygiene).length) response.index_hygiene = hygiene
  return response
})
