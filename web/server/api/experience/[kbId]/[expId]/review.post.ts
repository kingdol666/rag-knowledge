import { defineEventHandler, getRouterParam, readBody, setResponseStatus } from 'h3'
import { getServerConfig } from '~/utils/paths.mjs'

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

  const config = getServerConfig()
  const backendUrl = process.env.BACKEND_URL || config.backend_url || 'http://localhost:8765'

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

  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
  } catch (e) {
    setResponseStatus(event, 502)
    return { success: false, error: `Backend unreachable: ${e instanceof Error ? e.message : String(e)}` }
  }

  // Forward non-2xx as a structured error instead of passing it off as success.
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    let detail = text
    try {
      const parsed = text ? JSON.parse(text) : null
      if (parsed && typeof parsed === 'object' && 'error' in parsed) {
        detail = String((parsed as Record<string, unknown>).error)
      }
    } catch {
      // keep raw text
    }
    setResponseStatus(event, response.status)
    return {
      success: false,
      error: detail?.trim() || `Backend returned ${response.status} ${response.statusText}`
    }
  }

  try {
    return await response.json()
  } catch (e) {
    setResponseStatus(event, 502)
    return { success: false, error: `Backend returned non-JSON response: ${e instanceof Error ? e.message : String(e)}` }
  }
})
