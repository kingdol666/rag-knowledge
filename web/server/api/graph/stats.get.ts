import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async () => {
  const backendUrl = getDynamicBackendUrl()
  const res = await $fetch<{ success?: boolean; stats?: Record<string, unknown> }>(`${backendUrl}/api/v1/graph/stats`)
  // Backend returns { success, stats: {...} } — return as-is so frontend can extract .stats
  return res
})
