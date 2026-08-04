import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/persona-docs?soul_kb_id=xxx — 人格定义 4 文档 + RL 进化行统计。 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(query.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/persona-docs`, {
    timeout: 20000,
  })
})
