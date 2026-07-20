import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

/**
 * DELETE /api/kb/documents/delete
 *
 * Deletes a document from the file system and cleans up indexes.
 * Removes file from disk + .tree-fs.json + .knowledge-base.yml.
 * Automatically cleans up vector chunks and graph nodes (fire-and-forget).
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

  // deleteFile handles: disk delete + .tree-fs.json + .knowledge-base.yml
  const result = await treeService.deleteFile(file.id)

  return { ...result }
})
