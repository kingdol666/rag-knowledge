import { defineEventHandler, getRouterParam } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/tasks/:taskId — SOUL 长任务(训练/审批)实时进度。
 * 返回 {status: running|done|error, progress: {round, rounds, questions,
 * memories, docs_processed, ...} | {processed, total, approved, rejected},
 * result, error, elapsed_seconds} — 供前端轮询展示训练/审批进度。
 */
export default defineEventHandler(async (event) => {
  const taskId = getRouterParam(event, 'taskId')
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/tasks/${encodeURIComponent(taskId || '')}`, {
    timeout: 15000,
  })
})
