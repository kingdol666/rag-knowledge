import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * GET /api/graph/related?doc_path=xxx
 * Return documents related to a given document
 */
export default defineEventHandler(async (event): Promise<unknown> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/graph/document/related`, { query: q })
})
