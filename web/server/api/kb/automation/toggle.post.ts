import { defineEventHandler, readBody, createError } from 'h3'
import { coerceKbPayload } from '~/server/utils/kb-payload'
import { toggleKbAutomation } from '~/server/utils/kb-automation'

/**
 * POST /api/kb/automation/toggle
 *
 * 开启/关闭知识库自动经验总结。body: { kbId, enabled }。
 * 代理后端 POST /api/v1/automation/{kb_id}/toggle。
 */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}
  coerceKbPayload(body)

  if (!body.kbId?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'kbId is required' })
  }
  if (typeof body.enabled !== 'boolean') {
    throw createError({ statusCode: 400, statusMessage: 'enabled (boolean) is required' })
  }
  try {
    return await toggleKbAutomation(body.kbId.trim(), body.enabled)
  } catch (error: any) {
    throw createError({
      statusCode: error?.statusCode || error?.response?.status || 502,
      statusMessage: error?.message || 'Failed to toggle automation',
    })
  }
})
