import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/cognition-drafts — 生成认知草稿(策略更新建议)。
 * 异步: 立即返回 {task_id}; 轮询 GET /api/soul/tasks/:taskId 看 {created, skipped}。
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/cognition-drafts`, {
    method: 'POST',
    body: { async_mode: body.async_mode !== false },
    timeout: 30000,
  })
})
