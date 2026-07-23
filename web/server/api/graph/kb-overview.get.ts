import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * GET /api/graph/kb-overview?kb_id=xxx
 * KB-level graph overview: document stats + tag distribution + related KBs + Top documents
 */
export default defineEventHandler(async (event): Promise<unknown> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/graph/kb-overview`, { query: q })
})
