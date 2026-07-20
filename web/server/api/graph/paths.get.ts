import { defineEventHandler, getQuery } from 'h3'

/**
 * GET /api/graph/paths?doc_a=xxx&doc_b=xxx&max_depth=4
 * Shortest path between two documents
 */
export default defineEventHandler(async (event): Promise<any> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/document-paths`, { query: q })
})
