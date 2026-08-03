import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/status?soul_kb_id=xxx&summary_window=30 — 人格学习指标 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(query.soul_kb_id || ''))
  const window = query.summary_window || 30
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/status?summary_window=${window}`)
})
