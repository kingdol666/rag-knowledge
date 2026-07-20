import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl, invalidateConfigCache } from '~/server/utils/dynamic-config'

/** POST /api/config/reload — proxy to backend POST /api/v1/config/reload, then invalidate frontend cache */
export default defineEventHandler(async () => {
  const backendUrl = getDynamicBackendUrl()
  const result = await $fetch(`${backendUrl}/api/v1/config/reload`, {
    method: 'POST',
  })

  // Invalidate the frontend config cache
  invalidateConfigCache()

  return result
})
