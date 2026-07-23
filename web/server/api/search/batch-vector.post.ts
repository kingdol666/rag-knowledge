import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * POST /api/search/batch-vector
 * Batch vector similarity query — proxy to backend /api/v1/search/batch-vector
 */
export default defineEventHandler(async (event): Promise<unknown> => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/search/batch-vector`, {
    method: 'POST',
    body,
  })
})
