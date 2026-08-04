import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/tasks — SOUL 长任务列表(训练/审批), 供全局监控。 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/tasks${query.status ? `?status=${query.status}` : ''}`, {
    timeout: 15000,
  })
})
