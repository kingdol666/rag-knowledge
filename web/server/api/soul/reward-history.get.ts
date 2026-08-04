import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/reward-history?soul_kb_id=xxx — RL 进化曲线(逐轮 reward/四维分)。 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(query.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/reward-history?limit=${query.limit || 50}`, {
    timeout: 15000,
  })
})
