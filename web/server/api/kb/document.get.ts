import { defineEventHandler, getQuery, createError } from 'h3'
import { getTreeFileSystemService } from '~/server/utils/tree-service'
import { getKbSearchService } from '~/server/services/kb-search-service'

/**
 * GET /api/kb/document
 *
 * **Atomic operation**: Read a document's markdown body (paginated).
 *
 * Accepts one of:
 * - doc_id: document UUID (from .tree-fs.json / .knowledge-base.yml)
 * - path: full relative path (e.g. "kb_name/doc.md")
 * - kb_id + doc_path: KB identifier + document path (bare filename or relative)
 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  let path = (query.path as string || '').trim()
  const kbId = (query.kb_id as string || '').trim()
  const docPath = (query.doc_path as string || '').trim()
  const docId = (query.doc_id as string || '').trim()
  const offset = Number(query.offset) || 0
  const limit = Number(query.limit) || 200
  const maxChars = Number(query.max_chars) || 20000

  // doc_id priority: resolve file path via .tree-fs.json
  if (docId) {
    const treeService = await getTreeFileSystemService()
    await treeService.reloadMetadata()
    const file = await treeService.getFileById(docId)
    if (file) {
      path = file.path
    } else {
      // Fallback: try .knowledge-base.yml
      const { getKnowledgeBaseYamlService } = await import('~/server/services/knowledge-base-yaml-service')
      const { getTreeStorageAbsolutePath } = await import('~/server/utils/runtime-paths')
      const yamlService = getKnowledgeBaseYamlService(getTreeStorageAbsolutePath())
      const found = await yamlService.findDocumentById(docId)
      if (found) {
        path = found.doc.path
      } else {
        throw createError({ statusCode: 404, statusMessage: `Document not found by id: ${docId}` })
      }
    }
  } else if (!path && kbId && docPath) {
    const treeService = await getTreeFileSystemService()
    await treeService.reloadMetadata()
    path = await treeService.resolveDocPath(kbId, docPath) || ''
  }

  if (!path) {
    throw createError({ statusCode: 400, statusMessage: 'doc_id, path, or kb_id+doc_path is required' })
  }

  const service = getKbSearchService()
  try {
    const result = await service.readDocument(path, offset, limit, maxChars)
    return { success: true, path, ...result }
  } catch (error: any) {
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.message || 'Failed to read document',
    })
  }
})
