import { defineEventHandler, getQuery } from 'h3'

/**
 * GET /api/graph/related?doc_path=xxx
 * Return documents related to a given document
 */
export default defineEventHandler(async (event): Promise<any> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/document/related`, { query: q })
})
