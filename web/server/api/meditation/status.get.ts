import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * GET /api/meditation/status
 * Proxy to backend GET /api/v1/experience/meditation/status
 */
export default defineEventHandler(async () => {
  const backendUrl = getDynamicBackendUrl()
  try {
    const url = `${backendUrl}/api/v1/meditation/status`
    return await $fetch(url)
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})