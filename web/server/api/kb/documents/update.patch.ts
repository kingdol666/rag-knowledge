import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { coerceKbPayload } from '~/server/utils/kb-payload'

/**
 * PATCH /api/kb/documents/update
 * Update a document's metadata (name, description, metadata).
 *
 * Body: { kbId, docPath, name?, description?, metadata? }
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

  const updated = await treeService.updateFile(file.id, {
    name: body.name?.trim() || undefined,
    description: body.description?.trim() || undefined,
    metadata: body.metadata || undefined,
  })

  return { success: true, document: updated }
})