import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/config — proxy to backend GET /api/v1/config */
export default defineEventHandler(async (): Promise<any> => {
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/config`)
})
