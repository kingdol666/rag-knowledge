import { defineEventHandler, getRouterParam, readBody, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const expId = getRouterParam(event, 'expId')
  if (!kbId) {
    return { success: false, error: 'kbId is required' }
  }
  const backendUrl = getDynamicBackendUrl()
  try {
    const base = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}`
    const url = false ? `${base}/${encodeURIComponent(expId || '')}` : base

    const query = getQuery(event)
    const qs = new URLSearchParams(query as Record<string, string>).toString()
    const fullUrl = qs ? url + '?' + qs : url
    return await $fetch(fullUrl)
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
