import { defineEventHandler, readBody } from 'h3'

/**
 * POST /api/search/batch-vector
 * Batch vector similarity query — proxy to backend /api/v1/search/batch-vector
 */
export default defineEventHandler(async (event): Promise<any> => {
  const body = await readBody(event)
  const backendUrl = useRuntimeConfig().pdfParserApiUrl as string
  return await $fetch(`${backendUrl}/api/v1/search/batch-vector`, {
    method: 'POST',
    body,
  })
})
