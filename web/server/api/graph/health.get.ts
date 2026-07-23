import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (): Promise<unknown> => {
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/graph/health`)
})
