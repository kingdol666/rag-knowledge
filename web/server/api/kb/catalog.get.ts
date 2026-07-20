import { defineEventHandler, getQuery } from 'h3'
import { getKbSearchService } from '~/server/services/kb-search-service'

/**
 * GET /api/kb/catalog — list knowledge bases.
 * Without `kb_id`: returns top-level KBs only (parentId === null).
 * With `kb_id`: returns sub-KBs under that parent.
 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const parentKbId = (query.kb_id as string || '').trim()

  const service = getKbSearchService()
  const catalog = parentKbId
    ? await service.getSubCatalog(parentKbId)
    : await service.getTopLevelCatalog()

  return { success: true, count: catalog.length, knowledgeBases: catalog }
})
