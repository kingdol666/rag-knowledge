import { defineEventHandler, getRouterParam } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/tasks/:taskId/pause — 暂停运行中的训练/审批任务(轮次边界生效)。 */
export default defineEventHandler(async (event) => {
  const taskId = getRouterParam(event, 'taskId')
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/tasks/${encodeURIComponent(taskId || '')}/pause`, {
    method: 'POST', body: {}, timeout: 15000,
  })
})
