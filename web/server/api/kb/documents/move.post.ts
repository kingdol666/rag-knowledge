import { defineEventHandler, readBody, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

/**
 * POST /api/kb/documents/move
 * Move a document to a different knowledge base (or folder).
 *
 * Body: { docPath, targetKbId }
 *
 * docPath accepts full relative paths (e.g. "kb_name/doc.md") or bare
 * filenames (e.g. "doc.md").  Bare names are tried via the service's
 * getFileByPath against every folder path as prefix.
 */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}

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

  const moved = await treeService.moveFile(file.id, targetKb.id)
  return { success: true, document: moved }
})