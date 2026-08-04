import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/learn — 人格训练(单/多文档, 固定轮数 rounds)。
 * async_mode=true: 后端异步执行, 立即返回 {task_id}; 前端轮询
 * GET /api/soul/tasks/:taskId 获取实时进度(轮次/问题/记忆/文档)。
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/learn`, {
    method: 'POST',
    body: {
      doc_paths: body.doc_paths || [],
      limit: body.limit || 6,
      rounds: body.rounds || 1,
      async_mode: body.async_mode !== false,
    },
    timeout: 30000, // 异步模式秒回; 兼容同步模式(旧前端)时由后端 shield 长跑
  })
})
