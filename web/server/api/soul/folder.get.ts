import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/folder?soul_kb_id=xxx — SOUL 文件夹架构浏览器。 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(query.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/folder`, {
    timeout: 30000,
  })
})