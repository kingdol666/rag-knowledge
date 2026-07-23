import { defineEventHandler, getRouterParam, readBody, setResponseStatus } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/**
 * POST /api/experience/:kbId/:expId/review
 * Proxy to backend experience review endpoint.
 *
 * Body: forwarded verbatim as JSON to the backend.
 *
 * Return shape ({ success, error | data }) is kept consistent with the
 * other experience/* routes so the frontend can branch on `success`.
 */
export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const expId = getRouterParam(event, 'expId')
  if (!kbId || !expId) {
    setResponseStatus(event, 400)
    return { success: false, error: 'kbId and expId are required' }
  }

  const backendUrl = getDynamicBackendUrl()

  let body: unknown
  try {
    body = await readBody(event)
  } catch (e) {
    setResponseStatus(event, 400)
    return { success: false, error: `Invalid request body: ${e instanceof Error ? e.message : String(e)}` }
  }
  if (body === undefined || body === null) {
    setResponseStatus(event, 400)
    return { success: false, error: 'Request body is required' }
  }

  const url = `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}/${encodeURIComponent(expId)}/review`

  try {
    return await $fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
  } catch (e) {
    // ofetch throws a FetchError on non-2xx (carrying statusCode + parsed data)
    // and on transport-level failures; distinguish by statusCode presence.
    const fetchErr = e as { statusCode?: number; data?: unknown }
    const httpStatus = typeof fetchErr.statusCode === 'number' && fetchErr.statusCode >= 400
      ? fetchErr.statusCode
      : undefined
    if (httpStatus !== undefined) {
      setResponseStatus(event, httpStatus)
      let detail = ''
      const data = fetchErr.data
      if (data && typeof data === 'object') {
        const obj = data as Record<string, unknown>
        if ('error' in obj) detail = String(obj.error)
      } else if (typeof data === 'string' && data.length > 0) {
        detail = data
      }
      if (!detail) detail = e instanceof Error ? e.message : String(e)
      return { success: false, error: detail?.trim() || `Backend returned ${httpStatus}` }
    }
    // Transport-level failure (network unreachable, DNS, etc.)
    setResponseStatus(event, 502)
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }
})
