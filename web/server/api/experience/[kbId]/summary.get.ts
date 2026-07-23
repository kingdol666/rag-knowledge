import { defineEventHandler, getRouterParam, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  if (!kbId) {
    return { success: false, error: 'kbId is required' }
  }
  const backendUrl = getDynamicBackendUrl()
  try {
    const query = getQuery(event)
    const qs = new URLSearchParams(query as Record<string, string>).toString()
    const url = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}/summary${qs ? '?' + qs : ''}`
    return await $fetch(url)
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
