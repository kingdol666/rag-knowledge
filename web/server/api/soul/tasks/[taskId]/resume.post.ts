import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/tasks/:taskId/resume — 继续已暂停任务。 */
export default defineEventHandler(async (event) => {
  const taskId = getRouterParam(event, 'taskId')
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/tasks/${encodeURIComponent(taskId || '')}/resume`, {
    method: 'POST', body: {}, timeout: 15000,
  })
})
