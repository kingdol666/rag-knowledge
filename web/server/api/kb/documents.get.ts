import { defineEventHandler, getQuery, createError } from 'h3'
import { getKbSearchService } from '~/server/services/kb-search-service'
import { getTreeFileSystemService } from '~/server/utils/tree-service'

/** GET /api/kb/documents?kb_id=xxx — full document list of one KB. */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const kbId = (query.kb_id as string || '').trim()

  if (!kbId) {
    throw createError({ statusCode: 400, statusMessage: 'kb_id is required' })
  }

  const service = getKbSearchService()
  // Resolve UUID-based kbId to folder path if needed (using singleton service)
  const treeService = await getTreeFileSystemService()
  await treeService.reloadMetadata()
  const folder = await treeService.getFolderById(kbId)
  const resolvedKbId = folder?.path || kbId
  const documents = await service.getKbDocuments(resolvedKbId)
  return { success: true, kbId: resolvedKbId, count: documents.length, documents }
})
