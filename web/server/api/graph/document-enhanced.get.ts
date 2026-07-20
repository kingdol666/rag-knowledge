import { defineEventHandler, getQuery } from 'h3'

/**
 * GET /api/graph/document/enhanced?doc_path=xxx&limit=20
 * Enhanced document relation query: show truly related documents grouped by connection type
 */
export default defineEventHandler(async (event): Promise<any> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/document/enhanced`, { query: q })
})