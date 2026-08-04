import { defineEventHandler, getRouterParam } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** GET /api/soul/training/runs/:runId — 单次训练运行详情 + 阶段事件流。 */
export default defineEventHandler(async (event) => {
  const runId = getRouterParam(event, 'runId')
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/training/runs/${encodeURIComponent(runId || '')}`, {
    timeout: 15000,
  })
})
