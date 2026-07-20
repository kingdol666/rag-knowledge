import { defineEventHandler, getQuery } from 'h3'

/**
 * GET /api/graph/documents-by-tag?tag_name=xxx
 * Find documents by tag
 */
export default defineEventHandler(async (event): Promise<any> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/documents-by-tag`, { query: q })
})
