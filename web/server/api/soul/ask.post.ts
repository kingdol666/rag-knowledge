import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/ask — 人格问答(显式或自动路由);合成+PAS 可达 3 分钟 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/ask`, { method: 'POST', body, timeout: 300000 })
})
