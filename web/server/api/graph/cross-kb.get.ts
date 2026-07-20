import { defineEventHandler, getQuery } from 'h3'

/**
 * GET /api/graph/cross-kb?limit=50
 * Cross-KB bridge documents: documents connected to different KBs via shared_tag / vector_similar
 */
export default defineEventHandler(async (event): Promise<any> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/cross-kb-documents`, { query: q })
})
