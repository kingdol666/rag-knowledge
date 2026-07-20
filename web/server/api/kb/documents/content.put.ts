import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

/**
 * PUT /api/kb/documents/content
 *
 * **Atomic operation**: ONLY overwrites a document's on-disk content and
 * syncs metadata (.tree-fs.json file size + .knowledge-base.yml).
 *
 * Does NOT index (use POST /api/v1/search/index-document separately).
 */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}

  if (!body.kbId?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'kbId is required' })
  }
  if (!body.docPath?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'docPath is required' })
  }
  if (body.content == null) {
    throw createError({ statusCode: 400, statusMessage: 'content is required' })
  }

  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()

  const resolvedPath = await treeService.resolveDocPath(body.kbId, body.docPath)
  if (!resolvedPath) {
    throw createError({ statusCode: 404, statusMessage: "Document not found" })
  }

  // updateFileContentByPath handles: disk write + .tree-fs.json + .knowledge-base.yml
  const updated = await treeService.updateFileContentByPath(resolvedPath, String(body.content))
  if (!updated) {
    throw createError({ statusCode: 404, statusMessage: 'Document not found' })
  }

  return { success: true, document: updated }
})
