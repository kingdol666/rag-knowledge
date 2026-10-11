import { defineEventHandler, readBody, createError } from 'h3'
import { coerceKbPayload } from '~/server/utils/kb-payload'
import { summarizeKbAutomation } from '~/server/utils/kb-automation'

/**
 * POST /api/kb/automation/summarize
 *
 * 手动触发一次经验总结更新（不依赖开关状态）。body: { kbId }。
 * 代理后端 POST /api/v1/automation/{kb_id}/summarize。
 */
export default defineEventHandler(async (event) => {
  const body = (await readBody(event)) || {}
  coerceKbPayload(body)

  if (!body.kbId?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'kbId is required' })
  }
  try {
    return await summarizeKbAutomation(body.kbId.trim())
  } catch (error: any) {
    throw createError({
      statusCode: error?.statusCode || error?.response?.status || 502,
      statusMessage: error?.message || 'Failed to trigger summary',
    })
  }
})
