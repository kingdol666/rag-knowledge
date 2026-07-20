import { defineEventHandler, getQuery } from 'h3'

/**
 * GET /api/graph/kb-overview?kb_id=xxx
 * KB-level graph overview: document stats + tag distribution + related KBs + Top documents
 */
export default defineEventHandler(async (event): Promise<any> => {
  const q = getQuery(event) as Record<string, string>
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/graph/kb-overview`, { query: q })
})
