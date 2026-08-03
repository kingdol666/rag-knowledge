import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/router — 路由决策预览(可审计) */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/router`, { method: 'POST', body })
})
