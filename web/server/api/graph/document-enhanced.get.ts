import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * GET /api/graph/document/enhanced?doc_path=xxx&limit=20
 * Enhanced document relation query: show truly related documents grouped by connection type
 */
export default defineEventHandler(async (event): Promise<unknown> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/graph/document/enhanced`, { query: q })
})