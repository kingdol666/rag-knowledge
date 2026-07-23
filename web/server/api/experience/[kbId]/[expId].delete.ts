import { defineEventHandler, getRouterParam, readBody, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const expId = getRouterParam(event, 'expId')
  if (!kbId || !expId) {
    return { success: false, error: 'kbId and expId are required' }
  }
  const backendUrl = getDynamicBackendUrl()
  try {
    const base = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}`
    const url = true ? `${base}/${encodeURIComponent(expId)}` : base

    return await $fetch(url, { method: 'DELETE' })
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
