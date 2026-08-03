import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * POST /api/soul/qdcvr-ask — QDCVR + SOUL 组合问答(一键)
 *
 * 先按 knowledgebase-search skill 流程检索(两阶段+硬阈值+文档去重+短内容过滤),
 * 再把检索证据注入 SOUL 人格做增强回答。返回 answer + citations + pas_score + route_*。
 * Body: { query, soul_kb_id?, task_type?, task_goal?, top_k? }
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/soul/qdcvr-ask`, {
    method: 'POST',
    body: {
      query: body.query,
      soul_kb_id: body.soul_kb_id || '',
      task_type: body.task_type || '',
      task_goal: body.task_goal || '',
      top_k: body.top_k || 5,
    },
    timeout: 300000,
  })
})
