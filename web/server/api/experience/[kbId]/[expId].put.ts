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
    const body = await readBody(event)
    return await $fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
