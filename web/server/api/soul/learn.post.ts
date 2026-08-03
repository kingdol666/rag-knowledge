import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/learn — 人格训练(单/多文档,同步长任务) */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/learn`, {
    method: 'POST',
    body: { doc_paths: body.doc_paths || [], limit: body.limit || 6 },
    timeout: 1800000, // 训练可能 10-30 分钟
  })
})
