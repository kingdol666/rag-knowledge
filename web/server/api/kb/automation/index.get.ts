import { defineEventHandler, getQuery, createError } from 'h3'
import { coerceKbQuery } from '~/server/utils/kb-payload'
import { fetchKbAutomationStatus } from '~/server/utils/kb-automation'

/**
 * GET /api/kb/automation?kb_id=xxx（兼容 kbId）
 *
 * 查询知识库自动经验总结状态（开关/计数器/下次触发点/历史）。
 * 代理后端 GET /api/v1/automation/{kb_id}，前端无需接触后端地址与令牌。
 */
export default defineEventHandler(async (event) => {
  const query = coerceKbQuery(getQuery(event))
  const kbId = (query.kb_id as string || '').trim()
  if (!kbId) {
    throw createError({ statusCode: 400, statusMessage: 'kb_id is required' })
  }
  try {
    return await fetchKbAutomationStatus(kbId)
  } catch (error: any) {
    throw createError({
      statusCode: error?.statusCode || error?.response?.status || 502,
      statusMessage: error?.message || 'Failed to fetch automation status',
    })
  }
})
