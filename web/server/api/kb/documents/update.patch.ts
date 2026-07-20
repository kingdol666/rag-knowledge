import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

/**
 * PATCH /api/kb/documents/update
 * Update a document's metadata (name, description, metadata).
 *
 * Body: { kbId, docPath, name?, description?, metadata? }
 */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}

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
  const file = await treeService.getFileByPath(resolvedPath)
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