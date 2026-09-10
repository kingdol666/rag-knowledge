import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * GET /api/meditation/models?harness=<id>
 * Proxy to backend GET /api/v1/meditation/models
 * 按引擎返回模型目录（omp 动态发现，其余静态目录）。
 */
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const harness = String(query.harness || 'omp')
  const backendUrl = getDynamicBackendUrl()
  try {
    return await $fetch(`${backendUrl}/api/v1/meditation/models`, {
      params: { harness },
    })
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
