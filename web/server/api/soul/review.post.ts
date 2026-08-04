import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/review — 记忆草稿审批(list/approve/reject)
 * 批量 approve/reject(draft_ids 数组)默认异步: 后端提交 soul_task_runner,
 * 立即返回 {task_id}; 前端轮询 GET /api/soul/tasks/:taskId 看 {processed,total}。
 */
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
      draft_ids: Array.isArray(body.draft_ids) ? body.draft_ids : [],
      force: !!body.force,
      async_mode: body.async_mode !== false,
    },
    timeout: 30000,
  })
})
