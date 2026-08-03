import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/rollback — 回滚到检查点 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/rollback`, {
    method: 'POST',
    body: { checkpoint_id: body.checkpoint_id || '' },
  })
})
