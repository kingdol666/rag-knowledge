import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * GET /api/meditation/history?kb_id=X&limit=N
 * Proxy to backend GET /api/v1/meditation/history?kb_id=X&limit=N
 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const kbId = (query.kb_id as string || '').trim()
  const limit = Number(query.limit) || 20

  const backendUrl = getDynamicBackendUrl()
  try {
    const url = `${backendUrl}/api/v1/meditation/history?kb_id=${encodeURIComponent(kbId)}&limit=${limit}`
    return await $fetch(url)
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})