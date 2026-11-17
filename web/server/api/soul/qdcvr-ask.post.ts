import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * POST /api/soul/qdcvr-ask — deprecated alias for /api/soul/hmrs-ask
 *
 * The system was renamed from QDCVR to HMRS; this route is kept so existing
 * clients keep working. New callers should use /api/soul/hmrs-ask.
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const res = await fetch(`${backendUrl}/api/v1/soul/hmrs-ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: body.query,
      soul_kb_id: body.soul_kb_id || '',
      task_type: body.task_type || '',
      task_goal: body.task_goal || '',
      top_k: body.top_k || 5,
    }),
    signal: AbortSignal.timeout(300_000),
  })
  const text = await res.text()
  return JSON.parse(text)
})
