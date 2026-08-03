import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/init — 创建人格 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  // 编排层在 kb-mcp;soul_init 是 MCP 工具。后端 /init 仅为兼容入口。
  return await $fetch(`${backendUrl}/api/v1/soul/init`, { method: 'POST', body })
})
