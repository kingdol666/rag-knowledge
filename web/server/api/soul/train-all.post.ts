import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/train-all — 全库自举(空 soul_kb_id = 全部人格) */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  const path = kbId ? `/api/v1/soul/${kbId}/learn-all` : '/api/v1/soul/learn-all'
  return await $fetch(`${backendUrl}${path}`, {
    method: 'POST',
    body: { max_docs: body.max_docs || 20, dry_run: !!body.dry_run },
    timeout: 1800000,
  })
})
