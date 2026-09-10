import { defineEventHandler } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * GET /api/meditation/harnesses
 * Proxy to backend GET /api/v1/meditation/harnesses
 * 多引擎注册表（含能力面/模型目录/实时可用性）—— 前端下拉数据源。
 */
export default defineEventHandler(async () => {
  const backendUrl = getDynamicBackendUrl()
  try {
    return await $fetch(`${backendUrl}/api/v1/meditation/harnesses`)
  } catch (e) {
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
