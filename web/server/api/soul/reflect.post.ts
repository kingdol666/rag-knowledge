import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/reflect — 人格反思(漂移报告) */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/reflect`, {
    method: 'POST',
    timeout: 600000,
  })
})
