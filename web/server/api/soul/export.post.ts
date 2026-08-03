import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/export — 训练数据导出 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/export`, {
    method: 'POST',
    body: { min_score: body.min_score ?? 4.0, limit: body.limit ?? 1000 },
  })
})
