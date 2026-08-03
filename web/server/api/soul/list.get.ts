import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/list — 全部人格(排除模板) */
export default defineEventHandler(async (event) => {
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/list`)
})
