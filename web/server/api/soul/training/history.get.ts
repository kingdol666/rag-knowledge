import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/training/history?soul_kb_id=&limit= — SQLite 训练历史列表。 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(query.soul_kb_id || ''))
  const limit = query.limit || 30
  return await $fetch(`${backendUrl}/api/v1/soul/training/history?soul_kb_id=${kbId}&limit=${limit}`, {
    timeout: 15000,
  })
})
