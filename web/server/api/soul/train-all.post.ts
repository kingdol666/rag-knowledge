import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/train-all — 全库自举(空 soul_kb_id = 全部人格), 固定轮数 rounds。
 * async_mode=true(默认): 后端异步执行, 立即返回 {task_id}; 前端轮询
 * GET /api/soul/tasks/:taskId 获取实时进度(逐 SOUL 轮次)。
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  const path = kbId ? `/api/v1/soul/${kbId}/learn-all` : '/api/v1/soul/learn-all'
  return await $fetch(`${backendUrl}${path}`, {
    method: 'POST',
    body: {
      max_docs: body.max_docs || 20,
      dry_run: !!body.dry_run,
      rounds: body.rounds || 1,
      async_mode: body.async_mode !== false,
    },
    timeout: 30000,
  })
})
