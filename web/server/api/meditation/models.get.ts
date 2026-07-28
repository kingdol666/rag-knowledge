import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * GET /api/meditation/models
 * Proxy to backend GET /api/v1/meditation/models
 */
export default defineEventHandler(async () => {
  const backendUrl = getDynamicBackendUrl()
  try {
    return await $fetch(`${backendUrl}/api/v1/meditation/models`)
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
