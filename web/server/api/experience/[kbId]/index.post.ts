import { defineEventHandler, getRouterParam, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  if (!kbId) {
    return { success: false, error: 'kbId is required' }
  }
  const backendUrl = getDynamicBackendUrl()
  try {
    const body = await readBody(event)
    const url = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}`
    return await $fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
