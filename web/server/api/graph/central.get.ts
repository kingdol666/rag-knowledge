import { defineEventHandler, getQuery } from 'h3'

/**
 * GET /api/graph/central?kb_id=xxx&top_n=20
 * Documents with highest centrality within a KB (by RELATED_TO degree centrality)
 */
export default defineEventHandler(async (event): Promise<any> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/central-documents`, { query: q })
})
