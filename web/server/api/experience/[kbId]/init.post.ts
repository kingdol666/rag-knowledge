import { defineEventHandler, getRouterParam } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  if (!kbId) {
    return { success: false, error: 'kbId is required' }
  }
  const backendUrl = getDynamicBackendUrl()
  try {
    const url = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}/init`
    return await $fetch(url, { method: 'POST' })
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
