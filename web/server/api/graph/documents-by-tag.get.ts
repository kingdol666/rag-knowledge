import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * GET /api/graph/documents-by-tag?tag_name=xxx
 * Find documents by tag
 */
export default defineEventHandler(async (event): Promise<unknown> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/graph/documents-by-tag`, { query: q })
})
