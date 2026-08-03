import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/review — 记忆草稿审批(list/approve/reject) */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/review-drafts`, {
    method: 'POST',
    body: {
      action: body.action || 'list',
      type: body.draft_type || 'memory',
      draft_id: body.draft_id || '',
      force: !!body.force,
    },
  })
})
