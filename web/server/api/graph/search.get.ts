import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (event): Promise<unknown> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = getDynamicBackendUrl()

  // Determine search type: documents (default), kbs, or tags
  const searchType = q.type || 'documents'
  delete q.type  // Don't forward type to backend

  // Map 'keyword' or 'q' to backend's expected 'keyword' parameter
  if (q.keyword) {
    // already correct
  } else if (q.q) {
    q.keyword = q.q
    delete q.q
  }

  const validTypes = ['documents', 'kbs', 'tags']
  const endpoint = validTypes.includes(searchType)
    ? `/api/v1/graph/search/${searchType}`
    : '/api/v1/graph/search/documents'

  return await $fetch(`${backendUrl}${endpoint}`, { query: q })
})
