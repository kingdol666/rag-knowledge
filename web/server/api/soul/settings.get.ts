import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/settings — SOUL 系统级设置(默认 harness/model + harness 可用性) */
export default defineEventHandler(async (event) => {
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/settings`, { timeout: 15000 })
})
