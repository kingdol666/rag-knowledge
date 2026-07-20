import { defineEventHandler, getQuery, createError } from 'h3'
import { getKbSearchService } from '~/server/services/kb-search-service'

/** GET /api/kb/search?query=xxx&top_k=10 — cross-KB keyword search. */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const q = (query.query as string || '').trim()
  const topK = Number(query.top_k) || 10

  if (!q) {
    throw createError({ statusCode: 400, statusMessage: 'query is required' })
  }

  const service = getKbSearchService()
  const hits = await service.searchAll(q, topK)
  return { success: true, query: q, count: hits.length, hits }
})
